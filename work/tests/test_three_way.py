"""Fixture-free tests for the private three-way comparison decoder."""

from __future__ import annotations

import unittest

from time_twist.fds import FdsFile
from time_twist.textcodec import PackedSymbol, SymbolKind, pack_records
from time_twist.three_way import (
    COMPETITOR_COMMON_CHARACTERS,
    TextDialect,
    apply_ips,
    decode_scenario_file,
    parse_ips,
)


def _symbol(kind: SymbolKind, value: int) -> PackedSymbol:
    """Build one source-position-neutral symbol for synthetic packed text."""

    return PackedSymbol(kind, value, 0, 0)


def _entry(data: bytes) -> FdsFile:
    """Wrap synthetic scenario bytes in the production FDS-file abstraction."""

    header = bytearray(16)
    header[0] = 3
    header[3:11] = b"SYNTH\0\0\0"
    header[11:13] = (0xA200).to_bytes(2, "little")
    return FdsFile(0, header, data, 0, 0)


class IpsTests(unittest.TestCase):
    """Exercise strict IPS parsing and explicit-write provenance masks."""

    def test_literal_rle_and_truncate_are_applied(self) -> None:
        """Preserve literal and RLE offsets plus the optional truncate size."""

        payload = (
            b"PATCH"
            + b"\x00\x00\x01\x00\x02XY"
            + b"\x00\x00\x04\x00\x00\x00\x03Z"
            + b"EOF\x00\x00\x08"
        )
        patch = parse_ips(payload)
        output, mask = apply_ips(b"abcdefghij", patch)
        self.assertEqual(output, b"aXYdZZZh")
        self.assertEqual(mask, b"\0\1\1\0\1\1\1\0")

    def test_malformed_ips_is_rejected(self) -> None:
        """Reject bad signatures and truncated records instead of guessing."""

        with self.assertRaisesRegex(ValueError, "PATCH"):
            parse_ips(b"NOT-A-PATCH")
        with self.assertRaisesRegex(ValueError, "truncated"):
            parse_ips(b"PATCH\x00\x00\x01\x00\x04X")


class CompetitorScenarioTests(unittest.TestCase):
    """Prove the recovered competitor codec and logical-coordinate handling."""

    def test_recovered_common_map_decodes_mixed_case(self) -> None:
        """Keep the font-derived common slots stable, including k and v."""

        self.assertEqual(COMPETITOR_COMMON_CHARACTERS[25:32], "MkTv'A?")
        self.assertEqual(COMPETITOR_COMMON_CHARACTERS[32:], "ISGHWDNBC-OJPREY")

    def test_non_monotonic_groups_keep_logical_order(self) -> None:
        """Decode competitor groups by pointers and counts, not address order."""

        data = bytearray(0x100)
        data[0x16:0x18] = (0xA300).to_bytes(2, "little")
        data[0x24:0x26] = (0xA240).to_bytes(2, "little")
        data[0x26:0x28] = (0xA260).to_bytes(2, "little")
        data[0x40:0x42] = (0xA250).to_bytes(2, "little")
        data[0x50:0x51] = pack_records(((_symbol(SymbolKind.COMMON, 28),),))
        data[0x60:0x61] = pack_records(((_symbol(SymbolKind.COMMON, 30),),))
        decoded = decode_scenario_file(
            _entry(bytes(data)),
            (1, 1),
            TextDialect.COMPETITOR_ENGLISH,
        )
        self.assertEqual(
            [(record.group, record.record, record.text) for record in decoded.records],
            [(0, 0, "A"), (1, 0, "v")],
        )

    def test_competitor_extended_escape_reaches_entry_32(self) -> None:
        """Interpret extended value four as dictionary reference 32 only here."""

        data = bytearray(0x300)
        data[0x16:0x18] = (0xA280).to_bytes(2, "little")
        data[0x24:0x26] = (0xA240).to_bytes(2, "little")
        data[0x26:0x28] = (0xA250).to_bytes(2, "little")
        group = pack_records(((_symbol(SymbolKind.EXTENDED, 4),),))
        dictionary_records = [tuple() for _ in range(31)]
        dictionary_records.append((_symbol(SymbolKind.COMMON, 30),))
        dictionary = pack_records(tuple(dictionary_records))
        data[0x50 : 0x50 + len(group)] = group
        data[0x80 : 0x80 + len(dictionary)] = dictionary
        decoded = decode_scenario_file(
            _entry(bytes(data)),
            (1,),
            TextDialect.COMPETITOR_ENGLISH,
        )
        self.assertEqual(decoded.dictionary_entries, 32)
        self.assertEqual(decoded.records[0].text, "A")


if __name__ == "__main__":
    unittest.main()
