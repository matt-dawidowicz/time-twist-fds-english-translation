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
    merged_translation_map,
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
    """Keep reviewed prose synchronized with NOV2's four-row renderer state."""

    def test_newscaster_retranslation_uses_explicit_row_controls(self) -> None:
        """Reflow the screenshot regression without any implicit row crossing."""
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

    def test_exact_third_row_advances_without_premature_scroll(self) -> None:
        """Use row four when row three ends exactly at the 24-column edge."""
        template = (
            "Our sincere apologies.{CTRL:0}The correct words are:{CTRL:0}"
            '"Your smile makes the{CTRL:0}sun rise."{CTRL:3}'
            "Thank you for using us."
        )
        reviewed = (
            'We sincerely apologize. The correct phrase is: "When you smile, '
            'it\'s as though the sun rises." Thank you for using our service.'
        )

        output = layout_review_text("TT1A/g1/r0", reviewed, template)

        self.assertIn(
            '{CTRL:0}"When you smile, it\'s as{CTRL:0}though the sun rises."',
            output,
        )
        self.assertNotIn(
            '{CTRL:0}"When you smile, it\'s as{CTRL:4}though the sun rises."',
            output,
        )
        validate_renderer_buffer_layout(output)

    def test_adjacent_row_and_section_control_keeps_chant_boundary_natural(
        self,
    ) -> None:
        """Keep the source section change before the chant, not inside it."""
        template = (
            "Maradul Barao Garadura{CTRL:0}{CTRL:2}"
            "Chant it over and over.{CTRL:3}"
            "Maradul Barao Garadura{CTRL:4}Maradul Barao Garadura!"
        )
        reviewed = (
            "Maradul Barao Garadura… Chant it again and again. "
            "Maradul Barao Garadura… Maradul Barao Garadura!"
        )

        output = layout_review_text("TT1A/g0/r29", reviewed, template)

        self.assertEqual(
            output,
            "Maradul Barao Garadura…{CTRL:2}Chant it again and{CTRL:0}"
            "again.{CTRL:3}Maradul Barao Garadura…{CTRL:4}"
            "Maradul Barao Garadura!",
        )

    def test_section_anchor_does_not_treat_dr_as_sentence_end(self) -> None:
        """Keep the newspaper heading intact rather than breaking after DR."""
        template = (
            '"Dr. Simon Vanishes"{CTRL:0}{CTRL:2}'
            "Last night, Simon, 84,{CTRL:0}unveiled a warp theory."
        )
        reviewed = (
            '"DR. SIMON VANISHES" Last night, Dr. Simon, 84, '
            "revealed warp theory."
        )

        output = layout_review_text("TEST/g0/r2", reviewed, template)

        self.assertTrue(output.startswith('"DR. SIMON VANISHES"{CTRL:2}'))
        self.assertNotIn('"DR.{CTRL:2}', output)

    def test_layout_normalizes_repeated_interword_spacing(self) -> None:
        """Collapse source/editorial padding to one visible word space."""
        output = layout_review_text(
            "TEST/g0/r3",
            "Chant   it    again and again.",
            "Short source.",
        )
        visible = LAYOUT_CONTROL_RE.sub(" ", output)
        self.assertNotIn("  ", visible)
        self.assertEqual(
            visible.split(), ["Chant", "it", "again", "and", "again."]
        )

    def test_greedy_wrap_uses_maximum_available_width(self) -> None:
        """Fill each row greedily instead of balancing two short rows."""
        output = layout_review_text(
            "TEST/g0/r0",
            "Whatever… No time like the present!",
            "Short source.",
        )
        self.assertEqual(
            output,
            "Whatever… No time like{CTRL:0}the present!",
        )

    def test_new_speaker_starts_on_fresh_row(self) -> None:
        """Never append a new speaker label to the previous speaker's line."""
        output = layout_review_text(
            "TEST/g0/r1",
            "Resident: I'm staying. Me: I understand.",
            "Resident: Staying. Me: Fine.",
        )
        self.assertEqual(
            output,
            "Resident: I'm staying.{CTRL:0}Me: I understand.",
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
            "semantic controls",
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

    def test_known_pre_fix_newscaster_layout_is_rejected(self) -> None:
        """Detect the implicit wrapping pattern behind the screenshot corruption."""
        unsafe = (
            "Newscaster: Late last   night, Dr.{CTRL:0}"
            "Simon—the physicist     known{CTRL:2}"
            "as a reclusive          genius—made{CTRL:0}"
            "a remarkable statement  about{CTRL:4}time travel."
        )
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "crosses a 24-column row",
        ):
            validate_renderer_buffer_layout(unsafe)

    def test_explicit_override_is_the_final_editorial_layer(self) -> None:
        """Let a deliberate last-mile override supersede reviewed prose."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / "base"
            review = root / "review"
            overrides = root / "overrides"
            base.mkdir()
            review.mkdir()
            overrides.mkdir()
            record_id = "TT1A/g0/r0"
            (base / "TT1A.json").write_text(
                json.dumps({record_id: "Base."}) + "\n", encoding="utf-8"
            )
            (review / "TT1A_proposal.json").write_text(
                json.dumps({"records": {record_id: "Reviewed."}}) + "\n",
                encoding="utf-8",
            )
            (overrides / "TT1A.json").write_text(
                json.dumps({record_id: "Override."}) + "\n", encoding="utf-8"
            )

            merged = merged_translation_map(
                "TT1A",
                base_directory=base,
                review_directory=review,
                override_directory=overrides,
            )
            self.assertEqual(merged[record_id], "Override.")

    def test_entire_reviewed_corpus_materializes_buffer_safe(self) -> None:
        """Prove all 1,299 reviewed records preserve controls and row state."""
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
