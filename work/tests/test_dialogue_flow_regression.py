"""Regression coverage for compiled dialogue-row ownership assumptions."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist.dialogue_flow import trace_dialogue

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSLATION_ROOT = PROJECT_ROOT / "work" / "translations"


class DialogueFlowRegressionTests(unittest.TestCase):
    """Keep every canonical scenario record inside the four-row renderer."""

    def test_all_canonical_records_are_geometry_safe(self) -> None:
        """Reject row crossings, fixed-row re-entry, and staging overwrites."""
        checked = 0
        for path in sorted(TRANSLATION_ROOT.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for record_id, text in payload.items():
                with self.subTest(record=record_id):
                    trace_dialogue(record_id, text)
                checked += 1
        self.assertEqual(checked, 1299)

    def test_plural_men_line_wraps_within_24_columns(self) -> None:
        """Lock the TT6C plural pronoun fix to a safe physical-row break."""
        payload = json.loads(
            (TRANSLATION_ROOT / "TT6C.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            payload["TT6C/g0/r29"],
            "They gaze solemnly at{CTRL:0}the baby.",
        )
        trace_dialogue("TT6C/g0/r29", payload["TT6C/g0/r29"])


if __name__ == "__main__":
    unittest.main()
