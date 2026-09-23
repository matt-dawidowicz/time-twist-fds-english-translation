"""Model the verified Zenpen-to-Kouhen title/save handoff."""

from __future__ import annotations

from dataclasses import dataclass

SAVE_DISK_WRITE_MARKER = 0x55
SAVE_SECONDARY_MARKER = 0xAA
SAVE_MARKER_ADDRESS = 0x03DD
SAVE_SECONDARY_MARKER_ADDRESS = 0x03DE
TITLE_MARKER_ZP = 0xD2
TITLE_SECONDARY_MARKER_ZP = 0xD3
INVALID_SAVE_FLAG = 0xE3
PART2_MENU_FLAG = 0xE4
KOUHEN_FIRST_SCENE_TARGET = 0xC7


@dataclass(frozen=True)
class Part2TitleGate:
    """Describe title-menu visibility derived from restored SAVE state."""

    save_valid: bool
    disk_write_marker: int

    @property
    def load_visible(self) -> bool:
        """Return whether the title exposes Load."""
        return self.save_valid

    @property
    def part2_flag(self) -> bool:
        """Return the NOV4-derived E4 predicate flag."""
        return self.disk_write_marker != 0

    @property
    def part2_visible(self) -> bool:
        """Return whether the title exposes Part 2."""
        return self.save_valid and self.part2_flag


def title_gate_from_save(
    *,
    save_valid: bool,
    disk_write_marker: int,
) -> Part2TitleGate:
    """Build the verified title-menu gate from restored SAVE metadata."""
    if not 0 <= disk_write_marker <= 0xFF:
        raise ValueError("disk-write marker must fit in one byte")
    return Part2TitleGate(
        save_valid=save_valid,
        disk_write_marker=disk_write_marker,
    )
