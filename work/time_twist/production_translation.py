"""Materialize the production-localization layer over reviewed base maps.

The maintained ``work/translations`` files remain the last certified playable
baseline. Production builds layer the reviewed retranslation over that base,
then adapt it to the native 24-column, four-row text buffer. Source controls
remain in order, while control 0 may be inserted for native row advances and control 4 may be
inserted as the native one-row scroll continuation when approved prose needs
more display space. Editorial prose
therefore remains authoritative while the integration layer owns presentation
syntax.
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


def _wrapped_rows(
    text: str, *, columns: int = DISPLAY_COLUMNS
) -> tuple[str, ...]:
    """Wrap prose at word boundaries without relying on implicit row overflow.

    NOV2 stores four contiguous 24-glyph rows, but merely letting the output
    index cross a 24-glyph boundary does not update the renderer's row-state
    variables. Every physical row transition must therefore be represented by
    an explicit native control in the encoded stream. This helper only chooses
    the visible words for each row; :func:`_layout_chunk_at_cursor` inserts the
    required controls.
    """
    if not text:
        return ()
    words = text.split(" ")
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
            continue
        rows.append(current)
        current = word
    rows.append(current)
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
            cursor = _cursor_after_control(cursor, controls[index])


def validate_production_control_sequence(source: str, production: str) -> None:
    """Preserve source controls while allowing only native row/scroll insertions."""
    _source_segments, source_controls = _template_parts(source)
    _production_segments, production_controls = _template_parts(production)

    # A greedy subsequence check is insufficient because source controls 0 and
    # 4 are themselves also legal layout insertions. Track every possible count
    # of source controls consumed so an inserted 0/4 cannot accidentally steal
    # the identity of a later source control with the same value.
    states = {0}
    for control in production_controls:
        next_states: set[int] = set()
        for source_index in states:
            if (
                source_index < len(source_controls)
                and control == source_controls[source_index]
            ):
                next_states.add(source_index + 1)
            if control in INSERTABLE_LAYOUT_CONTROLS:
                next_states.add(source_index)
        if not next_states:
            raise ProductionTranslationError(
                f"production layout introduced non-layout control {control}"
            )
        states = next_states

    if len(source_controls) not in states:
        raise ProductionTranslationError(
            "production layout lost or reordered one or more source controls"
        )


def _layout_chunk_at_cursor(text: str, cursor: int) -> tuple[str, int, int]:
    """Lay out prose with explicit native row advances and row-four scrolling."""
    if not text:
        return "", cursor, 0

    output: list[str] = []
    inserted_scrolls = 0
    rows = _wrapped_rows(text)
    for row_index, row in enumerate(rows):
        row_end = _row_end_for_cursor(cursor)
        remaining_cells = (row_end - cursor) // 2
        if len(row) > remaining_cells:
            # Segment boundaries normally begin at row starts. If a reviewed
            # chunk reaches a partially used row, advance using the same native
            # line/scroll rule rather than crossing the boundary implicitly.
            if cursor < TEXT_ROW_BYTES * (TEXT_BUFFER_ROWS - 1):
                output.append(f"{{CTRL:{LINE_ADVANCE_CONTROL}}}")
                cursor = _cursor_after_control(cursor, LINE_ADVANCE_CONTROL)
            else:
                output.append(f"{{CTRL:{SCROLL_CONTROL}}}")
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

        if cursor < TEXT_ROW_BYTES * (TEXT_BUFFER_ROWS - 1):
            output.append(f"{{CTRL:{LINE_ADVANCE_CONTROL}}}")
            cursor = _cursor_after_control(cursor, LINE_ADVANCE_CONTROL)
        else:
            output.append(f"{{CTRL:{SCROLL_CONTROL}}}")
            inserted_scrolls += 1
            cursor = CONTROL_REENTRY_CURSOR[SCROLL_CONTROL]

    return "".join(output), cursor, inserted_scrolls


def _split_visible_text(
    text: str,
    template_segments: list[str],
    controls: list[int],
) -> list[str]:
    """Distribute prose across source controls without overrunning the renderer.

    Empty source slots remain empty because adjacent controls can carry scene
    semantics. Dynamic programming moves only word boundaries, minimizes added
    control-4 scrolls first, then stays close to the source segment proportions
    and prefers punctuation boundaries. Every candidate is simulated against
    NOV2's four-row staging-buffer cursor before it can be selected.
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
            "reviewed English has fewer words than nonempty control slots"
        )

    target_total = sum(
        max(1, len(template_segments[index])) for index in active
    )
    text_total = max(1, len(text))
    prefix_chars = [0]
    for word_index, word in enumerate(words):
        prefix_chars.append(
            prefix_chars[-1] + len(word) + (1 if word_index else 0)
        )

    # (next word, decoder cursor) -> (inserted scrolls, editorial score, chunks)
    states: dict[tuple[int, int], tuple[int, int, tuple[str, ...]]] = {
        (0, 0): (0, 0, ())
    }
    for segment_index, template_segment in enumerate(template_segments):
        remaining_active = sum(
            1 for segment in template_segments[segment_index + 1 :] if segment
        )
        next_states: dict[
            tuple[int, int], tuple[int, int, tuple[str, ...]]
        ] = {}
        for (start_word, cursor), (
            inserted,
            score,
            chunks,
        ) in states.items():
            if template_segment:
                minimum_end = start_word + 1
                maximum_end = len(words) - remaining_active
                ends = range(minimum_end, maximum_end + 1)
            else:
                ends = (start_word,)

            for end_word in ends:
                chunk = (
                    " ".join(words[start_word:end_word])
                    if template_segment
                    else ""
                )
                try:
                    rendered, end_cursor, added_scrolls = (
                        _layout_chunk_at_cursor(
                            chunk,
                            cursor,
                        )
                    )
                except ProductionTranslationError:
                    continue

                if segment_index < len(controls):
                    next_cursor = _cursor_after_control(
                        end_cursor,
                        controls[segment_index],
                    )
                else:
                    next_cursor = end_cursor

                if template_segment:
                    start_char = prefix_chars[start_word]
                    end_char = prefix_chars[end_word]
                    segment_length = end_char - start_char
                    if start_word:
                        segment_length -= 1
                    expected = (
                        len(template_segment) * text_total / target_total
                    )
                    boundary_penalty = (
                        _break_score(text, end_char)
                        if end_word < len(words)
                        else 0
                    )
                    wrap_penalty = max(0, len(_wrapped_rows(chunk)) - 1) * 8
                    trial_score = score + int((segment_length - expected) ** 2)
                    trial_score += boundary_penalty * 32 + wrap_penalty
                else:
                    trial_score = score

                key = (end_word, next_cursor)
                trial = (
                    inserted + added_scrolls,
                    trial_score,
                    (*chunks, rendered),
                )
                previous = next_states.get(key)
                if previous is None or trial < previous:
                    next_states[key] = trial

        states = next_states
        if not states:
            raise ProductionTranslationError(
                "cannot distribute reviewed English inside the native text buffer"
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
    return list(min(complete)[2])


def _layout_fixed_segments(
    segments: list[str], controls: list[int]
) -> list[str]:
    """Add native row/scroll controls to explicitly pre-segmented reviewed prose."""
    cursor = 0
    laid_out: list[str] = []
    for index, segment in enumerate(segments):
        rendered, cursor, _inserted = _layout_chunk_at_cursor(segment, cursor)
        laid_out.append(rendered)
        if index < len(controls):
            cursor = _cursor_after_control(cursor, controls[index])
    return laid_out


def layout_review_text(record_id: str, reviewed: str, template: str) -> str:
    """Fit approved prose to NOV2 while preserving source-control semantics."""
    reviewed = " ".join(reviewed.split())
    template_segments, controls = _template_parts(template)
    reviewed_controls = [int(value) for value in CONTROL_RE.findall(reviewed)]
    if reviewed_controls:
        if reviewed_controls != controls:
            raise ProductionTranslationError(
                f"{record_id}: reviewed control sequence differs from template"
            )
        reviewed_segments, _ = _template_parts(reviewed)
        laid_out = _layout_fixed_segments(reviewed_segments, controls)
    else:
        laid_out = _split_visible_text(reviewed, template_segments, controls)

    output = laid_out[0]
    for value, segment in zip(controls, laid_out[1:], strict=True):
        output += f"{{CTRL:{value}}}{segment}"

    try:
        validate_production_control_sequence(template, output)
        validate_renderer_buffer_layout(output)
    except ProductionTranslationError as error:
        raise ProductionTranslationError(f"{record_id}: {error}") from error
    return output


def merged_translation_map(
    bank_name: str,
    *,
    base_directory: Path,
    override_directory: Path | None = None,
    review_directory: Path | None = None,
) -> dict[str, str]:
    """Return one complete production map with source-safe stable IDs.

    Preexisting production overrides remain supported for compatibility, but
    the reviewed editorial layer has final precedence. Review prose is laid
    out against each base record so its ordered control values are preserved.
    """
    base = _load_string_map(
        base_directory / f"{bank_name}.json",
        label=f"{bank_name} base translation",
    )
    merged = dict(base)

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
            merged.update(overrides)

    if review_directory is not None:
        review = _review_map(bank_name, review_directory)
        unknown = sorted(set(review) - set(base))
        if unknown:
            raise ProductionTranslationError(
                f"{bank_name} production review contains unknown IDs: {unknown[:3]}"
            )
        for record_id, reviewed in review.items():
            merged[record_id] = layout_review_text(
                record_id,
                reviewed,
                base[record_id],
            )
    return merged


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
