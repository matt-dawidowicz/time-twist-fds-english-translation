"""Tests for the isolated third-party translation comparison helpers."""

from __future__ import annotations

import unittest

from tools.external_translation_compare import (
    overlay_sparse_payload,
    patch_spans,
)


class ExternalTranslationCompareTests(unittest.TestCase):
    """Protect external-patch reconstruction behavior used by audits."""

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
