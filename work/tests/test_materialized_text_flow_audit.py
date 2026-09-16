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

    def test_historical_atrocity_language_is_not_sanitized(self) -> None:
        """Keep Nazi persecution and slavery as explicit as the Japanese source."""
        cases = (
            (
                "TT3A",
                "TT3A/g1/r25",
                "rounding up spies and rebels and sending them to the gas chambers",
            ),
            (
                "TT3A",
                "TT3A/g3/r4",
                "imprisoned me and forced me to develop a secret weapon",
            ),
            (
                "TT5",
                "TT5/g0/r6",
                "We won't let the likes of you lord it over us!",
            ),
            ("TT5", "TT5/g0/r7", "You people were born slaves."),
            (
                "TT5",
                "TT5/g0/r18",
                "Devote your whole lives to us.",
            ),
            (
                "T25",
                "T25/g1/r24",
                "the graveyard of slaves who refused to obey",
            ),
        )
        for bank, record_id, expected in cases:
            with self.subTest(record_id=record_id):
                self.assertIn(expected, _plain(_production(bank)[record_id]))

    def test_sensitive_content_matches_source_intensity(self) -> None:
        """Preserve genuine ugliness without adding profanity the source lacks."""
        source_faithful = (
            ("TT2", "TT2/g0/r0", "Help us poor folk!"),
            ("TT2", "TT2/g0/r1", "Me: What's going on?!"),
            (
                "TT2",
                "TT2/g0/r9",
                "What's going on?! I'm in somebody else's body!",
            ),
            ("TT1B", "TT1B/g1/r2", "Wh-what the…?!"),
            ("T22", "T22/g1/r7", "enslaved to vile desire"),
            (
                "TT4",
                "TT4/g3/r3",
                "Rather than democracy, I believe in the gods.",
            ),
        )
        for bank, record_id, expected in source_faithful:
            with self.subTest(record_id=record_id):
                self.assertIn(expected, _plain(_production(bank)[record_id]))

        invented_intensity = (
            ("TT2", "TT2/g0/r0", "poor bastards"),
            ("TT2", "TT2/g0/r1", "What the hell"),
            ("TT2", "TT2/g0/r9", "What the hell"),
            ("TT1B", "TT1B/g1/r2", "what the hell"),
            ("TT4", "TT4/g3/r3", "To hell with democracy"),
        )
        for bank, record_id, rejected in invented_intensity:
            with self.subTest(record_id=record_id, rejected=rejected):
                self.assertNotIn(
                    rejected, _plain(_production(bank)[record_id])
                )

        explicit_source_content = (
            ("TT2", "TT2/g2/r17", "burns girls and then eats them"),
            ("TT2", "TT2/g4/r7", "tortures them"),
            ("TT4", "TT4/g4/r15", "You little shit"),
            ("TT4", "TT4/g4/r20", "kill you as many times as it takes"),
            ("TT6B", "TT6B/g1/r23", "Shit is shit."),
            ("TT6C", "TT6C/g2/r13", "prejudice and conflict"),
        )
        for bank, record_id, expected in explicit_source_content:
            with self.subTest(record_id=record_id):
                self.assertIn(expected, _plain(_production(bank)[record_id]))

    def test_audited_scene_controls_remain_on_natural_boundaries(self) -> None:
        """Lock timing controls that separate complete thoughts and responses."""
        tt3b = _production("TT3B")["TT3B/g1/r22"]
        self.assertIn(
            "Cougar: Mind's blank…{CTRL:0}Why am I here…?{CTRL:6}", tt3b
        )
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
