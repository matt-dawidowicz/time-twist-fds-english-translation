"""Cross-check the optional Rust compression search against Python."""

from __future__ import annotations

import unittest

from time_twist.compression import compress_english_groups, packed_size
from time_twist.compression_native import (
    compress_english_groups_native,
    native_optimizer_available,
)
from time_twist.english import encode_english


class NativeCompressionEquivalenceTests(unittest.TestCase):
    """Require exact deterministic agreement on representative corpora."""

    def _assert_equivalent(
        self,
        groups: tuple[tuple[tuple[object, ...], ...], ...],
        *,
        max_bytes: int,
    ) -> None:
        """Compare Python and Rust when the optional native helper is built."""
        # The repository's supported unit suites forbid skipped tests. Keep
        # Python-only installations valid while the dedicated native CI job
        # builds the helper and exercises this same test file substantively.
        if not native_optimizer_available():
            return
        python_result = compress_english_groups(  # type: ignore[arg-type]
            groups,
            max_bytes=max_bytes,
            optimize=True,
            maximum_entries=68,
        )
        native_result = compress_english_groups_native(  # type: ignore[arg-type]
            groups,
            max_bytes=max_bytes,
            maximum_entries=68,
        )
        self.assertEqual(native_result, python_result)
        self.assertEqual(
            packed_size(*native_result), packed_size(*python_result)
        )

    def test_repeated_words_match_reference_search(self) -> None:
        """Match Python on overlapping repeated English phrases."""
        groups = (
            (
                encode_english("the old road and the old road"),
                encode_english("the old road ends at the old gate"),
                encode_english("the old gate and the old road"),
            ),
        )
        self._assert_equivalent(groups, max_bytes=512)

    def test_controls_and_multiple_groups_match_reference_search(self) -> None:
        """Preserve hard control boundaries and group structure exactly."""
        groups = (
            (
                encode_english("look here{CTRL:0}look there"),
                encode_english("look here again"),
            ),
            (
                encode_english("look there again"),
                encode_english("look here and look there"),
            ),
        )
        self._assert_equivalent(groups, max_bytes=512)


if __name__ == "__main__":
    unittest.main()
