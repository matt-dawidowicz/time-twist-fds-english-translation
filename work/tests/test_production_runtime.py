"""Regression tests for the production English NOV2 runtime hardening."""

from __future__ import annotations

import unittest

from time_twist.production_runtime import (
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

    def test_variable_width_renderer_has_zero_count_guard(self) -> None:
        renderer = next(
            patch
            for patch in PRODUCTION_RUNTIME_PATCHES
            if patch.cpu_address == 0x949E
        )
        self.assertIn(
            bytes.fromhex("8A 4A D0 02 A9 06 85 31 A2 00"),
            renderer.replacement,
        )


if __name__ == "__main__":
    unittest.main()
