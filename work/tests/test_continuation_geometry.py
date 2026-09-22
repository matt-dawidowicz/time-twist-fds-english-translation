"""Regression coverage for source-led cross-record dialogue continuations."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist.continuation_contracts import CONTINUATION_PREDECESSORS
from time_twist.dialogue_flow import validate_continuation

ROOT = Path(__file__).resolve().parents[2]


class ContinuationGeometryTests(unittest.TestCase):
    """Keep retained four-row staging state from being overwritten."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load every active canonical translation record."""
        cls.texts = {
            key: value
            for path in (ROOT / "work/translations").glob("*.json")
            for key, value in json.loads(
                path.read_text(encoding="utf-8")
            ).items()
        }

    def test_all_registered_continuations_preserve_retained_rows(self) -> None:
        """Trace every reviewed predecessor/continuation pair."""
        self.assertEqual(len(CONTINUATION_PREDECESSORS), 63)
        for next_id, predecessors in CONTINUATION_PREDECESSORS.items():
            self.assertIn(next_id, self.texts)
            for previous_id in predecessors:
                self.assertIn(previous_id, self.texts)
                with self.subTest(previous=previous_id, next=next_id):
                    validate_continuation(
                        previous_id, next_id, self.texts
                    )


if __name__ == "__main__":
    unittest.main()
