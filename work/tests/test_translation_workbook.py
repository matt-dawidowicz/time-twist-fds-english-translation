"""Regression tests for the current translation workbook and playable-text authority."""

from __future__ import annotations

import csv
import json
import re
import unittest

from generate_translation_workbook import (
    CONTROL_OVERRIDE_IDS,
    OUTPUTS,
    PATCH_FOOTPRINT_RESULTS,
    controls,
    load_playable_scenario_text,
    make_glossary,
    make_rows,
    validate,
)
from time_twist.cli import PERSONALITY_QUESTION_IDS
from time_twist.english import encode_english, validate_display_width

REQUIRED_FIELDS = (
    "original_record_id",
    "bank",
    "record_type",
    "exact_japanese_source",
    "romaji",
    "reconstructed_japanese",
    "literal_english_meaning",
    "linguistic_and_cultural_notes",
    "speaker_or_narration_identity",
    "current_english",
    "problems_with_current_english",
    "final_natural_english_translation",
    "patch_safe_english_translation",
    "confidence_level",
    "translation_status",
)


class TranslationWorkbookTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare shared fixtures for the current contract tests."""
        cls.rows, cls.source_payload, cls.review_path = make_rows()
        cls.glossary = make_glossary(cls.rows)

    def test_all_source_records_are_present_once_and_in_order(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(len(self.rows), 2052)
        self.assertEqual(
            [row.original_record_id for row in self.rows],
            [row["text_id"] for row in self.source_payload["rows"]],
        )
        self.assertEqual(
            len({row.original_record_id for row in self.rows}),
            2052,
        )

    def test_exact_japanese_is_byte_for_byte_source_text(self) -> None:
        """Verify the current contract described by this regression test."""
        for workbook_row, source_row in zip(
            self.rows, self.source_payload["rows"], strict=True
        ):
            self.assertEqual(
                workbook_row.exact_japanese_source,
                source_row["japanese_exact"],
                workbook_row.original_record_id,
            )

    def test_every_record_has_required_translation_fields(self) -> None:
        """Verify the current contract described by this regression test."""
        for row in self.rows:
            for field in REQUIRED_FIELDS:
                value = getattr(row, field)
                self.assertNotEqual(
                    value, "", f"{row.original_record_id}: {field}"
                )

    def test_patch_controls_match_source_except_documented_ui_override(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        mismatches = {
            row.original_record_id
            for row in self.rows
            if controls(row.patch_safe_english_translation)
            != controls(row.exact_japanese_source)
        }
        self.assertEqual(mismatches, set(CONTROL_OVERRIDE_IDS))

    def test_patch_safe_text_matches_playable_authority(self) -> None:
        """Verify the current contract described by this regression test."""
        scenario = load_playable_scenario_text()
        for row in self.rows:
            if row.record_type == "scenario":
                self.assertEqual(
                    row.patch_safe_english_translation,
                    scenario[row.original_record_id],
                    row.original_record_id,
                )
            elif row.record_type in {"fixed-address", "graphics-text"}:
                self.assertEqual(
                    row.patch_safe_english_translation,
                    row.current_english,
                    row.original_record_id,
                )

    def test_every_scenario_patch_is_encodable_by_the_rom_font(self) -> None:
        """Verify the current contract described by this regression test."""
        for row in self.rows:
            if row.record_type == "scenario":
                encode_english(row.patch_safe_english_translation)
                validate_display_width(
                    row.patch_safe_english_translation,
                    allow_wrap=row.original_record_id
                    in PERSONALITY_QUESTION_IDS,
                )

    def test_visible_words_after_ellipses_have_a_space(self) -> None:
        """Verify the current contract described by this regression test."""
        missing_space = re.compile(r"\.\.\.(?=[A-Za-z0-9])")
        for row in self.rows:
            if row.record_type == "scenario":
                self.assertIsNone(
                    missing_space.search(row.patch_safe_english_translation),
                    row.original_record_id,
                )

    def test_reconstruction_avoids_known_substring_corruption(self) -> None:
        """Verify the current contract described by this regression test."""
        for row in self.rows:
            self.assertNotIn("き声る", row.reconstructed_japanese)
            self.assertNotIn("人らー", row.reconstructed_japanese)

    def test_romaji_contains_no_unromanized_japanese_characters(self) -> None:
        """Verify the current contract described by this regression test."""
        japanese = re.compile(r"[ぁ-んァ-ヶ一-龯]")
        for row in self.rows:
            self.assertIsNone(
                japanese.search(row.romaji),
                f"{row.original_record_id}: {row.romaji}",
            )

    def test_validation_function_accepts_completed_workbook(self) -> None:
        """Verify the current contract described by this regression test."""
        validate(self.rows, self.source_payload, self.glossary)

    def test_machine_readable_outputs_round_trip(self) -> None:
        """Verify the current contract described by this regression test."""
        json_path = OUTPUTS / "Time_Twist_complete_translation_workbook.json"
        csv_path = OUTPUTS / "Time_Twist_complete_translation_workbook.csv"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["rows"]), 2052)
        self.assertEqual(
            payload["patch_validation"]["revised_bank_footprints"],
            PATCH_FOOTPRINT_RESULTS,
        )
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        self.assertEqual(len(csv_rows), 2052)
        self.assertEqual(
            [row["original_record_id"] for row in payload["rows"]],
            [row["original_record_id"] for row in csv_rows],
        )

    def test_no_patch_safe_record_requires_storage_expansion(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertFalse(
            [
                row.original_record_id
                for row in self.rows
                if row.requires_technical_expansion == "yes"
            ]
        )

    def test_html_contains_required_filters_and_all_record_ids(self) -> None:
        """Verify the current contract described by this regression test."""
        html = (
            OUTPUTS / "Time_Twist_complete_translation_workbook.html"
        ).read_text(encoding="utf-8")
        for filter_id in (
            "bank",
            "kind",
            "speaker",
            "status",
            "confidence",
            "problem",
            "dialect",
            "gameplay",
            "technical",
            "search",
        ):
            self.assertIn(f'id="{filter_id}"', html)
        for row in self.rows:
            self.assertIn(row.original_record_id, html)


if __name__ == "__main__":
    unittest.main()
