"""Regression tests for production prose layout in NOV2's text buffer."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from time_twist.production_translation import (
    ProductionTranslationError,
    layout_review_text,
    materialize_production_maps,
    validate_production_control_sequence,
    validate_renderer_buffer_layout,
)

ROOT = Path(__file__).resolve().parents[2]
BANK_NAMES = (
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
LAYOUT_CONTROL_RE = re.compile(r"\{CTRL:[04]\}")


class ProductionTranslationLayoutTests(unittest.TestCase):
    """Keep reviewed prose synchronized with NOV2's native renderer protocol."""

    def test_newscaster_retranslation_respects_ctrl2_reentry_barrier(
        self,
    ) -> None:
        """Keep pre-CTRL2 prose out of row three so resume cannot overwrite it."""
        template = (
            "News: Dr. Simon, a{CTRL:0}reclusive genius in{CTRL:2}"
            "physics, issued this{CTRL:0}comment on time travel{CTRL:4}"
            "late last night."
        )
        reviewed = (
            "Newscaster: Late last night, Dr. Simon—the physicist known as a "
            "reclusive genius—made a remarkable statement about time travel."
        )

        output = layout_review_text("TT1A/g0/r1", reviewed, template)

        self.assertEqual(
            output,
            "Newscaster: Late last{CTRL:0}night, Dr. Simon—the{CTRL:2}"
            "physicist known as a{CTRL:0}reclusive genius—made a{CTRL:4}"
            "remarkable statement{CTRL:4}about time travel.",
        )
        validate_renderer_buffer_layout(output)
        validate_production_control_sequence(template, output)

    def test_personality_intro_respects_ctrl1_reentry_barrier(self) -> None:
        """Keep pre-CTRL1 prose on row one so row-two resume preserves it."""
        template = "First: personality test{CTRL:1}Please answer each one."
        reviewed = "First, we'll begin with a personality test. Please answer each question."

        output = layout_review_text("TT1A/g0/r5", reviewed, template)

        self.assertEqual(
            output,
            "First, we'll begin with{CTRL:1}a personality test.{CTRL:0}"
            "Please answer each{CTRL:0}question.",
        )
        validate_renderer_buffer_layout(output)
        validate_production_control_sequence(template, output)

    def test_century_intro_respects_ctrl6_reentry_barrier(self) -> None:
        """Keep pre-CTRL6 prose above row four before the native row-four resume."""
        template = (
            "A new century nears...{CTRL:1}yet few welcome the age{CTRL:0}"
            "about to begin.{CTRL:6}Conflict still rages{CTRL:4}across the world."
            "{CTRL:3}Environmental harm and{CTRL:4}food shortages worsen."
            "{CTRL:3}Anyone can see it:{CTRL:4}Earth's future is grim."
        )
        reviewed = (
            "The 21st century is almost here… but people aren't exactly eager to "
            "welcome the new age. Conflict still rages around the world. "
            "Environmental destruction and food shortages are growing worse. "
            "Anyone can see that Earth's future is full of uncertainty."
        )

        output = layout_review_text("TT1A/g1/r1", reviewed, template)

        self.assertIn("The 21st century is{CTRL:1}", output)
        self.assertIn("aren't exactly eager to{CTRL:6}", output)
        validate_renderer_buffer_layout(output)
        validate_production_control_sequence(template, output)
        self.assertEqual(
            re.sub(r"\{CTRL:[0-7]\}", " ", output).split(),
            reviewed.split(),
        )

    def test_long_prose_uses_only_native_layout_continuations(self) -> None:
        """Extend long prose with CTRL0/CTRL4 without truncating approved words."""
        template = "One short source line."
        reviewed = " ".join(f"word{index}" for index in range(40))

        output = layout_review_text("TEST/g0/r0", reviewed, template)

        self.assertIn("{CTRL:0}", output)
        self.assertIn("{CTRL:4}", output)
        validate_renderer_buffer_layout(output)
        validate_production_control_sequence(template, output)
        self.assertEqual(
            LAYOUT_CONTROL_RE.sub(" ", output).split(),
            reviewed.split(),
        )

    def test_non_layout_inserted_control_is_rejected(self) -> None:
        """Reject invented semantic controls other than row advance and scroll."""
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "non-layout control",
        ):
            validate_production_control_sequence(
                "Alpha{CTRL:0}beta",
                "Alpha{CTRL:1}beta{CTRL:0}gamma",
            )

    def test_implicit_row_crossing_is_rejected(self) -> None:
        """Reject a segment that silently crosses the 24-column row boundary."""
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "crosses a 24-column row",
        ):
            validate_renderer_buffer_layout("X" * 25)

    def test_ctrl1_reentry_overwrite_is_rejected(self) -> None:
        """Reject staged row-two text immediately before CTRL1 re-enters row two."""
        unsafe = "A" * 24 + "{CTRL:0}B{CTRL:1}"
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "control 1 re-enters",
        ):
            validate_renderer_buffer_layout(unsafe)

    def test_ctrl2_reentry_overwrite_is_rejected(self) -> None:
        """Reject staged row-three text immediately before CTRL2 re-enters row three."""
        unsafe = "A" * 24 + "{CTRL:0}" + "B" * 24 + "{CTRL:0}C{CTRL:2}"
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "control 2 re-enters",
        ):
            validate_renderer_buffer_layout(unsafe)

    def test_ctrl6_reentry_overwrite_is_rejected(self) -> None:
        """Reject staged row-four text immediately before CTRL6 re-enters row four."""
        unsafe = (
            "A" * 24
            + "{CTRL:0}"
            + "B" * 24
            + "{CTRL:0}"
            + "C" * 24
            + "{CTRL:0}D{CTRL:6}"
        )
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "control 6 re-enters",
        ):
            validate_renderer_buffer_layout(unsafe)

    def test_known_pre_fix_newscaster_reentry_layout_is_rejected(self) -> None:
        """Detect the pre-fix layout that staged prose below the CTRL2 barrier."""
        unsafe = (
            "Newscaster: Late last{CTRL:0}night, Dr.{CTRL:0}"
            "Simon—the physicist{CTRL:0}known as{CTRL:2}"
            "a reclusive genius—made{CTRL:0}a remarkable statement{CTRL:4}"
            "about time travel."
        )
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "control 2 re-enters",
        ):
            validate_renderer_buffer_layout(unsafe)

    def test_entire_reviewed_corpus_materializes_buffer_safe(self) -> None:
        """Prove all 1,299 reviewed records preserve controls and re-entry safety."""
        with tempfile.TemporaryDirectory(
            prefix="time_twist_prod_layout_"
        ) as directory:
            output_directory = Path(directory)
            counts = materialize_production_maps(
                BANK_NAMES,
                base_directory=ROOT / "work" / "translations",
                override_directory=ROOT / "work" / "production_overrides",
                review_directory=ROOT / "review" / "production_retranslation",
                output_directory=output_directory,
            )
            self.assertEqual(sum(counts.values()), 1299)

            for bank_name in BANK_NAMES:
                baseline = json.loads(
                    (
                        ROOT / "work" / "translations" / f"{bank_name}.json"
                    ).read_text(encoding="utf-8")
                )
                production = json.loads(
                    (output_directory / f"{bank_name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(set(production), set(baseline))
                for record_id, text in production.items():
                    validate_renderer_buffer_layout(text)
                    validate_production_control_sequence(
                        baseline[record_id], text
                    )


if __name__ == "__main__":
    unittest.main()
