"""Property tests for fixture-free packed-text and FDS invariants."""

from __future__ import annotations

import unittest

from hypothesis import given, settings
from hypothesis import strategies as st
from time_twist.compression import (
    compress_english_groups,
    expand_dictionary_symbols,
    packed_size,
)
from time_twist.fds import (
    DISK_INFO_SIZE,
    FDS_HEADER_SIZE,
    FILE_HEADER_SIZE,
    SIDE_SIZE,
    FdsFormatError,
    FdsImage,
)
from time_twist.textcodec import (
    PackedSymbol,
    SymbolKind,
    pack_records,
    split_records,
)


def symbol(kind: SymbolKind, value: int) -> PackedSymbol:
    """Create a position-neutral symbol for generated native streams."""
    return PackedSymbol(kind, value, 0, 0)


PACKABLE_SYMBOLS = st.one_of(
    st.integers(min_value=0, max_value=47).map(
        lambda value: symbol(SymbolKind.COMMON, value)
    ),
    st.integers(min_value=0, max_value=63).map(
        lambda value: symbol(SymbolKind.EXTENDED, value)
    ),
    st.integers(min_value=1, max_value=31).map(
        lambda value: symbol(SymbolKind.DICTIONARY, value)
    ),
    st.sampled_from((0, 1, 2, 3, 4, 6, 7)).map(
        lambda value: symbol(SymbolKind.CONTROL, value)
    ),
)
LITERAL_OR_CONTROL_SYMBOLS = st.one_of(
    st.integers(min_value=0, max_value=47).map(
        lambda value: symbol(SymbolKind.COMMON, value)
    ),
    st.integers(min_value=0, max_value=63).map(
        lambda value: symbol(SymbolKind.EXTENDED, value)
    ),
    st.sampled_from((0, 1, 2, 3, 4, 6, 7)).map(
        lambda value: symbol(SymbolKind.CONTROL, value)
    ),
)
PACKABLE_RECORD = st.lists(PACKABLE_SYMBOLS, max_size=12).map(tuple)
LITERAL_RECORD = st.lists(LITERAL_OR_CONTROL_SYMBOLS, max_size=12).map(tuple)
LITERAL_GROUP = st.lists(LITERAL_RECORD, min_size=1, max_size=4).map(tuple)
LITERAL_GROUPS = st.lists(LITERAL_GROUP, min_size=1, max_size=3).map(tuple)


def signatures(
    records: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[tuple[tuple[SymbolKind, int], ...], ...]:
    """Discard source bit positions when comparing semantic symbols."""
    return tuple(
        tuple((entry.kind, entry.value) for entry in record)
        for record in records
    )


def make_side(payloads: tuple[bytes, ...], *, padding_byte: int) -> bytes:
    """Build one valid synthetic archival side with arbitrary payloads."""
    disk_info = bytearray(DISK_INFO_SIZE)
    disk_info[0] = 0x01
    disk_info[16:20] = b"PROP"
    blocks = bytearray(disk_info)
    blocks.extend((0x02, len(payloads)))
    for index, payload in enumerate(payloads):
        header = bytearray(FILE_HEADER_SIZE)
        header[0] = 0x03
        header[1] = index
        header[2] = index
        header[3:11] = f"F{index:02d}".encode("ascii").ljust(8, b" ")
        header[11:13] = (0x6000).to_bytes(2, "little")
        header[13:15] = len(payload).to_bytes(2, "little")
        header[15] = index % 3
        blocks.extend(header)
        blocks.append(0x04)
        blocks.extend(payload)
    if len(blocks) > SIDE_SIZE:
        raise AssertionError("synthetic side strategy exceeded fixed capacity")
    blocks.extend(bytes((padding_byte,)) * (SIDE_SIZE - len(blocks)))
    return bytes(blocks)


class PackedBinaryPropertyTests(unittest.TestCase):
    """Exercise semantic round trips across native bitstream boundaries."""

    @settings(max_examples=100, deadline=None)
    @given(st.lists(PACKABLE_RECORD, max_size=8).map(tuple))
    def test_packed_records_round_trip(
        self,
        records: tuple[tuple[PackedSymbol, ...], ...],
    ) -> None:
        """Verify the current contract described by this regression test."""
        packed = pack_records(records)
        decoded, end = split_records(packed, limit=len(records))
        decoded_records = tuple(tuple(record) for record in decoded)
        self.assertEqual(signatures(decoded_records), signatures(records))
        self.assertEqual(end, len(packed))

    @settings(max_examples=60, deadline=None)
    @given(LITERAL_GROUPS)
    def test_compression_expands_to_original_symbols(
        self,
        groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    ) -> None:
        """Verify the current contract described by this regression test."""
        compressed, dictionary = compress_english_groups(groups)
        expanded = tuple(
            tuple(
                expand_dictionary_symbols(record, dictionary)
                for record in group
            )
            for group in compressed
        )
        self.assertEqual(expanded, groups)
        self.assertLessEqual(len(dictionary), 31)
        self.assertTrue(
            all(
                entry
                and all(
                    token.kind in (SymbolKind.COMMON, SymbolKind.EXTENDED)
                    for token in entry
                )
                for entry in dictionary
            )
        )
        self.assertLessEqual(
            packed_size(compressed, dictionary), packed_size(groups, ())
        )

    def test_repeated_literal_compression_regression(self) -> None:
        """Verify the current contract described by this regression test."""
        phrase = tuple(symbol(SymbolKind.COMMON, value) for value in range(12))
        groups = (((*phrase, *phrase), (*phrase, *phrase)),)
        compressed, dictionary = compress_english_groups(groups)
        self.assertTrue(dictionary)
        self.assertEqual(
            tuple(
                tuple(
                    expand_dictionary_symbols(record, dictionary)
                    for record in group
                )
                for group in compressed
            ),
            groups,
        )

    def test_nested_source_dictionary_expands_and_loops_fail(self) -> None:
        """Support nested source dictionaries while rejecting recursive loops."""
        literal = symbol(SymbolKind.COMMON, 47)
        reference_one = symbol(SymbolKind.DICTIONARY, 1)
        reference_two = symbol(SymbolKind.DICTIONARY, 2)
        dictionary = ((literal,), (reference_one, literal))
        self.assertEqual(
            expand_dictionary_symbols((reference_two,), dictionary),
            (literal, literal),
        )
        with self.assertRaisesRegex(ValueError, "dictionary loop"):
            expand_dictionary_symbols(
                (reference_one,),
                ((reference_two,), (reference_one,)),
            )


class FdsPropertyTests(unittest.TestCase):
    """Exercise lossless parsing for legal synthetic FDS layouts."""

    @settings(max_examples=30, deadline=None)
    @given(
        st.lists(
            st.lists(st.binary(max_size=64), max_size=5).map(tuple),
            min_size=1,
            max_size=3,
        ),
        st.booleans(),
        st.integers(min_value=0, max_value=255),
        st.binary(min_size=11, max_size=11),
    )
    def test_valid_synthetic_images_round_trip_byte_identically(
        self,
        side_payloads: list[tuple[bytes, ...]],
        headered: bool,
        padding_byte: int,
        header_tail: bytes,
    ) -> None:
        """Verify the current contract described by this regression test."""
        sides = b"".join(
            make_side(payloads, padding_byte=padding_byte)
            for payloads in side_payloads
        )
        if headered:
            header = b"FDS\x1a" + bytes((len(side_payloads),)) + header_tail
            self.assertEqual(len(header), FDS_HEADER_SIZE)
        else:
            header = b""
        raw = header + sides
        rebuilt = FdsImage.from_bytes(raw).to_bytes()
        self.assertEqual(rebuilt, raw)
        self.assertEqual(FdsImage.from_bytes(rebuilt).to_bytes(), raw)

    def test_single_file_exact_capacity_and_one_byte_overflow(self) -> None:
        """Verify the current contract described by this regression test."""
        maximum_payload = SIDE_SIZE - DISK_INFO_SIZE - 2 - FILE_HEADER_SIZE - 1
        image = FdsImage.from_bytes(
            make_side((b"x" * maximum_payload,), padding_byte=0)
        )
        self.assertEqual(len(image.to_bytes()), SIDE_SIZE)
        image.sides[0].files[0].data += b"x"
        with self.assertRaises(FdsFormatError):
            image.to_bytes()

    def test_file_and_header_side_count_boundaries_fail_cleanly(self) -> None:
        """Accept one-byte maxima and reject counts that cannot be serialized."""
        raw = make_side((b"",) * 0xFF, padding_byte=0)
        self.assertEqual(FdsImage.from_bytes(raw).to_bytes(), raw)

        image = FdsImage.from_bytes(make_side((b"",), padding_byte=0))
        image.sides[0].files *= 0x100
        with self.assertRaisesRegex(FdsFormatError, "file count 256"):
            image.to_bytes()

        header = b"FDS\x1a\x01" + b"\x00" * 11
        headered = FdsImage.from_bytes(
            header + make_side((b"",), padding_byte=0)
        )
        headered.sides *= 0x100
        with self.assertRaisesRegex(FdsFormatError, "side count 256"):
            headered.to_bytes()


if __name__ == "__main__":
    unittest.main()
