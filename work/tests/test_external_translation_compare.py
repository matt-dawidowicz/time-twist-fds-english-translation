"""Tests for the isolated third-party translation comparison helpers."""

from __future__ import annotations

import unittest

from tools.external_translation_compare import (
    EXTERNAL_FIXED_SEGMENTS,
    decode_external_fixed_segments,
    overlay_sparse_payload,
    patch_spans,
    render_record,
)


class ExternalTranslationCompareTests(unittest.TestCase):
    """Protect external-patch reconstruction behavior used by audits."""

    def test_external_fixed_segments_reassemble_logical_order(self) -> None:
        """Concatenate physically separate external records in declared order."""
        data = bytes([0x03, 0xE8, 0x00, 0x00, 0x07, 0xE8])
        records = decode_external_fixed_segments(data, ((0, 1), (4, 1)))
        self.assertEqual(
            [render_record(record, []) for record in records], [" ", "e"]
        )

    def test_external_fixed_segment_counts_match_recovered_tables(
        self,
    ) -> None:
        """Lock the independently recovered logical record counts per bank."""
        expected = {
            "TT1B": 53,
            "TT2": 70,
            "T22": 33,
            "TT3A": 95,
            "TT3B": 21,
            "TT4": 97,
            "TT5": 113,
            "T25": 42,
            "TT6A": 41,
            "TT6B": 62,
            "TT6C": 94,
        }
        actual = {
            bank: sum(count for _, count in segments)
            for bank, segments in EXTERNAL_FIXED_SEGMENTS.items()
        }
        self.assertEqual(actual, expected)
        self.assertEqual(sum(actual.values()), 721)

    def test_external_fixed_segments_reject_empty_layout(self) -> None:
        """Require explicit structural evidence before decoding fixed text."""
        with self.assertRaisesRegex(
            ValueError, "at least one fixed-text segment"
        ):
            decode_external_fixed_segments(b"x", ())

    def test_external_fixed_segments_reject_nonpositive_counts(self) -> None:
        """Reject segment declarations that cannot contain a real record."""
        with self.assertRaisesRegex(ValueError, "invalid count"):
            decode_external_fixed_segments(b"x", ((0, 0),))

    def test_patch_spans_merge_five_byte_gap(self) -> None:
        """Merge five-byte gaps but split spans separated by six bytes."""
        payload = bytearray(20)
        payload[2] = 1
        payload[8] = 2  # five zeros between changed bytes
        payload[15] = 3  # six zeros: new span
        self.assertEqual(patch_spans(bytes(payload)), [(2, 9), (15, 16)])

    def test_overlay_preserves_zero_writes_inside_hunk(self) -> None:
        """Copy intentional zero bytes that occur inside a recovered hunk."""
        base = b"abcdefghij"
        payload = bytes([0, 0, ord("X"), 0, 0, 0, 0, 0, ord("Y"), 0])
        rebuilt = overlay_sparse_payload(base, payload)
        self.assertEqual(rebuilt, b"abX\0\0\0\0\0Yj")
