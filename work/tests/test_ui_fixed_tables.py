"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import unittest

from time_twist import ui
from time_twist.english import encode_english, render_english
from time_twist.textcodec import SymbolKind, pack_records, split_records


class FixedMenuCopyTests(unittest.TestCase):
    """Keep the proven full command labels consistent across scenario banks."""

    def test_tt3b_fight_suffix_fits_the_fixed_record(self) -> None:
        """Spell Fight in full within its four-byte native menu slot."""
        dictionary = (encode_english("ight"),)
        packed = ui._encode_at_exact_record_size("Fight", dictionary, 4)
        record = split_records(packed, limit=1)[0][0]
        expanded = tuple(
            (
                dictionary[symbol.value - 1]
                if symbol.kind is SymbolKind.DICTIONARY
                else (symbol,)
            )
            for symbol in record
        )

        self.assertEqual(
            render_english(
                tuple(symbol for part in expanded for symbol in part)
            ).rstrip(),
            "Fight",
        )

    def test_proven_full_command_labels_use_title_case(self) -> None:
        """Protect the size-neutral replacements for cramped menu verbs."""
        expected = (
            (
                ui.TT1B_FIXED_TEXT_RECORDS,
                {
                    0: "Look",
                    1: "Talk",
                    2: "Move",
                    3: "Sky",
                    4: "Area",
                    5: "Museum",
                    8: "East",
                    9: "West",
                    10: "Use",
                    11: "Fight",
                    12: "Poke",
                    13: "Walk",
                    14: "Pot",
                    15: "Case",
                    18: "Fiend",
                    20: "Hold",
                    21: "Hug",
                    22: "Smile",
                    23: "Praise",
                    30: "Map",
                    31: "North",
                    34: "Intercom",
                    42: "Back",
                    45: "Ask",
                    52: "Run",
                },
            ),
            (
                ui.TT2_FIXED_TEXT_RECORDS,
                {1: "Talk", 3: "Use", 6: "Move", 18: "Walk", 47: "Move"},
            ),
            (
                ui.T22_FIXED_TEXT_RECORDS,
                {1: "Talk", 2: "Use", 4: "Move", 22: "Open", 32: "Walk"},
            ),
            (
                ui.TT3A_FIXED_TEXT_RECORDS,
                {1: "Talk", 3: "Use", 4: "Move", 18: "Walk", 41: "Toss"},
            ),
            (
                ui.TT3B_FIXED_TEXT_RECORDS,
                {1: "Talk", 3: "Use", 4: "Move", 13: "Fight", 15: "Run"},
            ),
            (
                ui.TT4_FIXED_TEXT_RECORDS,
                {
                    1: "Talk",
                    2: "Treat",
                    3: "Use",
                    5: "Move",
                    10: "Slap",
                    11: "Press",
                    23: "Eat",
                    46: "Crush",
                    47: "Prick",
                    50: "Wrap",
                    65: "Swing",
                    67: "Walk",
                },
            ),
            (
                ui.TT5_FIXED_TEXT_RECORDS,
                {1: "Talk", 3: "Move", 14: "Open", 21: "Use", 103: "Pour"},
            ),
            (
                ui.T25_FIXED_TEXT_RECORDS,
                {
                    1: "Talk",
                    2: "Use",
                    3: "Move",
                    23: "Open",
                    31: "Hide",
                    32: "Down",
                    33: "Up",
                },
            ),
            (
                ui.TT6A_FIXED_TEXT_RECORDS,
                {3: "Hold", 4: "Move", 10: "Turn", 35: "Down"},
            ),
            (
                ui.TT6B_FIXED_TEXT_RECORDS,
                {
                    3: "Hold",
                    4: "Move",
                    11: "Yell",
                    13: "Wink",
                    14: "Talk",
                    15: "Eat",
                    25: "Fight",
                    26: "Walk",
                    56: "Hug",
                    57: "Smile",
                },
            ),
            (
                ui.TT6C_FIXED_TEXT_RECORDS,
                {
                    2: "Leap",
                    5: "Talk",
                    7: "Eat",
                    8: "Use",
                    18: "Move",
                    19: "Open",
                    20: "Move",
                },
            ),
        )
        for records, expected_by_index in expected:
            for index, label in expected_by_index.items():
                with self.subTest(records=records, index=index):
                    self.assertEqual(records[index], label)

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

    def test_fixed_menu_labels_use_mixed_case_where_verified(self) -> None:
        """Keep complete menu words readable while leaving forced abbreviations."""
        expected = (
            (
                ui.TT2_FIXED_TEXT_RECORDS,
                {
                    7: "In",
                    11: "Wine",
                    12: "Empty",
                    16: "Out",
                    17: "Data",
                    19: "Area",
                    20: "Sign",
                    21: "Post",
                    23: "Wear",
                    24: "Remove",
                    25: "Man",
                    52: "No",
                    54: "Yes",
                    55: "No",
                    60: "Jail",
                    62: "Jailer",
                    63: "Women",
                    64: "Cellar",
                    67: "Rope",
                    68: "Candle",
                    69: "Cell",
                },
            ),
            (
                ui.T22_FIXED_TEXT_RECORDS,
                {
                    11: "Remove",
                    13: "Out",
                    16: "In",
                    19: "Rope",
                    26: "Scaffold",
                },
            ),
            (
                ui.TT3A_FIXED_TEXT_RECORDS,
                {
                    5: "Area",
                    9: "Out",
                    11: "Data",
                    12: "In",
                    13: "Wall",
                    15: "Out",
                    17: "In",
                    25: "Shower",
                    29: "Tile",
                    30: "Rock",
                    31: "Shower",
                    38: "Yes",
                    39: "No",
                    45: "Man",
                    47: "Red",
                    48: "Blue",
                    63: "No",
                    90: "Yes",
                    91: "No",
                    93: "Lamp",
                },
            ),
            (ui.TT3B_FIXED_TEXT_RECORDS, {5: "Area", 12: "Out", 14: "Guard"}),
            (
                ui.TT4_FIXED_TEXT_RECORDS,
                {
                    6: "In",
                    12: "Chin",
                    13: "Knee",
                    14: "Ears",
                    15: "Eyes",
                    16: "Nose",
                    17: "Pause",
                    20: "Oil",
                    25: "Out",
                    26: "Area",
                    29: "Man",
                    34: "No",
                    37: "Data",
                    39: "Youth",
                    40: "Up",
                    43: "Warm",
                    44: "Cool",
                    48: "None",
                    49: "Oil",
                    56: "Plant",
                    74: "Fisherman",
                    75: "Kid",
                    94: "Rice",
                    95: "Pearl",
                },
            ),
            (
                ui.TT5_FIXED_TEXT_RECORDS,
                {
                    6: "Men",
                    7: "Area",
                    15: "Data",
                    16: "Room",
                    20: "Out",
                    24: "No",
                    26: "Again",
                    29: "Water",
                    32: "Wood",
                    33: "Weed",
                    104: "End",
                    105: "Large",
                    106: "Medium",
                    112: "In",
                },
            ),
            (
                ui.T25_FIXED_TEXT_RECORDS,
                {
                    9: "Room",
                    15: "Out",
                    16: "Outside",
                    17: "Hall",
                    18: "Area",
                    19: "Guest",
                    20: "Study",
                    21: "Stair",
                    34: "On",
                    35: "Boat",
                },
            ),
            (
                ui.TT6A_FIXED_TEXT_RECORDS,
                {
                    5: "Area",
                    14: "Data",
                    16: "Kid",
                    20: "Hay",
                    21: "Water",
                    26: "Room",
                    33: "Out",
                    34: "On",
                    40: "Kids",
                },
            ),
            (
                ui.TT6B_FIXED_TEXT_RECORDS,
                {5: "Area", 18: "Men", 27: "Room", 52: "Oil", 53: "Hay"},
            ),
            (
                ui.TT6C_FIXED_TEXT_RECORDS,
                {
                    9: "Room",
                    13: "Men",
                    21: "Area",
                    32: "Bones",
                    54: "Bread",
                    76: "Gold",
                    77: "Silver",
                    78: "Copper",
                    79: "Tin",
                },
            ),
        )
        for records, expected_by_index in expected:
            for index, label in expected_by_index.items():
                with self.subTest(records=records, index=index):
                    self.assertEqual(records[index], label)

    def test_august_12_full_label_fit_examples_are_locked(self) -> None:
        """Protect the latest safe fixed-menu label expansions."""
        expected_by_bank = {
            "T25": {
                11: "Meyer",
                14: "Pot",
                24: "Desk",
                38: "Me",
            },
            "TT3A": {
                10: "Hit",
                14: "Charm",
                23: "Stove",
                24: "Bed",
                40: "Gun",
                49: "Notes",
                50: "Pass",
                54: "Tear",
                57: "East",
                59: "Mill",
                68: "Trash",
                75: "Gunboat",
                76: "Nazi",
                77: "U-boat",
                78: "Banana",
                79: "Gabin",
                83: "Truffaut",
            },
            "TT3B": {
                6: "Mill",
                9: "Gun",
                10: "Charm",
            },
            "TT4": {
                24: "Lick",
                41: "Down",
                52: "East",
                59: "Grind",
                60: "Boil",
                70: "Plato",
                78: "Alice",
                93: "Fig",
            },
            "TT5": {
                11: "East",
                27: "Schedule",
                28: "Call",
                31: "Roof",
                56: "Marine",
                58: "Red",
                65: "Whitney",
                67: "Etna",
                71: "Gin",
                72: "Plow",
                90: "Tens",
                91: "Ones",
                109: "Meyer",
            },
            "TT6A": {
                9: "Nod",
                15: "Elder",
                27: "Mary",
                29: "Mill",
                39: "Tile",
            },
            "TT6B": {
                7: "Mary",
                16: "Tent",
                20: "East",
                32: "Dung",
                35: "Isis",
                38: "Iraq",
                41: "Egypt",
                42: "David",
                54: "Wag",
                55: "Fleas",
                59: "Hoof",
                60: "Tail",
                61: "Mane",
            },
            "TT6C": {
                11: "Mary",
                28: "East",
                61: "Amacha",
                68: "Fred",
                69: "Bob",
                75: "Puma",
                85: "Meyer",
                87: "Nick",
                91: "Left",
                92: "Up",
            },
        }
        for bank_name, expected_by_index in expected_by_bank.items():
            records = getattr(ui, f"{bank_name}_FIXED_TEXT_RECORDS")
            for index, label in expected_by_index.items():
                with self.subTest(bank=bank_name, index=index):
                    self.assertEqual(records[index], label)

    def test_august_12_dictionary_assisted_full_word_experiment_is_locked(
        self,
    ) -> None:
        """Protect full-word labels proven by existing/reused dictionary slots."""
        expected_by_bank = {
            "T22": {0: "Look", 30: "Crowd"},
            "TT2": {8: "Pierre", 58: "Crowd"},
            "TT3B": {8: "Woman"},
            "TT4": {73: "Sea"},
            "TT5": {19: "Drawer", 55: "Trader", 73: "Camera"},
            "T25": {
                5: "Soldier",
                6: "Coffee",
                8: "Mansion",
                25: "Drawer",
                36: "Coyote",
            },
            "TT6A": {8: "Joseph", 22: "Hill"},
            "TT6B": {12: "Tongue", 17: "Camel", 30: "Sheep", 31: "Cow"},
            "TT6C": {86: "Hitler"},
        }
        for bank_name, expected_by_index in expected_by_bank.items():
            records = getattr(ui, f"{bank_name}_FIXED_TEXT_RECORDS")
            for index, label in expected_by_index.items():
                with self.subTest(bank=bank_name, index=index):
                    self.assertEqual(records[index], label)

    def test_full_word_target_branch_removes_known_placeholder_abbreviations(
        self,
    ) -> None:
        """The compression branch should target readable labels, not codes."""
        self.assertEqual(ui.TT5_FIXED_TEXT_RECORDS[23], "Yes")
        self.assertEqual(ui.TT6C_FIXED_TEXT_RECORDS[25], "Yes")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[9], "Body")
        self.assertEqual(ui.TT3A_FIXED_TEXT_RECORDS[6], "Body")
        self.assertEqual(ui.TT6C_FIXED_TEXT_RECORDS[16], "Body")
        self.assertEqual(
            ui.TT3A_FIXED_TEXT_RECORDS[56:59], ("North", "East", "West")
        )
        self.assertEqual(
            ui.TT6C_FIXED_TEXT_RECORDS[91:94], ("Left", "Up", "Right")
        )

    def test_full_word_blockers_are_explicit_and_source_reviewed(self) -> None:
        """Never turn an unavailable full-word target into a hidden success."""
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[28], "Crimea")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[34], "Criminals")
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[4], "Silver coin")
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[19], "Olive")
        self.assertEqual(ui.T25_FIXED_TEXT_RECORDS[29], "Picture")
        self.assertEqual(ui.FIXED_TEXT_BLOCKED_FALLBACKS["TT2"][28], "CRI")
        self.assertEqual(ui.FIXED_TEXT_BLOCKED_FALLBACKS["TT4"][4], "S")
        self.assertEqual(ui.FIXED_TEXT_BLOCKED_FALLBACKS["T25"][29], "P")
