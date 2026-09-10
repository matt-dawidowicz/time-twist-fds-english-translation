"""Regression tests for capacity-aware release compression selection."""

from __future__ import annotations

import unittest
from unittest import mock

from time_twist.release_compression import compress_release_groups


class ReleaseCompressionFastPathTests(unittest.TestCase):
    """Lock the cheap-first release compression policy."""

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


if __name__ == "__main__":
    unittest.main()
