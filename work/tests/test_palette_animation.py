"""Tests for recovered gameplay palette-animation records and controls."""

from __future__ import annotations

import unittest

from time_twist.palette_animation import (
    PALETTE_CONTROL_LOOP_FOREVER,
    PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY,
    PaletteAnimationError,
    effective_palette_duration,
    gate_palette_control,
    palette_control_after_cycle,
    parse_palette_animation_records,
)

LOAD = 0xA200


class PaletteAnimationTests(unittest.TestCase):
    """Protect the recovered palette-animation binary and control contracts."""

    def test_parser_decodes_multiple_sequences_and_frames(self) -> None:
        """Decode record/sequence/frame structure through an exact table end."""
        data = bytes(
            (
                2,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                1,
                0x7F,
                0x82,
                10,
                11,
            )
        )
        records = parse_palette_animation_records(
            data, LOAD, LOAD + len(data)
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0].sequences), 2)
        first, second = records[0].sequences
        self.assertEqual((first.frame_count, first.control), (2, 3))
        self.assertEqual(first.frames[1].sprite_palette_record, 9)
        self.assertEqual(second.control, PALETTE_CONTROL_LOOP_FOREVER)
        self.assertEqual(second.frames[0].duration, 2)
        self.assertTrue(second.frames[0].ignored_duration_high_bit)

    def test_parser_rejects_zero_sequence_record(self) -> None:
        """Reject a record shape the native selector cannot traverse safely."""
        with self.assertRaises(PaletteAnimationError):
            parse_palette_animation_records(bytes((0,)), LOAD, LOAD + 1)

    def test_high_bit_control_waits_for_fresh_a_then_clears(self) -> None:
        """Model NOV2's bit-7 pre-frame A-button gate."""
        blocked = gate_palette_control(0x85, fresh_a=False)
        self.assertFalse(blocked.active)
        self.assertEqual(blocked.control, 0x85)

        released = gate_palette_control(0x85, fresh_a=True)
        self.assertTrue(released.active)
        self.assertEqual(released.control, 0x05)

    def test_zero_control_is_inactive_before_high_bit_logic(self) -> None:
        """Keep the native early zero-control exit explicit."""
        result = gate_palette_control(0x00, fresh_a=True)
        self.assertFalse(result.active)
        self.assertEqual(result.control, 0x00)

    def test_raw_80_is_active_on_release_without_zero_recheck(self) -> None:
        """Preserve the odd source-unused $80 edge case exactly."""
        result = gate_palette_control(0x80, fresh_a=True)
        self.assertTrue(result.active)
        self.assertEqual(result.control, 0x00)

    def test_7f_loops_forever_at_cycle_boundary(self) -> None:
        """Keep the permanent-cycle sentinel independent of A input."""
        self.assertEqual(
            palette_control_after_cycle(
                PALETTE_CONTROL_LOOP_FOREVER, fresh_a=False
            ),
            PALETTE_CONTROL_LOOP_FOREVER,
        )
        self.assertEqual(
            palette_control_after_cycle(
                PALETTE_CONTROL_LOOP_FOREVER, fresh_a=True
            ),
            PALETTE_CONTROL_LOOP_FOREVER,
        )

    def test_7e_stops_only_on_fresh_a_at_cycle_boundary(self) -> None:
        """Model the cycle-until-A-boundary sentinel."""
        self.assertEqual(
            palette_control_after_cycle(
                PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY,
                fresh_a=False,
            ),
            PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY,
        )
        self.assertEqual(
            palette_control_after_cycle(
                PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY,
                fresh_a=True,
            ),
            0,
        )

    def test_ordinary_control_is_finite_cycle_counter(self) -> None:
        """Ordinary controls decrement once after each completed cycle."""
        self.assertEqual(palette_control_after_cycle(3, fresh_a=False), 2)
        self.assertEqual(palette_control_after_cycle(1, fresh_a=True), 0)

    def test_duration_high_bit_is_ignored(self) -> None:
        """NOV2 always masks frame duration with $7F."""
        self.assertEqual(effective_palette_duration(0x05), 5)
        self.assertEqual(effective_palette_duration(0x85), 5)
        self.assertEqual(effective_palette_duration(0xFF), 0x7F)


if __name__ == "__main__":
    unittest.main()
