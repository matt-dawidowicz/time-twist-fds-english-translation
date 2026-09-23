"""Tests for the recovered Part 1 to Part 2 title handoff."""

from __future__ import annotations

import unittest

from time_twist.part2_startup import (
    CURRENT_SCENE_INDEX_ZP,
    SAVE_FILE_ADDRESS,
    SAVE_FILE_ID,
    SAVE_FILE_NAME,
    SAVE_FILE_NUMBER,
    SAVE_FILE_SIZE,
    SAVE_SCENE_INDEX_ADDRESS,
    SAVE_TITLE_METADATA_ADDRESS,
    TITLE_PART2_FILTER,
    TITLE_PART2_SCENE_FILE_IDS,
    TITLE_PART2_SCENE_INDEX,
    TITLE_PART2_TRANSITION_OPERAND,
    TITLE_PART_MENU_LABELS,
    TITLE_PART_MENU_RECORD_IDS,
    TITLE_START_MENU_LABELS,
    TITLE_START_MENU_RECORD_IDS,
    part2_is_available,
    part2_predicate_allows,
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

    def test_part2_predicate_is_invalid_save_flag_gate(self) -> None:
        """Keep the native Part 2 filter tied to E3, not title metadata."""
        self.assertTrue(part2_predicate_allows(invalid_save_flag_set=False))
        self.assertFalse(part2_predicate_allows(invalid_save_flag_set=True))
        self.assertEqual(
            TITLE_PART2_FILTER,
            bytes.fromhex("91 E3 92 01 E3 E4 00"),
        )

    def test_cold_start_availability_follows_save_validation(self) -> None:
        """Model startup's invalid-SAVE -> E3 suppression contract."""
        self.assertFalse(part2_is_available(save_valid=False))
        self.assertTrue(part2_is_available(save_valid=True))

    def test_start_and_part_menus_are_distinct(self) -> None:
        """Do not conflate title descriptor 2 with the later disk-part selector."""
        self.assertEqual(TITLE_START_MENU_RECORD_IDS, (4, 5, 6))
        self.assertEqual(TITLE_START_MENU_LABELS, ("Start", "Load", "Part 2"))
        self.assertEqual(TITLE_PART_MENU_RECORD_IDS, (11, 12))
        self.assertEqual(TITLE_PART_MENU_LABELS, ("Part 1", "Part 2"))

    def test_03dd_is_title_metadata_not_part2_unlock_bit(self) -> None:
        """Keep the persisted title byte separate from the E3 visibility gate."""
        self.assertEqual(SAVE_TITLE_METADATA_ADDRESS, 0x03DD)

    def test_save_write_header_contract(self) -> None:
        """Lock the BIOS WriteFile target used by the resident save manager."""
        self.assertEqual(SAVE_FILE_NUMBER, 9)
        self.assertEqual(SAVE_FILE_ID, 0x03)
        self.assertEqual(SAVE_FILE_NAME, "SAVEDATA")
        self.assertEqual(SAVE_FILE_ADDRESS, 0x0390)
        self.assertEqual(SAVE_FILE_SIZE, 0x50)

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


if __name__ == "__main__":
    unittest.main()
