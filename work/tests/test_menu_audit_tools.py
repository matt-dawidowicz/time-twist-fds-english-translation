"""Fixture-free contracts for fixed-menu audit and reporting helpers."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from time_twist import ui
from time_twist.english import encode_english, render_english
from time_twist.entropy_codec import pack_entropy_pages, pack_entropy_stream
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from time_twist.scenario import DICTIONARY_POINTER_OFFSET
from time_twist.textcodec import PackedSymbol, SymbolKind

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

    def test_candidate_menu_decoder_uses_entropy_pages_and_dictionary(self) -> None:
        """Decode the production menu format rather than native packed text."""
        bank_name = "TT1B"
        load_address = 0xA200
        spec = ui.FIXED_RECORD_TABLE_SPECS[bank_name]
        dictionary = (encode_english("Look"),)
        reference = (
            PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0),
        )
        menu = tuple(reference for _ in spec.records)
        packed_menu, page_starts = pack_entropy_pages(
            menu, records_per_page=ui.FIXED_RECORDS_PER_PAGE
        )
        pointer_bytes = ui.fixed_record_table_page_pointer_bytes(bank_name)
        page_index_offset = spec.start + len(packed_menu)
        dictionary_offset = page_index_offset + pointer_bytes
        packed_dictionary = pack_entropy_stream(dictionary)
        data = bytearray(dictionary_offset + len(packed_dictionary))
        data[spec.start:page_index_offset] = packed_menu
        data[
            ui.FIXED_RECORD_PAGE_POINTER_OFFSET :
            ui.FIXED_RECORD_PAGE_POINTER_OFFSET + 2
        ] = (load_address + page_index_offset).to_bytes(2, "little")
        for index, start in enumerate(page_starts[1:]):
            offset = page_index_offset + index * 2
            data[offset : offset + 2] = (
                load_address + spec.start + start
            ).to_bytes(2, "little")
        data[
            DICTIONARY_POINTER_OFFSET : DICTIONARY_POINTER_OFFSET + 2
        ] = (load_address + dictionary_offset).to_bytes(2, "little")
        data[dictionary_offset:] = packed_dictionary

        decoded_menu = audit_fixed_menu_labels._candidate_menu_records(
            bytes(data),
            bank_name=bank_name,
            load_address=load_address,
            record_count=len(menu),
        )
        decoded_dictionary = (
            audit_fixed_menu_labels._candidate_dictionary_prefix(
                bytes(data),
                load_address=load_address,
                required_entries=1,
            )
        )
        expansions = expand_entropy_dictionary(decoded_dictionary)

        self.assertEqual(len(decoded_menu), len(menu))
        self.assertEqual(decoded_menu[0], reference)
        self.assertEqual(
            render_english(
                expand_entropy_record(decoded_menu[-1], expansions)
            ),
            "Look",
        )

    def test_target_audit_emits_the_current_target_schema(self) -> None:
        """Prevent a silent producer/consumer schema drift."""
        targets = audit_full_word_menu_targets.rows()
        self.assertGreater(len(targets), 0)
        self.assertTrue(all(row["width_ok"] for row in targets))
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
