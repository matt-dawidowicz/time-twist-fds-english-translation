"""Regression coverage for the final materialized text-flow audit."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:\d+\}")


def _production(bank_name: str) -> dict[str, str]:
    """Materialize one authoritative production bank."""
    return merged_translation_map(
        bank_name,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


def _plain(text: str) -> str:
    """Collapse renderer controls so prose assertions survive safe reflow."""
    return " ".join(CONTROL_RE.sub(" ", text).split())


class MaterializedTextFlowAuditTests(unittest.TestCase):
    """Protect source-backed fixes in the actual production layer."""

    def test_semantic_and_referent_corrections_survive_materialization(
        self,
    ) -> None:
        """Keep previously audited source distinctions in final production text."""
        cases = (
            ("TT1B", "TT1B/g2/r16", "His eyesight seems poor."),
            ("TT3B", "TT3B/g1/r22", "But we saw something terrible."),
            (
                "T25",
                "T25/g1/r20",
                "The men who attacked George and Belle last night",
            ),
            ("TT6A", "TT6A/g0/r18", "He came down from above"),
            ("TT6A", "TT6A/g2/r26", "waiting for someone"),
        )
        for bank, record_id, expected in cases:
            with self.subTest(record_id=record_id):
                self.assertIn(expected, _plain(_production(bank)[record_id]))

    def test_flow_and_grammar_corrections_survive_materialization(
        self,
    ) -> None:
        """Keep clear English in branch, quiz, and narration records."""
        cases = (
            ("T22", "T22/g0/r4", "Just thinking aloud."),
            ("TT3A", "TT3A/g4/r6", 'starred in "Pépé le Moko"?'),
            ("TT3B", "TT3B/g1/r8", "revealing the words beneath!"),
            (
                "TT6B",
                "TT6B/g1/r27",
                "Demon-Sealing Jar that can imprison devils",
            ),
        )
        for bank, record_id, expected in cases:
            with self.subTest(record_id=record_id):
                self.assertIn(expected, _plain(_production(bank)[record_id]))

    def test_audited_scene_controls_remain_on_natural_boundaries(self) -> None:
        """Lock timing controls that separate complete thoughts and responses."""
        tt3b = _production("TT3B")["TT3B/g1/r22"]
        self.assertIn("Cougar: Mind's blank…{CTRL:0}Why am I here…?{CTRL:6}", tt3b)
        self.assertNotIn("Mind's{CTRL:6}blank", tt3b)

        tt6c = _production("TT6C")["TT6C/g3/r8"]
        self.assertIn("Joseph: Ah… right…{CTRL:3}Me: Yes.{CTRL:3}", tt6c)
        self.assertIn("Both: Yes…{CTRL:3}Me: Yes… Jesus Christ!", tt6c)

    def test_final_yes_jesus_wordplay_is_preserved(self) -> None:
        """Do not compress away the source's Iesu/yes/Jesus payoff."""
        text = _plain(_production("TT6C")["TT6C/g3/r8"])
        self.assertIn("Me: Yes.", text)
        self.assertIn("Both: Yes…", text)
        self.assertIn("Me: Yes… Jesus Christ!", text)
        self.assertNotIn("Me: Right. Jesus Christ.", text)


if __name__ == "__main__":
    unittest.main()
