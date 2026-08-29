"""Regression tests for capacity-aware release compression performance."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from time_twist import compression
from time_twist.english import encode_english
from time_twist.textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT


class CompressionFastPathTests(unittest.TestCase):
    """Keep expensive optimization off the normal fitting release path."""

    def setUp(self) -> None:
        """Build a small corpus with enough repetition to create a dictionary."""
        self.groups = (
            (
                encode_english(
                    "TIME TWIST TIME TWIST HISTORY HISTORY TIME TWIST"
                ),
                encode_english(
                    "HISTORY TIME TWIST HISTORY TIME TWIST HISTORY"
                ),
            ),
        )

    def test_fitting_constrained_build_skips_expensive_search(self) -> None:
        """Return the validated greedy candidate without beam/order work."""
        baseline = compression.compress_english_groups(
            self.groups,
            max_bytes=4096,
            optimize=False,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        )
        validator = Mock(return_value=True)

        with (
            patch.object(
                compression,
                "_compress_english_groups_beam",
                side_effect=AssertionError("beam search should be skipped"),
            ),
            patch.object(
                compression,
                "_improve_dictionary_order",
                side_effect=AssertionError("order search should be skipped"),
            ),
        ):
            result = compression.compress_english_groups(
                self.groups,
                max_bytes=4096,
                optimize=True,
                maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
                candidate_validator=validator,
            )

        self.assertEqual(result, baseline)
        validator.assert_called_once_with(*baseline)

    def test_unbounded_optimization_retains_full_search(self) -> None:
        """Keep explicit minimum-size optimization behavior when unconstrained."""
        baseline = compression.compress_english_groups(
            self.groups,
            optimize=False,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        )

        with (
            patch.object(
                compression,
                "_compress_english_groups_beam",
                return_value=baseline,
            ) as beam,
            patch.object(
                compression,
                "_improve_dictionary_order",
                return_value=baseline,
            ) as reorder,
        ):
            result = compression.compress_english_groups(
                self.groups,
                optimize=True,
                maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
            )

        self.assertEqual(result, baseline)
        beam.assert_called_once()
        reorder.assert_called_once()


if __name__ == "__main__":
    unittest.main()
