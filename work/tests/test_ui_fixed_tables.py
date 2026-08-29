"""Fixture-free tests for canonical menu tables and standalone UI copy."""

from __future__ import annotations

import unittest

from time_twist import ui, ui_fixed_tables
from time_twist.english import encode_english
from time_twist.textcodec import pack_records

RELOCATED_BANKS = {
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
}


class FixedMenuTableTests(unittest.TestCase):
    """Protect the full-word menu data used by canonical release repacking."""

    def test_specs_cover_exactly_the_relocated_menu_banks(self) -> None:
        """Keep relocation metadata aligned with the modern release architecture."""
        self.assertEqual(set(ui.FIXED_RECORD_TABLE_SPECS), RELOCATED_BANKS)

    def test_specs_match_source_declarations_and_all_labels_encode(
        self,
    ) -> None:
        """Bind every spec to its source offsets/hash and supported English glyphs."""
        for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items():
            with self.subTest(bank=bank_name):
                self.assertEqual(
                    spec.start,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_START_OFFSET"
                    ),
                )
                self.assertEqual(
                    spec.end,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_END_OFFSET"
                    ),
                )
                self.assertEqual(
                    spec.source_sha256,
                    getattr(
                        ui_fixed_tables,
                        f"{bank_name}_FIXED_TEXT_SOURCE_SHA256",
                    ),
                )
                self.assertEqual(
                    spec.records,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_RECORDS"
                    ),
                )
                self.assertTrue(
                    all(encode_english(text) for text in spec.records)
                )
                self.assertEqual(
                    ui.fixed_record_table_page_pointer_bytes(bank_name),
                    2 * ((len(spec.records) - 1) // 32),
                )

    def test_high_value_full_word_labels_are_not_abbreviated(self) -> None:
        """Lock representative labels that motivated the relocated layout."""
        self.assertIn("Intercom", ui.FIXED_RECORD_TABLE_SPECS["TT1B"].records)
        self.assertIn(
            "Resistance", ui.FIXED_RECORD_TABLE_SPECS["TT3A"].records
        )
        self.assertIn("Fight", ui.FIXED_RECORD_TABLE_SPECS["TT3B"].records)
        self.assertIn("South", ui.FIXED_RECORD_TABLE_SPECS["TT4"].records)

    def test_disk_copy_remains_size_neutral_and_mixed_case(self) -> None:
        """Keep source-locked FDS prompts readable without moving NOV2 code."""
        for collection in (
            ui.DISK_PROMPT_PATCHES,
            ui.SIDE_NUMBER_ERROR_PATCHES,
            ui.DISK_NUMBER_ERROR_PATCHES,
            ui.WRONG_DISK_PATCHES,
        ):
            for _, original, replacement in collection:
                with self.subTest(replacement=replacement):
                    self.assertEqual(
                        len(pack_records((encode_english(replacement),))),
                        len(original),
                    )
        self.assertEqual(ui.DISK_SET_ERROR_ENGLISH, "Bad side.")
        self.assertEqual(
            ui.KOUHEN_BOOT_GUARD_LINES,
            ((11, "Please start with"), (13, "Part 1")),
        )

    def test_tt1a_fixed_choices_remain_title_case(self) -> None:
        """Keep the one non-relocated scenario bank's source-locked choices."""
        self.assertEqual(
            tuple(patch[2] for patch in ui.TT1A_CONFIRMATION_PATCHES),
            ("Yes", "No"),
        )
        self.assertEqual(ui.TT1A_MONTH_PATCHES[0][2], "Jan")
        self.assertEqual(ui.TT1A_MONTH_PATCHES[-1][2], "Dec")


if __name__ == "__main__":
    unittest.main()
