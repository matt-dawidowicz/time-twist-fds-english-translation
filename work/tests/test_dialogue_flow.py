"""Regression coverage for native row state and all source-led continuations."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from time_twist.dialogue_flow import trace_dialogue, validate_continuation
from time_twist.production_translation import QUIZ_QUESTION_RECORDS
from time_twist.production_translation_core import ProductionTranslationError
from time_twist.v38_build import restore_checkpoint, v39_checkpoint_records
from time_twist.v40_checkpoint import (
    CONTINUATION_PREDECESSORS,
    prepare_v40_dictionaries,
)

ROOT = Path(__file__).resolve().parents[2]


class DialogueFlowTests(unittest.TestCase):
    """Exercise retained text, scrolling, and coverage independently of hashes."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load active maps, source entry controls, and immutable old layouts."""
        cls.texts = {
            key: value
            for path in (ROOT / "work/translations").glob("*.json")
            for key, value in json.loads(path.read_text()).items()
        }
        cls.source_continuations = {
            record["id"]
            for path in (ROOT / "work/source_records").glob("*.json")
            for group in json.loads(path.read_text()).get("groups", [])
            for record in group["records"]
            if record["japanese"].startswith("{CTRL:")
        }
        with tempfile.TemporaryDirectory() as directory:
            cls.old = v39_checkpoint_records(
                restore_checkpoint(
                    ROOT / "recovery/v38/repro_bundle", Path(directory)
                )
            )

    def test_all_source_led_continuations_are_registered(self) -> None:
        """Do not silently omit a source continuation from retained-row checks."""
        self.assertEqual(
            set(CONTINUATION_PREDECESSORS), self.source_continuations
        )
        self.assertEqual(len(self.source_continuations), 63)

    def test_every_record_and_registered_transition_is_safe(self) -> None:
        """Trace all 1,299 records and every registered predecessor pair."""
        self.assertEqual(len(self.texts), 1299)
        for key, value in self.texts.items():
            with self.subTest(record=key):
                trace_dialogue(key, value)
        for next_id, predecessors in CONTINUATION_PREDECESSORS.items():
            for previous_id in predecessors:
                with self.subTest(previous=previous_id, next=next_id):
                    validate_continuation(previous_id, next_id, self.texts)

    def test_v39_exposes_54_retained_buffer_overlaps(self) -> None:
        """Ensure the regression model actually detects the old failure class."""
        failures = []
        for next_id, predecessors in CONTINUATION_PREDECESSORS.items():
            for previous_id in predecessors:
                try:
                    validate_continuation(previous_id, next_id, self.old)
                except ProductionTranslationError:
                    failures.append(next_id)
        self.assertEqual(len(failures), 54)

    def test_dictionary_wait_controls_are_rejected(self) -> None:
        """Prevent native returns with pending dictionary stack frames."""
        for control in (1, 2, 3, 4, 6):
            with (
                self.subTest(control=control),
                tempfile.TemporaryDirectory() as directory,
            ):
                source = Path(directory)
                restore_checkpoint(ROOT / "recovery/v38/repro_bundle", source)
                with (
                    patch(
                        "time_twist.v40_checkpoint.TT1B_DICTIONARY_ADDITIONS",
                        [[["ctrl", control]]],
                    ),
                    self.assertRaisesRegex(ValueError, "wait/scroll"),
                ):
                    prepare_v40_dictionaries(source)

    def test_complete_quiz_question_remains_in_final_buffer(self) -> None:
        """Keep the complete prompt after its final scroll before answer input."""
        self.assertEqual(len(QUIZ_QUESTION_RECORDS), 25)
        for record in QUIZ_QUESTION_RECORDS:
            with self.subTest(record=record):
                text = self.texts[record]
                trace = trace_dialogue(record, text)
                glyphs = len(re.sub(r"\{CTRL:[0-7]\}", "", text))
                self.assertEqual(trace.owners.count(record), 2 * glyphs)

    def test_two_leading_advances_use_native_line_state(self) -> None:
        """Model zero-page $72 instead of treating repeated controls as idempotent."""
        result = trace_dialogue("test", "{CTRL:0}{CTRL:0}Hello")
        self.assertEqual(result.positions[0], 96)
        with self.assertRaisesRegex(ProductionTranslationError, "crosses"):
            trace_dialogue(
                "test", "{CTRL:0}{CTRL:0}" + ("a" * 20 + "{CTRL:0}") * 3
            )

    def test_scrolling_preserves_retained_rows_without_overwrite(self) -> None:
        """Shift ownership with native scrolls before writing the bottom row."""
        text = "First{CTRL:0}Second{CTRL:0}Third{CTRL:0}Fourth"
        previous = trace_dialogue("previous", text)
        current = trace_dialogue("next", "{CTRL:4}Fifth", previous.owners)
        self.assertEqual(current.scrolls, 1)
        self.assertEqual(current.positions[0], 144)
        self.assertEqual(current.owners[0], "previous")
        with self.assertRaisesRegex(ProductionTranslationError, "overwrites"):
            trace_dialogue("next", "{CTRL:0}Fifth", previous.owners)

    def test_lost_continuation_control_fails_without_source_lock(self) -> None:
        """Reject a recurrence at map validation time, before ROM compilation."""
        texts = dict(self.texts)
        texts["TT1B/g0/r2"] = "No time for that now!"
        with self.assertRaisesRegex(ProductionTranslationError, "overwrites"):
            validate_continuation("TT1B/g0/r1", "TT1B/g0/r2", texts)


if __name__ == "__main__":
    unittest.main()
