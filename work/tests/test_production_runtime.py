"""Regression tests for the production English NOV2 runtime hardening."""

from __future__ import annotations

import unittest

from time_twist.production_runtime import (
    ADAPTIVE_DICTIONARY_RUNTIME_PATCHES,
    PALETTE_DATA_RANGE,
    PRODUCTION_RUNTIME_PATCHES,
    ProductionRuntimeError,
    patch_nov2,
)


class ProductionRuntimeTests(unittest.TestCase):
    def _synthetic_nov2(self, *, adaptive: bool = False) -> bytearray:
        patches = PRODUCTION_RUNTIME_PATCHES
        if adaptive:
            patches = (*patches, *ADAPTIVE_DICTIONARY_RUNTIME_PATCHES)
        size = max(
            patch.file_offset + len(patch.expected)
            for patch in patches
        )
        data = bytearray(b"\xCC" * size)
        for patch in patches:
            start = patch.file_offset
            data[start : start + len(patch.expected)] = patch.expected
        return data

    @staticmethod
    def _adaptive_patch(address: int):
        matches = [
            patch
            for patch in ADAPTIVE_DICTIONARY_RUNTIME_PATCHES
            if patch.cpu_address == address
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one adaptive patch at ${address:04X}")
        return matches[0]

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

    def test_dollar_sign_redirects_only_extended_code_63(self) -> None:
        patch = PRODUCTION_RUNTIME_PATCHES[1]
        self.assertEqual(patch.cpu_address, 0x8378)
        self.assertEqual(patch.expected, bytes.fromhex("AC"))
        self.assertEqual(patch.replacement, bytes.fromhex("B0"))

    def test_menu_renderer_uses_existing_eight_glyph_buffer(self) -> None:
        renderer = PRODUCTION_RUNTIME_PATCHES[2:4]
        self.assertEqual(
            [patch.cpu_address for patch in renderer],
            [0x94BC, 0x94E7],
        )
        for patch in renderer:
            self.assertEqual(patch.expected, bytes.fromhex("A9 06"))
            self.assertEqual(patch.replacement, bytes.fromhex("A9 08"))

    def test_selection_brackets_span_all_eight_visible_glyphs(self) -> None:
        patch = PRODUCTION_RUNTIME_PATCHES[4]
        self.assertEqual(patch.cpu_address, 0x98A3)
        self.assertEqual(patch.expected, bytes.fromhex("38"))
        self.assertEqual(patch.replacement, bytes.fromhex("48"))
        self.assertEqual(patch.expected[0], 6 * 8 + 8)
        self.assertEqual(patch.replacement[0], 8 * 8 + 8)

    def test_adaptive_dictionary_patch_is_size_neutral_and_idempotent(self) -> None:
        source = bytes(self._synthetic_nov2(adaptive=True))
        once = patch_nov2(source, adaptive_dictionary=True)
        twice = patch_nov2(once, adaptive_dictionary=True)
        self.assertEqual(len(once), len(source))
        self.assertEqual(twice, once)
        for patch in ADAPTIVE_DICTIONARY_RUNTIME_PATCHES:
            start = patch.file_offset
            end = start + len(patch.replacement)
            self.assertEqual(once[start:end], patch.replacement)

    def test_production_scan_limit_reaches_end_of_fds_prg_ram(self) -> None:
        patch = self._adaptive_patch(0x8142)
        self.assertEqual(patch.expected, bytes.fromhex("C9 D4"))
        self.assertEqual(patch.replacement, bytes.fromhex("C9 E0"))

    def test_top_level_decoder_always_clears_nesting_depth(self) -> None:
        branch = self._adaptive_patch(0x8154)
        stub = self._adaptive_patch(0x81FA)
        self.assertEqual(branch.expected, bytes.fromhex("A2 00 86 72 86 73"))
        self.assertEqual(branch.replacement, bytes.fromhex("4C FA 81 EA EA EA"))
        self.assertEqual(
            stub.replacement,
            bytes.fromhex("A2 00 86 71 86 72 86 73 A9 80 85 6C 4C 5E 81"),
        )

    def test_adaptive_dictionary_uses_dead_english_decoder_region(self) -> None:
        branch = self._adaptive_patch(0x8182)
        stub = self._adaptive_patch(0x81E0)
        self.assertEqual(branch.expected, bytes.fromhex("4C BE 82"))
        self.assertEqual(branch.replacement, bytes.fromhex("4C E0 81"))
        self.assertEqual(len(stub.expected), 26)
        self.assertEqual(len(stub.replacement), 26)
        self.assertIn(bytes.fromhex("20 0D 81"), stub.replacement)
        self.assertIn(bytes.fromhex("A2 08 20 28 83 CA D0 FA"), stub.replacement)
        self.assertIn(bytes.fromhex("8A 48"), stub.replacement)
        self.assertIn(bytes.fromhex("68 AA"), stub.replacement)
        self.assertTrue(stub.replacement.endswith(bytes.fromhex("4C C5 82")))

    def test_nested_dictionary_uses_depth_counter_not_boolean(self) -> None:
        enter = self._adaptive_patch(0x82C5)
        leave = self._adaptive_patch(0x8311)
        self.assertEqual(enter.expected, bytes.fromhex("A9 FF 85 71"))
        self.assertEqual(enter.replacement, bytes.fromhex("E6 71 EA EA"))
        self.assertEqual(leave.expected, bytes.fromhex("A9 00 85 71"))
        self.assertEqual(leave.replacement, bytes.fromhex("C6 71 EA EA"))

    def test_runtime_patches_never_overlap_live_palette_data(self) -> None:
        palette = set(PALETTE_DATA_RANGE)
        patches = (*PRODUCTION_RUNTIME_PATCHES, *ADAPTIVE_DICTIONARY_RUNTIME_PATCHES)
        for patch in patches:
            touched = set(
                range(patch.file_offset, patch.file_offset + len(patch.expected))
            )
            self.assertTrue(
                palette.isdisjoint(touched),
                f"{patch.label} overlaps NOV2 palette data",
            )


if __name__ == "__main__":
    unittest.main()
