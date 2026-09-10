"""Production-font regression tests for punctuation and vertical metrics."""

from __future__ import annotations

import unittest

from time_twist.english import (
    EXTENDED_CHARACTERS,
    EnglishTextError,
    encode_english,
    render_english,
)
from time_twist.font import (
    EXTENDED_TILE_IDS,
    glyph_ink_bounds,
    render_glyph,
)


class ProductionFontMetricsTests(unittest.TestCase):
    """Lock the production font's baseline, descenders, and punctuation."""

    def test_capitals_and_digits_share_one_vertical_box(self) -> None:
        """Verify capitals and digits share one vertical box."""
        for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            with self.subTest(character=character):
                self.assertEqual(glyph_ink_bounds(character), (0, 6))

    def test_x_height_lowercase_shares_one_baseline(self) -> None:
        """Verify x height lowercase shares one baseline."""
        for character in "aceomnrsuvwxz":
            with self.subTest(character=character):
                self.assertEqual(glyph_ink_bounds(character), (2, 6))

    def test_ascenders_share_the_cap_height_and_baseline(self) -> None:
        """Verify ascenders share the cap height and baseline."""
        for character in "bdfhklt":
            with self.subTest(character=character):
                self.assertEqual(glyph_ink_bounds(character), (0, 6))

    def test_true_descenders_use_the_eighth_row(self) -> None:
        """Verify true descenders use the eighth row."""
        for character in "gpqy":
            with self.subTest(character=character):
                self.assertEqual(glyph_ink_bounds(character), (2, 7))
        # j keeps its dot at cap height while its hook reaches the descender row.
        self.assertEqual(glyph_ink_bounds("j"), (0, 7))

    def test_ellipsis_and_em_dash_have_dedicated_runtime_codes(self) -> None:
        """Verify ellipsis and em dash have dedicated runtime codes."""
        self.assertEqual(EXTENDED_CHARACTERS[57], "—")
        self.assertEqual(EXTENDED_CHARACTERS[61], "…")
        self.assertEqual(
            render_english(encode_english("Wait… no—really!")),
            "Wait… no—really!",
        )
        self.assertEqual(glyph_ink_bounds("…"), (6, 6))
        self.assertEqual(glyph_ink_bounds("—"), (3, 3))
        self.assertNotEqual(render_glyph("-"), render_glyph("—"))

    def test_colon_uses_the_recovered_safe_code_45_slot(self) -> None:
        """Verify colon uses the recovered safe code 45 slot."""
        self.assertEqual(EXTENDED_CHARACTERS[45], ":")
        self.assertEqual(
            render_english(encode_english("Simon: Yes.")),
            "Simon: Yes.",
        )

    def test_dollar_sign_uses_the_runtime_tested_safe_tile(self) -> None:
        """Verify dollar sign uses the runtime tested safe tile."""
        self.assertEqual(EXTENDED_CHARACTERS[63], "$")
        self.assertEqual(EXTENDED_TILE_IDS[63], 0xB0)
        self.assertEqual(render_english(encode_english("$120")), "$120")
        self.assertEqual(glyph_ink_bounds("$"), (0, 6))

    def test_curly_quotes_encode_to_the_established_quote_glyphs(self) -> None:
        """Verify curly quotes encode to the established quote glyphs."""
        self.assertEqual(render_english(encode_english("“Yes.”")), '"Yes."')
        self.assertEqual(render_english(encode_english("don’t")), "don't")
        self.assertEqual(render_glyph("“"), render_glyph('"'))
        self.assertEqual(render_glyph("’"), render_glyph("'"))

    def test_slash_is_rejected_instead_of_rendering_as_the_em_dash_tile(
        self,
    ) -> None:
        """Verify slash is rejected instead of rendering as the em dash tile."""
        with self.assertRaises(EnglishTextError):
            encode_english("and/or")

    def test_all_active_extended_glyph_tiles_stay_in_safe_font_storage(
        self,
    ) -> None:
        """Verify all active extended glyph tiles stay in safe font storage."""
        active_tiles = {
            EXTENDED_TILE_IDS[value] for value in EXTENDED_CHARACTERS
        }
        self.assertNotIn(0xAC, active_tiles)
        self.assertTrue(all(0xB0 <= tile <= 0xFE for tile in active_tiles))


if __name__ == "__main__":
    unittest.main()
