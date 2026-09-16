"""Regression coverage for audited presentation-only CTRL:1 waits."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from time_twist.pagination_ctrl1_policy import (
    ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES,
)
from time_twist.production_translation import (
    PRESENTATION_ONLY_CTRL1_RECORDS,
    PRESENTATION_ONLY_CTRL1_TEMPLATES,
    ProductionTranslationError,
    layout_review_text,
    merged_translation_map,
    validate_record_production_control_sequence,
    validate_renderer_buffer_layout,
)

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:([0-7])\}")
EXPECTED_ORIGINAL_RECORDS = frozenset(
    {
        "TT1A/g0/r5",
        "TT1A/g0/r30",
        "TT1B/g0/r0",
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
EXPECTED_RECORDS = EXPECTED_ORIGINAL_RECORDS | frozenset(
    ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES
)


def _controls(text: str) -> tuple[int, ...]:
    """Return the ordered native control values in a record."""
    return tuple(int(value) for value in CONTROL_RE.findall(text))


class PresentationOnlyCtrl1Tests(unittest.TestCase):
    """Keep the ROM-wide playtest fix narrow, explicit, and source-preserving."""

    @classmethod
    def setUpClass(cls) -> None:
        """Materialize each affected bank once for the ROM-wide policy checks."""
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
        self.assertEqual(len(ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES), 54)
        self.assertEqual(len(EXPECTED_RECORDS), 66)
        self.assertEqual(PRESENTATION_ONLY_CTRL1_RECORDS, EXPECTED_RECORDS)
        self.assertEqual(
            frozenset(PRESENTATION_ONLY_CTRL1_TEMPLATES), EXPECTED_RECORDS
        )
        for record_id in (
            "TT1A/g0/r26",
            "T22/g0/r10",
            "TT3B/g1/r13",
            "T25/g1/r19",
            "TT6C/g1/r24",
            "TT6C/g2/r12",
        ):
            self.assertIn(record_id, EXPECTED_RECORDS)

    def test_certified_base_topology_remains_unchanged(self) -> None:
        """Keep audited CTRL:1 topology while allowing base prose revisions."""
        by_bank: dict[str, dict[str, str]] = {}
        for (
            record_id,
            historical_template,
        ) in PRESENTATION_ONLY_CTRL1_TEMPLATES.items():
            bank = record_id.split("/", 1)[0]
            if bank not in by_bank:
                by_bank[bank] = json.loads(
                    (
                        ROOT / "work" / "translations" / f"{bank}.json"
                    ).read_text(encoding="utf-8")
                )
            current = by_bank[bank][record_id]
            self.assertEqual(
                _controls(current), _controls(historical_template)
            )
            self.assertEqual(current.count("{CTRL:1}"), 1)

    def test_all_audited_waits_are_removed_from_production(self) -> None:
        """Let continuous English fill the box instead of pausing mid-thought."""
        for record_id in sorted(EXPECTED_RECORDS):
            bank = record_id.split("/", 1)[0]
            production = self.production_by_bank[bank][record_id]
            source = json.loads(
                (ROOT / "work" / "translations" / f"{bank}.json").read_text(
                    encoding="utf-8"
                )
            )[record_id]
            with self.subTest(record_id=record_id):
                self.assertNotIn("{CTRL:1}", production)
                validate_record_production_control_sequence(
                    record_id,
                    source,
                    production,
                )
                validate_renderer_buffer_layout(production)

    def test_personality_intro_flows_without_inherited_wait(self) -> None:
        """Keep the personality introduction continuous regardless of wording."""
        text = self.production_by_bank["TT1A"]["TT1A/g0/r5"]
        self.assertNotIn("{CTRL:1}", text)
        validate_renderer_buffer_layout(text)

    def test_time_travel_thought_flows_without_inherited_waits(self) -> None:
        """Keep TT1A/g0/r30 continuous regardless of editorial wording."""
        text = self.production_by_bank["TT1A"]["TT1A/g0/r30"]
        self.assertNotIn("{CTRL:1}", text)
        self.assertNotIn("{CTRL:6}", text)
        validate_renderer_buffer_layout(text)

    def test_unrelated_ctrl1_timing_remains_intact(self) -> None:
        """Keep dramatic, speaker-change, and intentional timing waits semantic."""
        controls_to_keep = {
            "TT1A": ("TT1A/g0/r0",),
            "TT1B": ("TT1B/g0/r26",),
            "TT3A": ("TT3A/g0/r19",),
            "TT4": ("TT4/g0/r12",),
            "TT6C": ("TT6C/g3/r4",),
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

    def test_policy_accepts_prose_change_with_same_topology(self) -> None:
        """Do not require a policy edit for ordinary wording revisions."""
        output = layout_review_text(
            "TT1A/g0/r5",
            "Rewritten personality-test introduction with different wording.",
            "Changed source.{CTRL:1}Still changed.",
        )
        self.assertNotIn("{CTRL:1}", output)
        validate_renderer_buffer_layout(output)

    def test_policy_fails_closed_if_audited_topology_changes(self) -> None:
        """Require a fresh audit only when runtime-significant controls change."""
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "control topology changed",
        ):
            layout_review_text(
                "TT1A/g0/r5",
                "Rewritten personality-test introduction.",
                "Changed source.{CTRL:3}Still changed.",
            )


if __name__ == "__main__":
    unittest.main()
