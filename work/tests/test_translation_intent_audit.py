"""Regression tests for source-grounded translation intent-gap ranking."""

from __future__ import annotations

import unittest

from tools.translation_intent_audit import (
    normalize_visible_text,
    rank_intent_gaps,
    score_row,
)


def scenario_row(**overrides: object) -> dict[str, object]:
    """Return a minimal neutral scenario workbook row for intent-audit tests."""
    row: dict[str, object] = {
        "record_type": "scenario",
        "original_record_id": "TT1B/g0/r1",
        "bank": "TT1B",
        "exact_japanese_source": "さいごにあおぞらをみたのは いつだっけ",
        "literal_english_meaning": "When was the last time I saw a blue sky?",
        "final_natural_english_translation": "When was the last time I saw a blue sky?",
        "patch_safe_english_translation": "When was the last time I saw a blue sky?",
        "speaker_or_narration_identity": "Protagonist's internal narration",
        "dialect_or_register": "Unmarked / neutral or context-dependent",
        "problems_with_current_english": "Accurate",
        "problem_categories": "Accurate",
        "nuance_lost_in_patch_safe_version": "",
        "requires_technical_expansion": "no",
        "requires_gameplay_context": "no",
        "unresolved_ambiguity": "",
    }
    row.update(overrides)
    return row


class TranslationIntentAuditTests(unittest.TestCase):
    """Keep intent-gap triage conservative and evidence-driven."""

    def test_presentation_control_only_difference_is_not_an_intent_gap(
        self,
    ) -> None:
        """Ignore an audited row break when the visible wording is identical."""
        row = scenario_row(
            patch_safe_english_translation=(
                "When was the last time{CTRL:0}I saw a blue sky?"
            )
        )

        self.assertIsNone(score_row(row))

    def test_editorial_speaker_labels_do_not_create_false_gap(self) -> None:
        """Treat Protagonist/Me and review slashes as metadata, not wording."""
        row = scenario_row(
            final_natural_english_translation=(
                "Protagonist: H-hello. / Girl: Hello…"
            ),
            patch_safe_english_translation=(
                "Me: H-hello.{CTRL:1}Girl: Hello..."
            ),
        )

        self.assertIsNone(score_row(row))

    def test_typography_only_difference_is_not_an_intent_gap(self) -> None:
        """Do not rank curly-versus-straight punctuation as lost wording."""
        row = scenario_row(
            final_natural_english_translation="I don’t know…",
            patch_safe_english_translation="I don't know...",
        )

        self.assertEqual(
            normalize_visible_text(
                str(row["final_natural_english_translation"])
            ),
            normalize_visible_text(str(row["patch_safe_english_translation"])),
        )
        self.assertIsNone(score_row(row))

    def test_explicit_lost_nuance_dominates_priority(self) -> None:
        """Give direct workbook evidence of nuance loss a high review weight."""
        gap = score_row(
            scenario_row(
                patch_safe_english_translation="Blue sky... how long ago?",
                nuance_lost_in_patch_safe_version=(
                    "The reflective full question was compressed for fit."
                ),
            )
        )

        self.assertIsNotNone(gap)
        assert gap is not None
        self.assertGreaterEqual(gap.score, 90)
        self.assertIn("workbook explicitly records lost nuance", gap.reasons)

    def test_marked_register_can_trigger_review_without_length_bias(
        self,
    ) -> None:
        """Surface source-marked voice even when natural and playable match."""
        gap = score_row(
            scenario_row(
                original_record_id="TT1B/g1/r0",
                dialect_or_register="ぞ: forceful assertion",
            )
        )

        self.assertIsNotNone(gap)
        assert gap is not None
        self.assertEqual(gap.score, 15)
        self.assertIn(
            "source has marked register/dialect/voice evidence", gap.reasons
        )

    def test_runtime_blockers_are_flagged_and_sorted_after_actionable_rows(
        self,
    ) -> None:
        """Do not let a high-score staging ambiguity invite an invented rewrite."""
        actionable = scenario_row(
            original_record_id="TT1B/g0/r10",
            patch_safe_english_translation="No one here.",
            nuance_lost_in_patch_safe_version="Subject nuance should be reviewed.",
        )
        blocked = scenario_row(
            original_record_id="TT1B/g0/r28",
            patch_safe_english_translation="Seen everything?",
            nuance_lost_in_patch_safe_version="Punctuation affects the reading.",
            requires_gameplay_context="yes",
            unresolved_ambiguity="Speaker staging must be verified in game.",
        )

        ranked = rank_intent_gaps([blocked, actionable])

        self.assertEqual(ranked[0].record_id, "TT1B/g0/r10")
        self.assertEqual(ranked[1].record_id, "TT1B/g0/r28")
        self.assertTrue(ranked[1].runtime_evidence_required)
        self.assertIn(
            "runtime/staging evidence required before rewriting",
            ranked[1].reasons,
        )


if __name__ == "__main__":
    unittest.main()
