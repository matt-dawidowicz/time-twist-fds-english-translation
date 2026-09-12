"""Regression coverage for the TT1A personality-test playtest timing fix."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:[0-7]\}")


class TT1APersonalityTestControlTests(unittest.TestCase):
    """Keep the one playtest-proven redundant wait out of production English."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.production = merged_translation_map(
            "TT1A",
            base_directory=ROOT / "work" / "translations",
            override_directory=ROOT / "work" / "production_overrides",
            review_directory=ROOT / "review" / "production_retranslation",
        )

    def test_personality_test_intro_has_no_semantic_wait(self) -> None:
        """Let the renderer fill the box before the normal end-of-record wait."""
        text = self.production["TT1A/g0/r5"]
        self.assertNotIn("{CTRL:1}", text)
        self.assertEqual(
            CONTROL_RE.sub(" ", text).split(),
            "First, we'll begin with a personality test. Please answer each question.".split(),
        )

    def test_unrelated_ctrl1_timing_remains_intact(self) -> None:
        """Prove the fix does not weaken CTRL:1 semantics across TT1A."""
        self.assertIn("{CTRL:1}", self.production["TT1A/g0/r26"])
        self.assertIn("{CTRL:1}", self.production["TT1A/g0/r30"])


if __name__ == "__main__":
    unittest.main()
