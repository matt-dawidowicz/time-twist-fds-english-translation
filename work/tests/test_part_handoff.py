"""Tests for the verified Zenpen-to-Kouhen title/save handoff."""

from __future__ import annotations

import unittest

from time_twist.part_handoff import (
    KOUHEN_FIRST_SCENE_TARGET,
    SAVE_DISK_WRITE_MARKER,
    title_gate_from_save,
)
from time_twist.scene_transitions import decode_fds_scene_transition_operand


class PartHandoffTests(unittest.TestCase):
    """Protect the recovered continuation-marker and title-gate semantics."""

    def test_invalid_save_hides_load_and_part2(self) -> None:
        """An invalid SAVE must expose neither continuation choice."""
        gate = title_gate_from_save(
            save_valid=False,
            disk_write_marker=SAVE_DISK_WRITE_MARKER,
        )
        self.assertFalse(gate.load_visible)
        self.assertFalse(gate.part2_visible)

    def test_valid_unmarked_save_exposes_load_only(self) -> None:
        """A valid SAVE without the disk-write marker does not expose Part 2."""
        gate = title_gate_from_save(
            save_valid=True,
            disk_write_marker=0,
        )
        self.assertTrue(gate.load_visible)
        self.assertFalse(gate.part2_visible)

    def test_valid_marked_save_exposes_part2(self) -> None:
        """A valid disk-written SAVE exposes Part 2."""
        gate = title_gate_from_save(
            save_valid=True,
            disk_write_marker=SAVE_DISK_WRITE_MARKER,
        )
        self.assertTrue(gate.load_visible)
        self.assertTrue(gate.part2_visible)
        self.assertTrue(gate.part2_flag)

    def test_nonzero_marker_matches_native_title_compare(self) -> None:
        """NOV4 derives E4 from D2 != 0 rather than one magic value compare."""
        self.assertTrue(
            title_gate_from_save(
                save_valid=True,
                disk_write_marker=1,
            ).part2_visible
        )

    def test_part2_target_is_kouhen_side_b_scene_7(self) -> None:
        """Lock the exact E0 C7 continuation target."""
        target = decode_fds_scene_transition_operand(KOUHEN_FIRST_SCENE_TARGET)
        self.assertEqual(target.disk_name, "Kouhen")
        self.assertEqual(target.side_name, "B")
        self.assertEqual(target.scene_index, 7)


if __name__ == "__main__":
    unittest.main()
