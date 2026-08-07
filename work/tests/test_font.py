from __future__ import annotations

import unittest

from time_twist.font import PIXEL_FONT_5X7, render_glyph


class PixelFontTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
