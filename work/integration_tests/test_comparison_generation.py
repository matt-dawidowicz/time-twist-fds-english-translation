from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

from generate_bilingual_comparison import build_rows


PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARISON = PROJECT_ROOT / "outputs" / "Time Twist Japanese-English script comparison.json"


class BilingualComparisonGenerationTests(unittest.TestCase):
    def test_regeneration_matches_committed_comparison_corpus(self) -> None:
        payload = json.loads(COMPARISON.read_text(encoding="utf-8"))
        generated = [asdict(row) for row in build_rows()]
        self.assertEqual(generated, payload["rows"])


if __name__ == "__main__":
    unittest.main()
