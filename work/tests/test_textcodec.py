from __future__ import annotations

import unittest

from time_twist.textcodec import (
    BitReader,
    BitWriter,
    PackedSymbol,
    SymbolKind,
    decode_symbol,
    encode_symbol,
    pack_records,
    split_records,
)


def bits_to_bytes(bits: str) -> bytes:
    padding = (-len(bits)) % 8
    return int(bits + "0" * padding, 2).to_bytes((len(bits) + padding) // 8, "big")


class PackedTextTests(unittest.TestCase):
    def test_prefix_tree(self) -> None:
        # common 17, extended 42, dictionary 9, control 6
        data = bits_to_bytes("010001" "110101010" "111001001" "1111110")
        reader = BitReader(data)
        symbols = [decode_symbol(reader) for _ in range(4)]
        self.assertEqual(
            [(symbol.kind, symbol.value) for symbol in symbols],
            [
                (SymbolKind.COMMON, 17),
                (SymbolKind.EXTENDED, 42),
                (SymbolKind.DICTIONARY, 9),
                (SymbolKind.CONTROL, 6),
            ],
        )

    def test_separator_aligns_the_next_record(self) -> None:
        # Record 0: common 1, control separator 5, three padding bits.
        # Record 1 begins at the following byte with common 2 and separator 5.
        data = bits_to_bytes("000001" "1111101" "000" "000010" "1111101")
        records, next_offset = split_records(data, limit=2)
        self.assertEqual(
            [[(symbol.kind, symbol.value) for symbol in record] for record in records],
            [
                [(SymbolKind.COMMON, 1)],
                [(SymbolKind.COMMON, 2)],
            ],
        )
        self.assertEqual(next_offset, 4)

    def test_encoder_round_trip(self) -> None:
        symbols = (
            PackedSymbol(SymbolKind.COMMON, 17, 0, 0),
            PackedSymbol(SymbolKind.EXTENDED, 42, 0, 0),
            PackedSymbol(SymbolKind.DICTIONARY, 9, 0, 0),
            PackedSymbol(SymbolKind.CONTROL, 6, 0, 0),
        )
        writer = BitWriter()
        for symbol in symbols:
            encode_symbol(writer, symbol)
        reader = BitReader(writer.to_bytes())
        decoded = tuple(decode_symbol(reader) for _ in symbols)
        self.assertEqual(
            [(symbol.kind, symbol.value) for symbol in decoded],
            [(symbol.kind, symbol.value) for symbol in symbols],
        )

    def test_pack_records_writes_aligned_separators(self) -> None:
        records = (
            (PackedSymbol(SymbolKind.COMMON, 1, 0, 0),),
            (PackedSymbol(SymbolKind.COMMON, 2, 0, 0),),
        )
        packed = pack_records(records)
        decoded, next_offset = split_records(packed, limit=2)
        self.assertEqual([symbol.value for symbol in decoded[0]], [1])
        self.assertEqual([symbol.value for symbol in decoded[1]], [2])
        self.assertEqual(next_offset, len(packed))


if __name__ == "__main__":
    unittest.main()
