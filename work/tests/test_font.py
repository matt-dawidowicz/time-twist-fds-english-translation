from __future__ import annotations

import hashlib
import unittest
from unittest import mock

from time_twist.font import (
    EXTENDED_TILE_IDS,
    NOV4_FONT_BASE_OFFSET,
    PART_2_LIGATURE_CODE,
    PART_2_LIGATURE_TILE_ID,
    PIXEL_FONT_5X7,
    SIDE_A_LIGATURE_CODE,
    SIDE_A_LIGATURE_TILE_ID,
    SUPPORTED_NOV4_FONT_SOURCE_SHA256,
    patched_nov4_font,
    render_compact_suffix,
    render_glyph,
)


class PixelFontTests(unittest.TestCase):
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

    def test_disk_prompt_ligature_tiles_are_distinct_right_aligned_suffixes(
        self,
    ) -> None:
        """Keep the size-locked Part 2 and Side A spaces visibly intact."""
        self.assertNotEqual(PART_2_LIGATURE_TILE_ID, SIDE_A_LIGATURE_TILE_ID)
        self.assertNotIn(
            PART_2_LIGATURE_CODE,
            {42, 43},
        )
        self.assertNotIn(
            SIDE_A_LIGATURE_CODE,
            {42, 43},
        )
        self.assertEqual(render_compact_suffix("A")[0], 0xF1)
        self.assertEqual(render_compact_suffix("2")[0], 0xF1)
        for glyph in (render_compact_suffix("A"), render_compact_suffix("2")):
            self.assertTrue(all(row & 0xE0 == 0xE0 for row in glyph))

    def test_patched_font_keeps_the_active_x_and_z_glyphs(self) -> None:
        """Never replace active uppercase letters with prompt ligatures."""
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


if __name__ == "__main__":
    unittest.main()
