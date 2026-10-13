"""Behavioral oracle for fast native-format dictionary substring counts.

These tests intentionally avoid retail ROM files and compare the optimized
implementation with the exact original leftmost, non-overlapping find loop.
"""

from __future__ import annotations

import random
import unittest

from time_twist.compression import _non_overlapping_byte_occurrences


def _legacy_occurrences(haystack: bytes, needle: bytes) -> int:
    """Preserve the original loop's overlap and search-offset semantics."""
    count = 0
    position = 0
    while True:
        position = haystack.find(needle, position)
        if position < 0:
            return count
        count += 1
        position += len(needle)


class NativeCompressionScanTests(unittest.TestCase):
    """Guard the native-code replacement for the compressor hot loop."""

    def test_known_overlap_and_binary_cases(self) -> None:
        """Match leftmost non-overlapping occurrences, including 0x00 bytes."""
        examples = (
            (b"aaaaa", b"aa", 2),
            (b"abababa", b"aba", 2),
            (b"abcabcabc", b"abc", 3),
            (b"\x00\x00\x00\x00\x00", b"\x00\x00", 2),
            (b"abc", b"xyz", 0),
            (b"", b"x", 0),
            (b"x", b"xx", 0),
        )
        for haystack, needle, expected in examples:
            with self.subTest(haystack=haystack, needle=needle):
                self.assertEqual(
                    _non_overlapping_byte_occurrences(haystack, needle),
                    expected,
                )

    def test_randomized_search_matches_preserved_reference(self) -> None:
        """Catch any change in match counts for overlapping patterns."""
        rng = random.Random(20261013)
        for _ in range(500):
            haystack = bytes(rng.randrange(6) for _ in range(rng.randrange(128)))
            needle = bytes(rng.randrange(6) for _ in range(rng.randrange(1, 13)))
            self.assertEqual(
                _non_overlapping_byte_occurrences(haystack, needle),
                _legacy_occurrences(haystack, needle),
            )

    def test_empty_needle_is_rejected(self) -> None:
        """Avoid silently treating an empty candidate as every boundary."""
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            _non_overlapping_byte_occurrences(b"example", b"")


if __name__ == "__main__":
    unittest.main()
