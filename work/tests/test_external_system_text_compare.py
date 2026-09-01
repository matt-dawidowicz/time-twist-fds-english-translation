"""Tests for the isolated external NOV2/NOV4 system-text layouts."""

from __future__ import annotations

import unittest

from tools.external_system_text_compare import (
    EXTERNAL_NOV4_APPENDED_TABLE,
    EXTERNAL_SYSTEM_RECORD_OFFSETS,
    EXTERNAL_SYSTEM_UNALIGNED_SOURCE_IDS,
    decode_external_named_records,
)
from tools.external_translation_compare import render_record


class ExternalSystemTextCompareTests(unittest.TestCase):
    """Protect recovered logical-to-physical system-text mappings."""

    def test_recovered_layouts_are_complete_and_unique(self) -> None:
        """Lock the independently recovered NOV2/NOV4 physical record starts."""
        nov2 = EXTERNAL_SYSTEM_RECORD_OFFSETS["NOV2"]
        nov4 = EXTERNAL_SYSTEM_RECORD_OFFSETS["NOV4"]

        self.assertEqual(len(nov2), 15)
        self.assertEqual(len(nov4), 2)
        self.assertEqual(len({record_id for record_id, _ in nov2}), len(nov2))
        self.assertEqual(len({offset for _, offset in nov2}), len(nov2))
        self.assertEqual(
            dict(nov4), {"NOV4/start": 0x2384, "NOV4/load": 0x2389}
        )
        self.assertEqual(EXTERNAL_NOV4_APPENDED_TABLE, (0x2375, 26))

    def test_unaligned_source_slots_are_explicit(self) -> None:
        """Do not invent external English for unchanged Japanese NOV2 slots."""
        self.assertEqual(
            EXTERNAL_SYSTEM_UNALIGNED_SOURCE_IDS["NOV2"],
            ("NOV2/disk/r5", "NOV2/disk/r6"),
        )
        self.assertEqual(EXTERNAL_SYSTEM_UNALIGNED_SOURCE_IDS["NOV4"], ())

    def test_named_decoder_uses_declared_logical_order(self) -> None:
        """Decode physically separated records without assuming source offsets."""
        data = bytes([0x03, 0xE8, 0x00, 0x00, 0x07, 0xE8])
        decoded = decode_external_named_records(
            data, (("first", 0), ("second", 4))
        )
        self.assertEqual(list(decoded), ["first", "second"])
        self.assertEqual(
            [render_record(record, []) for record in decoded.values()],
            [" ", "e"],
        )

    def test_named_decoder_rejects_ambiguous_layouts(self) -> None:
        """Reject duplicate IDs, duplicate offsets, and empty declarations."""
        with self.assertRaisesRegex(ValueError, "at least one"):
            decode_external_named_records(b"x", ())
        with self.assertRaisesRegex(ValueError, "duplicate.*ID"):
            decode_external_named_records(
                bytes([0x03, 0xE8, 0x07, 0xE8]),
                (("same", 0), ("same", 2)),
            )
        with self.assertRaisesRegex(ValueError, "duplicate.*offset"):
            decode_external_named_records(
                bytes([0x03, 0xE8]), (("one", 0), ("two", 0))
            )


if __name__ == "__main__":
    unittest.main()
