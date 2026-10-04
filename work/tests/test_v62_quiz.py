"""Regression coverage for the v62 quiz correction pass."""

from __future__ import annotations

import unittest

from time_twist import ui
from time_twist.quiz_manifest import QUIZ_ANSWERS
from time_twist.release_metadata import ReleaseBuildError
from time_twist.v62_quiz import (
    EVE_QUIZ_EXPECTED,
    EVE_QUIZ_OFFSET,
    EVE_QUIZ_REPLACEMENT,
    patch_tt6b_eve_quiz,
)


class V62QuizCorrectionTests(unittest.TestCase):
    """Lock the corrected answer labels and Eve selection routing."""

    def test_manifest_covers_all_scored_quizzes(self) -> None:
        self.assertEqual(len(QUIZ_ANSWERS), 39)
        keys = {(entry.bank, entry.selector) for entry in QUIZ_ANSWERS}
        self.assertEqual(len(keys), 39)

    def test_reviewed_answer_labels_are_locked(self) -> None:
        answers = {(entry.bank, entry.selector): entry.answer for entry in QUIZ_ANSWERS}
        self.assertEqual(answers[("TT2", 0x10)], "Commoners")
        self.assertEqual(answers[("TT4", 0x33)], "Parthenon")
        self.assertEqual(answers[("TT6B", 0x0F)], "Fruit of knowledge")
        self.assertEqual(answers[("TT6B", 0x10)], "Jehovah")

    def test_menu_source_keeps_jehovah_unchanged(self) -> None:
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[33], "Fruit of wisdom")
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[34], "Fruit of knowledge")
        self.assertEqual(ui.TT6B_FIXED_TEXT_RECORDS[37], "Jehovah")
        self.assertEqual(ui.TT2_FIXED_TEXT_RECORDS[32], "Commoners")

    def test_eve_quiz_routes_second_choice_to_success(self) -> None:
        bank = bytearray(EVE_QUIZ_OFFSET + len(EVE_QUIZ_EXPECTED))
        bank[EVE_QUIZ_OFFSET:EVE_QUIZ_OFFSET + len(EVE_QUIZ_EXPECTED)] = (
            EVE_QUIZ_EXPECTED
        )
        patched = patch_tt6b_eve_quiz(bytes(bank))
        self.assertEqual(
            patched[EVE_QUIZ_OFFSET:EVE_QUIZ_OFFSET + 3],
            EVE_QUIZ_REPLACEMENT,
        )
        # Native $31 relative targets are based at the opcode address $A643.
        deltas = tuple(
            int.from_bytes(bytes((value,)), signed=True)
            for value in EVE_QUIZ_REPLACEMENT[1:]
        )
        self.assertEqual(deltas, (63, 3))
        resolved = tuple(0xA643 + delta for delta in deltas)
        self.assertEqual(resolved, (0xA682, 0xA646))

    def test_eve_quiz_patch_is_idempotent_and_guarded(self) -> None:
        bank = bytearray(EVE_QUIZ_OFFSET + len(EVE_QUIZ_EXPECTED))
        bank[EVE_QUIZ_OFFSET:EVE_QUIZ_OFFSET + 3] = EVE_QUIZ_EXPECTED
        once = patch_tt6b_eve_quiz(bytes(bank))
        self.assertEqual(patch_tt6b_eve_quiz(once), once)

        bad = bytearray(bank)
        bad[EVE_QUIZ_OFFSET + 1] ^= 1
        with self.assertRaisesRegex(ReleaseBuildError, "source mismatch"):
            patch_tt6b_eve_quiz(bytes(bad))


if __name__ == "__main__":
    unittest.main()
