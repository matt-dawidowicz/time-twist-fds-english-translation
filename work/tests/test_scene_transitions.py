"""Tests for packed gameplay FDS/scene transition operands."""

from __future__ import annotations

import unittest

from time_twist.scene_transitions import decode_fds_scene_transition_operand


class SceneTransitionTests(unittest.TestCase):
    """Protect the recovered E0 packed-target contract."""

    def test_zenpen_side_b_scene_2(self) -> None:
        """Decode one Part 1 Side B transition."""
        target = decode_fds_scene_transition_operand(0x42)
        self.assertEqual(target.disk_name, "Zenpen")
        self.assertEqual(target.side_name, "B")
        self.assertEqual(target.scene_index, 2)

    def test_zenpen_side_a_scene_6(self) -> None:
        """Decode one Part 1 Side A transition."""
        target = decode_fds_scene_transition_operand(0x06)
        self.assertEqual(target.disk_name, "Zenpen")
        self.assertEqual(target.side_name, "A")
        self.assertEqual(target.scene_index, 6)

    def test_kouhen_side_b_scene_9(self) -> None:
        """Decode one Part 2 Side B transition."""
        target = decode_fds_scene_transition_operand(0xC9)
        self.assertEqual(target.disk_name, "Kouhen")
        self.assertEqual(target.side_name, "B")
        self.assertEqual(target.scene_index, 9)

    def test_kouhen_side_a_scene_14(self) -> None:
        """Decode one Part 2 Side A transition."""
        target = decode_fds_scene_transition_operand(0x8E)
        self.assertEqual(target.disk_name, "Kouhen")
        self.assertEqual(target.side_name, "A")
        self.assertEqual(target.scene_index, 14)

    def test_scene_index_uses_low_six_bits(self) -> None:
        """Keep disk/side flag bits out of the scene-table index."""
        self.assertEqual(
            decode_fds_scene_transition_operand(0xFF).scene_index,
            0x3F,
        )

    def test_rejects_non_byte_operand(self) -> None:
        """Reject transition values outside the native one-byte field."""
        with self.assertRaises(ValueError):
            decode_fds_scene_transition_operand(-1)
        with self.assertRaises(ValueError):
            decode_fds_scene_transition_operand(0x100)


if __name__ == "__main__":
    unittest.main()
