"""Regression tests for extended English dictionary optimization."""

from __future__ import annotations

import unittest

from time_twist.compression import (
    _improve_dictionary_order,
    expand_dictionary_symbols,
)
from time_twist.english import encode_english
from time_twist.textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT


class ExtendedDictionaryCompressionTests(unittest.TestCase):
    """Keep offline optimization compatible with the patched NOV2 decoder."""

    def test_dictionary_order_accepts_more_than_31_entries(self) -> None:
        """Allow hill-climbing across dictionaries that use extended slots."""
        dictionary = tuple(encode_english(f"A{index}") for index in range(33))
        groups = (
            (
                encode_english("A31 A32 A31 A32"),
                encode_english("A0 A1 A2"),
            ),
        )

        compressed, reordered = _improve_dictionary_order(
            groups,
            dictionary,
            required_entry_count=31,
            max_passes=1,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        )

        self.assertEqual(len(reordered), 33)
        expanded = tuple(
            tuple(
                expand_dictionary_symbols(record, reordered) for record in group
            )
            for group in compressed
        )
        self.assertEqual(expanded, groups)


if __name__ == "__main__":
    unittest.main()
