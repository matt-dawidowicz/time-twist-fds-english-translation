"""Regression coverage for audited kana-polysemy decisions."""

from __future__ import annotations

import unittest

from generate_translation_workbook import FIXED_NATURAL, GLOSSARY_SEEDS


class KanaPolysemyPolicyTests(unittest.TestCase):
    """Keep lexical ambiguity separate from verified gameplay labels."""

    def test_kiku_fixed_command_is_listen(self) -> None:
        """Keep the audited fixed-address command distinct from generic dictionary senses."""
        self.assertEqual(FIXED_NATURAL["きく"], "Listen")

    def test_kiku_glossary_keeps_ask_as_lexical_note_only(self) -> None:
        """Document broad Japanese senses without advertising an Ask menu state."""
        seed = next(item for item in GLOSSARY_SEEDS if item[1] == "きく")
        category, exact, reconstructed, chosen, alternatives, notes = seed
        self.assertEqual(category, "Command")
        self.assertEqual(exact, "きく")
        self.assertEqual(reconstructed, "聞く／聴く／訊く")
        self.assertEqual(chosen, "LISTEN")
        self.assertIn("ask/inquire", alternatives)
        self.assertIn("fixed gameplay command", notes)


if __name__ == "__main__":
    unittest.main()
