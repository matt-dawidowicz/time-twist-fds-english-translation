"""Regression coverage for the recovered TT1A Fortune Teller model."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map

ROOT = Path(__file__).resolve().parents[2]
TRANSLATIONS = ROOT / "work" / "translations"


def _canonical(bank_name: str) -> dict[str, str]:
    """Load one validated canonical translation bank."""
    return merged_translation_map(bank_name, base_directory=TRANSLATIONS)


QUESTION_NEXT = {
    "S1": ("S4", "S2"),
    "S2": ("S5", "S3"),
    "S3": ("S6", "S5"),
    "S4": ("S7", "S3"),
    "S5": ("S8", "S9"),
    "S6": ("S5", "S9"),
    "S7": ("S6", "S11"),
    "S8": ("S12", "S9"),
    "S9": ("S13", "S10"),
    "S10": ("S14", "S15"),
    "S11": ("S15", "S3"),
}
TERMINALS = {"S12", "S13", "S14", "S15"}
RECORD_BY_NODE = {
    f"S{index}": f"TT1A/g0/r{index + 5}" for index in range(1, 16)
}


def _statement_paths(node: str = "S1") -> list[tuple[str, ...]]:
    """Enumerate every distinct statement sequence through the acyclic graph."""
    if node in TERMINALS:
        return [(node,)]
    paths: list[tuple[str, ...]] = []
    for successor in QUESTION_NEXT[node]:
        for suffix in _statement_paths(successor):
            paths.append((node, *suffix))
    return paths


class FortuneTellerLogicTests(unittest.TestCase):
    """Keep the recovered questionnaire topology aligned with TT1A text."""

    def test_statement_graph_has_recovered_path_counts(self) -> None:
        """Lock the 69 statement routes and 138 terminal-answer routes."""
        paths = _statement_paths()
        self.assertEqual(len(paths), 69)
        self.assertEqual(len(paths) * 2, 138)
        self.assertEqual(min(map(len, paths)), 5)
        self.assertEqual(max(map(len, paths)), 11)

    def test_all_fifteen_nodes_map_to_current_statement_records(self) -> None:
        """Keep S1-S15 bound to TT1A r6-r20 in order."""
        tt1a = _canonical("TT1A")
        self.assertEqual(len(RECORD_BY_NODE), 15)
        for node, record_id in RECORD_BY_NODE.items():
            self.assertIn(record_id, tt1a, node)
            self.assertNotIn("?", tt1a[record_id], node)

    def test_terminal_statements_are_exactly_s12_through_s15(self) -> None:
        """Preserve the four nodes whose Yes/No result is routing-neutral."""
        self.assertEqual(TERMINALS, {"S12", "S13", "S14", "S15"})
        self.assertTrue(TERMINALS.isdisjoint(QUESTION_NEXT))

    def test_profile_records_remain_four_distinct_outputs(self) -> None:
        """Protect the four profile surfaces used by blood-type dispatch."""
        tt1a = _canonical("TT1A")
        profiles = {
            "AB": tt1a["TT1A/g0/r23"],
            "A": tt1a["TT1A/g0/r24"],
            "B": tt1a["TT1A/g0/r25"],
            "O": tt1a["TT1A/g0/r26"],
        }
        self.assertEqual(len(set(profiles.values())), 4)
        self.assertIn("cool-headed", profiles["AB"])
        self.assertIn("cautious", profiles["A"])
        self.assertIn("journalist", profiles["B"])
        self.assertIn("politician", profiles["O"])

    def test_known_example_routes_match_recovered_graph(self) -> None:
        """Lock representative shortest, longest, and uniform-answer routes."""
        paths = set(_statement_paths())
        self.assertIn(
            ("S1", "S4", "S7", "S6", "S5", "S8", "S12"),
            paths,
        )
        self.assertIn(
            ("S1", "S2", "S3", "S5", "S9", "S10", "S15"),
            paths,
        )
        self.assertIn(("S1", "S4", "S7", "S11", "S15"), paths)
        self.assertIn(
            (
                "S1",
                "S4",
                "S7",
                "S11",
                "S3",
                "S6",
                "S5",
                "S8",
                "S9",
                "S10",
                "S14",
            ),
            paths,
        )


if __name__ == "__main__":
    unittest.main()
