"""Tests for recovered gameplay audio-command selector semantics."""

from __future__ import annotations

import unittest

from time_twist.audio_commands import (
    AUDIO_LATCH_ROLES,
    COMPOSED_AUDIO_OWNER,
    MUSIC_SELECTOR_SLOTS,
    RESIDENT_LATCH0_COMMANDS,
    RESIDENT_LATCH2_SEQUENCES,
    RETAIL_AUDIO_VALUES,
    SCENE_LATCH1_ENTRY_POINTS,
    SCENE_LATCH1_STOP_ENTRY_POINTS,
    SCENE_MUSIC_TABLE_BASES,
)


class AudioCommandMapTests(unittest.TestCase):
    """Protect the completed value-level audio selector map."""

    def test_retail_audio_values_match_recovered_source_language(self) -> None:
        """Keep the exact source-used opcode/value sets stable."""
        self.assertEqual(
            RETAIL_AUDIO_VALUES,
            {
                0x83: (0x80, 0x01, 0x02, 0x08, 0x04),
                0x90: (0x02, 0x80),
                0x91: (
                    0x01,
                    0x80,
                    0x02,
                    0x04,
                    0x10,
                    0x08,
                    0x20,
                    0x40,
                    0x03,
                ),
                0x92: (0x01, 0x04, 0x02, 0x08, 0x80),
                0x93: (0x10, 0x40, 0x20, 0x80, 0x04, 0x01, 0x02),
            },
        )

    def test_resident_latch_zero_meanings_are_bound(self) -> None:
        """Distinguish source-used noise control from the direct typewriter click."""
        self.assertEqual(RESIDENT_LATCH0_COMMANDS[0x02].handler, 0xD843)
        self.assertEqual(
            RESIDENT_LATCH0_COMMANDS[0x04].name,
            "typewriter_noise_click",
        )
        self.assertEqual(RESIDENT_LATCH0_COMMANDS[0x80].handler, 0xD86C)

    def test_resident_pulse_sequences_match_nov3_selector_table(self) -> None:
        """Lock the five source-used $07E2 sequence-pair identities."""
        self.assertEqual(
            RESIDENT_LATCH2_SEQUENCES,
            {
                0x01: (0x00, 0x0A),
                0x02: (0x13, 0x2E),
                0x04: (0x49, 0x4E),
                0x08: (0x52, 0x58),
                0x80: (0x09, 0x00),
            },
        )

    def test_music_selector_groups_and_fixed_slots(self) -> None:
        """Protect global music-selector behavior independently of scene data."""
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x01][1], (8, 9, 10, 11, 12))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x02][1], (13, 14, 15, 16, 17))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x04][1], (18, 19, 20, 21))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x08][1], (3,))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x10][1], (4,))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x20][1], (5,))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x40][1], (6,))
        self.assertEqual(MUSIC_SELECTOR_SLOTS[0x80][0], "stop")

    def test_scene_audio_indirection_is_explicit(self) -> None:
        """Require scene-local owners instead of a false global $07E1 ID table."""
        self.assertEqual(SCENE_MUSIC_TABLE_BASES["TT3A"], 0xC25D)
        self.assertEqual(COMPOSED_AUDIO_OWNER["TT3B"], "TT3A")
        self.assertEqual(COMPOSED_AUDIO_OWNER["T22"], "TT2")
        self.assertEqual(SCENE_LATCH1_ENTRY_POINTS["TT3A"][0x20], 0xD0B0)
        self.assertEqual(SCENE_LATCH1_ENTRY_POINTS["TT3A"][0x03], 0xD071)
        self.assertEqual(SCENE_LATCH1_STOP_ENTRY_POINTS["TT3A"], 0xD058)

    def test_all_four_latch_roles_are_named(self) -> None:
        """Require the complete command-latch block to remain documented."""
        self.assertEqual(set(AUDIO_LATCH_ROLES), set(range(0x07E0, 0x07E4)))


if __name__ == "__main__":
    unittest.main()
