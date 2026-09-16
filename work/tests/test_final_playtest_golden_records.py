"""Protect final-playtest control geometry without freezing editorial prose."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.production_translation import (
    CONTROL_RE,
    ProductionTranslationError,
    merged_translation_map,
    validate_record_production_control_sequence,
    validate_renderer_buffer_layout,
)

ROOT = Path(__file__).resolve().parents[2]

# These are the runtime-significant invariants approved by the final playtest.
# Visible wording is intentionally not duplicated here so translation edits do
# not require synchronized assertion updates.
GOLDEN_CONTROL_SEQUENCES = {
    "TT1A/g0/r3": (0, 0, 0),
    "TT1A/g0/r24": (0, 0, 0, 4, 4, 4, 4, 4, 4),
    "TT1A/g0/r30": (0, 0, 0, 4),
    "TT1A/g0/r31": (1, 0, 6, 4, 4),
    "TT1A/g1/r1": (0, 0, 0, 3, 4, 3, 4, 4, 4, 4),
    "TT1B/g0/r0": (0, 0, 0),
}


def _production(bank: str) -> dict[str, str]:
    """Materialize one bank with the maintained production source layers."""
    return merged_translation_map(
        bank,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


def _controls(text: str) -> tuple[int, ...]:
    """Return the native control sequence for one materialized record."""
    return tuple(int(value) for value in CONTROL_RE.findall(text))


class FinalPlaytestGoldenRecordTests(unittest.TestCase):
    """Keep final-playtest control geometry stable while permitting prose edits."""

    def test_materialized_records_preserve_playtest_control_geometry(
        self,
    ) -> None:
        """Require approved records to retain controls and renderer-safe layout."""
        by_bank = {bank: _production(bank) for bank in {"TT1A", "TT1B"}}
        for record_id, expected_controls in GOLDEN_CONTROL_SEQUENCES.items():
            bank = record_id.split("/", 1)[0]
            with self.subTest(record_id=record_id):
                text = by_bank[bank][record_id]
                self.assertEqual(_controls(text), expected_controls)
                validate_renderer_buffer_layout(text)

    def test_materialization_accepts_base_prose_drift_with_same_controls(
        self,
    ) -> None:
        """Permit editorial changes when the audited source topology is unchanged."""
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
                (
                    ROOT / "work" / "production_overrides" / "TT1A.json"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            materialized = merged_translation_map(
                "TT1A",
                base_directory=base_directory,
                override_directory=override_directory,
            )
            self.assertIn("TT1A/g0/r30", materialized)

    def test_materialization_still_fails_closed_on_base_topology_drift(
        self,
    ) -> None:
        """Require re-audit when a policy record changes native controls."""
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
                "{CTRL:1}", "{CTRL:3}", 1
            )
            (base_directory / "TT1A.json").write_text(
                json.dumps(base, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (override_directory / "TT1A.json").write_text(
                (
                    ROOT / "work" / "production_overrides" / "TT1A.json"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ProductionTranslationError, "base control topology changed"
            ):
                merged_translation_map(
                    "TT1A",
                    base_directory=base_directory,
                    override_directory=override_directory,
                )

    def test_runtime_validation_accepts_text_with_same_topology(self) -> None:
        """Apply record policy by native controls, not visible text."""
        production = _production("TT1A")["TT1A/g0/r30"]
        source_shaped = (
            "source A{CTRL:1}source B{CTRL:0}source C{CTRL:6}source D"
        )
        validate_record_production_control_sequence(
            "TT1A/g0/r30", source_shaped, production
        )

    def test_runtime_validation_fails_closed_on_topology_drift(self) -> None:
        """Reject native control geometry that drifts from the reviewed policy."""
        production = _production("TT1A")["TT1A/g0/r30"]
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
