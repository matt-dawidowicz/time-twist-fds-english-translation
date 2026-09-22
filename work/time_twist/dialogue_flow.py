"""Trace four-row dialogue geometry across record calls.

Timing semantics are authoritative in TEXT_CONTROL_STATE_MACHINE.md; this helper
models only staging-buffer ownership/geometry for overwrite regression checks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .production_translation_core import ProductionTranslationError


@dataclass(frozen=True)
class DialogueTrace:
    """Record physical writes and the ownership of the final staging buffer."""

    positions: tuple[int, ...]
    owners: tuple[str | None, ...]
    scrolls: int
    cursor: int


def trace_dialogue(
    record: str,
    text: str,
    inherited: tuple[str | None, ...] | None = None,
) -> DialogueTrace:
    """Reject overwrites using NOV2's cursor and persistent line-state rules.

    Controls 3/4 scroll the existing rows. Controls 1/2/6 wait and re-enter
    fixed rows. CTRL:0 also consults zero-page $72, so two leading advances
    enter row three rather than repeatedly selecting row two.
    """
    owners: list[str | None] = (
        list(inherited) if inherited is not None else [None] * 192
    )
    if len(owners) != 192:
        raise ProductionTranslationError("staging buffer must be 192 bytes")
    cursor = line_state = scrolls = 0
    positions: list[int] = []
    for part in re.split(r"(\{CTRL:[0-7]\})", text):
        if part.startswith("{CTRL:"):
            control = int(part[6])
            if control == 0:
                if cursor < 49 and not line_state:
                    cursor, line_state = 48, 1
                elif cursor < 97:
                    cursor, line_state = 96, 2
                elif cursor < 145:
                    cursor, line_state = 144, 3
            elif control in (3, 4):
                owners = owners[48:] + [None] * 48
                cursor = 144
                scrolls += 1
            elif control in (1, 2, 6):
                target = {1: 48, 2: 96, 6: 144}[control]
                if cursor > target:
                    raise ProductionTranslationError(
                        f"{record}: control {control} would overwrite staged prose"
                    )
                cursor = target
            else:
                raise ProductionTranslationError(
                    f"{record}: unsupported dialogue control {control}"
                )
            continue
        if not part:
            continue
        row_end = (cursor // 48 + 1) * 48
        if cursor + 2 * len(part) > min(row_end, 192):
            raise ProductionTranslationError(
                f"{record}: text crosses a 24-column row or four-row buffer"
            )
        for _character in part:
            if owners[cursor] is not None:
                raise ProductionTranslationError(
                    f"{record}: overwrites {owners[cursor]} at byte {cursor}"
                )
            positions.append(cursor)
            owners[cursor : cursor + 2] = [record, record]
            cursor += 2
    return DialogueTrace(tuple(positions), tuple(owners), scrolls, cursor)


def validate_continuation(
    previous_id: str, next_id: str, texts: dict[str, str]
) -> None:
    """Render a continuation over its predecessor's retained staging rows."""
    previous = trace_dialogue(previous_id, texts[previous_id])
    trace_dialogue(next_id, texts[next_id], previous.owners)
