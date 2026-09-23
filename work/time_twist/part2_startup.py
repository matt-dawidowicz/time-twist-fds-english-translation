"""Recovered Zenpen-to-Kouhen title/startup handoff constants."""

from __future__ import annotations

from dataclasses import dataclass

# NOV2 copies zero page $C5-$D4 into SAVE $03D0-$03DF.
SAVE_ZERO_PAGE_SOURCE = 0x00C5
SAVE_ZERO_PAGE_DESTINATION = 0x03D0
SAVE_ZERO_PAGE_LENGTH = 0x10

CURRENT_SCENE_INDEX_ZP = 0x00CE
SAVE_SCENE_INDEX_ADDRESS = (
    SAVE_ZERO_PAGE_DESTINATION + CURRENT_SCENE_INDEX_ZP - SAVE_ZERO_PAGE_SOURCE
)

SAVE_CHECKSUM_LOW_ADDRESS = 0x03CD
SAVE_CHECKSUM_HIGH_ADDRESS = 0x03CE
SAVE_CHECKSUM_MARKER_ADDRESS = 0x03CF
SAVE_CHECKSUM_MARKER_VALUE = 0xA5

# A successful persisted-save transaction writes this nonzero marker. NOV2
# reloads it through $03DD -> $D2, and NOV4 uses $D2 to expose Part 2.
SAVE_PART2_MARKER_ADDRESS = 0x03DD
SAVE_PART2_MARKER_VALUE = 0x55
SAVE_SECONDARY_MARKER_ADDRESS = 0x03DE
SAVE_SECONDARY_MARKER_VALUE = 0xAA

TITLE_INVALID_SAVE_FLAG = 0xE3
TITLE_PART2_MARKER_FLAG = 0xE4

TITLE_MAIN_MENU_INDEX = 3
TITLE_MAIN_MENU_RECORD_IDS = (4, 5, 6)
TITLE_MAIN_MENU_LABELS = ("Start", "Load", "Part 2")

TITLE_PART2_TRANSITION_ADDRESS = 0xC059
TITLE_PART2_TRANSITION_OPERAND = 0xC7
TITLE_PART2_SCENE_INDEX = 7
TITLE_PART2_SCENE_FILE_IDS = (0x47, 0x57, 0xFF, 0xFF)


@dataclass(frozen=True)
class Part2Eligibility:
    """Describe the title-side inputs controlling Part 2 availability."""

    save_valid: bool
    persisted_marker: int

    @property
    def available(self) -> bool:
        """Return whether the title filter permits the Part 2 choice."""
        return self.save_valid and self.persisted_marker != 0


def save_address_for_zero_page(address: int) -> int:
    """Map one persisted zero-page address into the 80-byte SAVE block."""
    if not SAVE_ZERO_PAGE_SOURCE <= address < (
        SAVE_ZERO_PAGE_SOURCE + SAVE_ZERO_PAGE_LENGTH
    ):
        raise ValueError("zero-page address is outside the persisted $C5-$D4 block")
    return SAVE_ZERO_PAGE_DESTINATION + address - SAVE_ZERO_PAGE_SOURCE


def part2_is_available(*, save_valid: bool, persisted_marker: int) -> bool:
    """Return the verified NOV4 Part 2 menu-eligibility result."""
    if not 0 <= persisted_marker <= 0xFF:
        raise ValueError("persisted marker must fit in one byte")
    return Part2Eligibility(save_valid, persisted_marker).available
