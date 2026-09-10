"""Materialize the production-localization layer over reviewed base maps.

The maintained ``work/translations`` files remain the last certified playable
baseline. Production builds layer the reviewed retranslation over that base,
then automatically restore the source control topology and native 24-column
word wrapping. Editorial prose therefore remains authoritative while the
integration layer owns presentation syntax.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONTROL_RE = re.compile(r"\{CTRL:([0-7])\}")
DISPLAY_COLUMNS = 24

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
        raise ProductionTranslationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise ProductionTranslationError(f"{label} must be a JSON object: {path}")
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


def _word_wrap_segment(text: str, *, columns: int = DISPLAY_COLUMNS) -> str:
    """Pad native automatic rows while keeping every word visibly separated.

    The renderer advances automatically after ``columns`` visible cells. A
    nonfinal row must therefore end with at least one blank tile: otherwise a
    word ending exactly in column 24 becomes byte-adjacent to the first word on
    the next row (for example ``men'ssweat``) even though the screen wraps it.
    Final rows may use the full width because no following word needs a
    separator. No new control code is invented.
    """
    if not text:
        return ""
    words = text.split(" ")
    if any(len(word) > columns for word in words):
        longest = max(words, key=len)
        raise ProductionTranslationError(
            f"word {longest!r} exceeds the {columns}-column renderer"
        )

    rows: list[str] = []
    remaining = list(words)
    while remaining:
        final_text = " ".join(remaining)
        if len(final_text) <= columns:
            rows.append(final_text)
            break

        current = remaining.pop(0)
        if len(current) >= columns:
            raise ProductionTranslationError(
                f"word {current!r} leaves no padding cell before an automatic wrap"
            )
        while remaining:
            candidate = f"{current} {remaining[0]}"
            if len(candidate) > columns - 1:
                break
            current = candidate
            remaining.pop(0)
        rows.append(current.ljust(columns))

    return "".join(rows)


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


def _split_visible_text(text: str, template_segments: list[str]) -> list[str]:
    """Split polished prose across the template's nonempty control slots.

    Empty template slots remain empty because leading or adjacent controls can
    carry scene semantics. Nonempty slots receive contiguous polished words.
    Dynamic programming minimizes deviation from the template's relative text
    distribution while preferring punctuation boundaries.
    """
    active = [index for index, segment in enumerate(template_segments) if segment]
    if not active:
        if text:
            raise ProductionTranslationError(
                "template has no visible segment for reviewed English"
            )
        return ["" for _ in template_segments]
    if len(active) == 1:
        result = ["" for _ in template_segments]
        result[active[0]] = text
        return result

    words = text.split(" ")
    if len(words) < len(active):
        raise ProductionTranslationError(
            "reviewed English has fewer words than nonempty control slots"
        )

    target_lengths = [max(1, len(template_segments[index])) for index in active]
    target_total = sum(target_lengths)
    text_total = max(1, len(text))
    prefix_chars = [0]
    for word_index, word in enumerate(words):
        added = len(word) + (1 if word_index else 0)
        prefix_chars.append(prefix_chars[-1] + added)

    states: dict[int, tuple[int, tuple[int, ...]]] = {0: (0, ())}
    for slot_index, target in enumerate(target_lengths[:-1]):
        remaining_slots = len(target_lengths) - slot_index - 1
        next_states: dict[int, tuple[int, tuple[int, ...]]] = {}
        for start_word, (score, breaks) in states.items():
            minimum_end = start_word + 1
            maximum_end = len(words) - remaining_slots
            for end_word in range(minimum_end, maximum_end + 1):
                start_char = prefix_chars[start_word]
                end_char = prefix_chars[end_word]
                segment_length = end_char - start_char
                if start_word:
                    segment_length -= 1
                expected = target * text_total / target_total
                boundary_position = end_char
                boundary_penalty = _break_score(text, boundary_position)
                trial_score = score + int((segment_length - expected) ** 2)
                trial_score += boundary_penalty * 32
                previous = next_states.get(end_word)
                trial = (trial_score, (*breaks, end_word))
                if previous is None or trial < previous:
                    next_states[end_word] = trial
        states = next_states
        if not states:
            raise ProductionTranslationError("cannot distribute reviewed English")

    _, (_, breaks) = min(states.items(), key=lambda item: item[1])
    all_breaks = (*breaks, len(words))
    chunks: list[str] = []
    start = 0
    for end in all_breaks:
        chunks.append(" ".join(words[start:end]))
        start = end
    if start != len(words) or len(chunks) != len(active):
        raise ProductionTranslationError("internal production-layout mismatch")

    result = ["" for _ in template_segments]
    for index, chunk in zip(active, chunks, strict=True):
        result[index] = chunk
    return result


def layout_review_text(record_id: str, reviewed: str, template: str) -> str:
    """Restore exact control topology and safe automatic wrapping to prose."""
    reviewed = " ".join(reviewed.split())
    template_segments, controls = _template_parts(template)
    reviewed_controls = [int(value) for value in CONTROL_RE.findall(reviewed)]
    if reviewed_controls:
        if reviewed_controls != controls:
            raise ProductionTranslationError(
                f"{record_id}: reviewed control sequence differs from template"
            )
        reviewed_segments, _ = _template_parts(reviewed)
        laid_out = [_word_wrap_segment(segment) for segment in reviewed_segments]
    else:
        raw_segments = _split_visible_text(reviewed, template_segments)
        laid_out = [_word_wrap_segment(segment) for segment in raw_segments]

    output = laid_out[0]
    for value, segment in zip(controls, laid_out[1:], strict=True):
        output += f"{{CTRL:{value}}}{segment}"
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
