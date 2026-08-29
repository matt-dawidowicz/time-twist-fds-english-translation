"""Private integration tests for current fixed UI and runtime patch behavior."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import time_twist.ui as ui
from time_twist.english import encode_english, render_english
from time_twist.textcodec import pack_records, split_records

WORK_DIR = Path(__file__).resolve().parents[1]
SCENARIO_SOURCES = {
    "TT1B": WORK_DIR / "extracted_zenpen/side1_00_TT1B_A200.bin",
    "TT2": WORK_DIR / "extracted_zenpen/side1_02_TT2_A200.bin",
    "T22": WORK_DIR / "extracted_zenpen/side1_03_T22_A200.bin",
    "TT3A": WORK_DIR / "extracted_zenpen/side0_01_TT3A_A200.bin",
    "TT3B": WORK_DIR / "extracted_zenpen/side0_02_TT3B_A200.bin",
    "TT4": WORK_DIR / "extracted_kouhen/side1_00_TT4_A200.bin",
    "TT5": WORK_DIR / "extracted_kouhen/side1_01_TT5_A200.bin",
    "T25": WORK_DIR / "extracted_kouhen/side1_02_T25_A200.bin",
    "TT6A": WORK_DIR / "extracted_kouhen/side0_04_TT6A_A200.bin",
    "TT6B": WORK_DIR / "extracted_kouhen/side0_03_TT6B_A200.bin",
    "TT6C": WORK_DIR / "extracted_kouhen/side0_02_TT6C_A200.bin",
}
SCENARIO_LOAD_ADDRESS = 0xA200


def _decode_kouhen_guard_tilemap(data: bytes) -> bytes:
    """Decode SON-KOUH's small $C0-$FE run format for assertions."""
    decoded = bytearray()
    offset = ui.KOUHEN_BOOT_GUARD_TILEMAP_OFFSET
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


def _changed_indices(source: bytes, target: bytes) -> set[int]:
    """Return all byte positions changed by a same-size patch."""
    if len(source) != len(target):
        raise AssertionError("patch changed component size")
    return {
        index
        for index, (before, after) in enumerate(
            zip(source, target, strict=True)
        )
        if before != after
    }


class StaticUiTests(unittest.TestCase):
    """Protect the UI transformations used by the canonical release."""

    def test_kouhen_direct_boot_guard_is_horizontal_english(self) -> None:
        """Patch only the owned SON-KOUH tilemap/CHR regions."""
        path = WORK_DIR / "extracted_kouhen/side0_01_SON-KOUH_DD1D.bin"
        original = path.read_bytes()
        patched = ui.patched_kouhen_boot_guard(original)
        self.assertEqual(len(patched), len(original))

        permitted = set(
            range(
                ui.KOUHEN_BOOT_GUARD_TILEMAP_OFFSET,
                ui.KOUHEN_BOOT_GUARD_TILEMAP_END,
            )
        )
        chr_end = (
            ui.KOUHEN_BOOT_GUARD_CHR_OFFSET
            + ui.KOUHEN_BOOT_GUARD_TILE_COUNT * 8
        )
        permitted.update(range(ui.KOUHEN_BOOT_GUARD_CHR_OFFSET, chr_end))
        changed = _changed_indices(original, patched)
        self.assertTrue(changed)
        self.assertLessEqual(changed, permitted)

        tilemap = _decode_kouhen_guard_tilemap(patched)
        self.assertEqual(len(tilemap), ui.KOUHEN_BOOT_GUARD_DECODED_SIZE)
        tile_by_character = {
            character: tile
            for tile, character in enumerate(
                ui.KOUHEN_BOOT_GUARD_TILE_CHARACTERS
            )
        }
        nametable_start = ui.KOUHEN_BOOT_GUARD_PPU_START - 0x2000
        for row, text in ui.KOUHEN_BOOT_GUARD_LINES:
            column = (32 - len(text)) // 2
            start = row * 32 + column - nametable_start
            expected = bytes(
                ui.KOUHEN_BOOT_GUARD_BLANK_TILE
                if character == " "
                else tile_by_character[character]
                for character in text
            )
            self.assertEqual(tilemap[start : start + len(text)], expected)

        damaged = bytearray(original)
        damaged[0] ^= 0x01
        with self.assertRaises(ui.UiPatchError):
            ui.patched_kouhen_boot_guard(bytes(damaged))

    def test_nov2_patch_set_is_size_neutral_and_scoped(self) -> None:
        """Verify all current NOV2 text/code patches and their owned bytes."""
        path = WORK_DIR / "extracted_zenpen/side0_06_NOV2_6000.bin"
        original = path.read_bytes()
        patched = ui.patched_nov2_ui(original)
        self.assertEqual(len(patched), len(original))

        permitted: set[int] = set()

        def own(offset: int, size: int) -> None:
            permitted.update(range(offset, offset + size))

        for offset, source, english in ui.DISK_PROMPT_PATCHES:
            replacement = pack_records((encode_english(english),))
            self.assertEqual(len(replacement), len(source))
            self.assertEqual(patched[offset : offset + len(source)], replacement)
            own(offset, len(source))

        disk_set = pack_records((encode_english(ui.DISK_SET_ERROR_ENGLISH),))
        self.assertEqual(len(disk_set), len(ui.DISK_SET_ERROR_SOURCE))
        self.assertEqual(
            patched[
                ui.DISK_SET_ERROR_OFFSET : ui.DISK_SET_ERROR_OFFSET
                + len(disk_set)
            ],
            disk_set,
        )
        own(ui.DISK_SET_ERROR_OFFSET, len(ui.DISK_SET_ERROR_SOURCE))

        for collection in (
            ui.SIDE_NUMBER_ERROR_PATCHES,
            ui.DISK_NUMBER_ERROR_PATCHES,
            ui.WRONG_DISK_PATCHES,
        ):
            for offset, source, english in collection:
                replacement = pack_records((encode_english(english),))
                self.assertEqual(len(replacement), len(source))
                self.assertEqual(
                    patched[offset : offset + len(source)], replacement
                )
                own(offset, len(source))

        fixed_records = (
            (
                ui.WAIT_PROMPT_OFFSET,
                ui.ORIGINAL_WAIT_PROMPT,
                ui.ENGLISH_WAIT_PROMPT,
            ),
            (
                ui.START_PROMPT_OFFSET,
                ui.ORIGINAL_START_PROMPT,
                ui.ENGLISH_START_PROMPT,
            ),
            (
                ui.SAVE_PROMPT_OFFSET,
                ui.ORIGINAL_SAVE_PROMPT,
                ui.ENGLISH_SAVE_PROMPT,
            ),
            (
                ui.LOAD_PROMPT_OFFSET,
                ui.ORIGINAL_LOAD_PROMPT,
                ui.ENGLISH_LOAD_PROMPT,
            ),
        )
        for offset, source, replacement in fixed_records:
            self.assertEqual(len(replacement), len(source))
            self.assertEqual(
                patched[offset : offset + len(source)], replacement
            )
            own(offset, len(source))

        wait_records, wait_end = split_records(
            ui.ENGLISH_WAIT_PROMPT,
            limit=1,
        )
        self.assertEqual(wait_end, len(ui.ENGLISH_WAIT_PROMPT))
        self.assertEqual(
            render_english(wait_records[0]).rstrip(),
            "Please wait...",
        )

        for patch in ui.NOV2_OPAQUE_CLEAR_PATCHES:
            self.assertEqual(
                patched[
                    patch.file_offset : patch.file_offset
                    + len(patch.replacement)
                ],
                patch.replacement,
            )
            own(patch.file_offset, len(patch.expected))

        dictionary_patch = ui.NOV2_EXTENDED_DICTIONARY_PATCH
        self.assertEqual(
            patched[
                dictionary_patch.file_offset : dictionary_patch.file_offset
                + len(dictionary_patch.replacement)
            ],
            dictionary_patch.replacement,
        )
        own(dictionary_patch.file_offset, len(dictionary_patch.expected))

        for patch in ui.NOV2_SINGLE_CHOICE_B_PATCHES:
            self.assertEqual(
                patched[
                    patch.file_offset : patch.file_offset
                    + len(patch.replacement)
                ],
                patch.replacement,
            )
            own(patch.file_offset, len(patch.expected))

        dialogue_offset, dialogue_source = ui.NOV2_DIALOGUE_ROW_COPY
        self.assertEqual(
            patched[
                dialogue_offset : dialogue_offset + len(dialogue_source)
            ],
            dialogue_source,
        )
        self.assertLessEqual(_changed_indices(original, patched), permitted)

        damaged = bytearray(original)
        damaged[ui.START_PROMPT_OFFSET] ^= 0x01
        with self.assertRaises(ui.UiPatchError):
            ui.patched_nov2_ui(bytes(damaged))

    def test_nov4_patches_start_and_load_only(self) -> None:
        """Keep both title-menu choices translated without moving NOV4 data."""
        path = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        original = path.read_bytes()
        patched = ui.patched_nov4_ui(original)
        self.assertEqual(len(patched), len(original))

        start_end = ui.NOV4_START_PROMPT_OFFSET + len(ui.ORIGINAL_START_PROMPT)
        load_end = (
            ui.NOV4_LOAD_PROMPT_OFFSET + len(ui.ORIGINAL_NOV4_LOAD_PROMPT)
        )
        self.assertEqual(
            patched[ui.NOV4_START_PROMPT_OFFSET:start_end],
            ui.ENGLISH_START_PROMPT,
        )
        self.assertEqual(
            patched[ui.NOV4_LOAD_PROMPT_OFFSET:load_end],
            ui.ENGLISH_NOV4_LOAD_PROMPT,
        )
        permitted = set(range(ui.NOV4_START_PROMPT_OFFSET, start_end))
        permitted.update(range(ui.NOV4_LOAD_PROMPT_OFFSET, load_end))
        self.assertLessEqual(_changed_indices(original, patched), permitted)

    def test_tt1a_choice_tables_preserve_every_fixed_slot(self) -> None:
        """Patch mixed-case TT1A choices inside their original allocations."""
        path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        original = path.read_bytes()
        patched = ui.patched_tt1a_ui(original)
        self.assertEqual(len(patched), len(original))

        permitted: set[int] = set()
        for offset, source, english in (
            *ui.TT1A_BLOOD_TYPE_PATCHES,
            *ui.TT1A_MONTH_PATCHES,
            *ui.TT1A_CONFIRMATION_PATCHES,
        ):
            records, end = split_records(patched, offset=offset, limit=1)
            self.assertEqual(end, offset + len(source))
            self.assertEqual(render_english(records[0]).rstrip(), english)
            permitted.update(range(offset, offset + len(source)))
        self.assertLessEqual(_changed_indices(original, patched), permitted)

    def test_relocated_menu_sources_match_the_locked_native_tables(self) -> None:
        """Protect source hashes and page-table boundaries for relocated menus."""
        self.assertEqual(set(SCENARIO_SOURCES), set(ui.FIXED_RECORD_TABLE_SPECS))
        for bank_name, path in SCENARIO_SOURCES.items():
            with self.subTest(bank=bank_name):
                data = path.read_bytes()
                spec = ui.FIXED_RECORD_TABLE_SPECS[bank_name]
                source = data[spec.start : spec.end]
                self.assertEqual(
                    hashlib.sha256(source).hexdigest().upper(),
                    spec.source_sha256,
                )
                base = int.from_bytes(data[0x14:0x16], "little")
                page = int.from_bytes(data[0x1A:0x1C], "little")
                self.assertEqual(base - SCENARIO_LOAD_ADDRESS, spec.start)
                self.assertEqual(page - SCENARIO_LOAD_ADDRESS, spec.end)
                self.assertEqual(
                    ui.fixed_record_table_page_pointer_bytes(bank_name),
                    2 * ((len(spec.records) - 1) // 32),
                )


if __name__ == "__main__":
    unittest.main()
