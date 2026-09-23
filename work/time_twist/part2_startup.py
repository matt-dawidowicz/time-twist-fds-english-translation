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

# These bytes are persisted title/system metadata. $03DD is loaded into $D2 and
# $03DE into $D3 after a valid SAVE, but neither is the Part 2 visibility bit.
SAVE_TITLE_METADATA_ADDRESS = 0x03DD
SAVE_TITLE_METADATA_VALUE = 0x55
SAVE_SECONDARY_METADATA_ADDRESS = 0x03DE
SAVE_SECONDARY_METADATA_VALUE = 0xAA

# Startup SAVE validation sets persistent flag E3 only for an invalid or
# uninitialized SAVE. The Part 2 menu predicate survives iff E3 is clear.
TITLE_INVALID_SAVE_FLAG = 0xE3
TITLE_AUXILIARY_CONTINUATION_FLAG = 0xE4

TITLE_START_MENU_INDEX = 2
TITLE_START_MENU_RECORD_IDS = (4, 5, 6)
TITLE_START_MENU_LABELS = ("Start", "Load", "Part 2")

TITLE_PART_MENU_INDEX = 3
TITLE_PART_MENU_RECORD_IDS = (11, 12)
TITLE_PART_MENU_LABELS = ("Part 1", "Part 2")
TITLE_PART_MENU_SECONDARY_SELECTOR = 1
TITLE_PART1_FILTER = bytes.fromhex("00")
TITLE_PART2_FILTER = bytes.fromhex("91 E3 92 01 E3 E4 00")

TITLE_PART2_TRANSITION_ADDRESS = 0xC059
TITLE_PART2_TRANSITION_OPERAND = 0xC7
TITLE_PART2_SCENE_INDEX = 7
TITLE_PART2_SCENE_FILE_IDS = (0x47, 0x57, 0xFF, 0xFF)

SAVE_FILE_NUMBER = 9
SAVE_FILE_ID = 0x03
SAVE_FILE_NAME = "SAVEDATA"
SAVE_FILE_ADDRESS = 0x0390
SAVE_FILE_SIZE = 0x50
SAVE_TRANSFER_LOAD_FILE_IDS = (0x02, 0x03, 0xFF)


@dataclass(frozen=True)
class Part2PredicateState:
    """Describe the persistent-flag state controlling Part 2 visibility."""

    invalid_save_flag_set: bool

    @property
    def available(self) -> bool:
        """Return whether the native menu filter keeps the Part 2 choice."""
        return not self.invalid_save_flag_set


def save_address_for_zero_page(address: int) -> int:
    """Map one persisted zero-page address into the 80-byte SAVE block."""
    if not SAVE_ZERO_PAGE_SOURCE <= address < (
        SAVE_ZERO_PAGE_SOURCE + SAVE_ZERO_PAGE_LENGTH
    ):
        raise ValueError("zero-page address is outside the persisted $C5-$D4 block")
    return SAVE_ZERO_PAGE_DESTINATION + address - SAVE_ZERO_PAGE_SOURCE


def part2_predicate_allows(*, invalid_save_flag_set: bool) -> bool:
    """Return the verified NOV4 Part 2 menu-filter result."""
    return Part2PredicateState(invalid_save_flag_set).available


def part2_is_available(*, save_valid: bool) -> bool:
    """Return the title-startup availability implied by SAVE validation.

    On a cold title startup NOV2 sets flag E3 when SAVE validation fails. A
    valid SAVE leaves that fresh-start suppressor clear, so the Part 2 choice
    survives the menu filter.
    """
    return part2_predicate_allows(invalid_save_flag_set=not save_valid)
