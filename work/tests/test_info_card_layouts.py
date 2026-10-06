"""Regression coverage for chapter identity cards shared by intro and Info."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from time_twist.production_translation import (
    merged_translation_map,
    validate_renderer_buffer_layout,
)

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:[0-7]\}")


def _production(bank_name: str) -> dict[str, str]:
    """Materialize one authoritative production bank."""
    return merged_translation_map(
        bank_name,
        base_directory=ROOT / "work" / "translations",
    )


class InfoCardLayoutTests(unittest.TestCase):
    """Keep identity-card fields visually separate at both runtime entry points."""

    def test_france_card_uses_standard_fields_and_scrolling(self) -> None:
        """Retain the shared three-row heading and scroll the occupation field."""
        tt2 = _production("TT2")
        self.assertEqual(
            tt2["TT2/g1/r4"],
            "Time: October 1428{CTRL:0}Place: A castle town in{CTRL:0}France",
        )
        self.assertEqual(
            tt2["TT2/g1/r5"],
            "{CTRL:6}Name: Pierre{CTRL:4}Occupation: Glassmaker",
        )
        self.assertEqual(
            tt2["TT2/g1/r6"],
            "{CTRL:6}Name: Chino{CTRL:4}Occupation: Locksmith",
        )

    def test_long_identity_cards_keep_fields_on_separate_segments(
        self,
    ) -> None:
        """Start every field on a new row, including the Nazareth identity card."""
        cards = {
            ("TT3A", "TT3A/g0/r14"): (
                "Time:",
                "Place:",
                "Name:",
                "Occupation:",
            ),
            ("TT4", "TT4/g1/r22"): (
                "Time:",
                "Place:",
                "Name:",
                "Occupation:",
            ),
            ("TT5", "TT5/g1/r6"): (
                "Time:",
                "Place:",
                "Name:",
                "Occupation:",
            ),
            ("TT6A", "TT6A/g0/r8"): (
                "Time:",
                "Place:",
                "Name:",
                "Occupation:",
            ),
            ("TT6A", "TT6A/g1/r10"): (
                "Time:",
                "Place:",
                "Name:",
                "Occupation:",
            ),
        }
        cache: dict[str, dict[str, str]] = {}
        for (bank_name, record_id), labels in cards.items():
            production = cache.setdefault(bank_name, _production(bank_name))
            text = production[record_id]
            validate_renderer_buffer_layout(text)
            for label in labels:
                self.assertIn(label, text)
            for segment in CONTROL_RE.split(text):
                present = [label for label in labels if label in segment]
                with self.subTest(record_id=record_id, segment=segment):
                    self.assertLessEqual(len(present), 1)


if __name__ == "__main__":
    unittest.main()
