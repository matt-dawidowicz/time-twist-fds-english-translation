from __future__ import annotations

import unittest

from generate_bilingual_comparison import BANK_ORDER, build_rows


class BilingualComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = build_rows()

    def test_all_scenario_records_are_present_once(self) -> None:
        scenario = [row for row in self.rows if row.kind == "scenario"]
        self.assertEqual(len(scenario), 1299)
        self.assertEqual(len({row.text_id for row in scenario}), 1299)
        self.assertEqual(tuple(dict.fromkeys(row.bank for row in scenario)), BANK_ORDER)

    def test_every_row_keeps_japanese_and_english(self) -> None:
        for row in self.rows:
            self.assertTrue(row.japanese_exact, row.text_id)
            self.assertTrue(row.current_english_exact, row.text_id)

    def test_scenario_control_sequences_match(self) -> None:
        mismatches = [
            row.text_id
            for row in self.rows
            if row.kind == "scenario" and row.control_match != "yes"
        ]
        self.assertEqual(mismatches, [])

    def test_comparison_ids_are_unique(self) -> None:
        self.assertEqual(len(self.rows), len({row.text_id for row in self.rows}))


if __name__ == "__main__":
    unittest.main()
