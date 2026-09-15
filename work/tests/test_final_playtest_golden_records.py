"""Lock the scenario records approved in the final playtest build."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.production_translation import (
    ProductionTranslationError,
    merged_translation_map,
    validate_record_production_control_sequence,
)

ROOT = Path(__file__).resolve().parents[2]

GOLDEN_RECORDS = {
    "TT1A/g0/r3": 'The Fortune Service{CTRL:0}Center presents "Today\'s{CTRL:0}Fortune". Please enter{CTRL:0}your blood type.',
    "TT1A/g0/r24": "You're cautious and{CTRL:0}methodical, so you{CTRL:0}rarely fail, but you can{CTRL:0}come across as ordinary.{CTRL:4}Principled and diligent,{CTRL:4}you're a serious,{CTRL:4}stubborn scholar type.{CTRL:4}You worry so much about{CTRL:4}other people that you{CTRL:4}wear yourself out.{CTRL:4}You're awkward in love,{CTRL:4}but a romantic at heart.",
    "TT1A/g0/r30": "Time travel, huh… So{CTRL:0}far, it's all talk.{CTRL:0}Nobody's ever actually{CTRL:0}made it work. More{CTRL:4}importantly…",
    "TT1A/g0/r31": "…………{CTRL:1}Weird… Some kind of{CTRL:0}magic spell?{CTRL:6}{CTRL:4}Whatever… No time like{CTRL:4}the present!",
    "TT1A/g1/r1": "The 21st century is{CTRL:0}almost here… but people{CTRL:0}aren't exactly eager{CTRL:0}to welcome the new age.{CTRL:3}Conflict still rages{CTRL:4}around the world.{CTRL:3}Environmental{CTRL:4}destruction and food{CTRL:4}shortages are growing{CTRL:4}worse. Anyone can see{CTRL:4}that Earth's future is{CTRL:4}full of uncertainty.",
    "TT1B/g0/r0": "Here we are… the Devil{CTRL:0}Museum. I've been{CTRL:0}meaning to visit this{CTRL:0}place.",
}


def _production(bank: str) -> dict[str, str]:
    return merged_translation_map(
        bank,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


class FinalPlaytestGoldenRecordTests(unittest.TestCase):
    """Keep final-playtest prose and control geometry byte-deterministic."""

    def test_materialized_records_match_golden_build(self) -> None:
        by_bank = {bank: _production(bank) for bank in {"TT1A", "TT1B"}}
        for record_id, expected in GOLDEN_RECORDS.items():
            bank = record_id.split("/", 1)[0]
            with self.subTest(record_id=record_id):
                self.assertEqual(by_bank[bank][record_id], expected)

    def test_materialization_fails_closed_on_exact_base_prose_drift(self) -> None:
        """Require re-audit even when changed base prose keeps the same controls."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_directory = root / "translations"
            override_directory = root / "production_overrides"
            base_directory.mkdir()
            override_directory.mkdir()

            base = json.loads(
                (ROOT / "work" / "translations" / "TT1A.json").read_text(
                    encoding="utf-8"
                )
            )
            base["TT1A/g0/r30"] = base["TT1A/g0/r30"].replace(
                "More importantly...", "Different prose..."
            )
            (base_directory / "TT1A.json").write_text(
                json.dumps(base, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (override_directory / "TT1A.json").write_text(
                (ROOT / "work" / "production_overrides" / "TT1A.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ProductionTranslationError, "certified base template changed"
            ):
                merged_translation_map(
                    "TT1A",
                    base_directory=base_directory,
                    override_directory=override_directory,
                )

    def test_runtime_validation_accepts_japanese_text_with_same_topology(self) -> None:
        """Apply record policy by native controls, not English visible text."""
        production = GOLDEN_RECORDS["TT1A/g0/r30"]
        japanese_shaped = (
            "source A{CTRL:1}source B{CTRL:0}source C{CTRL:6}source D"
        )
        validate_record_production_control_sequence(
            "TT1A/g0/r30", japanese_shaped, production
        )

    def test_runtime_validation_fails_closed_on_topology_drift(self) -> None:
        production = GOLDEN_RECORDS["TT1A/g0/r30"]
        with self.assertRaisesRegex(
            ProductionTranslationError, "native control topology changed"
        ):
            validate_record_production_control_sequence(
                "TT1A/g0/r30",
                "source A{CTRL:1}source B{CTRL:3}source C{CTRL:6}source D",
                production,
            )


if __name__ == "__main__":
    unittest.main()
