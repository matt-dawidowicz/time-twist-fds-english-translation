"""Tests for recovered gameplay scene-data formats."""

from __future__ import annotations

import unittest

from time_twist.gameplay_graphics import (
    GameplayGraphicsError,
    decode_background_map_stream,
    parse_actor_spawn_records,
    parse_background_map_records,
    parse_hotspot_records,
    parse_metasprite_definitions,
    parse_static_placement_records,
)

LOAD = 0xA200


class GameplayGraphicsFormatTests(unittest.TestCase):
    """Protect the recovered binary contracts without private ROM fixtures."""

    def test_metasprite_definition_handles_visible_and_transparent_cells(
        self,
    ) -> None:
        """Verify metasprites preserve visible and transparent packed cells."""
        data = bytes((5, 0x21, 0x22, 0x43, 0xFF))
        definitions = parse_metasprite_definitions(
            data,
            LOAD,
            LOA + len(data),
        )
        self.assertEqual(len(definitions), 1)
        definition = definitions[0]
        self.assertEqual((definition.width, definition.height), (2, 1))
        self.assertEqual(definition.cells[0].tile, 0x22)
        self.assertEqual(definition.cells[0].attributes, 0x43)
        self.assertIsNone(definition.cells[1].tile)
        self.assertIsNone(definition.cells[1].attributes)

    def test_metasprite_definition_rejects_record_length_drift(self) -> None:
        """Reject metasprite records whose declared span is inconsistent."""
        with self.assertRaises(GameplayGraphicsError):
            parse_metasprite_definitions(
                bytes((6, 0x21, 0x22, 0x43, 0xFF, 0x00)),
                LOAD,
                LOAD + 6,
            )

    def test_static_placement_records_are_count_prefixed_triples(self) -> None:
        """Verify static placements are count-prefixed three-byte entries."""
        data = bytes((2, 3, 4, 5, 6, 7, 8, 1, 9, 10, 11))
        records = parse_static_placement_records(data, LOAD, LOAD + len(data))
        self.assertEqual(
            [len(record.placements) for record in records], [2, 1]
        )
        self.assertEqual(
            (
                records[0].placements[1].metasprite_index,
                records[0].placements[1].x_cell,
                records[0].placements[1].y_cell,
            ),
            (6, 7, 8),
        )

    def test_actor_spawn_records_preserve_raw_coordinate_sentinels(
        self,
    ) -> None:
        """Verify actor spawns retain native coordinate sentinel bytes."""
        data = bytes((2, 4, 0x20, 0x01, 0x30, 5, 0xFF, 0xFF, 0x40))
        records = parse_actor_spawn_records(data, LOAD, LOAD + len(data))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].actors[0].x_raw, 0x0120)
        self.assertEqual(records[0].actors[1].x_raw, 0xFFFF)

    def test_hotspot_records_expose_flags_and_special_bottom_markers(
        self,
    ) -> None:
        """Verify hotspot flags and native special terminal marker bytes."""
        data = bytes((2, 0x85, 2, 9, 0xFD, 3, 4, 8, 0xFE))
        records = parse_hotspot_records(data, LOAD, LOAD + len(data))
        first, second = records[0].rectangles
        self.assertTrue(first.context_flag)
        self.assertEqual(first.left, 5)
        self.assertEqual(first.bottom_or_special, 0xFD)
        self.assertEqual(second.bottom_or_special, 0xFE)

    def test_background_map_stream_decodes_literals_runs_and_rectangle(
        self,
    ) -> None:
        """Verify gameplay map RLE expands to the declared rectangle."""
        data = bytes((0, 1, 3, 0x11, 0xC3, 0x22, 0xFF))
        stream = decode_background_map_stream(data, LOAD, LOAD + len(data))
        self.assertEqual((stream.width, stream.height), (2, 2))
        self.assertEqual(stream.tiles, (0x11, 0x22, 0x22, 0x22))
        self.assertEqual(stream.encoded_end_address, LOAD + len(data))

    def test_background_descriptor_decodes_inline_and_pointer_variants(
        self,
    ) -> None:
        """Verify map descriptors combine inline and pointer-selected variants."""
        first_stream = bytes((0, 1, 0, 0x11, 0xC3, 0x22, 0xFF))
        second_stream = bytes((2, 3, 4, 3, 4, 5, 6, 0xFF))
        byte_length = 4 + len(first_stream) + len(second_stream)
        second_address = LOAD + 4 + len(first_stream)
        header = bytes(
            (
                byte_length,
                0x80,
                second_address & 0xFF,
                second_address >> 8,
            )
        )
        data = header + first_stream + second_stream
        records = parse_background_map_records(data, LOAD, LOAD + len(data))
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0].streams), 2)
        self.assertEqual(records[0].streams[0].tiles, (0x11, 0x22, 0x22, 0x22))
        self.assertEqual(records[0].streams[1].tiles, (3, 4, 5, 6))

    def test_background_stream_rejects_nonrectangular_tile_count(self) -> None:
        """Reject map streams whose tiles do not fill whole rows."""
        data = bytes((0, 1, 0, 1, 2, 3, 0xFF))
        with self.assertRaises(GameplayGraphicsError):
            decode_background_map_stream(data, LOAD, LOAD + len(data))

    def test_background_stream_accepts_canonical_empty_noop(self) -> None:
        """Accept the native empty background-map no-op encoding."""
        stream = decode_background_map_stream(
            bytes((0, 0, 0, 0xFF)),
            LOAD,
            LOAD + 4,
        )
        self.assertEqual(
            (stream.width, stream.height, stream.tiles), (1, 0, ())
        )


if __name__ == "__main__":
    unittest.main()
