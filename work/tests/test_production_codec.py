"""Regression tests for the production 255-entry packed-text extension."""

from __future__ import annotations

import unittest

from time_twist.compression import expand_dictionary_symbols
from time_twist.english import encode_english
from time_twist.production_codec import (
    PRODUCTION_DICTIONARY_ENTRY_COUNT,
    _dictionary_expansions,
    _rebalanced_result,
    compress_production_groups,
    decode_production_symbol,
    optimal_parse_groups,
    pack_production_records,
    production_packed_size,
    split_production_records,
)
from time_twist.textcodec import (
    BitReader,
    BitWriter,
    PackedSymbol,
    PackedTextError,
    SymbolKind,
    pack_records,
)


class ProductionCodecTests(unittest.TestCase):
    """Keep the larger dictionary deterministic and backward compatible."""

    def test_entries_through_68_keep_existing_encoding(self) -> None:
        """Do not change any certified native/English dictionary reference."""
        for index in (1, 31, 32, 68):
            record = ((PackedSymbol(SymbolKind.DICTIONARY, index, 0, 0),),)
            self.assertEqual(
                pack_production_records(record), pack_records(record)
            )

    def test_high_dictionary_escape_round_trips_69_and_255(self) -> None:
        """Use native dictionary index zero as a 17-bit high-index escape."""
        records = (
            (
                PackedSymbol(SymbolKind.DICTIONARY, 69, 0, 0),
                PackedSymbol(SymbolKind.DICTIONARY, 255, 0, 0),
            ),
        )
        packed = pack_production_records(records)
        decoded, end = split_production_records(packed, limit=1)

        self.assertEqual(end, len(packed))
        self.assertEqual(
            [(symbol.kind, symbol.value) for symbol in decoded[0]],
            [
                (SymbolKind.DICTIONARY, 69),
                (SymbolKind.DICTIONARY, 255),
            ],
        )

    def test_high_dictionary_escape_rejects_noncanonical_payload(self) -> None:
        """Reserve the extended form exclusively for entries 69 through 255."""
        writer = BitWriter()
        writer.write_bits(0b1110, 4)
        writer.write_bits(0, 5)
        writer.write_bits(68, 8)
        reader = BitReader(writer.to_bytes())
        with self.assertRaisesRegex(PackedTextError, "noncanonical"):
            decode_production_symbol(reader)

    def test_optimal_parser_uses_nested_high_entry(self) -> None:
        """Allow entry 69 to reuse earlier entries while matching literal text."""
        hello = encode_english("hello")
        fillers = tuple(encode_english(f"R{index}") for index in range(1, 68))
        low_dictionary = (hello, *fillers)
        self.assertEqual(len(low_dictionary), 68)
        reference_one = PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0)
        entry_69 = (reference_one, *encode_english(" world"))
        dictionary = (*low_dictionary, entry_69)
        source = ((encode_english("hello world hello world"),),)

        parsed = optimal_parse_groups(source, dictionary)

        self.assertEqual(
            [(symbol.kind, symbol.value) for symbol in parsed[0][0]],
            [
                (SymbolKind.DICTIONARY, 69),
                (SymbolKind.COMMON, 0),
                (SymbolKind.DICTIONARY, 69),
            ],
        )
        expanded = expand_dictionary_symbols(parsed[0][0], dictionary)
        self.assertEqual(expanded, source[0][0])

    def test_cheap_tier_participates_in_unified_nested_grammar(self) -> None:
        """Build nested entries from slot 1 instead of freezing a flat tier."""
        source = (
            tuple(
                encode_english("alpha beta alpha beta gamma")
                for _ in range(10)
            ),
        )

        _compressed, dictionary = compress_production_groups(
            source,
            maximum_entries=10,
            rebalance_passes=0,
        )

        self.assertGreaterEqual(len(dictionary), 2)
        self.assertTrue(
            any(
                symbol.kind is SymbolKind.DICTIONARY
                for symbol in dictionary[1]
            )
        )

    def test_rebalance_promotes_heavy_high_entry_into_cheap_tier(self) -> None:
        """Let one logical dictionary move phrases across the 68-slot boundary."""
        fillers = tuple(
            encode_english(f"R{index:02d}") for index in range(1, 69)
        )
        hot_phrase = encode_english("alpha beta gamma")
        dictionary = (*fillers, hot_phrase)
        source = (
            tuple(
                encode_english("alpha beta gamma alpha beta gamma")
                for _ in range(20)
            ),
        )
        baseline = optimal_parse_groups(source, dictionary)
        baseline_size = production_packed_size(baseline, dictionary)

        parsed, rebalanced = _rebalanced_result(
            source,
            dictionary,
            required_entry_count=0,
            candidate_limit=6,
            maximum_passes=3,
        )

        self.assertLess(
            production_packed_size(parsed, rebalanced), baseline_size
        )
        self.assertLessEqual(
            _dictionary_expansions(rebalanced).index(hot_phrase) + 1,
            68,
        )

    def test_compressor_adds_profitable_high_entries(self) -> None:
        """Prove the adaptive compressor can grow beyond the 68 cheap slots."""
        required = tuple(encode_english(f"R{index}") for index in range(68))
        phrase = "alpha beta gamma delta epsilon"
        source = (
            tuple(
                encode_english(f"{phrase} {phrase} {phrase} {index}")
                for index in range(20)
            ),
        )

        compressed, dictionary = compress_production_groups(
            source,
            required_entries=required,
            maximum_entries=PRODUCTION_DICTIONARY_ENTRY_COUNT,
            maximum_grammar_tokens=12,
            maximum_nesting_depth=4,
            trial_candidates=4,
        )

        self.assertGreater(len(dictionary), 68)
        for original, packed in zip(source[0], compressed[0], strict=True):
            self.assertEqual(
                expand_dictionary_symbols(packed, dictionary),
                original,
            )
        baseline = optimal_parse_groups(source, required)
        self.assertLess(
            production_packed_size(compressed, dictionary),
            production_packed_size(baseline, required),
        )


if __name__ == "__main__":
    unittest.main()
