"""Regression tests for the recovered NOV2 save-system text."""

from __future__ import annotations

import unittest

from time_twist import ui
from time_twist.english import encode_english
from time_twist.textcodec import pack_records


class Nov2SaveSystemTests(unittest.TestCase):
    """Protect the six source-verified NOV2 save-system replacements."""

    def test_replacements_keep_exact_source_sizes(self) -> None:
        """Keep the reviewed English and every fixed packed allocation."""
        self.assertEqual(
            tuple(replacement for _, _, replacement in ui.NOV2_SAVE_SYSTEM_PATCHES),
            (
                "A RAM Save{CTRL:0}B Disk{CTRL:0}Select Cancel ",
                "Saving{CTRL:0}to disk. ",
                "Chapter",
                "Disk error",
                "Store",
                "Fetch",
            ),
        )
        for offset, original, replacement in ui.NOV2_SAVE_SYSTEM_PATCHES:
            with self.subTest(offset=offset, replacement=replacement):
                self.assertEqual(
                    len(pack_records([encode_english(replacement)])),
                    len(original),
                )

    def test_patcher_replaces_only_verified_source_slots(self) -> None:
        """Patch a synthetic NOV2 image without changing its total size."""
        size = max(
            offset + len(original)
            for offset, original, _ in ui.NOV2_SAVE_SYSTEM_PATCHES
        )
        source = bytearray(size)
        for offset, original, _ in ui.NOV2_SAVE_SYSTEM_PATCHES:
            source[offset : offset + len(original)] = original

        patched = ui._patched_save_system_text(bytes(source))
        self.assertEqual(len(patched), len(source))
        for offset, original, replacement in ui.NOV2_SAVE_SYSTEM_PATCHES:
            expected = pack_records([encode_english(replacement)])
            self.assertEqual(patched[offset : offset + len(original)], expected)

    def test_patcher_rejects_source_drift(self) -> None:
        """Fail closed if any supposedly immutable source slot changes."""
        size = max(
            offset + len(original)
            for offset, original, _ in ui.NOV2_SAVE_SYSTEM_PATCHES
        )
        source = bytearray(size)
        for offset, original, _ in ui.NOV2_SAVE_SYSTEM_PATCHES:
            source[offset : offset + len(original)] = original
        first_offset = ui.NOV2_SAVE_SYSTEM_PATCHES[0][0]
        source[first_offset] ^= 0x01

        with self.assertRaisesRegex(ui.UiPatchError, "does not match source"):
            ui._patched_save_system_text(bytes(source))


if __name__ == "__main__":
    unittest.main()
