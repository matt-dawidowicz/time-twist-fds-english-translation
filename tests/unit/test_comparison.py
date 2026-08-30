"""Regression tests for the current bilingual comparison review corpus."""

from __future__ import annotations

import json
import unittest

from tests.support.paths import PROJECT_ROOT

COMPARISON = (
    PROJECT_ROOT
    / "outputs"
    / "Time Twist Japanese-English script comparison.json"
)
TRANSLATIONS = PROJECT_ROOT / "work" / "translations"
BANK_ORDER = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
)


class BilingualComparisonTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare shared fixtures for the current contract tests."""
        payload = json.loads(COMPARISON.read_text(encoding="utf-8"))
        cls.assert_schema(payload)
        cls.rows = payload["rows"]
        cls.playable = {}
        for bank in BANK_ORDER:
            values = json.loads(
                (TRANSLATIONS / f"{bank}.json").read_text(encoding="utf-8")
            )
            cls.playable.update(values)

    @staticmethod
    def assert_schema(payload: object) -> None:
        """Assert the current contract against the prepared test fixture."""
        if not isinstance(payload, dict):
            raise AssertionError("comparison output is not a JSON object")
        if payload.get("schema") != "time-twist-bilingual-comparison-v1":
            raise AssertionError("unsupported comparison schema")
        if not isinstance(payload.get("rows"), list):
            raise AssertionError("comparison output has no row list")

    def test_all_scenario_records_are_present_once(self) -> None:
        """Verify the current contract described by this regression test."""
        scenario = [row for row in self.rows if row["kind"] == "scenario"]
        self.assertEqual(len(scenario), 1299)
        self.assertEqual(len({row["text_id"] for row in scenario}), 1299)
        self.assertEqual(
            tuple(dict.fromkeys(row["bank"] for row in scenario)), BANK_ORDER
        )

    def test_every_row_keeps_japanese_and_english(self) -> None:
        """Verify the current contract described by this regression test."""
        for row in self.rows:
            self.assertTrue(row["japanese_exact"], row["text_id"])
            self.assertTrue(row["current_english_exact"], row["text_id"])

    def test_scenario_control_sequences_and_playable_text_match(self) -> None:
        """Verify the current contract described by this regression test."""
        scenario = [row for row in self.rows if row["kind"] == "scenario"]
        self.assertEqual(
            {row["text_id"] for row in scenario}, set(self.playable)
        )
        for row in scenario:
            self.assertEqual(row["control_match"], "yes", row["text_id"])
            self.assertEqual(
                row["current_english_exact"],
                self.playable[row["text_id"]],
                row["text_id"],
            )

    def test_comparison_ids_are_unique_and_complete(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(len(self.rows), 2058)
        self.assertEqual(
            len(self.rows), len({row["text_id"] for row in self.rows})
        )
        counts = {
            kind: sum(row["kind"] == kind for row in self.rows)
            for kind in ("scenario", "fixed-address", "graphics-text")
        }
        self.assertEqual(
            counts,
            {"scenario": 1299, "fixed-address": 756, "graphics-text": 3},
        )


if __name__ == "__main__":
    unittest.main()
