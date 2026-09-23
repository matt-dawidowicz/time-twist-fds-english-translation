"""Decode Time Twist gameplay FDS/scene transition operands."""

from __future__ import annotations

from dataclasses import dataclass

FDS_TRANSITION_DISK_MASK = 0x80
FDS_TRANSITION_SIDE_MASK = 0x40
FDS_TRANSITION_SCENE_MASK = 0x3F

FDS_DISK_NAMES = ("Zenpen", "Kouhen")
FDS_SIDE_NAMES = ("A", "B")


@dataclass(frozen=True)
class FdsSceneTransitionTarget:
    """Describe one packed E0 transition operand."""

    raw: int
    disk_index: int
    disk_name: str
    side_index: int
    side_name: str
    scene_index: int


def decode_fds_scene_transition_operand(
    operand: int,
) -> FdsSceneTransitionTarget:
    """Decode the packed target byte consumed by retail opcode E0.

    Bit 7 selects Zenpen/Kouhen, bit 6 selects FDS side A/B, and bits 5-0
    select one of NOV2's scene-load-table rows.
    """
    if not 0 <= operand <= 0xFF:
        raise ValueError("transition operand must fit in one byte")

    disk_index = 1 if operand & FDS_TRANSITION_DISK_MASK else 0
    side_index = 1 if operand & FDS_TRANSITION_SIDE_MASK else 0
    return FdsSceneTransitionTarget(
        raw=operand,
        disk_index=disk_index,
        disk_name=FDS_DISK_NAMES[disk_index],
        side_index=side_index,
        side_name=FDS_SIDE_NAMES[side_index],
        scene_index=operand & FDS_TRANSITION_SCENE_MASK,
    )
