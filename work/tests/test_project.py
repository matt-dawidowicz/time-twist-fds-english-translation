from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.english import encode_english
from time_twist.project import infer_bank_name, required_dictionary_entries


class ProjectConfigurationTests(unittest.TestCase):
    def test_bank_name_inference_accepts_supported_patterns(self) -> None:
        self.assertEqual(
            infer_bank_name(Path("side1_01_TT1A_A200.bin")),
            "TT1A",
        )
        self.assertEqual(
            infer_bank_name(Path("TT1A_fixed_footprint.bin")),
            "TT1A",
        )

    def test_bank_name_inference_rejects_ambiguous_or_unknown_names(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            infer_bank_name(Path("translated_fixed_footprint.bin"))
        with self.assertRaises(ValueError):
            infer_bank_name(Path("TT1A_TT1B.bin"))

    def test_explicit_bank_name_is_validated(self) -> None:
        self.assertEqual(infer_bank_name(Path("anything.bin"), "TT6D"), "TT6D")
        with self.assertRaises(ValueError):
            infer_bank_name(Path("anything.bin"), "UNKNOWN")

    def test_tt6c_reserves_dictionary_token_for_fixed_cougar_label(
        self,
    ) -> None:
        self.assertEqual(
            required_dictionary_entries("TT6C"),
            (encode_english("Cougar"),),
        )


if __name__ == "__main__":
    unittest.main()
