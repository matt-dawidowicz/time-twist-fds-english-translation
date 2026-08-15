"""Regression coverage for NOV4 font-source ownership."""

from __future__ import annotations

import unittest

from time_twist.english import COMMON_CHARACTERS, EXTENDED_CHARACTERS
from time_twist.font import EXTENDED_TILE_IDS, NOV4_FONT_BASE_OFFSET, common_tile_id

# Recovered post-title NOV4 source ownership.  The direct 2bpp LoadTileset
# source begins at file $203D and occupies slots $98-$AF when viewed through
# the surrounding eight-byte table geometry.  The actual 1bpp font source
# begins at $20FD / slot $B0 and continues through slot $FE.
DIRECT_2BPP_SOURCE_START = 0x203D
FONT_1BPP_SOURCE_START = 0x20FD
FONT_1BPP_SOURCE_END = 0x2375
DIRECT_2BPP_SLOT_MIN = 0x98
DIRECT_2BPP_SLOT_MAX = 0xAF
FONT_SLOT_MIN = 0xB0
FONT_SLOT_MAX = 0xFE


def active_english_font_tiles() -> frozenset[int]:
    """Return every runtime tile written by the active English font map."""
    common_tiles = {
        common_tile_id(value) for value, _ in enumerate(COMMON_CHARACTERS)
    }
    extended_tiles = {
        EXTENDED_TILE_IDS[value] for value in EXTENDED_CHARACTERS
    }
    return frozenset(common_tiles | extended_tiles)


class Nov4FontSourceSafetyTests(unittest.TestCase):
    """Prevent font glyphs from aliasing post-title graphics source bytes."""

    def test_recovered_source_boundaries_match_font_table_geometry(self) -> None:
        """Lock the direct-graphics/font boundary to recovered NOV4 offsets."""
        self.assertEqual(
            NOV4_FONT_BASE_OFFSET + DIRECT_2BPP_SLOT_MIN * 8,
            DIRECT_2BPP_SOURCE_START,
        )
        self.assertEqual(
            NOV4_FONT_BASE_OFFSET + FONT_SLOT_MIN * 8,
            FONT_1BPP_SOURCE_START,
        )
        self.assertEqual(
            NOV4_FONT_BASE_OFFSET + (FONT_SLOT_MAX + 1) * 8,
            FONT_1BPP_SOURCE_END,
        )
        self.assertEqual(DIRECT_2BPP_SLOT_MAX + 1, FONT_SLOT_MIN)

    def test_active_english_tiles_stay_in_proven_font_source(self) -> None:
        """Fail if any active glyph enters slots $98-$AF or leaves $B0-$FE."""
        tiles = active_english_font_tiles()
        self.assertTrue(tiles)
        for tile_id in tiles:
            with self.subTest(tile_id=f"${tile_id:02X}"):
                self.assertGreaterEqual(tile_id, FONT_SLOT_MIN)
                self.assertLessEqual(tile_id, FONT_SLOT_MAX)
                offset = NOV4_FONT_BASE_OFFSET + tile_id * 8
                self.assertGreaterEqual(offset, FONT_1BPP_SOURCE_START)
                self.assertLessEqual(offset + 8, FONT_1BPP_SOURCE_END)

    def test_direct_graphics_slots_are_never_active_font_tiles(self) -> None:
        """Catch future reuse of slots $98-$AF, including the old $AC alias."""
        direct_graphics_slots = set(
            range(DIRECT_2BPP_SLOT_MIN, DIRECT_2BPP_SLOT_MAX + 1)
        )
        self.assertEqual(active_english_font_tiles() & direct_graphics_slots, set())

        # Native lookup metadata can keep these aliases for decoding/audit, but
        # the English character map must not activate them as writable glyphs.
        self.assertEqual(EXTENDED_TILE_IDS[63], 0xAC)
        self.assertNotIn(63, EXTENDED_CHARACTERS)
        self.assertEqual(EXTENDED_TILE_IDS[45], 0xFA)
        self.assertNotIn(45, EXTENDED_CHARACTERS)


if __name__ == "__main__":
    unittest.main()
