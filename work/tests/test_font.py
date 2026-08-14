"""Regression tests for current deterministic English font behavior."""

from __future__ import annotations

import hashlib
import unittest
from unittest import mock

from time_twist.font import (
    EXTENDED_TILE_IDS,
    NOV4_FONT_BASE_OFFSET,
    PIXEL_FONT_5X7,
    SUPPORTED_NOV4_FONT_SOURCE_SHA256,
    patched_nov4_font,
    render_glyph,
)


class PixelFontTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    def test_title_case_start_intermediate_is_explicitly_allowlisted(
        self,
    ) -> None:
        """Permit only the recovered NOV4 state produced by the Start patch."""
        self.assertIn(
            "A1F06D72FBEA6C695999A1A3419E0E07787852A4AF30872A2348C2B1FF06EE76",
            SUPPORTED_NOV4_FONT_SOURCE_SHA256,
        )

    def test_title_menu_load_intermediate_is_explicitly_allowlisted(
        self,
    ) -> None:
        """Permit only the guarded NOV4 state with both title choices patched."""
        self.assertIn(
            "D84D037891E41BCAC93A91E81ABA34F660272490764DE8E6E2E8F81C81DE9232",
            SUPPORTED_NOV4_FONT_SOURCE_SHA256,
        )

    def test_apostrophe_is_a_closing_mark(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(
            PIXEL_FONT_5X7["'"],
            (
                "00100",
                "00100",
                "01000",
                "00000",
                "00000",
                "00000",
                "00000",
            ),
        )
        self.assertEqual(len(render_glyph("'")), 8)

    def test_patched_font_keeps_the_active_x_and_z_glyphs(self) -> None:
        """Never replace active uppercase letters with prompt-only glyphs."""
        source = bytes(NOV4_FONT_BASE_OFFSET + (0xFE + 1) * 8)
        source_hash = hashlib.sha256(source).hexdigest().upper()
        with mock.patch(
            "time_twist.font.SUPPORTED_NOV4_FONT_SOURCE_SHA256",
            frozenset({source_hash}),
        ):
            patched = patched_nov4_font(source)
        for code, character in ((42, "X"), (43, "Z")):
            with self.subTest(character=character):
                tile_id = EXTENDED_TILE_IDS[code]
                offset = NOV4_FONT_BASE_OFFSET + tile_id * 8
                self.assertEqual(
                    patched[offset : offset + 8], render_glyph(character)
                )

    def test_patched_font_preserves_the_title_background_tile(self) -> None:
        """Do not repurpose NOV4 tile $AC, which the title nametable draws."""
        source = bytes(NOV4_FONT_BASE_OFFSET + (0xFE + 1) * 8)
        source_hash = hashlib.sha256(source).hexdigest().upper()
        with mock.patch(
            "time_twist.font.SUPPORTED_NOV4_FONT_SOURCE_SHA256",
            frozenset({source_hash}),
        ):
            patched = patched_nov4_font(source)
        tile_id = EXTENDED_TILE_IDS[63]
        offset = NOV4_FONT_BASE_OFFSET + tile_id * 8
        self.assertEqual(
            patched[offset : offset + 8], source[offset : offset + 8]
        )


if __name__ == "__main__":
    unittest.main()
