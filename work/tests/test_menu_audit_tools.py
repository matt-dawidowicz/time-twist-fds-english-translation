"""Fixture-free contracts for fixed-menu audit and reporting helpers."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import (
    audit_fixed_menu_labels,
    audit_full_word_menu_targets,
    report_full_word_menu_candidate,
)


class FixedMenuAuditToolTests(unittest.TestCase):
    """Keep the source target audit compatible with the candidate audit."""

    def test_target_loader_accepts_canonical_and_legacy_label_columns(
        self,
    ) -> None:
        """Load target CSVs written by either public audit field name."""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "targets.csv"
            path.write_text(
                "bank,index,target_label,full_word_target\n"
                "TT1B,0,Legacy,\n"
                "TT1B,1,,Canonical\n",
                encoding="utf-8",
            )
            self.assertEqual(
                audit_fixed_menu_labels._load_targets(path),
                {("TT1B", 0): "Legacy", ("TT1B", 1): "Canonical"},
            )

    def test_target_audit_emits_the_candidate_audits_canonical_column(
        self,
    ) -> None:
        """Prevent a silent producer/consumer target-label schema drift."""
        targets = audit_full_word_menu_targets.rows()
        self.assertGreater(len(targets), 0)
        self.assertIn("full_word_target", targets[0])
        self.assertNotIn("target_label", targets[0])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "targets.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(targets[0]))
                writer.writeheader()
                writer.writerows(targets)
            loaded = audit_fixed_menu_labels._load_targets(path)
        first = targets[0]
        self.assertEqual(
            loaded[(str(first["bank"]), int(first["index"]))],
            first["full_word_target"],
        )


class CandidateReportTests(unittest.TestCase):
    """Require current, complete candidate evidence before reporting success."""

    candidate_sha256 = "A" * 64
    bank_sha256 = "B" * 64

    def _row(self) -> dict[str, str]:
        """Return one otherwise-valid candidate audit row."""
        return {
            "bank": "TT1B",
            "index": "0",
            "source_label": "Look",
            "decoded_label": "Look",
            "slot_bytes": "4",
            "representation": "literal",
            "proposed_full_label": "Look",
            "fallback_label": "",
            "status": "full-word",
            "width_ok": "True",
            "width_error": "",
            "candidate_fds_sha256": self.candidate_sha256,
            "bank_sha256": self.bank_sha256,
        }

    def _manifest(self) -> dict[str, object]:
        """Return the manifest fields the report must compare to its audit."""
        return {
            "outputs": {"four_side": {"sha256": self.candidate_sha256}},
            "scenario_banks": {
                "TT1B": {
                    "records": 1,
                    "dictionary_entries": 0,
                    "packed_bytes": 1,
                    "capacity_bytes": 1,
                    "remaining_bytes": 0,
                    "sha256": self.bank_sha256,
                }
            },
        }

    def _write_inputs(
        self,
        directory: Path,
        rows: list[dict[str, str]],
        manifest: dict[str, object],
    ) -> tuple[Path, Path]:
        """Write one synthetic audit/manifest pair for report validation."""
        audit_path = directory / "audit.csv"
        with audit_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=report_full_word_menu_candidate.AUDIT_FIELDNAMES,
            )
            writer.writeheader()
            writer.writerows(rows)
        manifest_path = directory / "release_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return audit_path, manifest_path

    def test_report_writes_only_a_manifest_matched_candidate_audit(
        self,
    ) -> None:
        """Bind the report to both the candidate image and its scenario bank."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            audit_path, manifest_path = self._write_inputs(
                directory, [self._row()], self._manifest()
            )
            output_dir = directory / "report"

            summary = report_full_word_menu_candidate.report(
                audit_path, manifest_path, output_dir
            )

            self.assertEqual(
                summary["candidate_fds_sha256"], self.candidate_sha256
            )
            self.assertTrue(
                (output_dir / "fixed_menu_label_summary.json").is_file()
            )

    def test_report_rejects_source_only_and_width_failures_before_output(
        self,
    ) -> None:
        """Do not label source-only or overflowing rows as candidate evidence."""
        for status, width_ok, expected in (
            ("source-only", "True", "non-reportable statuses"),
            ("full-word", "False", "display-width failure"),
        ):
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory() as temporary,
            ):
                directory = Path(temporary)
                row = self._row()
                row["status"] = status
                row["width_ok"] = width_ok
                audit_path, manifest_path = self._write_inputs(
                    directory, [row], self._manifest()
                )
                output_dir = directory / "report"

                with self.assertRaisesRegex(
                    report_full_word_menu_candidate.CandidateAuditError,
                    expected,
                ):
                    report_full_word_menu_candidate.report(
                        audit_path, manifest_path, output_dir
                    )

                self.assertFalse(output_dir.exists())

    def test_report_rejects_empty_and_stale_candidate_audits(self) -> None:
        """Reject missing evidence and rows from a different candidate image."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            audit_path, manifest_path = self._write_inputs(
                directory, [], self._manifest()
            )
            with self.assertRaisesRegex(
                report_full_word_menu_candidate.CandidateAuditError,
                "has no fixed-label rows",
            ):
                report_full_word_menu_candidate.report(
                    audit_path, manifest_path, directory / "empty-report"
                )

            stale_row = self._row()
            stale_row["candidate_fds_sha256"] = "C" * 64
            audit_path, manifest_path = self._write_inputs(
                directory, [stale_row], self._manifest()
            )
            with self.assertRaisesRegex(
                report_full_word_menu_candidate.CandidateAuditError,
                "does not match the release manifest",
            ):
                report_full_word_menu_candidate.report(
                    audit_path, manifest_path, directory / "stale-report"
                )

    def test_report_rejects_a_bank_from_another_candidate(self) -> None:
        """Require each audited scenario bank to match the release manifest."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            stale_row = self._row()
            stale_row["bank_sha256"] = "C" * 64
            audit_path, manifest_path = self._write_inputs(
                directory, [stale_row], self._manifest()
            )

            with self.assertRaisesRegex(
                report_full_word_menu_candidate.CandidateAuditError,
                "bank SHA-256 does not match",
            ):
                report_full_word_menu_candidate.report(
                    audit_path, manifest_path, directory / "stale-report"
                )


if __name__ == "__main__":
    unittest.main()
