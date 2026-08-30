"""Public tests for small translation patch fragments."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist.english import control_values

from tools.maintenance.validate_translation_patch_fragments import (
    validate_fragment,
)

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "work/translation_patches/TT6B_camel_ibaraki_style.json"


class TranslationPatchFragmentTests(unittest.TestCase):
    """Validate the public translation patch fragment format."""

    def test_camel_dialect_fragment_is_internally_valid(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(validate_fragment(PATCH), [])

    def test_camel_dialect_fragment_preserves_expected_records(self) -> None:
        """Verify the current contract described by this regression test."""
        data = json.loads(PATCH.read_text(encoding="utf-8"))
        replacements = {
            record["id"]: record["replacement"] for record in data["records"]
        }
        self.assertEqual(
            set(replacements), {"TT6B/g0/r29", "TT6B/g0/r30", "TT6B/g0/r31"}
        )
        self.assertEqual(
            replacements["TT6B/g0/r29"],
            "Camel: Whaddya want?{CTRL:1}"
            "Me: May I eat the hay?{CTRL:0}"
            "Camel: Eat your fill.",
        )
        self.assertEqual(
            replacements["TT6B/g0/r30"], "Camel: I don't lie none."
        )
        self.assertEqual(
            replacements["TT6B/g0/r31"],
            "Camel: Of them three,{CTRL:0}"
            "one always tells truth.{CTRL:2}"
            "One only tells lies.{CTRL:6}"
            "Last one lies sometimes.{CTRL:4}"
            "Can't trust that one.",
        )

    def test_camel_dialect_fragment_keeps_control_orders(self) -> None:
        """Verify the current contract described by this regression test."""
        data = json.loads(PATCH.read_text(encoding="utf-8"))
        for record in data["records"]:
            self.assertEqual(
                control_values(record["current"]),
                control_values(record["replacement"]),
            )


if __name__ == "__main__":
    unittest.main()
