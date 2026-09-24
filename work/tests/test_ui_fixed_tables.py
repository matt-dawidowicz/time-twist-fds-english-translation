"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import hashlib
import unittest

from time_twist import ui
from time_twist.english import encode_english, render_english
from time_twist.textcodec import SymbolKind, pack_records, split_records

PLAYTESTED_FIXED_TABLES = {
    "TT1B": (
        53,
        "7F40767B8E4C110CA84F25B6EB3C186B4E37ACFF66E5104A1D947679E9AEE5BB",
    ),
    "TT2": (
        70,
        "77155CCE0FAF29C347B4B57A854023C8972C656A00EFBC37484A52EB442849E1",
    ),
    "T22": (
        33,
        "2798D991054590F189C58C61A3BF6C568FCFE5FFA91AD898D66BD77EB6A5E907",
    ),
    "TT3A": (
        95,
        "27BFD7DA79BABF4169A84651CBF7145A1E3D83B9806C47E8D703B6FDA1F24FD1",
    ),
    "TT3B": (
        21,
        "1C6729FEA026AFD19E9141F59549DCA83AF619408D5ECAA78F447263EAB7B4F0",
    ),
    "TT4": (
        97,
        "0E0D53BADFC47768697F5470474762B267D27C1F81B1023559198BC434E61E2C",
    ),
    "TT5": (
        113,
        "A4399663BEA81C0CE2A8CB63557E43ED8C5FD4DEA6EC93A4547AB543CD23B88A",
    ),
    "T25": (
        42,
        "9AEC9EC9864E32882A3366C4203539178BEBD3D6DFD5E1FE5A6B59FAA999E4AF",
    ),
    "TT6A": (
        41,
        "2E996F73C58D3C51873D0220B15A3C620820082FFC0C6E2EFFF1BC9096E56959",
    ),
    "TT6B": (
        62,
        "6F00CDF2ACBBE586D5EF3474DAA839A7AC1F98303F038C6C3322CEC8DF5E6A25",
    ),
    "TT6C": (
        94,
        "FEE855A3CD5E626EB96A042A3021FFAF575882274CE7009AC1A5D6214DEBBBB3",
    ),
}


def _table_digest(records: tuple[str, ...]) -> str:
    """Return a stable semantic digest for one ordered fixed-menu table."""
    return (
        hashlib.sha256("\0".join(records).encode("utf-8")).hexdigest().upper()
    )


class FixedMenuCopyTests(unittest.TestCase):
    """Keep fixed-menu copy synchronized with the runtime-playtested release."""

    def test_playtested_fixed_tables_are_locked(self) -> None:
        """Lock every ordered label without duplicating hundreds of strings."""
        for bank_name, (
            expected_count,
            expected_digest,
        ) in PLAYTESTED_FIXED_TABLES.items():
            records = getattr(ui, f"{bank_name}_FIXED_TEXT_RECORDS")
            with self.subTest(bank=bank_name):
                self.assertEqual(len(records), expected_count)
                self.assertEqual(_table_digest(records), expected_digest)

    def test_playtested_expanded_labels_are_locked(self) -> None:
        """Keep representative runtime-verified full labels human-readable."""
        expected = {
            "TT1B": {
                11: "Attack",
                15: "Exhibit",
                18: "Monster",
                20: "Hold hands",
                22: "Smile at",
                23: "Compliment",
                33: "Nameplate",
                35: "Newspaper",
                36: "Magnifier",
                52: "Run away",
            },
            "TT2": {
                12: "Empty bottle",
                20: "Signboard",
                21: "Posted sign",
                22: "Bottles",
                24: "Take off",
                58: "Onlookers",
                44: "Deneuve",
                64: "Basement",
                66: "Joan",
            },
            "T22": {
                11: "Take off",
                24: "Scrap paper",
                27: "Joan",
                30: "Onlookers",
            },
            "TT3A": {
                9: "Outside fence",
                12: "Room",
                25: "Shower room",
                30: "Pebble",
                41: "Throw",
                47: "Red writing",
                48: "Blue writing",
                50: "Password",
                55: "Combine",
                59: "Watermill",
                68: "Trash can",
                76: "Nazi boat",
                78: "Banana boat",
                84: "Montgomery",
                89: "MacArthur",
                93: "Streetlamp",
            },
            "TT3B": {6: "Watermill", 12: "Outside car", 15: "Run away"},
            "TT4": {
                10: "Slap cheeks",
                11: "Press abdomen",
                12: "Lift chin",
                13: "Bend knees",
                17: "With pauses",
                18: "Continuously",
                33: "Medicinal herb",
                46: "Squeeze",
                47: "Prick",
                48: "Leave it",
                49: "Apply oil",
                50: "Wrap with cloth",
                56: "Plantain herb",
                94: "Brown rice",
            },
            "TT5": {
                28: "Call Meyer",
                29: "Get water",
                30: "Pick cotton",
                31: "Repair roof",
                32: "Split wood",
                33: "Pull weeds",
                34: "4 buckets",
                35: "6 buckets",
                36: "8 buckets",
                37: "10 buckets",
                56: "Marine Corps",
                58: "Red ship",
                63: "Mrs. Aquino",
                71: "Cotton gin",
                72: "Cultivator",
                90: "Tens digit",
                91: "Ones digit",
                98: "Six or more",
                103: "Pour in",
                105: "Large bottle",
                106: "Medium bottle",
                107: "Small bottle",
            },
            "T25": {
                16: "Outside window",
                19: "Guest room",
                26: "First drawer",
                27: "Second drawer",
                28: "Third drawer",
                32: "Get down",
                33: "Go up",
                34: "Get on",
            },
            "TT6A": {
                10: "Turn aside",
                21: "Well water",
                23: "Right house",
                24: "Left house",
                29: "Hand mill",
                34: "Get on",
                35: "Get down",
                38: "On stand",
                39: "Roof tile",
                40: "Children",
            },
            "TT6B": {
                11: "Shout",
                12: "Stick out tongue",
                25: "Attack",
                33: "Fruit of wisdom",
                34: "Fruit of knowledge",
                54: "Wag tail",
                55: "Remove fleas",
                57: "Smile at",
                58: "Compliment",
            },
            "TT6C": {
                2: "Leap at",
                14: "My body",
                17: "Time Belt",
                18: "Move aside",
                25: "Ash",
                32: "Human bones",
                46: "Wine merchant",
                60: "Plantain herb",
                76: "Gold bracelet",
                77: "Silver bracelet",
                78: "Copper bracelet",
                79: "Tin bracelet",
                88: "Joan",
            },
        }
        for bank_name, expected_by_index in expected.items():
            records = getattr(ui, f"{bank_name}_FIXED_TEXT_RECORDS")
            for index, label in expected_by_index.items():
                with self.subTest(bank=bank_name, index=index):
                    self.assertEqual(records[index], label)

    def test_fixed_menu_labels_have_clean_semantic_spacing(self) -> None:
        """Do not encode accidental leading or trailing spaces in menu labels."""
        for bank_name in PLAYTESTED_FIXED_TABLES:
            records = getattr(ui, f"{bank_name}_FIXED_TEXT_RECORDS")
            for index, label in enumerate(records):
                with self.subTest(bank=bank_name, index=index, label=label):
                    self.assertEqual(label, label.strip())
                    self.assertNotIn("  ", label)

    def test_contextual_menu_localization_audit_is_locked(self) -> None:
        """Protect source-reviewed contextual menu corrections."""
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[14], "Jar")
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[36], "Magnifier")
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[38], "Old man")
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[40], "Ground")
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[41], "Forward")
        self.assertEqual(ui.TT1B_FIXED_TEXT_RECORDS[51], "Time Belt")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[47], "Offer")
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[56], "Plantain herb")

    def test_disk_copy_is_title_case_and_exactly_size_neutral(self) -> None:
        """Preserve every NOV2 prompt slot while avoiding all-caps copy."""
        self.assertEqual(
            tuple(patch[2] for patch in ui.DISK_PROMPT_PATCHES),
            (
                "Part 1",
                "Part2",
                "{CTRL:0}SideA",
                "{CTRL:0}Side B",
                "{CTRL:0}{CTRL:0}Insert now.",
            ),
        )
        self.assertEqual(
            tuple(patch[2] for patch in ui.SIDE_NUMBER_ERROR_PATCHES),
            ("Bad side.", "{CTRL:0}Try again."),
        )
        self.assertEqual(
            tuple(patch[2] for patch in ui.DISK_NUMBER_ERROR_PATCHES),
            ("Wrong side.",),
        )
        rendered_side_number_error = "".join(
            render_english(
                split_records(
                    pack_records([ui._encode_side_number_error(replacement)]),
                    limit=1,
                )[0][0]
            )
            for _, _, replacement in ui.SIDE_NUMBER_ERROR_PATCHES
        )
        self.assertEqual(
            rendered_side_number_error,
            "Bad side.{CTRL:0}Try again.",
        )
        self.assertEqual(
            render_english(ui._encode_disk_prompt("Part2")), "Part2"
        )
        self.assertEqual(
            render_english(ui._encode_disk_prompt("{CTRL:0}SideA")),
            "{CTRL:0}SideA",
        )
        for replacement in ("Part2", "{CTRL:0}SideA"):
            with self.subTest(replacement=replacement):
                self.assertTrue(
                    all(
                        not (
                            symbol.kind is SymbolKind.EXTENDED
                            and symbol.value in {45, 63}
                        )
                        for symbol in ui._encode_disk_prompt(replacement)
                    )
                )
        self.assertEqual(
            tuple(patch[2] for patch in ui.WRONG_DISK_PATCHES),
            ("Wrong disk! ", "{CTRL:0}Try another side"),
        )
        for _, original, replacement in (
            *ui.DISK_PROMPT_PATCHES,
            (
                ui.DISK_SET_ERROR_OFFSET,
                ui.DISK_SET_ERROR_SOURCE,
                ui.DISK_SET_ERROR_ENGLISH,
            ),
            *ui.SIDE_NUMBER_ERROR_PATCHES,
            *ui.WRONG_DISK_PATCHES,
        ):
            with self.subTest(replacement=replacement):
                encoder = (
                    ui._encode_disk_prompt
                    if replacement in {"Part2", "{CTRL:0}SideA"}
                    else (
                        ui._encode_side_number_error
                        if replacement == "Wrong side."
                        else encode_english
                    )
                )
                self.assertEqual(
                    len(pack_records([encoder(replacement)])),
                    len(original),
                )
        for _, original, replacement in ui.DISK_NUMBER_ERROR_PATCHES:
            with self.subTest(replacement=replacement):
                self.assertEqual(
                    len(pack_records([encode_english(replacement)])),
                    len(original),
                )

    def test_fixed_month_and_confirmation_choices_use_title_case(self) -> None:
        """Keep selector choices consistent with the rest of the English UI."""
        self.assertEqual(
            tuple(patch[2] for patch in ui.TT1A_MONTH_PATCHES),
            (
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul-Dec",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ),
        )
        self.assertEqual(
            tuple(patch[2] for patch in ui.TT1A_CONFIRMATION_PATCHES),
            ("Yes", "No"),
        )

    def test_kouhen_direct_boot_copy_uses_the_same_title_case_style(
        self,
    ) -> None:
        """Keep the FDS-only direct-boot warning consistent with NOV2."""
        self.assertEqual(
            ui.KOUHEN_BOOT_GUARD_LINES,
            ((11, "Please start with"), (13, "Part 1")),
        )
        stream, glyphs = ui._kouhen_boot_guard_assets()
        self.assertEqual(
            len(stream),
            ui.KOUHEN_BOOT_GUARD_TILEMAP_END
            - ui.KOUHEN_BOOT_GUARD_TILEMAP_OFFSET,
        )
        self.assertEqual(
            len(glyphs),
            ui.KOUHEN_BOOT_GUARD_TILE_COUNT * 8,
        )

    def test_full_word_targets_preserve_complete_labels(self) -> None:
        """Keep source-reviewed labels complete across the repacked tables."""
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[28], "Crimea")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[34], "Criminals")
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[4], "Silver coin")
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[19], "Olive")
        self.assertEqual(ui.T25_FIXED_TEXT_RECORDS[29], "Picture")
        self.assertEqual(
            ui.TT3A_FIXED_TEXT_RECORDS[56:59], ("North", "East", "West")
        )
        self.assertEqual(
            ui.TT6C_FIXED_TEXT_RECORDS[91:94], ("Left", "Up", "Right")
        )


if __name__ == "__main__":
    unittest.main()
