"""Tests for compression-aware editorial layout candidate generation."""

from __future__ import annotations

import unittest

from time_twist.editorial_layout import presentation_break_variants
from time_twist.english import EnglishTextError


class EditorialLayoutTests(unittest.TestCase):
    """Keep natural prose intact while enumerating safe row layouts."""

    def test_blue_sky_sentence_has_only_three_minimum_row_layouts(
        self,
    ) -> None:
        """Enumerate only the three useful two-row presentations."""
        variants = presentation_break_variants(
            "When was the last time I saw a blue sky?"
        )

        self.assertEqual(
            variants,
            (
                "When was the last{CTRL:0}time I saw a blue sky?",
                "When was the last time{CTRL:0}I saw a blue sky?",
                "When was the last time I{CTRL:0}saw a blue sky?",
            ),
        )

    def test_variants_preserve_visible_words_exactly(self) -> None:
        """Replace only spaces with row controls; never rewrite the sentence."""
        source = "When was the last time I saw a blue sky?"
        variants = presentation_break_variants(source)

        for variant in variants:
            self.assertEqual(variant.replace("{CTRL:0}", " "), source)

    def test_single_row_sentence_is_retained(self) -> None:
        """Do not force a break when natural text already fits."""
        self.assertEqual(
            presentation_break_variants("It is locked."), ("It is locked.",)
        )

    def test_existing_controls_are_not_repositioned_by_layout_helper(
        self,
    ) -> None:
        """Keep semantic/control-aware composition outside this narrow helper."""
        with self.assertRaisesRegex(EnglishTextError, "existing controls"):
            presentation_break_variants("Hello{CTRL:4}world")

    def test_unwrappable_word_fails_closed(self) -> None:
        """Reject a word that exceeds the renderer instead of splitting it."""
        with self.assertRaisesRegex(EnglishTextError, "word is wider"):
            presentation_break_variants("X" * 25)

    def test_variant_limit_prevents_minimal_layout_runaway(self) -> None:
        """Bound even the set of equally minimal layouts for pathological text."""
        with self.assertRaisesRegex(EnglishTextError, "variant limit"):
            presentation_break_variants(
                "a b c d e f g h i j",
                columns=7,
                max_variants=2,
            )


if __name__ == "__main__":
    unittest.main()
