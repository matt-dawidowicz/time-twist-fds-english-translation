"""Regression tests for current project identity and source layout."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.project import infer_bank_name


class ProjectConfigurationTests(unittest.TestCase):
    """Protect scenario-bank identity and filename inference."""

    def test_bank_name_inference_accepts_supported_patterns(self) -> None:
        """Recognize extracted and generated filenames without ambiguity."""
        self.assertEqual(
            infer_bank_name(Path("side1_01_TT1A_A200.bin")), "TT1A"
        )
        self.assertEqual(infer_bank_name(Path("TT1A_candidate.bin")), "TT1A")

    def test_bank_name_inference_rejects_ambiguous_or_unknown_names(
        self,
    ) -> None:
        """Fail closed rather than guessing a bank name."""
        with self.assertRaises(ValueError):
            infer_bank_name(Path("translated_candidate.bin"))
        with self.assertRaises(ValueError):
            infer_bank_name(Path("TT1A_TT1B.bin"))

    def test_explicit_bank_name_is_validated(self) -> None:
        """Accept a supported override and reject unknown bank identifiers."""
        self.assertEqual(infer_bank_name(Path("anything.bin"), "TT6D"), "TT6D")
        with self.assertRaises(ValueError):
            infer_bank_name(Path("anything.bin"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
