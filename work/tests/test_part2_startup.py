"""Tests for the recovered Part 1 to Part 2 title handoff."""

from __future__ import annotations

import unittest

from time_twist.part2_startup import (
    CURRENT_SCENE_INDEX_ZP,
    SAVE_PART2_MARKER_VALUE,
    SAVE_SCENE_INDEX_ADDRESS,
    TITLE_MAIN_MENU_LABELS,
    TITLE_MAIN_MENU_RECORD_IDS,
    TITLE_PART2_SCENE_FILE_IDS,
    TITLE_PART2_SCENE_INDEX,
    TITLE_PART2_TRANSITION_OPERAND,
    part2_is_available,
    save_address_for_zero_page,
)
from time_twist.scene_transitions import decode_fds_scene_transition_operand


class Part2StartupTests(unittest.TestCase):
    """Protect the recovered Zenpen-to-Kouhen startup contract."""

    def test_scene_index_maps_to_save_03d9(self) -> None:
        """Persist current scene index $CE at SAVE address $03D9."""
        self.assertEqual(CURRENT_SCENE_INDEX_ZP, 0xCE)
        self.assertEqual(save_address_for_zero_page(0xCE), 0x03D9)
        self.assertEqual(SAVE_SCENE_INDEX_ADDRESS, 0x03D9)

    def test_part2_requires_valid_save_and_nonzero_marker(self) -> None:
        """Match the title filter's NOT-E3 AND E4 eligibility rule."""
        self.assertFalse(part2_is_available(save_valid=False, persisted_marker=0))
        self.assertFalse(
            part2_is_available(
                save_valid=False,
                persisted_marker=SAVE_PART2_MARKER_VALUE,
            )
        )
        self.assertFalse(part2_is_available(save_valid=True, persisted_marker=0))
        self.assertTrue(
            part2_is_available(
                save_valid=True,
                persisted_marker=SAVE_PART2_MARKER_VALUE,
            )
        )

    def test_title_menu_three_is_start_load_part2(self) -> None:
        """Lock the three title records dispatched by menu index 3."""
        self.assertEqual(TITLE_MAIN_MENU_RECORD_IDS, (4, 5, 6))
        self.assertEqual(TITLE_MAIN_MENU_LABELS, ("Start", "Load", "Part 2"))

    def test_part2_target_is_explicit_kouhen_side_b_scene_7(self) -> None:
        """Decode NOV4's explicit E0 C7 Part 2 branch."""
        target = decode_fds_scene_transition_operand(
            TITLE_PART2_TRANSITION_OPERAND
        )
        self.assertEqual(TITLE_PART2_TRANSITION_OPERAND, 0xC7)
        self.assertEqual(target.disk_name, "Kouhen")
        self.assertEqual(target.side_name, "B")
        self.assertEqual(target.scene_index, TITLE_PART2_SCENE_INDEX)
        self.assertEqual(target.scene_index, 7)
        self.assertEqual(TITLE_PART2_SCENE_FILE_IDS, (0x47, 0x57, 0xFF, 0xFF))

    def test_save_mapper_rejects_nonpersisted_zero_page(self) -> None:
        """Keep SAVE layout claims inside the verified $C5-$D4 copy."""
        with self.assertRaises(ValueError):
            save_address_for_zero_page(0xC4)
        with self.assertRaises(ValueError):
            save_address_for_zero_page(0xD5)

    def test_part2_marker_must_be_byte(self) -> None:
        """Reject impossible title-marker values."""
        with self.assertRaises(ValueError):
            part2_is_available(save_valid=True, persisted_marker=-1)
        with self.assertRaises(ValueError):
            part2_is_available(save_valid=True, persisted_marker=0x100)


if __name__ == "__main__":
    unittest.main()
