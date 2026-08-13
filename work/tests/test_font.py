from __future__ import annotations

import unittest

from time_twist.font import (
    PART_2_LIGATURE_TILE_ID,
    PIXEL_FONT_5X7,
    SIDE_A_LIGATURE_TILE_ID,
    SUPPORTED_NOV4_FONT_SOURCE_SHA256,
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
        self.assertEqual(render_compact_suffix("A")[0], 0xF1)
        self.assertEqual(render_compact_suffix("2")[0], 0xF1)
        for glyph in (render_compact_suffix("A"), render_compact_suffix("2")):
            self.assertTrue(all(row & 0xE0 == 0xE0 for row in glyph))


if __name__ == "__main__":
    unittest.main()
