"""Regression coverage for the second Codex semantic-control review."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from time_twist.production_translation import (
    ProductionTranslationError,
    layout_review_text,
    merged_translation_map,
)

ROOT = Path(__file__).resolve().parents[2]


def _production(bank_name: str) -> dict[str, str]:
    """Materialize one authoritative production bank."""
    return merged_translation_map(
        bank_name,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


class CodexFollowupSemanticTests(unittest.TestCase):
    """Keep pagination fixes from moving genuine semantic/timing boundaries."""

    def test_source_speaker_ctrl2_fails_closed_if_reviewed_turn_is_too_long(
        self,
    ) -> None:
        """Never slide a source speaker change into the preceding utterance."""
        template = (
            "Member 1: I felt dread{CTRL:0}all morning, so I came.{CTRL:2}"
            "Member 2: Me too.{CTRL:0}I couldn't sit still."
        )
        reviewed = (
            "Member 1: I've had a feeling of dread all morning, so I came here. "
            "Member 2: Me too. I couldn't sit still."
        )

        with self.assertRaisesRegex(
            ProductionTranslationError,
            "source CTRL:2 speaker boundary",
        ):
            layout_review_text("TEST/g0/r0", reviewed, template)

    def test_tt1b_speaker_transition_is_pinned_after_member_one(self) -> None:
        """Use the fit-safe wording rather than relocating the speaker control."""
        text = _production("TT1B")["TT1B/g3/r26"]
        self.assertIn("so I came.{CTRL:2}Member 2:", text)
        self.assertNotIn("all{CTRL:2}morning", text)

    def test_frankie_pendant_handoff_keeps_its_timing_boundary(self) -> None:
        """Keep the source handoff break before Frankie's second utterance."""
        text = _production("TT3A")["TT3A/g1/r9"]
        self.assertIn("A pendant.{CTRL:2}Frankie: From Grandma,", text)

    def test_bethlehem_inn_turn_keeps_its_ctrl2_boundary(self) -> None:
        """Keep Joseph's plea separate from the host's next reply."""
        text = _production("TT6B")["TT6B/g1/r13"]
        self.assertIn("Joseph: Please...{CTRL:2}Host: Sleep by the road", text)

    def test_angel_reveal_keeps_narration_to_joseph_ctrl2(self) -> None:
        """Keep the reveal pause before Joseph recognizes the apparent angel."""
        text = _production("TT6C")["TT6C/g1/r10"]
        self.assertIn("back again...!{CTRL:0}{CTRL:2}Joseph: Angel!", text)

    def test_quoted_dr_simon_heading_stays_whole(self) -> None:
        """Periods inside a quoted heading must not create a fake speaker label."""
        text = _production("TT1B")["TT1B/g2/r12"]
        self.assertTrue(text.startswith('"DR. SIMON VANISHES":{CTRL:2}'))
        self.assertNotIn('"DR. SIMON{CTRL:2}VANISHES"', text)

    def test_ctrl3_does_not_move_when_weak_ctrl2_is_demoted(self) -> None:
        """Preserve the scholar/result boundary during full-box pagination."""
        text = _production("TT1A")["TT1A/g0/r24"]
        self.assertNotIn("scholar{CTRL:3}type", text)
        self.assertIn("serious,{CTRL:3}stubborn scholar type.", text)

    def test_bishop_pact_signature_keeps_final_ctrl3_field(self) -> None:
        """Keep the pact signer visually and semantically separate from prose."""
        text = _production("T22")["T22/g0/r10"]
        self.assertIn("every evil.{CTRL:3}Bishop\"", text)
        self.assertEqual(
            [1, 0, 6, 4, 3],
            [
                int(value)
                for value in re.findall(r"\{CTRL:([0-7])\}", text)
                if int(value) in {0, 1, 3, 4, 6}
            ],
        )


if __name__ == "__main__":
    unittest.main()
