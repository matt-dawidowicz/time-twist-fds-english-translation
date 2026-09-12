"""Regression coverage for audited presentation-only CTRL:1 waits."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from time_twist.production_translation import (
    PRESENTATION_ONLY_CTRL1_RECORDS,
    PRESENTATION_ONLY_CTRL1_TEMPLATES,
    ProductionTranslationError,
    layout_review_text,
    merged_translation_map,
    validate_production_control_sequence,
)

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:[0-7]\}")
EXPECTED_RECORDS = frozenset(
    {
        "TT1A/g0/r5",
        "TT1B/g0/r6",
        "TT1B/g2/r11",
        "TT1B/g2/r29",
        "T25/g0/r24",
        "T25/g1/r12",
        "TT3A/g0/r1",
        "TT4/g0/r30",
        "TT6B/g0/r6",
        "TT6C/g2/r5",
    }
)


class PresentationOnlyCtrl1Tests(unittest.TestCase):
    """Keep the ROM-wide playtest fix narrow, explicit, and source-preserving."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.production_by_bank: dict[str, dict[str, str]] = {}
        for record_id in EXPECTED_RECORDS:
            bank = record_id.split("/", 1)[0]
            if bank in cls.production_by_bank:
                continue
            cls.production_by_bank[bank] = merged_translation_map(
                bank,
                base_directory=ROOT / "work" / "translations",
                override_directory=ROOT / "work" / "production_overrides",
                review_directory=ROOT / "review" / "production_retranslation",
            )

    def test_policy_is_exact_audited_record_set(self) -> None:
        """Prevent accidental broadening or silent removal of an audited case."""
        self.assertEqual(PRESENTATION_ONLY_CTRL1_RECORDS, EXPECTED_RECORDS)
        self.assertEqual(
            frozenset(PRESENTATION_ONLY_CTRL1_TEMPLATES), EXPECTED_RECORDS
        )

    def test_certified_base_topology_remains_unchanged(self) -> None:
        """Keep CTRL:1 in the certified base maps; demotion is production-only."""
        by_bank: dict[str, dict[str, str]] = {}
        for (
            record_id,
            expected_template,
        ) in PRESENTATION_ONLY_CTRL1_TEMPLATES.items():
            bank = record_id.split("/", 1)[0]
            if bank not in by_bank:
                by_bank[bank] = json.loads(
                    (
                        ROOT / "work" / "translations" / f"{bank}.json"
                    ).read_text(encoding="utf-8")
                )
            self.assertEqual(by_bank[bank][record_id], expected_template)
            self.assertEqual(expected_template.count("{CTRL:1}"), 1)

    def test_all_audited_waits_are_removed_from_production(self) -> None:
        """Let continuous English fill the box instead of pausing after line one."""
        for record_id in sorted(EXPECTED_RECORDS):
            bank = record_id.split("/", 1)[0]
            production = self.production_by_bank[bank][record_id]
            with self.subTest(record_id=record_id):
                self.assertNotIn("{CTRL:1}", production)
                validate_production_control_sequence(
                    PRESENTATION_ONLY_CTRL1_TEMPLATES[record_id], production
                )

    def test_personality_intro_preserves_reviewed_words(self) -> None:
        """Retain the exact reviewed prose that exposed the playtest problem."""
        text = self.production_by_bank["TT1A"]["TT1A/g0/r5"]
        expected = (
            "First, we'll begin with a personality test. "
            "Please answer each question."
        )
        self.assertEqual(CONTROL_RE.sub(" ", text).split(), expected.split())

    def test_unrelated_ctrl1_timing_remains_intact(self) -> None:
        """Keep dramatic, speaker-change, and intentional timing waits semantic."""
        controls_to_keep = {
            "TT1A": ("TT1A/g0/r26", "TT1A/g0/r30"),
            "TT1B": ("TT1B/g0/r26",),
            "TT3A": ("TT3A/g1/r21",),
            "TT4": ("TT4/g0/r12",),
            "TT6C": ("TT6C/g1/r18",),
        }
        for bank, record_ids in controls_to_keep.items():
            production = self.production_by_bank.get(bank)
            if production is None:
                production = merged_translation_map(
                    bank,
                    base_directory=ROOT / "work" / "translations",
                    override_directory=ROOT / "work" / "production_overrides",
                    review_directory=ROOT
                    / "review"
                    / "production_retranslation",
                )
            for record_id in record_ids:
                with self.subTest(record_id=record_id):
                    self.assertIn("{CTRL:1}", production[record_id])

    def test_policy_fails_closed_if_audited_base_template_changes(
        self,
    ) -> None:
        """Require a fresh audit instead of carrying an exception onto new text."""
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "re-audit before building",
        ):
            layout_review_text(
                "TT1A/g0/r5",
                "First, we'll begin with a personality test. Please answer each question.",
                "Changed source.{CTRL:1}Still changed.",
            )


if __name__ == "__main__":
    unittest.main()
