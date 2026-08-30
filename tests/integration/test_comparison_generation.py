"""Private-overlay integration tests for the current generated bilingual comparison corpus."""

from __future__ import annotations

import json
import unittest
from dataclasses import asdict

from tests.support.paths import PROJECT_ROOT
from tools.generation.generate_bilingual_comparison import build_rows

COMPARISON = (
    PROJECT_ROOT
    / "outputs"
    / "Time Twist Japanese-English script comparison.json"
)


class BilingualComparisonGenerationTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    def test_regeneration_matches_committed_comparison_corpus(self) -> None:
        """Verify the current contract described by this regression test."""
        payload = json.loads(COMPARISON.read_text(encoding="utf-8"))
        generated = [asdict(row) for row in build_rows()]
        self.assertEqual(generated, payload["rows"])


if __name__ == "__main__":
    unittest.main()
