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

    def test_target_loader_accepts_the_canonical_label_column(self) -> None:
        """Load the current full-word-target CSV format."""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "targets.csv"
            path.write_text(
                "bank,index,full_word_target\n" "TT1B,0,Canonical\n",
                encoding="utf-8",
            )
            self.assertEqual(
                audit_fixed_menu_labels._load_targets(path),
                {("TT1B", 0): "Canonical"},
            )

    def test_target_audit_emits_the_current_target_schema(self) -> None:
        """Prevent a silent producer/consumer schema drift."""
        targets = audit_full_word_menu_targets.rows()
        self.assertGreater(len(targets), 0)
        self.assertEqual(
            set(targets[0]),
            {
                "bank",
                "index",
                "full_word_target",
                "packed_bytes_literal",
                "encode_ok",
                "encode_error",
                "width_ok",
                "width_error",
            },
        )
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
                    "scenario_bytes": 1,
                    "menu_bytes": 0,
                    "dictionary_bytes": 0,
                    "spill_bytes": 0,
                    "loaded_end": "0xD7B4",
                    "nov3_headroom": 1,
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

    def test_report_removes_only_retired_files_after_validating_inputs(
        self,
    ) -> None:
        """Clear stale generated reports while preserving failed-run evidence."""
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            output_dir = directory / "report"
            output_dir.mkdir()
            previous_files = {
                "fixed_menu_label_blockers.csv": b"old blockers",
                "fixed_menu_label_mismatches.csv": b"old mismatches",
                "review-notes.txt": b"keep these notes",
            }
            for name, content in previous_files.items():
                (output_dir / name).write_bytes(content)
            invalid_row = self._row()
            invalid_row["status"] = "mismatch"
            audit_path, manifest_path = self._write_inputs(
                directory, [invalid_row], self._manifest()
            )
            with self.assertRaises(
                report_full_word_menu_candidate.CandidateAuditError
            ):
                report_full_word_menu_candidate.report(
                    audit_path, manifest_path, output_dir
                )
            for name, content in previous_files.items():
                self.assertEqual((output_dir / name).read_bytes(), content)

            audit_path, manifest_path = self._write_inputs(
                directory, [self._row()], self._manifest()
            )
            report_full_word_menu_candidate.report(
                audit_path, manifest_path, output_dir
            )
            self.assertEqual(
                {path.name for path in output_dir.iterdir()},
                {
                    "fixed_menu_full_word_literal.csv",
                    "fixed_menu_full_word_dictionary.csv",
                    "fixed_menu_label_summary.json",
                    "entropy_layout_report_by_bank.csv",
                    "review-notes.txt",
                },
            )
            self.assertEqual(
                (output_dir / "review-notes.txt").read_bytes(),
                previous_files["review-notes.txt"],
            )

    def test_report_rejects_source_only_and_width_failures_before_output(
        self,
    ) -> None:
        """Do not label source-only or overflowing rows as candidate evidence."""
        for status, width_ok, expected in (
            ("source-only", "True", "non-reportable statuses"),
            ("blocked", "True", "non-reportable statuses"),
            ("mismatch", "True", "non-reportable statuses"),
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
