"""Private-overlay integration tests for current fixed-UI text and source-verified binary-patch behavior."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.compression import expand_dictionary_symbols
from time_twist.english import encode_english, render_english
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import pack_records, split_records
from time_twist.ui import (
    DISK_PROMPT_PATCHES,
    ENGLISH_START_PROMPT,
    ENGLISH_WAIT_PROMPT,
    KOUHEN_BOOT_GUARD_BLANK_TILE,
    KOUHEN_BOOT_GUARD_CHR_OFFSET,
    KOUHEN_BOOT_GUARD_DECODED_SIZE,
    KOUHEN_BOOT_GUARD_LINES,
    KOUHEN_BOOT_GUARD_PPU_START,
    KOUHEN_BOOT_GUARD_TILE_CHARACTERS,
    KOUHEN_BOOT_GUARD_TILE_COUNT,
    KOUHEN_BOOT_GUARD_TILEMAP_END,
    KOUHEN_BOOT_GUARD_TILEMAP_OFFSET,
    NOV2_BLANK_TILE,
    NOV2_DIALOGUE_ROW_COPY,
    NOV2_EXTENDED_DICTIONARY_PATCH,
    NOV2_OPAQUE_CLEAR_PATCHES,
    NOV2_SINGLE_CHOICE_B_PATCHES,
    NOV4_START_PROMPT_OFFSET,
    ORIGINAL_START_PROMPT,
    ORIGINAL_WAIT_PROMPT,
    START_PROMPT_OFFSET,
    T22_FIXED_TEXT_END_OFFSET,
    T22_FIXED_TEXT_RECORDS,
    T22_FIXED_TEXT_START_OFFSET,
    T25_FIXED_TEXT_END_OFFSET,
    T25_FIXED_TEXT_RECORDS,
    T25_FIXED_TEXT_START_OFFSET,
    TT1A_BLOOD_TYPE_PATCHES,
    TT1A_CONFIRMATION_PATCHES,
    TT1A_MONTH_PATCHES,
    TT1B_FIXED_TEXT_END_OFFSET,
    TT1B_FIXED_TEXT_RECORDS,
    TT1B_FIXED_TEXT_START_OFFSET,
    TT2_FIXED_TEXT_END_OFFSET,
    TT2_FIXED_TEXT_RECORDS,
    TT2_FIXED_TEXT_START_OFFSET,
    TT3A_FIXED_TEXT_END_OFFSET,
    TT3A_FIXED_TEXT_RECORDS,
    TT3A_FIXED_TEXT_START_OFFSET,
    TT3B_FIXED_TEXT_END_OFFSET,
    TT3B_FIXED_TEXT_RECORDS,
    TT3B_FIXED_TEXT_START_OFFSET,
    TT4_FIXED_TEXT_END_OFFSET,
    TT4_FIXED_TEXT_RECORDS,
    TT4_FIXED_TEXT_START_OFFSET,
    TT5_FIXED_TEXT_END_OFFSET,
    TT5_FIXED_TEXT_RECORDS,
    TT5_FIXED_TEXT_START_OFFSET,
    TT6A_FIXED_TEXT_END_OFFSET,
    TT6A_FIXED_TEXT_RECORDS,
    TT6A_FIXED_TEXT_START_OFFSET,
    TT6B_FIXED_TEXT_END_OFFSET,
    TT6B_FIXED_TEXT_RECORDS,
    TT6B_FIXED_TEXT_START_OFFSET,
    TT6C_FIXED_TEXT_END_OFFSET,
    TT6C_FIXED_TEXT_RECORDS,
    TT6C_FIXED_TEXT_START_OFFSET,
    WAIT_PROMPT_OFFSET,
    WRONG_DISK_PATCHES,
    UiPatchError,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_t22_ui,
    patched_t25_ui,
    patched_tt1a_ui,
    patched_tt1b_ui,
    patched_tt2_ui,
    patched_tt3a_ui,
    patched_tt3b_ui,
    patched_tt4_ui,
    patched_tt5_ui,
    patched_tt6a_ui,
    patched_tt6b_ui,
    patched_tt6c_ui,
)

WORK_DIR = Path(__file__).resolve().parents[1]


def _record_ends(data: bytes, start: int, count: int) -> tuple[int, ...]:
    """Return every absolute record end in a byte-aligned packed table."""
    ends: list[int] = []
    offset = start
    for _ in range(count):
        _, offset = split_records(data, offset=offset, limit=1)
        ends.append(offset)
    return tuple(ends)


def _decode_kouhen_guard_tilemap(data: bytes) -> bytes:
    """Decode SON-KOUH's small $C0-$FE run format for assertions."""
    decoded = bytearray()
    offset = KOUHEN_BOOT_GUARD_TILEMAP_OFFSET
    while data[offset] != 0xFF:
        value = data[offset]
        offset += 1
        if value >= 0xC0:
            count = value & 0x3F
            decoded.extend([data[offset]] * count)
            offset += 1
        else:
            decoded.append(value)
    return bytes(decoded)


class StaticUiTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    def test_kouhen_direct_boot_guard_is_horizontal_english(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_kouhen/side0_01_SON-KOUH_DD1D.bin"
        if not path.exists():
            self.fail("Kouhen direct-boot fixture is not available")
        original = path.read_bytes()
        patched = patched_kouhen_boot_guard(original)

        self.assertEqual(len(patched), len(original))
        permitted = set(
            range(
                KOUHEN_BOOT_GUARD_TILEMAP_OFFSET, KOUHEN_BOOT_GUARD_TILEMAP_END
            )
        )
        chr_end = (
            KOUHEN_BOOT_GUARD_CHR_OFFSET + KOUHEN_BOOT_GUARD_TILE_COUNT * 8
        )
        permitted.update(range(KOUHEN_BOOT_GUARD_CHR_OFFSET, chr_end))
        changed = {
            index
            for index, (source, target) in enumerate(
                zip(original, patched, strict=True)
            )
            if source != target
        }
        self.assertTrue(changed)
        self.assertLessEqual(changed, permitted)

        tilemap = _decode_kouhen_guard_tilemap(patched)
        self.assertEqual(len(tilemap), KOUHEN_BOOT_GUARD_DECODED_SIZE)
        tile_by_character = {
            character: tile
            for tile, character in enumerate(KOUHEN_BOOT_GUARD_TILE_CHARACTERS)
        }
        nametable_start = KOUHEN_BOOT_GUARD_PPU_START - 0x2000
        expected_nonblank: set[int] = set()
        for row, text in KOUHEN_BOOT_GUARD_LINES:
            column = (32 - len(text)) // 2
            start = row * 32 + column - nametable_start
            expected = bytes(
                (
                    KOUHEN_BOOT_GUARD_BLANK_TILE
                    if character == " "
                    else tile_by_character[character]
                )
                for character in text
            )
            self.assertEqual(tilemap[start : start + len(text)], expected)
            expected_nonblank.update(
                start + index
                for index, character in enumerate(text)
                if character != " "
            )
        self.assertEqual(
            {
                index
                for index, tile in enumerate(tilemap)
                if tile != KOUHEN_BOOT_GUARD_BLANK_TILE
            },
            expected_nonblank,
        )
        blank_start = (
            KOUHEN_BOOT_GUARD_CHR_OFFSET + KOUHEN_BOOT_GUARD_BLANK_TILE * 8
        )
        self.assertEqual(patched[blank_start : blank_start + 8], b"\x00" * 8)

    def test_kouhen_direct_boot_guard_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_kouhen/side0_01_SON-KOUH_DD1D.bin"
        if not path.exists():
            self.fail("Kouhen direct-boot fixture is not available")
        modified = bytearray(path.read_bytes())
        modified[0] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_kouhen_boot_guard(bytes(modified))

    def test_start_prompt_patch_is_exactly_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(len(ORIGINAL_START_PROMPT), 6)
        self.assertEqual(len(ENGLISH_START_PROMPT), 6)
        self.assertEqual(ENGLISH_START_PROMPT.hex().upper(), "85C763700FA0")

    def test_zenpen_nov2_start_prompt_patch(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)
        end = START_PROMPT_OFFSET + len(ORIGINAL_START_PROMPT)

        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[START_PROMPT_OFFSET:end], ENGLISH_START_PROMPT
        )

    def test_zenpen_nov2_disk_prompt_patch_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)
        expected_changed = set(
            range(offset, offset + len(source))
            for offset, source, _ in DISK_PROMPT_PATCHES
        )
        expected_changed = set().union(*expected_changed)
        expected_changed.update(
            index
            for offset, source, _ in WRONG_DISK_PATCHES
            for index in range(offset, offset + len(source))
        )
        expected_changed.update(
            range(
                START_PROMPT_OFFSET,
                START_PROMPT_OFFSET + len(ORIGINAL_START_PROMPT),
            )
        )
        expected_changed.update(
            range(
                WAIT_PROMPT_OFFSET,
                WAIT_PROMPT_OFFSET + len(ORIGINAL_WAIT_PROMPT),
            )
        )
        expected_changed.update(
            patch.file_offset for patch in NOV2_OPAQUE_CLEAR_PATCHES
        )
        expected_changed.update(
            index
            for patch in NOV2_SINGLE_CHOICE_B_PATCHES
            for index in range(
                patch.file_offset,
                patch.file_offset + len(patch.expected),
            )
        )
        self.assertEqual(len(patched), len(original))
        for offset, source, english in DISK_PROMPT_PATCHES:
            replacement = pack_records([encode_english(english)])
            self.assertEqual(len(replacement), len(source))
            self.assertEqual(
                patched[offset : offset + len(source)], replacement
            )
        for offset, source, english in WRONG_DISK_PATCHES:
            replacement = pack_records([encode_english(english)])
            self.assertEqual(len(replacement), len(source))
            self.assertEqual(
                patched[offset : offset + len(source)], replacement
            )
        self.assertEqual(
            {
                index
                for index, pair in enumerate(
                    zip(original, patched, strict=True)
                )
                if pair[0] != pair[1]
            },
            {
                index
                for index in expected_changed
                if original[index] != patched[index]
            },
        )

    def test_zenpen_nov2_preserves_dialogue_rows_and_transparent_tails(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)

        for patch in NOV2_OPAQUE_CLEAR_PATCHES:
            self.assertEqual(
                original[
                    patch.file_offset : patch.file_offset + len(patch.expected)
                ],
                patch.expected,
            )
            self.assertEqual(patch.replacement, bytes((NOV2_BLANK_TILE,)))
            self.assertEqual(
                patched[
                    patch.file_offset : patch.file_offset
                    + len(patch.replacement)
                ],
                patch.replacement,
            )

        # Dialogue keeps its original transparent tail fill, avoiding phantom
        # typing.  The scroll uploader must also copy the real bottom row;
        # replacing this load with an immediate blank deleted whole lines.
        self.assertEqual(original[0x245F], 0xAC)
        self.assertEqual(patched[0x245F], 0xAC)
        offset, source = NOV2_DIALOGUE_ROW_COPY
        self.assertEqual(original[offset : offset + len(source)], source)
        self.assertEqual(patched[offset : offset + len(source)], source)

    def test_zenpen_nov2_extended_dictionary_skips_native_index_reader(
        self,
    ) -> None:
        """Resume extended refs after the native five-bit index reader."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)
        patch = NOV2_EXTENDED_DICTIONARY_PATCH

        self.assertEqual(
            original[0x22BE:0x22C5],
            bytes.fromhex("A9 00 85 3A 20 0D 81"),
        )
        self.assertEqual(original[0x22C5:0x22C8], bytes.fromhex("A9 FF 85"))
        self.assertEqual(
            patched[patch.file_offset : patch.file_offset + len(patch.replacement)],
            patch.replacement,
        )
        self.assertEqual(patch.replacement[-3:], bytes.fromhex("4C C5 82"))

    def test_zenpen_nov2_wait_prompt_patch_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)
        end = WAIT_PROMPT_OFFSET + len(ORIGINAL_WAIT_PROMPT)
        self.assertEqual(len(ENGLISH_WAIT_PROMPT), len(ORIGINAL_WAIT_PROMPT))
        self.assertEqual(patched[WAIT_PROMPT_OFFSET:end], ENGLISH_WAIT_PROMPT)
        records, record_end = split_records(ENGLISH_WAIT_PROMPT, limit=1)
        self.assertEqual(record_end, len(ENGLISH_WAIT_PROMPT))
        self.assertEqual(render_english(records[0]).rstrip(), "PLEASE WAIT...")
        self.assertNotIn("{CTRL:", render_english(records[0]))

    def test_zenpen_nov2_b_ignores_one_choice_but_keeps_normal_back(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov2_ui(original)

        for patch in NOV2_SINGLE_CHOICE_B_PATCHES:
            self.assertEqual(
                original[
                    patch.file_offset : patch.file_offset + len(patch.expected)
                ],
                patch.expected,
            )
            self.assertEqual(
                patched[
                    patch.file_offset : patch.file_offset
                    + len(patch.replacement)
                ],
                patch.replacement,
            )

        # $99DC-$99E0 retains the original saved-destination guard.  Its
        # nonzero path now detours to $6A2E.
        self.assertEqual(
            patched[0x39DC:0x39E1], bytes.fromhex("A5 9C D0 01 60")
        )
        self.assertEqual(patched[0x39E1:0x39E4], bytes.fromhex("4C 2E 6A"))

        # The helper loads the visible-choice count from $98 and decrements Y
        # only for comparison.  One choice branches to the existing RTS at
        # $6A93; larger menus retain action 4 and state $22 through $7DB8.
        helper = patched[0x0A2E:0x0A3A]
        self.assertEqual(
            helper,
            bytes.fromhex("A4 98 88 F0 60 A9 04 85 A1 4C B8 7D"),
        )
        helper_address = 0x6A2E
        branch_pc_after_operand = helper_address + 5
        self.assertEqual(branch_pc_after_operand + helper[4], 0x6A93)
        self.assertEqual(
            patched[0x1DB8:0x1DBD], bytes.fromhex("A9 22 4C 09 61")
        )

    def test_zenpen_nov4_live_start_prompt_patch(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov4_ui(original)
        end = NOV4_START_PROMPT_OFFSET + len(ORIGINAL_START_PROMPT)

        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[NOV4_START_PROMPT_OFFSET:end], ENGLISH_START_PROMPT
        )
        self.assertEqual(
            patched[:NOV4_START_PROMPT_OFFSET] + patched[end:],
            original[:NOV4_START_PROMPT_OFFSET] + original[end:],
        )

    def test_tt1a_choice_menu_patch_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_tt1a_ui(original)
        expected_changed: set[int] = set()

        self.assertEqual(len(patched), len(original))
        for offset, source, english in (
            *TT1A_BLOOD_TYPE_PATCHES,
            *TT1A_MONTH_PATCHES,
            *TT1A_CONFIRMATION_PATCHES,
        ):
            replacement = pack_records([encode_english(english)])
            self.assertEqual(len(replacement), len(source))
            self.assertEqual(
                patched[offset : offset + len(source)], replacement
            )
            expected_changed.update(range(offset, offset + len(source)))
        self.assertEqual(
            {
                index
                for index, pair in enumerate(
                    zip(original, patched, strict=True)
                )
                if pair[0] != pair[1]
            },
            {
                index
                for index in expected_changed
                if original[index] != patched[index]
            },
        )

    def test_translated_tt1a_contains_english_blood_type_choices(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translated_banks/TT1A_fixed_footprint.bin"
        if not path.exists():
            self.fail("translated TT1A fixture is not available")
        records, end = split_records(path.read_bytes(), offset=0x025B, limit=4)
        self.assertEqual(end, 0x026A)
        self.assertEqual(
            [render_english(record) for record in records],
            ["A ", "B  ", "O ", "AB   "],
        )

    def test_translated_tt1a_contains_english_month_choices(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translated_banks/TT1A_fixed_footprint.bin"
        if not path.exists():
            self.fail("translated TT1A fixture is not available")
        records, end = split_records(
            path.read_bytes(), offset=0x026A, limit=13
        )
        self.assertEqual(end, 0x02A4)
        self.assertEqual(
            [render_english(record).rstrip() for record in records],
            [
                "JAN",
                "FEB",
                "MAR",
                "APR",
                "MAY",
                "JUN",
                "JUL-DEC",
                "JUL",
                "AUG",
                "SEP",
                "OCT",
                "NOV",
                "DEC",
            ],
        )

    def test_translated_tt1a_contains_english_confirmation_choices(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translated_banks/TT1A_fixed_footprint.bin"
        if not path.exists():
            self.fail("translated TT1A fixture is not available")
        records, end = split_records(path.read_bytes(), offset=0x02A4, limit=2)
        self.assertEqual(end, 0x02AB)
        self.assertEqual(
            [render_english(record) for record in records],
            ["YES", "NO"],
        )

    def test_tt1b_fixed_menu_and_object_table_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT1B_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT1B scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt1b_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT1B_FIXED_TEXT_START_OFFSET],
            original[:TT1B_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT1B_FIXED_TEXT_END_OFFSET:],
            original[TT1B_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT1B_FIXED_TEXT_START_OFFSET,
                len(TT1B_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT1B_FIXED_TEXT_START_OFFSET,
                len(TT1B_FIXED_TEXT_RECORDS),
            ),
        )

        records, end = split_records(
            patched[TT1B_FIXED_TEXT_START_OFFSET:TT1B_FIXED_TEXT_END_OFFSET],
            limit=len(TT1B_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT1B_FIXED_TEXT_END_OFFSET - TT1B_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT1B_FIXED_TEXT_RECORDS)
        self.assertEqual(rendered[:3], ("LOOK", "TALK", "MOVE"))
        self.assertEqual(rendered[5], "MUSEUM")
        self.assertEqual(rendered[8:10], ("EAST", "WEST"))
        self.assertEqual(rendered[4], "AROUND")
        self.assertEqual(rendered[40], "GROUND")
        self.assertEqual(rendered[48], "MEMBER")
        self.assertEqual(
            rendered[45:53],
            (
                "ASK",
                "CHURCH",
                "PRIEST",
                "MEMBER",
                "SERMON",
                "DEVIL",
                "BELT",
                "RUN",
            ),
        )

    def test_tt1b_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT1B_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT1B scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[TT1B_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_tt1b_ui(bytes(damaged))

    def test_tt2_fixed_menu_and_quiz_table_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT2_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT2 scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt2_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT2_FIXED_TEXT_START_OFFSET],
            original[:TT2_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT2_FIXED_TEXT_END_OFFSET:],
            original[TT2_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT2_FIXED_TEXT_START_OFFSET,
                len(TT2_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT2_FIXED_TEXT_START_OFFSET,
                len(TT2_FIXED_TEXT_RECORDS),
            ),
        )

        records, end = split_records(
            patched[TT2_FIXED_TEXT_START_OFFSET:TT2_FIXED_TEXT_END_OFFSET],
            limit=len(TT2_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT2_FIXED_TEXT_END_OFFSET - TT2_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT2_FIXED_TEXT_RECORDS)
        self.assertEqual(
            rendered[0:8],
            ("SE", "SAY", "GT", "USE", "AS", "SN", "GO", "IN"),
        )
        self.assertEqual(
            rendered[26:31],
            ("DAM", "JERUS", "CRI", "100", "PAC"),
        )

    def test_tt2_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT2_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT2 scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[TT2_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_tt2_ui(bytes(damaged))

    def test_t22_fixed_menu_and_object_table_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/T22_english_scenario.bin"
        if not path.exists():
            self.fail("translated T22 scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_t22_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:T22_FIXED_TEXT_START_OFFSET],
            original[:T22_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[T22_FIXED_TEXT_END_OFFSET:],
            original[T22_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                T22_FIXED_TEXT_START_OFFSET,
                len(T22_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                T22_FIXED_TEXT_START_OFFSET,
                len(T22_FIXED_TEXT_RECORDS),
            ),
        )

        records, end = split_records(
            patched[T22_FIXED_TEXT_START_OFFSET:T22_FIXED_TEXT_END_OFFSET],
            limit=len(T22_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            T22_FIXED_TEXT_END_OFFSET - T22_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, T22_FIXED_TEXT_RECORDS)
        self.assertEqual(
            rendered[0:5],
            ("SE", "SAY", "USE", "AS", "GO"),
        )
        self.assertEqual(
            rendered[26:33],
            ("SCAFFOLD", "Jeanne", "Bishop", "Lugot", "CROWD", "PRIS", "GO"),
        )

    def test_t22_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/T22_english_scenario.bin"
        if not path.exists():
            self.fail("translated T22 scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[T22_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_t22_ui(bytes(damaged))

    def test_tt3a_fixed_menu_and_quiz_table_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT3A_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT3A scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt3a_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT3A_FIXED_TEXT_START_OFFSET],
            original[:TT3A_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT3A_FIXED_TEXT_END_OFFSET:],
            original[TT3A_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT3A_FIXED_TEXT_START_OFFSET,
                len(TT3A_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT3A_FIXED_TEXT_START_OFFSET,
                len(TT3A_FIXED_TEXT_RECORDS),
            ),
        )
        records, end = split_records(
            patched[TT3A_FIXED_TEXT_START_OFFSET:TT3A_FIXED_TEXT_END_OFFSET],
            limit=len(TT3A_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT3A_FIXED_TEXT_END_OFFSET - TT3A_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT3A_FIXED_TEXT_RECORDS)
        self.assertEqual(
            tuple(rendered[index] for index in (70, 73, 77, 79, 86)),
            ("Gestapo", "RESIST", "UBOAT", "GABN", "EISEN"),
        )

    def test_tt3b_fixed_menu_and_battle_table_is_size_neutral(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT3B_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT3B scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt3b_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT3B_FIXED_TEXT_START_OFFSET],
            original[:TT3B_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT3B_FIXED_TEXT_END_OFFSET:],
            original[TT3B_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT3B_FIXED_TEXT_START_OFFSET,
                len(TT3B_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT3B_FIXED_TEXT_START_OFFSET,
                len(TT3B_FIXED_TEXT_RECORDS),
            ),
        )
        records, end = split_records(
            patched[TT3B_FIXED_TEXT_START_OFFSET:TT3B_FIXED_TEXT_END_OFFSET],
            limit=len(TT3B_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT3B_FIXED_TEXT_END_OFFSET - TT3B_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT3B_FIXED_TEXT_RECORDS)
        self.assertEqual(
            rendered[13:18],
            ("FGT", "GUARD", "RUN", "AS", "RD"),
        )

    def test_tt3_fixed_tables_reject_unknown_sources(self) -> None:
        """Verify the current contract described by this regression test."""
        fixtures = (
            (
                WORK_DIR / "build/TT3A_english_scenario.bin",
                TT3A_FIXED_TEXT_START_OFFSET,
                patched_tt3a_ui,
            ),
            (
                WORK_DIR / "build/TT3B_english_scenario.bin",
                TT3B_FIXED_TEXT_START_OFFSET,
                patched_tt3b_ui,
            ),
        )
        if not all(path.exists() for path, _, _ in fixtures):
            self.fail("translated TT3 fixtures are not available")
        for path, offset, patcher in fixtures:
            with self.subTest(bank=path.stem):
                damaged = bytearray(path.read_bytes())
                damaged[offset] ^= 0x01
                with self.assertRaises(UiPatchError):
                    patcher(bytes(damaged))

    def test_tt4_fixed_table_preserves_every_record_address(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT4_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT4 scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt4_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT4_FIXED_TEXT_START_OFFSET],
            original[:TT4_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT4_FIXED_TEXT_END_OFFSET:],
            original[TT4_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT4_FIXED_TEXT_START_OFFSET,
                len(TT4_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT4_FIXED_TEXT_START_OFFSET,
                len(TT4_FIXED_TEXT_RECORDS),
            ),
        )
        records, end = split_records(
            patched[TT4_FIXED_TEXT_START_OFFSET:TT4_FIXED_TEXT_END_OFFSET],
            limit=len(TT4_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT4_FIXED_TEXT_END_OFFSET - TT4_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT4_FIXED_TEXT_RECORDS)
        self.assertEqual(
            tuple(rendered[index] for index in (77, 81, 83, 90, 93)),
            ("POL", "SPAR", "HERAC", "PARTH", "FIG"),
        )

    def test_tt4_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT4_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT4 scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[TT4_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_tt4_ui(bytes(damaged))

    def test_tt5_fixed_table_preserves_every_record_address(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT5_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT5 scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_tt5_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:TT5_FIXED_TEXT_START_OFFSET],
            original[:TT5_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[TT5_FIXED_TEXT_END_OFFSET:],
            original[TT5_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                TT5_FIXED_TEXT_START_OFFSET,
                len(TT5_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                TT5_FIXED_TEXT_START_OFFSET,
                len(TT5_FIXED_TEXT_RECORDS),
            ),
        )
        records, end = split_records(
            patched[TT5_FIXED_TEXT_START_OFFSET:TT5_FIXED_TEXT_END_OFFSET],
            limit=len(TT5_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            TT5_FIXED_TEXT_END_OFFSET - TT5_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, TT5_FIXED_TEXT_RECORDS)
        self.assertEqual(
            tuple(rendered[index] for index in (56, 57, 62, 68, 71, 74)),
            ("MARINE", "CAV", "STOWE", "RUSH", "GIN", "AIR"),
        )
        self.assertEqual(
            rendered[79:82],
            ("CW", "SHP", "PG"),
        )

    def test_tt5_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/TT5_english_scenario.bin"
        if not path.exists():
            self.fail("translated TT5 scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[TT5_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_tt5_ui(bytes(damaged))

    def test_t25_fixed_table_preserves_every_record_address(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/T25_english_scenario.bin"
        if not path.exists():
            self.fail("translated T25 scenario fixture is not available")
        original = path.read_bytes()
        patched = patched_t25_ui(original)
        self.assertEqual(len(patched), len(original))
        self.assertEqual(
            patched[:T25_FIXED_TEXT_START_OFFSET],
            original[:T25_FIXED_TEXT_START_OFFSET],
        )
        self.assertEqual(
            patched[T25_FIXED_TEXT_END_OFFSET:],
            original[T25_FIXED_TEXT_END_OFFSET:],
        )
        self.assertEqual(
            _record_ends(
                patched,
                T25_FIXED_TEXT_START_OFFSET,
                len(T25_FIXED_TEXT_RECORDS),
            ),
            _record_ends(
                original,
                T25_FIXED_TEXT_START_OFFSET,
                len(T25_FIXED_TEXT_RECORDS),
            ),
        )
        records, end = split_records(
            patched[T25_FIXED_TEXT_START_OFFSET:T25_FIXED_TEXT_END_OFFSET],
            limit=len(T25_FIXED_TEXT_RECORDS),
        )
        self.assertEqual(
            end,
            T25_FIXED_TEXT_END_OFFSET - T25_FIXED_TEXT_START_OFFSET,
        )
        dictionary = parse_scenario_bank(path).dictionary
        rendered = tuple(
            render_english(
                expand_dictionary_symbols(record, dictionary)
            ).rstrip()
            for record in records
        )
        self.assertEqual(rendered, T25_FIXED_TEXT_RECORDS)
        self.assertEqual(
            rendered[35:42],
            ("BOAT", "COY", "RV", "ME", "COY1", "COY2", "COY3"),
        )

    def test_t25_fixed_table_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "build/T25_english_scenario.bin"
        if not path.exists():
            self.fail("translated T25 scenario fixture is not available")
        damaged = bytearray(path.read_bytes())
        damaged[T25_FIXED_TEXT_START_OFFSET] ^= 0x01
        with self.assertRaises(UiPatchError):
            patched_t25_ui(bytes(damaged))

    def test_tt6_fixed_tables_preserve_every_record_address(self) -> None:
        """Verify the current contract described by this regression test."""
        fixtures = (
            (
                "TT6A",
                TT6A_FIXED_TEXT_START_OFFSET,
                TT6A_FIXED_TEXT_END_OFFSET,
                TT6A_FIXED_TEXT_RECORDS,
                patched_tt6a_ui,
            ),
            (
                "TT6B",
                TT6B_FIXED_TEXT_START_OFFSET,
                TT6B_FIXED_TEXT_END_OFFSET,
                TT6B_FIXED_TEXT_RECORDS,
                patched_tt6b_ui,
            ),
            (
                "TT6C",
                TT6C_FIXED_TEXT_START_OFFSET,
                TT6C_FIXED_TEXT_END_OFFSET,
                TT6C_FIXED_TEXT_RECORDS,
                patched_tt6c_ui,
            ),
        )
        for bank_name, start, end_offset, labels, patcher in fixtures:
            path = WORK_DIR / f"build/{bank_name}_english_scenario.bin"
            if not path.exists():
                self.fail(f"translated {bank_name} fixture is not available")
            with self.subTest(bank=bank_name):
                original = path.read_bytes()
                patched = patcher(original)
                self.assertEqual(len(patched), len(original))
                self.assertEqual(patched[:start], original[:start])
                self.assertEqual(patched[end_offset:], original[end_offset:])
                self.assertEqual(
                    _record_ends(patched, start, len(labels)),
                    _record_ends(original, start, len(labels)),
                )
                records, parsed_end = split_records(
                    patched[start:end_offset], limit=len(labels)
                )
                self.assertEqual(parsed_end, end_offset - start)
                dictionary = parse_scenario_bank(path).dictionary
                rendered = tuple(
                    render_english(
                        expand_dictionary_symbols(record, dictionary)
                    ).rstrip()
                    for record in records
                )
                self.assertEqual(rendered, labels)

    def test_tt6_fixed_tables_reject_unknown_sources(self) -> None:
        """Verify the current contract described by this regression test."""
        fixtures = (
            ("TT6A", TT6A_FIXED_TEXT_START_OFFSET, patched_tt6a_ui),
            ("TT6B", TT6B_FIXED_TEXT_START_OFFSET, patched_tt6b_ui),
            ("TT6C", TT6C_FIXED_TEXT_START_OFFSET, patched_tt6c_ui),
        )
        for bank_name, offset, patcher in fixtures:
            path = WORK_DIR / f"build/{bank_name}_english_scenario.bin"
            if not path.exists():
                self.fail(f"translated {bank_name} fixture is not available")
            with self.subTest(bank=bank_name):
                damaged = bytearray(path.read_bytes())
                damaged[offset] ^= 0x01
                with self.assertRaises(UiPatchError):
                    patcher(bytes(damaged))

    def test_start_prompt_patch_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        data = bytearray(START_PROMPT_OFFSET + len(ORIGINAL_START_PROMPT))
        with self.assertRaises(UiPatchError):
            patched_nov2_ui(bytes(data))


if __name__ == "__main__":
    unittest.main()
