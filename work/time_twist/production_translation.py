"""Canonical scenario-English source loading and validation.

There is exactly one active English source for scenario text:
``work/translations/BANK.json``. Those files contain the complete, materialized,
playtested wording and the approved control layout. The release path does not
merge a base translation, review proposal, or override layer.

Generic layout helpers remain available from :mod:`production_translation_core`
for deliberate future editing tools, but release materialization copies the
canonical maps verbatim after validating their renderer contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import production_translation_core as _core

CONTROL_RE = _core.CONTROL_RE
DISPLAY_COLUMNS = _core.DISPLAY_COLUMNS
TEXT_ROW_BYTES = _core.TEXT_ROW_BYTES
TEXT_BUFFER_ROWS = _core.TEXT_BUFFER_ROWS
TEXT_BUFFER_BYTES = _core.TEXT_BUFFER_BYTES
LINE_ADVANCE_CONTROL = _core.LINE_ADVANCE_CONTROL
SCROLL_CONTROL = _core.SCROLL_CONTROL
INSERTABLE_LAYOUT_CONTROLS = _core.INSERTABLE_LAYOUT_CONTROLS
SEMANTIC_CONTROLS = _core.SEMANTIC_CONTROLS
ProductionTranslationError = _core.ProductionTranslationError
validate_renderer_buffer_layout = _core.validate_renderer_buffer_layout
validate_production_control_sequence = (
    _core.validate_production_control_sequence
)
layout_review_text = _core.layout_review_text

CANONICAL_RECORD_COUNTS = {
    "TT1A": 35,
    "TT1B": 137,
    "TT2": 169,
    "T22": 58,
    "TT3A": 152,
    "TT3B": 58,
    "TT4": 183,
    "TT5": 123,
    "T25": 76,
    "TT6A": 100,
    "TT6B": 94,
    "TT6C": 106,
    "TT6D": 8,
}

# Exact v38 layouts that predate the generic greedy/23-column policy.
# Hashes scope exceptions to reviewed text; edits use the strict policy.
V38_LAYOUT_EXCEPTIONS = {
    "TT5/g2/r16": "3ea8b405bfe5e4ac0f7e6e8020acb2d2776b6cdb4bb6ab3adfbb15b949f77de5",
    "TT3A/g4/r7": "35e87952c633e7e59ba0276764ce9c9eeb41aa1e4ad624ed612109b7d956f643",
    "TT6B/g1/r30": "924190a4c2608ae6db2b89a17dbac572664817d3b48d9b0685a9d7e9b5500063",
    "TT6B/g2/r1": "552c39d9409803f56fe98172202930ef41376957bc79d46f995c5c119ae44c23",
    "TT6B/g2/r2": "629387fb4ef02450d5c32aacf922e35b79fba8088a7ef8b88b8855f3441bda25",
    "TT6B/g2/r3": "ef44ae455716a0ff0f0baafab2d607a59ceb96e01c0b315b0374b55cc53405a3",
    "TT4/g5/r11": "1689722348c6a4e9f262a3517b9ecdcc7bb160683e76fda559541d4d7b11127e",
}


def _is_checkpoint_layout(record_id: str, text: str) -> bool:
    """Recognize only the exact preserved v38 layout exceptions."""
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest() == V38_LAYOUT_EXCEPTIONS.get(record_id)


QUIZ_QUESTION_RECORDS = frozenset(
    {
        "TT2/g1/r12",
        "TT2/g1/r15",
        "TT2/g1/r16",
        "TT2/g1/r17",
        "TT2/g1/r18",
        "TT3A/g4/r2",
        "TT3A/g4/r4",
        "TT3A/g4/r5",
        "TT3A/g4/r6",
        "TT3A/g4/r7",
        "TT4/g5/r7",
        "TT4/g5/r10",
        "TT4/g5/r11",
        "TT4/g5/r12",
        "TT4/g5/r13",
        "TT5/g2/r12",
        "TT5/g2/r15",
        "TT5/g2/r16",
        "TT5/g2/r17",
        "TT5/g2/r18",
        "TT6B/g1/r30",
        "TT6B/g2/r0",
        "TT6B/g2/r1",
        "TT6B/g2/r2",
        "TT6B/g2/r3",
    }
)

INFO_CARD_RECORDS = frozenset(
    {
        "TT2/g1/r4",
        "TT2/g1/r5",
        "TT2/g1/r6",
        "TT3A/g0/r14",
        "TT4/g1/r22",
        "TT5/g1/r6",
        "TT6A/g0/r8",
        "TT6A/g1/r10",
    }
)

PRESENTATION_LAYOUT_RECORDS = frozenset(
    {
        # The quoted service title is a complete presentation unit. Keep the
        # following input instruction on a fresh row even though "Enter" would
        # technically fit beside the title under the generic greedy wrapper.
        "TT1A/g0/r3",
    }
)

STRUCTURAL_LAYOUT_RECORDS = (
    QUIZ_QUESTION_RECORDS | INFO_CARD_RECORDS | PRESENTATION_LAYOUT_RECORDS
)
QUIZ_MAX_SEGMENT_COLUMNS = 23


def validate_record_production_control_sequence(
    record_id: str, source: str, production: str
) -> None:
    """Compatibility wrapper for generic control-sequence validation."""
    try:
        _core.validate_production_control_sequence(source, production)
    except ProductionTranslationError as error:
        raise ProductionTranslationError(f"{record_id}: {error}") from error


def _control_sequence(text: str) -> tuple[int, ...]:
    """Return every native control value in textual order."""
    return tuple(int(value) for value in CONTROL_RE.findall(text))


def _leading_record_cursor(text: str) -> int | None:
    """Return the first visible-row cursor after leading controls, if any."""
    cursor = 0
    position = 0
    saw_control = False
    while True:
        match = CONTROL_RE.match(text, position)
        if match is None:
            break
        saw_control = True
        cursor = _core._cursor_after_control(cursor, int(match.group(1)))
        position = match.end()
    return cursor if saw_control else None


def _maximum_written_cursor(text: str) -> int:
    """Return the furthest byte written by one record in the four-row buffer."""
    segments, controls = _core._template_parts(text)
    cursor = 0
    maximum = 0
    for index, segment in enumerate(segments):
        cursor += len(segment) * 2
        maximum = max(maximum, cursor)
        if index < len(controls):
            cursor = _core._cursor_after_control(cursor, controls[index])
    return maximum


def _validate_quiz_question_geometry(
    bank_name: str,
    base: dict[str, str],
    production: dict[str, str],
) -> None:
    """Validate the canonical row geometry used by native quiz answer menus."""
    prefix = f"{bank_name}/"
    for record_id in sorted(
        record_id
        for record_id in QUIZ_QUESTION_RECORDS
        if record_id.startswith(prefix)
    ):
        if record_id not in production:
            raise ProductionTranslationError(
                f"{record_id}: registered quiz question is missing"
            )
        translated = production[record_id]
        if _is_checkpoint_layout(record_id, translated):
            continue
        segments, _controls = _core._template_parts(translated)
        for index, segment in enumerate(segments):
            if len(segment) > QUIZ_MAX_SEGMENT_COLUMNS:
                raise ProductionTranslationError(
                    f"{record_id}: quiz segment {index} is "
                    f"{len(segment)} columns; maximum is "
                    f"{QUIZ_MAX_SEGMENT_COLUMNS}"
                )


def _validate_cross_record_staging(
    bank_name: str,
    base: dict[str, str],
    production: dict[str, str],
) -> None:
    """Compatibility validator for callers comparing two materialized maps."""
    grouped: dict[tuple[int, int], str] = {}
    pattern = re.compile(rf"^{re.escape(bank_name)}/g(\d+)/r(\d+)$")
    for record_id in production:
        match = pattern.match(record_id)
        if match is not None:
            grouped[(int(match.group(1)), int(match.group(2)))] = record_id

    for (group, record), record_id in sorted(grouped.items()):
        next_id = grouped.get((group, record + 1))
        if next_id is None or next_id not in base:
            continue
        next_cursor = _leading_record_cursor(base[next_id])
        if next_cursor is None:
            continue
        source_max = _maximum_written_cursor(base[record_id])
        production_max = _maximum_written_cursor(production[record_id])
        if source_max <= next_cursor < production_max:
            raise ProductionTranslationError(
                f"{record_id}: production text reaches 0x{production_max:02X}, "
                f"but following {next_id} re-enters at 0x{next_cursor:02X}"
            )


def _speaker_geometry(text: str) -> tuple[set[int], list[str]]:
    """Return segment indexes that begin speaker turns and any label errors."""
    segments, _controls = _core._template_parts(text)
    plain = "".join(segments)
    char_map: list[tuple[int, int]] = []
    for segment_index, segment in enumerate(segments):
        char_map.extend(
            (segment_index, offset) for offset in range(len(segment))
        )

    starts: set[int] = set()
    errors: list[str] = []
    for start, end in _core._speaker_label_spans(plain):
        if not char_map or start >= len(char_map) or end <= start:
            continue
        start_segment, start_offset = char_map[start]
        end_segment, _end_offset = char_map[end - 1]
        label = plain[start:end]
        if start_segment != end_segment:
            errors.append(f"speaker label {label!r} is split by a control")
            continue
        if start_offset != 0:
            errors.append(
                f"speaker label {label!r} does not start a fresh row"
            )
            continue
        starts.add(start_segment)
    return starts, errors


def _validate_greedy_soft_wrap(record_id: str, text: str) -> None:
    """Require maximal 24-column fill except at structural or speaker rows."""
    if record_id in STRUCTURAL_LAYOUT_RECORDS or _is_checkpoint_layout(
        record_id, text
    ):
        return
    segments, controls = _core._template_parts(text)
    speaker_starts, errors = _speaker_geometry(text)
    if errors:
        raise ProductionTranslationError(f"{record_id}: " + "; ".join(errors))

    for index, control in enumerate(controls):
        if control not in INSERTABLE_LAYOUT_CONTROLS:
            continue
        left = segments[index].rstrip()
        right = segments[index + 1].lstrip()
        if not left or not right:
            continue
        if index + 1 in speaker_starts:
            continue
        first_word = right.split()[0]
        if len(left) + 1 + len(first_word) <= DISPLAY_COLUMNS:
            raise ProductionTranslationError(
                f"{record_id}: unnecessary soft wrap after {left!r}; "
                f"next word {first_word!r} still fits"
            )


def _validate_canonical_bank(bank_name: str, data: dict[str, str]) -> None:
    """Validate one sole-source scenario map before any build consumes it."""
    expected = CANONICAL_RECORD_COUNTS.get(bank_name)
    if expected is None:
        raise ProductionTranslationError(
            f"unknown canonical scenario bank {bank_name!r}"
        )
    if len(data) != expected:
        raise ProductionTranslationError(
            f"{bank_name}: expected {expected} canonical records, found {len(data)}"
        )
    pattern = re.compile(rf"^{re.escape(bank_name)}/g\d+/r\d+$")
    malformed = [
        record_id for record_id in data if not pattern.match(record_id)
    ]
    if malformed:
        raise ProductionTranslationError(
            f"{bank_name}: malformed canonical record IDs: {malformed[:3]}"
        )

    for record_id, text in data.items():
        try:
            validate_renderer_buffer_layout(text)
            _validate_greedy_soft_wrap(record_id, text)
        except ProductionTranslationError as error:
            if str(error).startswith(f"{record_id}:"):
                raise
            raise ProductionTranslationError(
                f"{record_id}: {error}"
            ) from error

    _validate_quiz_question_geometry(bank_name, data, data)


def merged_translation_map(
    bank_name: str,
    *,
    base_directory: Path,
    override_directory: Path | None = None,
    review_directory: Path | None = None,
) -> dict[str, str]:
    """Load one canonical bank; legacy layered inputs are deliberately rejected."""
    if override_directory is not None or review_directory is not None:
        raise ProductionTranslationError(
            "legacy translation layering is retired; "
            "edit work/translations/BANK.json directly"
        )
    data = _core._load_string_map(
        base_directory / f"{bank_name}.json",
        label=f"{bank_name} canonical translation",
    )
    _validate_canonical_bank(bank_name, data)
    return data


def materialize_production_maps(
    bank_names: tuple[str, ...],
    *,
    base_directory: Path,
    output_directory: Path,
    override_directory: Path | None = None,
    review_directory: Path | None = None,
) -> dict[str, int]:
    """Copy validated canonical maps into a deterministic build staging directory."""
    if override_directory is not None or review_directory is not None:
        raise ProductionTranslationError(
            "legacy translation layering is retired; "
            "only canonical scenario maps may enter a release"
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for bank_name in bank_names:
        canonical = merged_translation_map(
            bank_name,
            base_directory=base_directory,
        )
        path = output_directory / f"{bank_name}.json"
        path.write_text(
            json.dumps(canonical, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        counts[bank_name] = len(canonical)
    return counts
