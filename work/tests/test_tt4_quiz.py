"""Regression coverage for the TT4 Athena-temple quiz mapping."""

from __future__ import annotations

import unittest

from time_twist.release_metadata import ReleaseBuildError
from time_twist.tt4_quiz import (
    ATHENA_QUIZ_EXPECTED,
    ATHENA_QUIZ_OFFSET,
    ATHENA_QUIZ_REPLACEMENT,
    patch_tt4_athena_quiz,
)


class TT4AthenaQuizTests(unittest.TestCase):
    """Keep Parthenon as the fifth and only successful answer."""

    def setUp(self) -> None:
        """Create a source-matching synthetic TT4 bank for each test."""
        self.bank = bytearray(ATHENA_QUIZ_OFFSET + len(ATHENA_QUIZ_EXPECTED))
        self.bank[
            ATHENA_QUIZ_OFFSET : ATHENA_QUIZ_OFFSET + len(ATHENA_QUIZ_EXPECTED)
        ] = ATHENA_QUIZ_EXPECTED

    def test_parthenon_is_the_only_success_target(self) -> None:
        """Route only the fifth answer, Parthenon, to the success branch."""
        patched = patch_tt4_athena_quiz(bytes(self.bank))
        actual = patched[
            ATHENA_QUIZ_OFFSET : ATHENA_QUIZ_OFFSET
            + len(ATHENA_QUIZ_REPLACEMENT)
        ]
        self.assertEqual(actual, ATHENA_QUIZ_REPLACEMENT)

        # The five signed offsets begin immediately after opcode $31.
        targets = tuple(
            int.from_bytes(bytes((value,)), signed=True)
            for value in ATHENA_QUIZ_REPLACEMENT[3:8]
        )
        self.assertEqual(targets, (-37, -37, -37, -37, 6))

        branch_pc = 0xAE3E
        resolved = tuple(branch_pc + delta for delta in targets)
        self.assertEqual(resolved[:4], (0xAE19,) * 4)
        self.assertEqual(resolved[4], 0xAE44)

    def test_unknown_source_is_rejected(self) -> None:
        """Fail closed when the guarded source bytes no longer match."""
        changed = bytearray(self.bank)
        changed[ATHENA_QUIZ_OFFSET + 5] ^= 1
        with self.assertRaisesRegex(ReleaseBuildError, "source mismatch"):
            patch_tt4_athena_quiz(bytes(changed))

    def test_patch_is_idempotent(self) -> None:
        """Accept an already-corrected quiz without changing it again."""
        once = patch_tt4_athena_quiz(bytes(self.bank))
        self.assertEqual(patch_tt4_athena_quiz(once), once)


if __name__ == "__main__":
    unittest.main()
