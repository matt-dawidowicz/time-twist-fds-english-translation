"""Materialize canonical production English over the certified base maps.

The base maps supply stable record IDs and native semantic-control topology.
Reviewed retranslation JSON and explicit overrides choose the visible English;
this module then regenerates 24-column row/scroll geometry for the NOV2
four-row renderer. Semantic controls remain in order while source-only Japanese
presentation breaks are replaced by English layout controls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONTROL_RE = re.compile(r"\{CTRL:([0-7])\}")
DISPLAY_COLUMNS = 24
TEXT_ROW_BYTES = DISPLAY_COLUMNS * 2
TEXT_BUFFER_ROWS = 4
TEXT_BUFFER_BYTES = TEXT_ROW_BYTES * TEXT_BUFFER_ROWS
LINE_ADVANCE_CONTROL = 0
SCROLL_CONTROL = 4
INSERTABLE_LAYOUT_CONTROLS = frozenset({LINE_ADVANCE_CONTROL, SCROLL_CONTROL})
SEMANTIC_CONTROLS = frozenset({1, 2, 3, 6})
NON_SPEAKER_LABELS = frozenset(
    {
        "TIME",
        "NAME",
        "PLACE",
        "OCCUPATION",
        "Password",
        "Memo",
        "Right",
        "Middle",
        "Left",
        "Both",
        "Name",
        "LOCATION",
        "Pierre Trade",
        "Chino Trade",
        "2",
    }
)
OVERWRITE_REENTRY_LIMIT = {
    1: TEXT_ROW_BYTES,
    2: TEXT_ROW_BYTES * 2,
    6: TEXT_ROW_BYTES * 3,
}
CONTROL_REENTRY_CURSOR = {
    1: TEXT_ROW_BYTES,
    2: TEXT_ROW_BYTES * 2,
    3: TEXT_ROW_BYTES * 3,
    4: TEXT_ROW_BYTES * 3,
    6: TEXT_ROW_BYTES * 3,
}

REVIEW_FILES = {
    "TT1A": ("TT1A_proposal.json", "records"),
    "TT1B": ("TT1B_proposal.json", "records"),
    "TT2": ("TT2_changes.json", "changes"),
    "T22": ("T22_changes.json", "changes"),
    "TT3A": ("TT3A_changes.json", "changes"),
    "TT3B": ("TT3B_changes.json", "changes"),
    "TT4": ("TT4_changes.json", "changes"),
    "TT5": ("TT5_changes.json", "changes"),
    "T25": ("T25_changes.json", "changes"),
    "TT6A": ("TT6A_changes.json", "changes"),
    "TT6B": ("TT6B_changes.json", "changes"),
    "TT6C": ("TT6C_changes.json", "changes"),
    "TT6D": ("TT6D_proposal.json", "records"),
}


class ProductionTranslationError(ValueError):
    """Report malformed review data or a layout that cannot preserve controls."""


def _load_json_object(path: Path, *, label: str) -> dict[str, object]:
    """Load one JSON object with contextual errors."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductionTranslationError(
            f"cannot load {label}: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise ProductionTranslationError(
            f"{label} must be a JSON object: {path}"
        )
    return payload


def _string_map(value: object, *, label: str) -> dict[str, str]:
    """Validate an object as a nonempty string-to-string map."""
    if not isinstance(value, dict):
        raise ProductionTranslationError(f"{label} must be a JSON object")
    result: dict[str, str] = {}
    for key, text in value.items():
        if not isinstance(key, str) or not isinstance(text, str) or not text:
            raise ProductionTranslationError(
                f"{label} must map nonempty string IDs to nonempty strings"
            )
        result[key] = text
    return result


def _load_string_map(path: Path, *, label: str) -> dict[str, str]:
    """Load a JSON object whose keys and values are all strings."""
    return _string_map(_load_json_object(path, label=label), label=label)


def _review_map(bank_name: str, review_directory: Path) -> dict[str, str]:
    """Load the reviewed unconstrained English for one scenario bank."""
    try:
        filename, field = REVIEW_FILES[bank_name]
    except KeyError as error:
        raise ProductionTranslationError(
            f"no production-review source registered for {bank_name}"
        ) from error
    path = review_directory / filename
    payload = _load_json_object(path, label=f"{bank_name} production review")
    return _string_map(
        payload.get(field),
        label=f"{bank_name} production review field {field!r}",
    )


def _template_parts(template: str) -> tuple[list[str], list[int]]:
    """Return visible template segments plus their ordered control values."""
    pieces = CONTROL_RE.split(template)
    segments = pieces[::2]
    controls = [int(value) for value in pieces[1::2]]
    return segments, controls


def _semantic_template_parts(template: str) -> tuple[list[str], list[int]]:
    """Collapse source-only line geometry while retaining semantic boundaries.

    Controls 1, 2, 3, and 6 carry native timing/continuation semantics and must
    remain in order. Interior controls 0 and 4 are Japanese presentation
    geometry, so production English regenerates them from its own 24-column
    layout. Leading/trailing presentation controls are retained because they can
    position record entry/exit even when no source glyph surrounds them.
    """
    segments, controls = _template_parts(template)
    visible = [index for index, segment in enumerate(segments) if segment]
    if not visible:
        return segments, controls
    first_visible = visible[0]
    last_visible = visible[-1]

    collapsed = [segments[0]]
    kept_controls: list[int] = []
    for index, control in enumerate(controls):
        keep = (
            control in SEMANTIC_CONTROLS
            or index < first_visible
            or index >= last_visible
        )
        if keep:
            kept_controls.append(control)
            collapsed.append(segments[index + 1])
        else:
            collapsed[-1] += segments[index + 1]
    return collapsed, kept_controls


def _semantic_anchor_ordinals(template: str) -> frozenset[int]:
    """Return source section controls that followed an explicit row break.

    A source ``{CTRL:0}{CTRL:2}`` pair marks a header/instruction boundary: the
    Japanese script ended a display row and then entered the next semantic
    section. Production English drops the Japanese row geometry but should
    still place that section transition at a natural phrase boundary.
    """
    segments, controls = _template_parts(template)
    semantic_ordinal = -1
    anchored: set[int] = set()
    for index, control in enumerate(controls):
        if control not in SEMANTIC_CONTROLS:
            continue
        semantic_ordinal += 1
        if (
            control == 2
            and index > 0
            and controls[index - 1] in INSERTABLE_LAYOUT_CONTROLS
            and not segments[index]
        ):
            anchored.add(semantic_ordinal)
    return frozenset(anchored)


def _is_strong_semantic_break(words: list[str], end_word: int) -> bool:
    """Return whether a word boundary cleanly ends a section phrase."""
    if end_word <= 0 or end_word >= len(words):
        return True
    raw_token = words[end_word - 1]
    closes_quote = raw_token.endswith(('"', "”", "’"))
    token = raw_token.rstrip('"”’)]}')
    next_is_dash = words[end_word].startswith(("—", "–"))
    if (
        (closes_quote and not next_is_dash)
        or token in {"—", "–"}
        or token.endswith(("…", "...", "!", "?"))
    ):
        return True
    if token.endswith((".", ";", ":")):
        stem = token[:-1].lstrip('"“‘([')
        abbreviations = {
            "DR",
            "MR",
            "MRS",
            "MS",
            "ST",
            "JR",
            "SR",
            "U.S",
        }
        return not (
            token.endswith(".")
            and (len(stem) <= 2 or stem.upper() in abbreviations)
        )
    return False


def _speaker_label_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Locate compact English speaker labels without mistaking prior prose.

    A label is the one- or two-word title-cased fragment immediately following
    sentence punctuation (or the record start) and ending in a colon. This
    recognizes the reviewed corpus's character/role labels while excluding
    prose such as ``How terrible… Meyer:`` from the label itself.
    """
    spans: list[tuple[int, int]] = []
    for match in re.finditer(":", text):
        colon = match.start()
        if colon >= 1 and text[colon - 1] == "…":
            start = colon - 1
            candidate = "…"
        elif colon >= 3 and text[colon - 3 : colon] == "...":
            start = colon - 3
            candidate = "..."
        else:
            boundary = colon - 1
            while boundary >= 0 and text[boundary] not in ".!?…:":
                boundary -= 1
            raw = text[boundary + 1 : colon]
            stripped = raw.lstrip(" \t\n\r\"“”'‘’()[]")
            start = boundary + 1 + len(raw) - len(stripped)
            candidate = stripped.rstrip(" \t\n\r\"“”'‘’()[]")
        words = candidate.split()
        if (
            not candidate
            or candidate in NON_SPEAKER_LABELS
            or len(candidate) > DISPLAY_COLUMNS
            or len(words) > 2
        ):
            continue
        if not all(
            word in {"…", "..."}
            or (word and (word[0].isupper() or word[0].isdigit()))
            for word in words
        ):
            continue
        spans.append((start, colon + 1))
    return tuple(spans)


def _speaker_turns(text: str) -> tuple[str, ...]:
    """Split prose so every recognized speaker begins a fresh layout unit."""
    spans = _speaker_label_spans(text)
    if not spans:
        return (text,) if text else ()
    starts = [start for start, _end in spans]
    turns: list[str] = []
    if starts[0] > 0:
        prefix = text[: starts[0]]
        if prefix.strip(" \t\n\r\"“”'‘’()[]"):
            turns.append(prefix.strip())
        else:
            starts[0] = 0
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        turn = text[start:end].strip()
        if turn:
            turns.append(turn)
    return tuple(turns)


def _forbidden_speaker_breaks(text: str) -> frozenset[int]:
    """Return word-boundary indices that would orphan a speaker label."""
    forbidden: set[int] = set()
    for _start, end in _speaker_label_spans(text):
        word_boundary = len(text[:end].split())
        if word_boundary < len(text.split()):
            forbidden.add(word_boundary)
    return frozenset(forbidden)


def _greedy_turn_rows(text: str, columns: int) -> tuple[str, ...]:
    """Return maximum-width rows, correcting only tiny final-word orphans."""
    words = text.split()
    if not words:
        return ()
    if any(len(word) > columns for word in words):
        longest = max(words, key=len)
        raise ProductionTranslationError(
            f"word {longest!r} exceeds the {columns}-column renderer"
        )
    rows: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= columns:
            current = candidate
        else:
            rows.append(current)
            current = word
    rows.append(current)

    # Greedy fill is authoritative. The only aesthetic exception is a final
    # one- or two-character word stranded by itself; borrow the previous row's
    # last word when that produces two legal rows.
    if len(rows) >= 2 and len(rows[-1]) <= 2:
        previous_words = rows[-2].split()
        if len(previous_words) >= 2:
            borrowed = previous_words[-1]
            revised_last = f"{borrowed} {rows[-1]}"
            revised_previous = " ".join(previous_words[:-1])
            if revised_previous and len(revised_last) <= columns:
                rows[-2] = revised_previous
                rows[-1] = revised_last
    return tuple(rows)


def _wrapped_rows(
    text: str, *, columns: int = DISPLAY_COLUMNS
) -> tuple[str, ...]:
    """Greedily fill rows while forcing recognized speaker turns to fresh rows.

    Each row takes the longest word-boundary prefix that fits. This deliberately
    favors full use of the 24-column dialogue box over visually balanced rows.
    A speaker label may never be stranded on a row without its first spoken word.
    """
    if not text:
        return ()
    rows: list[str] = []
    for turn in _speaker_turns(text):
        turn_rows = _greedy_turn_rows(turn, columns)
        spans = _speaker_label_spans(turn)
        if spans and len(turn.split()) > len(
            turn[spans[0][0] : spans[0][1]].split()
        ):
            label = turn[spans[0][0] : spans[0][1]]
            if turn_rows and turn_rows[0] == label:
                raise ProductionTranslationError(
                    f"speaker label {label!r} cannot be orphaned from its dialogue"
                )
        rows.extend(turn_rows)
    return tuple(rows)


def _break_score(text: str, position: int) -> int:
    """Prefer sentence and clause boundaries when assigning source controls."""
    before = text[position - 1] if position else ""
    if before in ".!?…":
        return 0
    if before in ";:":
        return 1
    if before in ",—":
        return 2
    return 3


def _semantic_boundary_penalty(template: str, text: str, position: int) -> int:
    """Score a reviewed split against the source segment's semantic cadence."""
    source = template.rstrip()
    before = text[position - 1] if position else ""
    if not source:
        return 0
    if source[-1] in ".!?…":
        source_mark = "…" if source[-1] in ".…" else source[-1]
        target_mark = "…" if before in ".…" else before
        if target_mark == source_mark:
            return 0
        if before in ".!?…":
            return 500
        return 10000
    if source[-1] in ";:":
        return 0 if before in ".!?…;:" else 1000
    if source[-1] in ",—":
        return 0 if before in ".!?…;:,—" else 500
    return _break_score(text, position)


def _cursor_after_control(cursor: int, control: int) -> int:
    """Model the native decoder's X cursor after one control transition.

    The text staging buffer stores two tile bytes per visible glyph. Control 0
    rounds X up to the next 0x30-byte row start until row four. Controls 1 and
    2 resume on rows two and three, while controls 3, 4, and 6 eventually
    continue on row four. Control 4 additionally scrolls rows two through four
    upward in the native runtime, which makes it the safe continuation control
    for production prose that needs another visible row.
    """
    if control == 0:
        if cursor < TEXT_ROW_BYTES + 1:
            return TEXT_ROW_BYTES
        if cursor < TEXT_ROW_BYTES * 2 + 1:
            return TEXT_ROW_BYTES * 2
        if cursor < TEXT_ROW_BYTES * 3 + 1:
            return TEXT_ROW_BYTES * 3
        return cursor
    try:
        return CONTROL_REENTRY_CURSOR[control]
    except KeyError as error:
        raise ProductionTranslationError(
            f"unsupported production control {control}"
        ) from error


def _row_end_for_cursor(cursor: int) -> int:
    """Return the exclusive byte end of the physical row containing ``cursor``."""
    if not 0 <= cursor <= TEXT_BUFFER_BYTES:
        raise ProductionTranslationError(
            f"renderer cursor X=${cursor:02X} is outside the text buffer"
        )
    if cursor == TEXT_BUFFER_BYTES:
        return TEXT_BUFFER_BYTES
    row = cursor // TEXT_ROW_BYTES
    return (row + 1) * TEXT_ROW_BYTES


def validate_renderer_buffer_layout(text: str) -> None:
    """Reject implicit row crossing and writes beyond NOV2's four-row buffer."""
    segments, controls = _template_parts(text)
    cursor = 0
    for index, segment in enumerate(segments):
        row_end = _row_end_for_cursor(cursor)
        end_cursor = cursor + len(segment) * 2
        if end_cursor > row_end:
            raise ProductionTranslationError(
                f"renderer segment {index} crosses a 24-column row without "
                f"an explicit row control: X=${cursor:02X} -> ${end_cursor:02X}, "
                f"row ends at ${row_end:02X}"
            )
        if end_cursor > TEXT_BUFFER_BYTES:
            raise ProductionTranslationError(
                f"renderer segment {index} reaches X=${end_cursor:02X}; "
                f"four-row buffer ends at ${TEXT_BUFFER_BYTES:02X}"
            )
        cursor = end_cursor
        if index < len(controls):
            control = controls[index]
            overwrite_limit = OVERWRITE_REENTRY_LIMIT.get(control)
            if overwrite_limit is not None and cursor > overwrite_limit:
                raise ProductionTranslationError(
                    f"renderer control {control} re-enters at X=${overwrite_limit:02X} "
                    f"and would overwrite staged prose through X=${cursor:02X}"
                )
            cursor = _cursor_after_control(cursor, control)


def validate_production_control_sequence(source: str, production: str) -> None:
    """Preserve semantic native controls while regenerating English line geometry."""
    _source_segments, source_controls = _semantic_template_parts(source)
    _production_segments, production_controls = _template_parts(production)
    required = [
        value for value in source_controls if value in SEMANTIC_CONTROLS
    ]
    actual_semantic = [
        value for value in production_controls if value in SEMANTIC_CONTROLS
    ]
    if actual_semantic != required:
        raise ProductionTranslationError(
            "production layout lost or reordered one or more semantic controls"
        )
    unexpected = [
        value
        for value in production_controls
        if value not in SEMANTIC_CONTROLS | INSERTABLE_LAYOUT_CONTROLS
    ]
    if unexpected:
        raise ProductionTranslationError(
            f"production layout introduced unsupported controls: {unexpected}"
        )


def _layout_chunk_at_cursor(
    text: str, cursor: int
) -> tuple[str, int, int, int]:
    """Lay out prose with explicit native row advances and row-four scrolling."""
    if not text:
        return "", cursor, 0, 0

    output: list[str] = []
    inserted_controls = 0
    inserted_scrolls = 0
    rows = _wrapped_rows(text)
    for row_index, row in enumerate(rows):
        row_end = _row_end_for_cursor(cursor)
        remaining_cells = (row_end - cursor) // 2
        if len(row) > remaining_cells:
            if cursor < TEXT_ROW_BYTES * (TEXT_BUFFER_ROWS - 1):
                output.append(f"{{CTRL:{LINE_ADVANCE_CONTROL}}}")
                inserted_controls += 1
                cursor = _cursor_after_control(cursor, LINE_ADVANCE_CONTROL)
            else:
                output.append(f"{{CTRL:{SCROLL_CONTROL}}}")
                inserted_controls += 1
                inserted_scrolls += 1
                cursor = CONTROL_REENTRY_CURSOR[SCROLL_CONTROL]
            row_end = _row_end_for_cursor(cursor)
            remaining_cells = (row_end - cursor) // 2
            if len(row) > remaining_cells:
                raise ProductionTranslationError(
                    f"row {row!r} cannot fit from renderer X=${cursor:02X}"
                )

        output.append(row)
        cursor += len(row) * 2
        if row_index == len(rows) - 1:
            continue

        row_four_start = TEXT_ROW_BYTES * (TEXT_BUFFER_ROWS - 1)
        if cursor <= row_four_start:
            output.append(f"{{CTRL:{LINE_ADVANCE_CONTROL}}}")
            inserted_controls += 1
            # At the exact row-three boundary the corrected control no longer
            # scrolls, but retain the old ranking penalty so the presentation
            # fix does not reshuffle unrelated semantic-control assignments.
            if cursor == row_four_start:
                inserted_scrolls += 1
            cursor = _cursor_after_control(cursor, LINE_ADVANCE_CONTROL)
        else:
            output.append(f"{{CTRL:{SCROLL_CONTROL}}}")
            inserted_controls += 1
            inserted_scrolls += 1
            cursor = CONTROL_REENTRY_CURSOR[SCROLL_CONTROL]

    return "".join(output), cursor, inserted_controls, inserted_scrolls


def _split_visible_text(
    text: str,
    template_segments: list[str],
    controls: list[int],
    *,
    anchored_semantic_ordinals: frozenset[int] = frozenset(),
) -> list[str]:
    """Distribute reviewed prose across preserved semantic control boundaries.

    Dynamic programming moves only word boundaries around controls 1/2/3/6.
    English line/scroll controls are regenerated by the greedy 24-column wrapper.
    A semantic boundary may not strand a speaker label without spoken text.
    """
    active = [
        index for index, segment in enumerate(template_segments) if segment
    ]
    if not active:
        if text:
            raise ProductionTranslationError(
                "template has no visible segment for reviewed English"
            )
        return ["" for _ in template_segments]

    words = text.split(" ")
    if len(words) < len(active):
        raise ProductionTranslationError(
            "reviewed English has fewer words than nonempty semantic slots"
        )
    forbidden_breaks = _forbidden_speaker_breaks(text)

    target_total = sum(
        max(1, len(template_segments[index])) for index in active
    )
    text_total = max(1, len(text))
    prefix_chars = [0]
    for word_index, word in enumerate(words):
        prefix_chars.append(
            prefix_chars[-1] + len(word) + (1 if word_index else 0)
        )

    # (next word, decoder cursor) ->
    # (anchor violations, layout controls, scrolls, score, chunks)
    states: dict[
        tuple[int, int], tuple[int, int, int, int, tuple[str, ...]]
    ] = {(0, 0): (0, 0, 0, 0, ())}
    semantic_ordinal_by_control: dict[int, int] = {}
    semantic_ordinal = -1
    for control_index, control in enumerate(controls):
        if control in SEMANTIC_CONTROLS:
            semantic_ordinal += 1
            semantic_ordinal_by_control[control_index] = semantic_ordinal
    for segment_index, template_segment in enumerate(template_segments):
        remaining_active = sum(
            1 for segment in template_segments[segment_index + 1 :] if segment
        )
        next_states: dict[
            tuple[int, int], tuple[int, int, int, int, tuple[str, ...]]
        ] = {}
        for (start_word, cursor), (
            anchor_violations,
            inserted_controls,
            inserted_scrolls,
            score,
            chunks,
        ) in states.items():
            if template_segment:
                minimum_end = start_word + 1
                maximum_end = len(words) - remaining_active
                ends: range | tuple[int, ...] = range(
                    minimum_end, maximum_end + 1
                )
            else:
                ends = (start_word,)

            for end_word in ends:
                if end_word in forbidden_breaks:
                    continue
                chunk = (
                    " ".join(words[start_word:end_word])
                    if template_segment
                    else ""
                )
                if (
                    template_segment
                    and not any(
                        character.isalnum() for character in template_segment
                    )
                    and any(character.isalnum() for character in chunk)
                ):
                    continue
                try:
                    rendered, end_cursor, added_controls, added_scrolls = (
                        _layout_chunk_at_cursor(chunk, cursor)
                    )
                except ProductionTranslationError:
                    continue

                if segment_index < len(controls):
                    source_control = controls[segment_index]
                    overwrite_limit = OVERWRITE_REENTRY_LIMIT.get(
                        source_control
                    )
                    if (
                        overwrite_limit is not None
                        and end_cursor > overwrite_limit
                    ):
                        continue
                    next_cursor = _cursor_after_control(
                        end_cursor, source_control
                    )
                else:
                    next_cursor = end_cursor

                if template_segment:
                    start_char = prefix_chars[start_word]
                    end_char = prefix_chars[end_word]
                    segment_length = (
                        end_char - start_char - (1 if start_word else 0)
                    )
                    expected = (
                        len(template_segment) * text_total / target_total
                    )
                    boundary_penalty = (
                        _semantic_boundary_penalty(
                            template_segment, text, end_char
                        )
                        if end_word < len(words)
                        else 0
                    )
                    trial_score = score + int((segment_length - expected) ** 2)
                    trial_score += boundary_penalty
                else:
                    trial_score = score

                anchor_violation = 0
                control_semantic_ordinal = semantic_ordinal_by_control.get(
                    segment_index
                )
                if (
                    control_semantic_ordinal in anchored_semantic_ordinals
                    and end_word < len(words)
                    and not _is_strong_semantic_break(words, end_word)
                ):
                    anchor_violation = 1

                key = (end_word, next_cursor)
                trial = (
                    anchor_violations + anchor_violation,
                    inserted_controls + added_controls,
                    inserted_scrolls + added_scrolls,
                    trial_score,
                    (*chunks, rendered),
                )
                previous = next_states.get(key)
                if previous is None or trial < previous:
                    next_states[key] = trial

        states = next_states
        if not states:
            raise ProductionTranslationError(
                "cannot distribute reviewed English inside native "
                "semantic boundaries"
            )

    complete = [
        state
        for (word_index, _cursor), state in states.items()
        if word_index == len(words)
    ]
    if not complete:
        raise ProductionTranslationError(
            "cannot place all reviewed English inside the native text buffer"
        )
    return list(min(complete)[4])


def _layout_fixed_segments(
    segments: list[str], controls: list[int]
) -> list[str]:
    """Lay out explicitly controlled prose while enforcing re-entry barriers."""
    cursor = 0
    laid_out: list[str] = []
    for index, segment in enumerate(segments):
        rendered, cursor, _inserted_controls, _inserted_scrolls = (
            _layout_chunk_at_cursor(segment, cursor)
        )
        laid_out.append(rendered)
        if index < len(controls):
            source_control = controls[index]
            overwrite_limit = OVERWRITE_REENTRY_LIMIT.get(source_control)
            if overwrite_limit is not None and cursor > overwrite_limit:
                raise ProductionTranslationError(
                    f"source control {source_control} would overwrite staged prose "
                    f"at X=${cursor:02X}; must end by X=${overwrite_limit:02X}"
                )
            cursor = _cursor_after_control(cursor, source_control)
    return laid_out


def layout_review_text(record_id: str, reviewed: str, template: str) -> str:
    """Fit approved prose using greedy English geometry and native semantics."""
    reviewed = " ".join(reviewed.split())
    reviewed_controls = [int(value) for value in CONTROL_RE.findall(reviewed)]
    if reviewed_controls:
        template_segments, controls = _template_parts(template)
        if reviewed_controls != controls:
            raise ProductionTranslationError(
                f"{record_id}: reviewed control sequence differs from template"
            )
        reviewed_segments, _ = _template_parts(reviewed)
        laid_out = _layout_fixed_segments(reviewed_segments, controls)
    else:
        template_segments, controls = _semantic_template_parts(template)
        laid_out = _split_visible_text(
            reviewed,
            template_segments,
            controls,
            anchored_semantic_ordinals=_semantic_anchor_ordinals(template),
        )

    output = laid_out[0]
    for value, segment in zip(controls, laid_out[1:], strict=True):
        output += f"{{CTRL:{value}}}{segment}"

    try:
        validate_production_control_sequence(template, output)
        validate_renderer_buffer_layout(output)
    except ProductionTranslationError as error:
        raise ProductionTranslationError(f"{record_id}: {error}") from error
    if CONTROL_RE.sub(" ", output).split() != reviewed.split():
        raise ProductionTranslationError(
            f"{record_id}: layout changed reviewed prose"
        )
    return output


def merged_translation_map(
    bank_name: str,
    *,
    base_directory: Path,
    override_directory: Path | None = None,
    review_directory: Path | None = None,
) -> dict[str, str]:
    """Return one complete production map with ROM-wide English reflow.

    Editorial overrides choose the visible prose, but every scenario record is
    then re-laid out against the certified base record's native semantic-control
    topology. This keeps unchanged baseline lines from retaining obsolete
    Japanese-era spacing while preserving the exact selected English words.
    """
    base = _load_string_map(
        base_directory / f"{bank_name}.json",
        label=f"{bank_name} base translation",
    )
    selected = dict(base)

    if review_directory is not None:
        review = _review_map(bank_name, review_directory)
        unknown = sorted(set(review) - set(base))
        if unknown:
            raise ProductionTranslationError(
                f"{bank_name} production review contains unknown IDs: "
                f"{unknown[:3]}"
            )
        selected.update(review)

    # Explicit overrides are the final editorial layer. Keeping this narrow
    # hook permits a reviewed last-mile correction without creating another
    # translation or build pipeline.
    if override_directory is not None:
        override_path = override_directory / f"{bank_name}.json"
        if override_path.exists():
            overrides = _load_string_map(
                override_path,
                label=f"{bank_name} production override",
            )
            unknown = sorted(set(overrides) - set(base))
            if unknown:
                raise ProductionTranslationError(
                    f"{bank_name} production overrides contain unknown IDs: "
                    f"{unknown[:3]}"
                )
            selected.update(overrides)

    laid_out: dict[str, str] = {}
    for record_id, selected_text in selected.items():
        prose = " ".join(CONTROL_RE.sub(" ", selected_text).split())
        laid_out[record_id] = layout_review_text(
            record_id,
            prose,
            base[record_id],
        )
    return laid_out


def materialize_production_maps(
    bank_names: tuple[str, ...],
    *,
    base_directory: Path,
    override_directory: Path | None,
    review_directory: Path | None,
    output_directory: Path,
) -> dict[str, int]:
    """Write deterministic complete translation maps for a production build."""
    output_directory.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for bank_name in bank_names:
        merged = merged_translation_map(
            bank_name,
            base_directory=base_directory,
            override_directory=override_directory,
            review_directory=review_directory,
        )
        path = output_directory / f"{bank_name}.json"
        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        counts[bank_name] = len(merged)
    return counts
