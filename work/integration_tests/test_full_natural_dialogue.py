"""Regression tests for the isolated full-natural-dialogue playtest overlay."""

from __future__ import annotations

import unittest

from time_twist.english import (
    control_values,
    render_english,
    validate_display_width,
)
from time_twist.scenario_validation import (
    FULL_NATURAL_DIALOGUE_IDS,
    FULL_NATURAL_DIALOGUE_OVERRIDES,
    WRAPPED_SCENARIO_IDS,
    encode_validated_english,
    experimental_natural_dialogue,
)


class FullNaturalDialogueTests(unittest.TestCase):
    """Keep the experimental seven-record expansion narrow and reversible."""

    def test_exactly_seven_reviewed_records_are_overridden(self) -> None:
        """Limit the experiment to the seven workbook-reviewed records."""
        self.assertEqual(len(FULL_NATURAL_DIALOGUE_IDS), 7)
        self.assertEqual(
            FULL_NATURAL_DIALOGUE_IDS,
            frozenset(
                {
                    "TT1B/g0/r1",
                    "TT1B/g0/r28",
                    "TT1B/g0/r31",
                    "TT1B/g1/r14",
                    "TT1B/g2/r5",
                    "TT3A/g2/r30",
                    "TT6A/g0/r13",
                }
            ),
        )

    def test_natural_overlay_preserves_controls_and_safe_wraps(self) -> None:
        """Prove every expanded line retains controls and wrap boundaries."""
        for record_id, (
            compact,
            natural,
        ) in FULL_NATURAL_DIALOGUE_OVERRIDES.items():
            with self.subTest(record=record_id):
                self.assertEqual(
                    control_values(natural), control_values(compact)
                )
                self.assertIn(record_id, WRAPPED_SCENARIO_IDS)
                validate_display_width(natural, allow_wrap=True)
                encoded = encode_validated_english(record_id, compact, compact)
                self.assertEqual(render_english(encoded), natural)

    def test_explicit_caller_edit_is_not_silently_overridden(self) -> None:
        """Leave an explicit non-promoted caller edit untouched."""
        record_id = "TT1B/g0/r1"
        custom = "Custom line."
        self.assertEqual(
            experimental_natural_dialogue(record_id, custom),
            custom,
        )

    def test_unrelated_records_are_unchanged(self) -> None:
        """Leave every record outside the seven-ID allowlist untouched."""
        record_id = "TT1B/g0/r2"
        original = "No time for that now!"
        self.assertEqual(
            experimental_natural_dialogue(record_id, original),
            original,
        )


if __name__ == "__main__":
    unittest.main()
