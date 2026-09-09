"""Regression tests for the production English NOV2 runtime hardening."""

from __future__ import annotations

import unittest

from time_twist.production_runtime import (
    PALETTE_DATA_RANGE,
    PRODUCTION_RUNTIME_PATCHES,
    ProductionRuntimeError,
    patch_nov2,
)


class ProductionRuntimeTests(unittest.TestCase):
    def _synthetic_nov2(self) -> bytearray:
        size = max(
            patch.file_offset + len(patch.expected)
            for patch in PRODUCTION_RUNTIME_PATCHES
        )
        data = bytearray(b"\xCC" * size)
        for patch in PRODUCTION_RUNTIME_PATCHES:
            start = patch.file_offset
            data[start : start + len(patch.expected)] = patch.expected
        return data

    def test_patches_are_size_neutral_and_source_verified(self) -> None:
        source = bytes(self._synthetic_nov2())
        patched = patch_nov2(source)
        self.assertEqual(len(patched), len(source))
        for patch in PRODUCTION_RUNTIME_PATCHES:
            start = patch.file_offset
            end = start + len(patch.replacement)
            self.assertEqual(patched[start:end], patch.replacement)

    def test_patching_is_idempotent(self) -> None:
        once = patch_nov2(bytes(self._synthetic_nov2()))
        self.assertEqual(patch_nov2(once), once)

    def test_source_drift_fails_closed(self) -> None:
        source = self._synthetic_nov2()
        patch = PRODUCTION_RUNTIME_PATCHES[1]
        source[patch.file_offset] ^= 0x01
        with self.assertRaises(ProductionRuntimeError):
            patch_nov2(bytes(source))

    def test_extended_dictionary_enters_after_native_index_reader(self) -> None:
        patch = PRODUCTION_RUNTIME_PATCHES[0]
        self.assertEqual(patch.cpu_address, 0x81D3)
        self.assertEqual(patch.expected[-3:], bytes.fromhex("4C BE 82"))
        self.assertEqual(patch.replacement[-3:], bytes.fromhex("4C C5 82"))

    def test_menu_renderer_uses_existing_eight_glyph_buffer(self) -> None:
        renderer = PRODUCTION_RUNTIME_PATCHES[1:3]
        self.assertEqual(
            [patch.cpu_address for patch in renderer],
            [0x94BB, 0x94E6],
        )
        for patch in renderer:
            self.assertEqual(patch.expected, bytes.fromhex("A9 06"))
            self.assertEqual(patch.replacement, bytes.fromhex("A9 08"))

    def test_selection_brackets_span_all_eight_visible_glyphs(self) -> None:
        patch = PRODUCTION_RUNTIME_PATCHES[3]
        self.assertEqual(patch.cpu_address, 0x98A3)
        self.assertEqual(patch.expected, bytes.fromhex("38"))
        self.assertEqual(patch.replacement, bytes.fromhex("48"))
        # Native span is six glyph cells plus one bracket cell: 6*8+8=$38.
        # Production span is eight glyph cells plus the same bracket cell.
        self.assertEqual(patch.replacement[0], 8 * 8 + 8)

    def test_runtime_patches_never_overlap_live_palette_data(self) -> None:
        palette = set(PALETTE_DATA_RANGE)
        for patch in PRODUCTION_RUNTIME_PATCHES:
            touched = set(
                range(patch.file_offset, patch.file_offset + len(patch.expected))
            )
            self.assertTrue(
                palette.isdisjoint(touched),
                f"{patch.label} overlaps NOV2 palette data",
            )


if __name__ == "__main__":
    unittest.main()
