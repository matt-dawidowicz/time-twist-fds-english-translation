"""Regression tests for capacity-aware release compression selection."""

from __future__ import annotations

import unittest
from unittest import mock

from time_twist.release_compression import compress_release_groups


class ReleaseCompressionFastPathTests(unittest.TestCase):
    """Lock the cheap-first and editorial release compression policies."""

    def test_fitting_fast_candidate_skips_optimizer(self) -> None:
        """Accept a fitting fast candidate without expensive search."""
        fast = ((), ())
        compressor = mock.Mock(return_value=fast)
        measure = mock.Mock(return_value=10)

        result = compress_release_groups(
            (), max_bytes=10, compressor=compressor, measure=measure
        )

        self.assertEqual(result, fast)
        self.assertEqual(compressor.call_count, 1)
        self.assertFalse(compressor.call_args.kwargs["optimize"])

    def test_over_capacity_fast_candidate_uses_optimizer(self) -> None:
        """Escalate when the fast result still exceeds capacity."""
        fast = ((), ())
        optimized = (((),), ())
        compressor = mock.Mock(side_effect=(fast, optimized))
        measure = mock.Mock(return_value=11)

        result = compress_release_groups(
            (), max_bytes=10, compressor=compressor, measure=measure
        )

        self.assertEqual(result, optimized)
        self.assertEqual(compressor.call_count, 2)
        self.assertFalse(compressor.call_args_list[0].kwargs["optimize"])
        self.assertTrue(compressor.call_args_list[1].kwargs["optimize"])

    def test_incompatible_fast_candidate_uses_optimizer(self) -> None:
        """Escalate when fixed-UI validation rejects a fitting result."""
        fast = ((), ())
        optimized = (((),), ())
        compressor = mock.Mock(side_effect=(fast, optimized))
        measure = mock.Mock(return_value=5)
        validator = mock.Mock(return_value=False)

        result = compress_release_groups(
            (),
            max_bytes=10,
            candidate_validator=validator,
            compressor=compressor,
            measure=measure,
        )

        self.assertEqual(result, optimized)
        validator.assert_called_once_with(*fast)
        self.assertIs(
            compressor.call_args_list[1].kwargs["candidate_validator"],
            validator,
        )
        self.assertTrue(compressor.call_args_list[1].kwargs["optimize"])

    def test_maximize_headroom_runs_optimizer_without_fast_accept(self) -> None:
        """Use the strongest search even when a greedy result would fit."""
        optimized = (((),), ())
        compressor = mock.Mock(return_value=optimized)
        measure = mock.Mock()
        validator = mock.Mock()

        result = compress_release_groups(
            (),
            max_bytes=10,
            candidate_validator=validator,
            compressor=compressor,
            measure=measure,
            maximize_headroom=True,
        )

        self.assertEqual(result, optimized)
        compressor.assert_called_once_with(
            (),
            required_entries=(),
            max_bytes=10,
            optimize=True,
            maximum_entries=68,
            candidate_validator=validator,
        )
        measure.assert_not_called()
        validator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
