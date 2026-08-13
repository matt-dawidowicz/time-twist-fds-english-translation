"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist import ui
from time_twist.english import encode_english, render_english
from time_twist.textcodec import pack_records, split_records
from time_twist.ui import (
    COMPONENT_LOAD_ADDRESSES,
    ENGLISH_LOAD_PROMPT,
    ENGLISH_NOV4_LOAD_PROMPT,
    ENGLISH_SAVE_PROMPT,
    ENGLISH_START_PROMPT,
    LOAD_PROMPT_OFFSET,
    NOV2_OPAQUE_CLEAR_PATCHES,
    NOV2_SINGLE_CHOICE_B_PATCHES,
    NOV4_LOAD_PROMPT_OFFSET,
    ORIGINAL_LOAD_PROMPT,
    ORIGINAL_NOV4_LOAD_PROMPT,
    ORIGINAL_SAVE_PROMPT,
    SAVE_PROMPT_OFFSET,
    SourceVerifiedPatch,
    UiPatchError,
    _patched_load_prompt,
    _patched_nov4_load_prompt,
    _patched_save_prompt,
)


class SourceVerifiedPatchTests(unittest.TestCase):
    """Verify source guards and size neutrality without proprietary inputs."""

    def setUp(self) -> None:
        """Create one representative two-byte component patch."""
        self.patch = SourceVerifiedPatch(
            component="NOV2",
            file_offset=2,
            cpu_address=0x6002,
            expected=b"\x10\x20",
            replacement=b"\x30\x40",
            label="branch guard",
        )

    def test_matching_source_is_patched_in_place(self) -> None:
        """Apply a same-size replacement at its declared file offset."""
        data = bytearray(b"\x00\x01\x10\x20\x05")

        self.patch.apply_to(data)

        self.assertEqual(data, bytearray(b"\x00\x01\x30\x40\x05"))

    def test_source_mismatch_fails_without_mutation(self) -> None:
        """Reject an unexpected binary revision before changing bytes."""
        data = bytearray(b"\x00\x01\x10\x21\x05")
        original = bytes(data)

        with self.assertRaisesRegex(UiPatchError, "does not match source"):
            self.patch.apply_to(data)

        self.assertEqual(bytes(data), original)

    def test_size_changing_metadata_is_rejected(self) -> None:
        """Reject declarative metadata that would move following code."""
        with self.assertRaisesRegex(UiPatchError, "changed size"):
            SourceVerifiedPatch(
                component="NOV2",
                file_offset=0,
                cpu_address=0x6000,
                expected=b"\x10\x20",
                replacement=b"\x30",
                label="invalid",
            )

    def test_cpu_address_must_match_verified_component_load(self) -> None:
        """Reject a descriptive CPU address that disagrees with the file offset."""
        with self.assertRaisesRegex(UiPatchError, "expected \\$6002"):
            SourceVerifiedPatch(
                component="NOV2",
                file_offset=2,
                cpu_address=0x8002,
                expected=b"\x10",
                replacement=b"\x20",
                label="bad address",
            )

    def test_unknown_component_load_mapping_is_rejected(self) -> None:
        """Avoid inventing generic mappings for unverified components."""
        with self.assertRaisesRegex(UiPatchError, "no verified component"):
            SourceVerifiedPatch(
                component="SYNTH",
                file_offset=0,
                cpu_address=0x8000,
                expected=b"\x10",
                replacement=b"\x20",
                label="unknown load",
            )

    def test_all_declared_patch_addresses_match_the_verified_load(
        self,
    ) -> None:
        """Audit every production record through its established load mapping."""
        patches = (
            *NOV2_OPAQUE_CLEAR_PATCHES,
            *NOV2_SINGLE_CHOICE_B_PATCHES,
        )
        for patch in patches:
            with self.subTest(label=patch.label):
                self.assertEqual(
                    patch.cpu_address,
                    COMPONENT_LOAD_ADDRESSES[patch.component]
                    + patch.file_offset,
                )

    def test_documented_patch_offsets_match_declarative_records(self) -> None:
        """Keep the implementation guide's file/CPU pairs auditable."""
        project_root = Path(__file__).resolve().parents[2]
        documentation = (
            project_root / "docs" / "BUG_FIXES_AND_TITLE_IMPLEMENTATION.md"
        ).read_text(encoding="utf-8")
        patches = (
            *NOV2_OPAQUE_CLEAR_PATCHES,
            *NOV2_SINGLE_CHOICE_B_PATCHES,
        )
        for patch in patches:
            with self.subTest(label=patch.label):
                row_pair = (
                    f"| `${patch.file_offset:04X}` | "
                    f"`${patch.cpu_address:04X}` |"
                )
                self.assertIn(row_pair, documentation)


class FixedPromptTests(unittest.TestCase):
    """Verify fixed packed UI records without proprietary fixtures."""

    def test_title_menu_prompts_use_title_case_without_growing(self) -> None:
        """Keep the live Start and Load choices readable and size-neutral."""
        self.assertEqual(ENGLISH_START_PROMPT.hex().upper(), "8420C9080FA0")
        self.assertEqual(ENGLISH_LOAD_PROMPT.hex().upper(), "9440CAFA")
        self.assertEqual(
            ENGLISH_NOV4_LOAD_PROMPT.hex().upper(), "9440CA000FA0"
        )

    def test_nov4_load_prompt_replaces_the_visible_saved_game_choice(
        self,
    ) -> None:
        """Render Load in NOV4's six-byte title-menu saved-game slot."""
        data = bytearray(
            NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT) + 1
        )
        data[
            NOV4_LOAD_PROMPT_OFFSET : NOV4_LOAD_PROMPT_OFFSET
            + len(ORIGINAL_NOV4_LOAD_PROMPT)
        ] = ORIGINAL_NOV4_LOAD_PROMPT

        patched = _patched_nov4_load_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(
            patched[
                NOV4_LOAD_PROMPT_OFFSET : NOV4_LOAD_PROMPT_OFFSET
                + len(ENGLISH_NOV4_LOAD_PROMPT)
            ],
            ENGLISH_NOV4_LOAD_PROMPT,
        )

    def test_nov4_load_prompt_rejects_an_unknown_source(self) -> None:
        """Reject an unknown title-overlay revision without altering it."""
        data = bytes(NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "NOV4 load prompt"):
            _patched_nov4_load_prompt(data)

    def test_load_prompt_replaces_only_its_verified_four_byte_slot(
        self,
    ) -> None:
        """Render Load after Start without moving following NOV2 data."""
        data = bytearray(LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT) + 1)
        data[
            LOAD_PROMPT_OFFSET : LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT)
        ] = ORIGINAL_LOAD_PROMPT

        patched = _patched_load_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(ENGLISH_LOAD_PROMPT.hex().upper(), "9440CAFA")
        self.assertEqual(
            patched[
                LOAD_PROMPT_OFFSET : LOAD_PROMPT_OFFSET
                + len(ENGLISH_LOAD_PROMPT)
            ],
            ENGLISH_LOAD_PROMPT,
        )

    def test_save_prompt_replaces_only_its_verified_four_byte_slot(
        self,
    ) -> None:
        """Render Save in NOV2's visible system-menu command slot."""
        data = bytearray(SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT) + 1)
        data[
            SAVE_PROMPT_OFFSET : SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT)
        ] = ORIGINAL_SAVE_PROMPT

        patched = _patched_save_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(ENGLISH_SAVE_PROMPT.hex().upper(), "8434C1FA")
        self.assertEqual(
            patched[
                SAVE_PROMPT_OFFSET : SAVE_PROMPT_OFFSET
                + len(ENGLISH_SAVE_PROMPT)
            ],
            ENGLISH_SAVE_PROMPT,
        )

    def test_save_prompt_rejects_an_unknown_source(self) -> None:
        """Fail closed instead of writing Save onto an unknown revision."""
        data = bytes(SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "save prompt"):
            _patched_save_prompt(data)

    def test_load_prompt_rejects_an_unknown_source(self) -> None:
        """Fail closed instead of writing Load onto an unverified revision."""
        data = bytes(LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "load prompt"):
            _patched_load_prompt(data)

    def test_disk_set_error_record_is_translated_in_place(self) -> None:
        """Replace the byte-aligned double-swap retry heading."""
        source = ui.DISK_SET_ERROR_SOURCE
        start = ui.DISK_SET_ERROR_OFFSET
        data = bytearray(start + len(source) + 1)
        data[start : start + len(source)] = source

        patched = ui._patched_disk_set_error_message(bytes(data))

        self.assertEqual(len(patched), len(data))
        expected = pack_records([encode_english(ui.DISK_SET_ERROR_ENGLISH)])
        self.assertEqual(len(expected), len(source))
        self.assertEqual(patched[start : start + len(source)], expected)
        self.assertEqual(patched[:start], data[:start])
        self.assertEqual(
            patched[start + len(source) :], data[start + len(source) :]
        )
        symbols = split_records(patched, offset=start, limit=1)[0][0]
        self.assertEqual(render_english(symbols), ui.DISK_SET_ERROR_ENGLISH)

    def test_disk_set_error_record_rejects_unknown_source(self) -> None:
        """Guard the recovered source bytes before changing them."""
        data = bytes(ui.DISK_SET_ERROR_OFFSET + len(ui.DISK_SET_ERROR_SOURCE))

        with self.assertRaisesRegex(UiPatchError, "disk-set error"):
            ui._patched_disk_set_error_message(data)


class FixedMenuCopyTests(unittest.TestCase):
    """Keep the proven full command labels consistent across scenario banks."""

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
                    34: "Call",
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
                {1: "Talk", 2: "Use", 4: "Move", 22: "Open", 32: "Move"},
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
                "Part 2",
                "{CTRL:0}Side A",
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
            render_english(ui._encode_disk_prompt("Part 2")), "Part 2"
        )
        self.assertEqual(
            render_english(ui._encode_disk_prompt("{CTRL:0}Side A")),
            "{CTRL:0}Side A",
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
                    if replacement in {"Part 2", "{CTRL:0}Side A"}
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
                    62: "Jail",
                    67: "Rope",
                    68: "Lamp",
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
                    74: "Fish",
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
                    16: "Wood",
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
                78: "Aristotle",
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


if __name__ == "__main__":
    unittest.main()
