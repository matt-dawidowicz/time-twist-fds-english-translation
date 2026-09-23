"""Regression tests for bounded incremental entropy recompilation."""

from __future__ import annotations

import unittest

from time_twist.english import encode_english
from time_twist.entropy_codec import pack_entropy_stream
from time_twist.incremental_build import (
    IncrementalBuildError,
    rebuild_entropy_bank,
)
from time_twist.scenario import (
    DICTIONARY_POINTER_OFFSET,
    GROUP_TABLE_POINTER_OFFSET,
    GROUP_ZERO_POINTER_OFFSET,
    LOAD_ADDRESS,
)
from time_twist.textcodec import PackedSymbol, SymbolKind


def _write_word(data: bytearray, offset: int, value: int) -> None:
    """Write one little-endian word into a synthetic test bank."""
    data[offset : offset + 2] = value.to_bytes(2, "little")


def _bank(
    group_zero,
    group_one,
    *,
    group_zero_offset: int = 0x80,
    group_one_offset: int | None = None,
    dictionary=(),
) -> bytes:
    """Construct a minimal two-group entropy bank for bounded-rebuild tests."""
    prefix = bytearray(max(group_zero_offset, 0x80))
    table_offset = 0x50
    dictionary_offset = 0x60
    group_zero_blob = pack_entropy_stream(group_zero)
    if group_one_offset is None:
        group_one_offset = group_zero_offset + len(group_zero_blob)
    group_one_blob = pack_entropy_stream(group_one)

    _write_word(
        prefix,
        DICTIONARY_POINTER_OFFSET,
        LOAD_ADDRESS + dictionary_offset,
    )
    _write_word(
        prefix,
        GROUP_TABLE_POINTER_OFFSET,
        LOAD_ADDRESS + table_offset,
    )
    _write_word(
        prefix,
        GROUP_ZERO_POINTER_OFFSET,
        LOAD_ADDRESS + group_zero_offset,
    )
    _write_word(
        prefix,
        table_offset,
        LOAD_ADDRESS + group_one_offset,
    )

    if dictionary:
        dictionary_blob = pack_entropy_stream(dictionary)
        prefix[
            dictionary_offset : dictionary_offset + len(dictionary_blob)
        ] = dictionary_blob

    output = bytearray(prefix)
    if len(output) < group_zero_offset:
        output.extend(bytes(group_zero_offset - len(output)))
    if group_zero_offset < len(output):
        end = group_zero_offset + len(group_zero_blob)
        if end > len(output):
            raise AssertionError("fixed synthetic group exceeds prefix")
        output[group_zero_offset:end] = group_zero_blob
    else:
        output.extend(group_zero_blob)

    if len(output) < group_one_offset:
        output.extend(bytes(group_one_offset - len(output)))
    if len(output) != group_one_offset:
        raise AssertionError("synthetic group offsets overlap")
    output.extend(group_one_blob)
    return bytes(output)


class IncrementalBuildTests(unittest.TestCase):
    """Keep the development builder bounded and byte-stable."""

    def test_no_change_returns_original_bytes(self) -> None:
        """Leave a semantically current entropy bank byte-identical."""
        data = _bank(
            (encode_english("A"),),
            (encode_english("B"),),
        )
        result = rebuild_entropy_bank(
            data,
            "TEST",
            {
                "TEST/g0/r0": "A",
                "TEST/g1/r0": "B",
            },
        )
        self.assertEqual(result.data, data)
        self.assertEqual(result.changed_records, ())

    def test_terminal_group_resize_updates_following_pointer(self) -> None:
        """Resize a terminal stream and update the next group pointer."""
        data = _bank(
            (encode_english("A"),),
            (encode_english("B"),),
        )
        old_pointer = int.from_bytes(data[0x50:0x52], "little")
        result = rebuild_entropy_bank(
            data,
            "TEST",
            {
                "TEST/g0/r0": "AAAAAA",
                "TEST/g1/r0": "B",
            },
        )
        new_pointer = int.from_bytes(result.data[0x50:0x52], "little")
        self.assertNotEqual(new_pointer, old_pointer)
        self.assertEqual(result.changed_records, ("TEST/g0/r0",))

        verified = rebuild_entropy_bank(
            result.data,
            "TEST",
            {
                "TEST/g0/r0": "AAAAAA",
                "TEST/g1/r0": "B",
            },
        )
        self.assertEqual(verified.data, result.data)
        self.assertEqual(verified.changed_records, ())

    def test_nonterminal_group_cannot_grow(self) -> None:
        """Reject growth that would overwrite unknown fixed-position bytes."""
        first = (encode_english("A"),)
        second = (encode_english("B"),)
        first_blob = pack_entropy_stream(first)
        data = _bank(
            first,
            second,
            group_zero_offset=0x40,
            group_one_offset=0x80,
        )
        self.assertLess(0x40 + len(first_blob), 0x80)

        with self.assertRaisesRegex(
            IncrementalBuildError,
            "outside the resizable terminal suffix",
        ):
            rebuild_entropy_bank(
                data,
                "TEST",
                {
                    "TEST/g0/r0": "This text is deliberately much longer.",
                    "TEST/g1/r0": "B",
                },
            )

    def test_forward_dictionary_reference_is_resolved(self) -> None:
        """Resolve forward references used by recovered v38 dictionaries."""
        d2 = encode_english("AB")
        d1 = (
            PackedSymbol(SymbolKind.DICTIONARY, 2, 0, 0),
        )
        group_zero = (
            (
                PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0),
            ),
        )
        data = _bank(
            group_zero,
            (encode_english("C"),),
            dictionary=(d1, d2),
        )
        result = rebuild_entropy_bank(
            data,
            "TEST",
            {
                "TEST/g0/r0": "AB",
                "TEST/g1/r0": "C",
            },
        )
        self.assertEqual(result.data, data)
        self.assertEqual(result.changed_records, ())


if __name__ == "__main__":
    unittest.main()
