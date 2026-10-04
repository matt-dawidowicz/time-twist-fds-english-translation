"""Regression coverage for the faithful quiz-localization policy."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist import ui
from time_twist.production_translation import merged_translation_map
from time_twist.quiz_manifest import QUIZ_ANSWERS

ROOT = Path(__file__).resolve().parents[2]


class FaithfulQuizLocalizationTests(unittest.TestCase):
    """Separate technical/localization fixes from source-content rewrites."""

    def test_manifest_covers_all_scored_quizzes(self) -> None:
        self.assertEqual(len(QUIZ_ANSWERS), 39)
        keys = {(entry.bank, entry.selector) for entry in QUIZ_ANSWERS}
        self.assertEqual(len(keys), 39)

    def test_reviewed_visible_answers_are_locked(self) -> None:
        answers = {
            (entry.bank, entry.selector): entry.answer
            for entry in QUIZ_ANSWERS
        }
        self.assertEqual(answers[("TT2", 0x10)], "Commoners")
        self.assertEqual(answers[("TT4", 0x33)], "Parthenon")
        self.assertEqual(answers[("TT6B", 0x0F)], "Fruit of wisdom")
        self.assertEqual(answers[("TT6B", 0x10)], "Jehovah")

    def test_original_tt6b_choice_labels_are_preserved(self) -> None:
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[33], "Fruit of wisdom")
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[34], "Fruit of knowledge")
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[37], "Jehovah")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[32], "Commoners")

    def test_only_localization_ambiguities_are_reworded(self) -> None:
        tt3a = merged_translation_map(
            "TT3A", base_directory=ROOT / "work" / "translations"
        )
        tt4 = merged_translation_map(
            "TT4", base_directory=ROOT / "work" / "translations"
        )
        self.assertEqual(
            tt3a["TT3A/g4/r7"],
            "{CTRL:0}{CTRL:0}Who was Supreme Allied{CTRL:0}"
            "Commander for the{CTRL:4}Normandy invasion?",
        )
        self.assertEqual(
            tt4["TT4/g5/r7"],
            "{CTRL:0}{CTRL:0}What was a Greek{CTRL:0}city-state called?",
        )

    def test_original_questionable_trivia_is_preserved(self) -> None:
        tt4 = merged_translation_map(
            "TT4", base_directory=ROOT / "work" / "translations"
        )
        tt5 = merged_translation_map(
            "TT5", base_directory=ROOT / "work" / "translations"
        )
        self.assertEqual(
            tt4["TT4/g5/r13"],
            "{CTRL:0}{CTRL:0}Alongside olives and{CTRL:0}grapes, what was"
            "{CTRL:4}Greece's third major{CTRL:4}crop?",
        )
        self.assertEqual(
            tt5["TT5/g2/r18"],
            "Edison's three great{CTRL:0}inventions were the{CTRL:0}"
            "phonograph, the{CTRL:0}generator, and what?",
        )


if __name__ == "__main__":
    unittest.main()
