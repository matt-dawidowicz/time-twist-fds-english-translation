"""Model Time Twist palette-animation records and controls.

The source table selected through scenario header word `$A21C` stores one or
more animation sequences per record. NOV2 expands the selected record into a
runtime buffer at `$92DA` and advances it from `$91AD`.

This module models the machine behavior without inventing story-facing names
for source-unused control values.
"""

from __future__ import annotations

from dataclasses import dataclass

OVERLAY_LOAD_ADDRESS = 0xA200
PALETTE_CONTROL_STOPPED = 0x00
PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY = 0x7E
PALETTE_CONTROL_LOOP_FOREVER = 0x7F
PALETTE_CONTROL_A_GATE = 0x80
PALETTE_DURATION_MASK = 0x7F
PALETTE_DURATION_HOLD_FOREVER = 0x7F


class PaletteAnimationError(ValueError):
    """Report malformed recovered palette-animation data."""


@dataclass(frozen=True)
class PaletteAnimationFrame:
    """One three-byte palette-animation frame descriptor."""

    duration_raw: int
    background_palette_record: int
    sprite_palette_record: int

    @property
    def duration(self) -> int:
        """Return the native seven-bit frame duration."""
        return self.duration_raw & PALETTE_DURATION_MASK

    @property
    def holds_forever(self) -> bool:
        """Return whether this frame never advances by duration expiry."""
        return self.duration == PALETTE_DURATION_HOLD_FOREVER

    @property
    def ignored_duration_high_bit(self) -> bool:
        """Return whether NOV2 masks bit 7 from the source duration."""
        return bool(self.duration_raw & 0x80)


@dataclass(frozen=True)
class PaletteAnimationSequence:
    """One frame list and its native repeat/control byte."""

    frame_count: int
    control: int
    frames: tuple[PaletteAnimationFrame, ...]

    @property
    def initial_a_gate(self) -> bool:
        """Return whether bit 7 blocks advancement pending a fresh A press."""
        return bool(self.control & PALETTE_CONTROL_A_GATE)

    @property
    def low_control(self) -> int:
        """Return the control byte after the native A-gate bit is cleared."""
        return self.control & 0x7F


@dataclass(frozen=True)
class PaletteAnimationRecord:
    """One source record selected by the one-based `$89` selector."""

    address: int
    sequences: tuple[PaletteAnimationSequence, ...]
    encoded_end_address: int


@dataclass(frozen=True)
class PaletteControlGateResult:
    """Result of the native control pre-check at NOV2 `$9209-$9225`."""

    active: bool
    control: int


def gate_palette_control(
    control: int, *, fresh_a: bool
) -> PaletteControlGateResult:
    """Apply the native per-frame zero/high-bit control gate.

    A zero control is inactive. A control with bit 7 set remains blocked until
    a fresh A-button edge is present; on that frame NOV2 clears bit 7 and
    continues without re-running the zero test.
    """
    if not 0 <= control <= 0xFF:
        raise ValueError("palette control must fit in one byte")
    if control == PALETTE_CONTROL_STOPPED:
        return PaletteControlGateResult(False, control)
    if control & PALETTE_CONTROL_A_GATE:
        if not fresh_a:
            return PaletteControlGateResult(False, control)
        return PaletteControlGateResult(True, control & 0x7F)
    return PaletteControlGateResult(True, control)


def palette_control_after_cycle(control: int, *, fresh_a: bool) -> int:
    """Return the control byte after one complete frame-list cycle.

    `$7F` is the permanent loop sentinel. `$7E` continues cycling until a
    fresh A edge occurs on a cycle boundary, at which point it becomes zero and
    stops on later ticks. All other values decrement with ordinary 8-bit wrap.
    """
    if not 0 <= control <= 0xFF:
        raise ValueError("palette control must fit in one byte")
    if control == PALETTE_CONTROL_LOOP_FOREVER:
        return control
    if control == PALETTE_CONTROL_LOOP_UNTIL_A_AT_BOUNDARY:
        return 0 if fresh_a else control
    return (control - 1) & 0xFF


def effective_palette_duration(duration_raw: int) -> int:
    """Return the duration value used by NOV2 after `AND #$7F`."""
    if not 0 <= duration_raw <= 0xFF:
        raise ValueError("palette duration must fit in one byte")
    return duration_raw & PALETTE_DURATION_MASK


def parse_palette_animation_records(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[PaletteAnimationRecord, ...]:
    """Parse a complete half-open palette-animation table range."""
    start = start_address - load_address
    end = end_address - load_address
    if start < 0 or end < start or end > len(data):
        raise PaletteAnimationError(
            "invalid palette-animation range 0x{:04X}-0x{:04X}".format(
                start_address, end_address
            )
        )

    cursor = start
    records: list[PaletteAnimationRecord] = []
    while cursor < end:
        record_address = load_address + cursor
        sequence_count = data[cursor]
        cursor += 1
        if sequence_count == 0:
            raise PaletteAnimationError(
                "zero-sequence palette record at 0x{:04X}".format(record_address)
            )

        sequences: list[PaletteAnimationSequence] = []
        for _ in range(sequence_count):
            if cursor + 2 > end:
                raise PaletteAnimationError(
                    "truncated palette sequence at 0x{:04X}".format(
                        load_address + cursor
                    )
                )
            frame_count = data[cursor]
            control = data[cursor + 1]
            cursor += 2
            if frame_count == 0:
                raise PaletteAnimationError(
                    "zero-frame palette sequence at 0x{:04X}".format(
                        load_address + cursor - 2
                    )
                )
            payload_end = cursor + frame_count * 3
            if payload_end > end:
                raise PaletteAnimationError(
                    "palette frames overrun table at 0x{:04X}".format(
                        load_address + cursor
                    )
                )
            frames = tuple(
                PaletteAnimationFrame(*data[offset : offset + 3])
                for offset in range(cursor, payload_end, 3)
            )
            cursor = payload_end
            sequences.append(
                PaletteAnimationSequence(
                    frame_count=frame_count,
                    control=control,
                    frames=frames,
                )
            )

        records.append(
            PaletteAnimationRecord(
                address=record_address,
                sequences=tuple(sequences),
                encoded_end_address=load_address + cursor,
            )
        )

    if cursor != end:
        raise PaletteAnimationError("palette-animation table did not end exactly")
    return tuple(records)
