"""Regression coverage for TT4's fisherman speaker label."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist import ui
from time_twist.production_translation import merged_translation_map

ROOT = Path(__file__).resolve().parents[2]
FISHERMAN_RECORDS = (
    "TT4/g5/r6",
    "TT4/g5/r8",
    "TT4/g5/r9",
    "TT4/g5/r14",
    "TT4/g5/r15",
    "TT4/g5/r16",
    "TT4/g5/r17",
    "TT4/g5/r18",
    "TT4/g5/r21",
)


def _production() -> dict[str, str]:
    """Materialize the authoritative TT4 production bank."""
    return merged_translation_map(
        "TT4",
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


class TT4FishermanSpeakerLabelTests(unittest.TestCase):
    """Keep the TT4 fisherman named consistently in menus and dialogue."""

    def test_dialogue_uses_fisherman_for_tsuribito(self) -> None:
        """Use the same source-accurate identity on every spoken line."""
        tt4 = _production()
        for record_id in FISHERMAN_RECORDS:
            with self.subTest(record_id=record_id):
                self.assertIn("Fisherman:", tt4[record_id])
                self.assertNotIn("Fisher:", tt4[record_id])

    def test_herb_advice_restores_the_missing_speaker(self) -> None:
        """Preserve the source speaker on the plantain advice line."""
        self.assertTrue(_production()["TT4/g5/r16"].startswith("Fisherman:"))

    def test_quiz_questions_use_safe_two_line_english(self) -> None:
        """Use natural English without scrolling beyond the quiz-safe rows."""
        tt4 = _production()
        self.assertEqual(
            tt4["TT4/g5/r7"],
            "{CTRL:0}{CTRL:0}What were city-states{CTRL:0}in Greece called?",
        )
        self.assertEqual(
            tt4["TT4/g5/r10"],
            "{CTRL:0}{CTRL:0}Which city-state was{CTRL:0}"
            "Athens' greatest rival?",
        )
        self.assertEqual(
            tt4["TT4/g5/r11"],
            "{CTRL:0}{CTRL:0}Who was the great hero{CTRL:0}"
            "of Greek mythology?",
        )
        self.assertEqual(
            tt4["TT4/g5/r12"],
            "{CTRL:0}{CTRL:0}Which temple was built{CTRL:0}"
            "for the goddess Athena?",
        )
        self.assertEqual(
            tt4["TT4/g5/r13"],
            "{CTRL:0}{CTRL:0}What crop joined olives{CTRL:0}and grapes in Greece?",
        )

    def test_herb_advice_names_the_ailment(self) -> None:
        """Do not reduce the three source treatment hints to bare plant names."""
        tt4 = _production()
        self.assertIn("For a cough", tt4["TT4/g5/r16"])
        self.assertIn("For food poisoning", tt4["TT4/g5/r17"])
        self.assertIn("For sores", tt4["TT4/g5/r18"])

    def test_fixed_menu_uses_the_same_identity(self) -> None:
        """Keep the selectable fisherman label aligned with dialogue."""
        self.assertEqual(ui.TT4_FIXED_TEXT_RECORDS[74], "Fisherman")


if __name__ == "__main__":
    unittest.main()
