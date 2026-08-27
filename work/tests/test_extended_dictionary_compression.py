"""Regression tests for extended English dictionary optimization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from time_twist.compression import (
    _improve_dictionary_order,
    expand_dictionary_symbols,
)
from time_twist.english import encode_english
from time_twist.scenario import (
    ScenarioBank,
    ScenarioRecord,
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from time_twist.textcodec import (
    EXTENDED_DICTIONARY_ENTRY_COUNT,
    PackedSymbol,
    SymbolKind,
)


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
                expand_dictionary_symbols(record, reordered)
                for record in group
            )
            for group in compressed
        )
        self.assertEqual(expanded, groups)

    def test_extended_rebuild_round_trips_and_preserves_fixed_tail(self) -> None:
        """Keep dictionary slots above 31 decodable without moving fixed data."""
        load_address = 0xA200
        group_zero_offset = 0x40
        fixed_tail_offset = 0x180
        fixed_tail = bytes(range(64))
        source = bytes([0xCC]) * fixed_tail_offset + fixed_tail
        source_bank = ScenarioBank(
            path=Path("synthetic-TT1A.bin"),
            data=source,
            load_address=load_address,
            dictionary_address=load_address + 0x80,
            group_table_address=load_address + 0x70,
            group_addresses=(load_address + group_zero_offset,),
            dictionary=(),
            dictionary_end_offset=fixed_tail_offset,
            records=(
                ScenarioRecord(
                    0,
                    0,
                    encode_english("source"),
                ),
            ),
        )
        reference_33 = PackedSymbol(SymbolKind.DICTIONARY, 33, 0, 0)
        dictionary = tuple(encode_english("A") for _ in range(33))

        rebuilt = rebuild_scenario_bank(
            source_bank,
            (((reference_33,),),),
            dictionary=dictionary,
            preserve_memory_footprint=True,
            maximum_dictionary_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        )

        self.assertEqual(rebuilt[fixed_tail_offset:], fixed_tail)
        self.assertEqual(len(rebuilt), len(source))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rebuilt.bin"
            path.write_bytes(rebuilt)
            parsed = parse_scenario_bank(
                path,
                load_address=load_address,
                extended_dictionary=True,
            )

        self.assertEqual(len(parsed.dictionary), 33)
        self.assertEqual(parsed.records[0].symbols[0].kind, SymbolKind.DICTIONARY)
        self.assertEqual(parsed.records[0].symbols[0].value, 33)
        self.assertEqual(
            render_symbols(parsed.records[0].symbols, parsed.dictionary),
            "A",
        )


if __name__ == "__main__":
    unittest.main()
