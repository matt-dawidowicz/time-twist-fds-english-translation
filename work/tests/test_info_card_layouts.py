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
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


class InfoCardLayoutTests(unittest.TestCase):
    """Keep identity-card fields visually separate at both runtime entry points."""

    def test_france_card_retains_playtested_four_row_geometry(self) -> None:
        """Keep the compact France/Pierre/Chino cards on their approved rows."""
        tt2 = _production("TT2")
        self.assertEqual(
            tt2["TT2/g1/r4"],
            "October 1428. A castle{CTRL:0}town in France.",
        )
        self.assertEqual(
            tt2["TT2/g1/r5"],
            "{CTRL:0}{CTRL:0}Name: Pierre{CTRL:0}Trade: glassmaker",
        )
        self.assertEqual(
            tt2["TT2/g1/r6"],
            "{CTRL:0}{CTRL:0}Name: Chino{CTRL:0}Trade: locksmith",
        )

    def test_long_identity_cards_keep_fields_on_separate_segments(self) -> None:
        """Never append a new field label to the preceding field's visible row."""
        cards = {
            ("TT3A", "TT3A/g0/r14"): (
                "TIME:",
                "LOCATION:",
                "NAME:",
                "RANK:",
            ),
            ("TT4", "TT4/g1/r22"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT5", "TT5/g1/r6"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT6A", "TT6A/g0/r8"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT6A", "TT6A/g1/r10"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
        }
        cache: dict[str, dict[str, str]] = {}
        for (bank_name, record_id), labels in cards.items():
            production = cache.setdefault(bank_name, _production(bank_name))
            text = production[record_id]
            validate_renderer_buffer_layout(text)
            for segment in CONTROL_RE.split(text):
                present = [label for label in labels if label in segment]
                with self.subTest(record_id=record_id, segment=segment):
                    self.assertLessEqual(len(present), 1)


if __name__ == "__main__":
    unittest.main()
