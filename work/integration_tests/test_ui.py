"""Private-overlay integration tests for current fixed-UI text and source-verified binary-patch behavior."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.english import encode_english, render_english
from time_twist.textcodec import pack_records, split_records
from time_twist.ui import (
    DISK_NUMBER_ERROR_PATCHES,
    DISK_PROMPT_PATCHES,
    DISK_SET_ERROR_OFFSET,
    DISK_SET_ERROR_SOURCE,
    ENGLISH_NOV4_LOAD_PROMPT,
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
    LOAD_PROMPT_OFFSET,
    NOV2_BLANK_TILE,
    NOV2_DIALOGUE_ROW_COPY,
    NOV2_EXTENDED_DICTIONARY_PATCH,
    NOV2_OPAQUE_CLEAR_PATCHES,
    NOV2_SAVE_SYSTEM_PATCHES,
    NOV2_SINGLE_CHOICE_B_PATCHES,
    NOV4_LOAD_PROMPT_OFFSET,
    NOV4_START_PROMPT_OFFSET,
    ORIGINAL_LOAD_PROMPT,
    ORIGINAL_NOV4_LOAD_PROMPT,
    ORIGINAL_SAVE_PROMPT,
    ORIGINAL_START_PROMPT,
    ORIGINAL_WAIT_PROMPT,
    SAVE_PROMPT_OFFSET,
    SIDE_NUMBER_ERROR_PATCHES,
    START_PROMPT_OFFSET,
    TT1A_BLOOD_TYPE_PATCHES,
    TT1A_CONFIRMATION_PATCHES,
    TT1A_MONTH_PATCHES,
    WAIT_PROMPT_OFFSET,
    WRONG_DISK_PATCHES,
    UiPatchError,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_tt1a_ui,
)

WORK_DIR = Path(__file__).resolve().parents[1]


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
        self.assertEqual(ENGLISH_START_PROMPT.hex().upper(), "8420C9080FA0")

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
            index
            for offset, source, _ in NOV2_SAVE_SYSTEM_PATCHES
            for index in range(offset, offset + len(source))
        )
        expected_changed.update(
            range(
                DISK_SET_ERROR_OFFSET,
                DISK_SET_ERROR_OFFSET + len(DISK_SET_ERROR_SOURCE),
            )
        )
        expected_changed.update(
            index
            for offset, source, _ in SIDE_NUMBER_ERROR_PATCHES
            for index in range(offset, offset + len(source))
        )
        expected_changed.update(
            index
            for offset, source, _ in DISK_NUMBER_ERROR_PATCHES
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
            range(
                SAVE_PROMPT_OFFSET,
                SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT),
            )
        )
        expected_changed.update(
            range(
                LOAD_PROMPT_OFFSET,
                LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT),
            )
        )
        expected_changed.update(
            range(
                NOV2_EXTENDED_DICTIONARY_PATCH.file_offset,
                NOV2_EXTENDED_DICTIONARY_PATCH.file_offset
                + len(NOV2_EXTENDED_DICTIONARY_PATCH.expected),
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
        self.assertEqual(render_english(records[0]).rstrip(), "Please wait...")
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
        load_end = NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT)
        self.assertEqual(
            patched[NOV4_LOAD_PROMPT_OFFSET:load_end],
            ENGLISH_NOV4_LOAD_PROMPT,
        )
        self.assertEqual(
            patched[:NOV4_START_PROMPT_OFFSET] + patched[load_end:],
            original[:NOV4_START_PROMPT_OFFSET] + original[load_end:],
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
            symbols = encode_english(english)
            common_space = encode_english(" ")[0]
            while len(pack_records((symbols,))) < len(source):
                symbols = (*symbols, common_space)
            replacement = pack_records((symbols,))
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

    def test_start_prompt_patch_rejects_unknown_source(self) -> None:
        """Verify the current contract described by this regression test."""
        data = bytearray(START_PROMPT_OFFSET + len(ORIGINAL_START_PROMPT))
        with self.assertRaises(UiPatchError):
            patched_nov2_ui(bytes(data))


if __name__ == "__main__":
    unittest.main()
