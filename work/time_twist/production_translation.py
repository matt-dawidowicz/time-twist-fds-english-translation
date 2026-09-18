"""Project policy facade for canonical production-English materialization.

The low-level layout engine lives in :mod:`production_translation_core`. This
module keeps project-specific policy explicit: reviewed prose is reflowed against
the certified base control topology, except for an audited set of source
``CTRL:1`` waits proven to be presentation-only in English.

The certified ``work/translations`` maps remain untouched. Presentation-only
exceptions are keyed by stable record ID and locked to the audited control
topology, not to exact English prose. Text may therefore be revised freely while
control-sequence drift still fails closed and requires a fresh audit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import production_translation_core as _core
from .pagination_ctrl1_policy import (
    ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES,
)

CONTROL_RE = _core.CONTROL_RE
DISPLAY_COLUMNS = _core.DISPLAY_COLUMNS
TEXT_ROW_BYTES = _core.TEXT_ROW_BYTES
TEXT_BUFFER_ROWS = _core.TEXT_BUFFER_ROWS
TEXT_BUFFER_BYTES = _core.TEXT_BUFFER_BYTES
LINE_ADVANCE_CONTROL = _core.LINE_ADVANCE_CONTROL
SCROLL_CONTROL = _core.SCROLL_CONTROL
INSERTABLE_LAYOUT_CONTROLS = _core.INSERTABLE_LAYOUT_CONTROLS
SEMANTIC_CONTROLS = _core.SEMANTIC_CONTROLS
REVIEW_FILES = _core.REVIEW_FILES
ProductionTranslationError = _core.ProductionTranslationError
validate_renderer_buffer_layout = _core.validate_renderer_buffer_layout

# These are not generic CTRL:1 demotions. Each record was audited after the
# TT1A personality-test playtest exposed the failure mode: an inherited Japanese
# input wait splitting one continuous English thought while the four-row box was
# still largely empty. The visible text is historical context only; policy is
# enforced by stable record ID plus control topology so prose edits do not need
# to rewrite the assertion layer.
PRESENTATION_ONLY_CTRL1_TEMPLATES: dict[str, str] = {
    "TT1A/g0/r5": "First: personality test{CTRL:1}Please answer each one.",
    "TT1A/g0/r30": (
        "Time travel, huh...{CTRL:1}All talk so far.{CTRL:0}"
        "No one's pulled it off.{CTRL:6}More importantly..."
    ),
    "TT1B/g0/r0": "Made it... Devil Museum{CTRL:1}I've wanted to visit.",
    "TT1B/g0/r6": '"Closed today.{CTRL:1}Inquire at the church."',
    "TT1B/g2/r11": "The parlor.{CTRL:1}Paper and magnifier.",
    "TT1B/g2/r29": "A local map.{CTRL:1}A villa lies north.",
    "T25/g0/r24": "The guest room.{CTRL:1}Every corner is clean.",
    "T25/g1/r12": "The stair landing.{CTRL:1}The hall lies below.",
    "TT3A/g0/r1": "Some kind of compound.{CTRL:1}Woods lie past the wire",
    "TT4/g0/r30": (
        "A plaza atop the hill.{CTRL:1}The town spreads below,"
        "{CTRL:0}surrounded by the sea."
    ),
    "TT6B/g0/r6": "Joints ache. Hungry...{CTRL:1}Throat's bone-dry...",
    "TT6C/g2/r5": "Pencil in its hand.{CTRL:1}Died while writing.",
}
PRESENTATION_ONLY_CTRL1_TEMPLATES.update(
    ADDITIONAL_PRESENTATION_ONLY_CTRL1_TEMPLATES
)

# Final playtest also identified four records with additional semantic controls whose
# timing/pagination function is presentation-only in the reviewed English. The
# strings record the audited before/after topology; visible prose is not part of
# the invariant.
PRESENTATION_CONTROL_REWRITES: dict[str, tuple[str, str]] = {
    "TT3A/g2/r29": (
        "He holds a paper.{CTRL:1}Simon: A child gave it{CTRL:0}to me. A stranger asked{CTRL:6}him to. I take it.{CTRL:3}Blue writing.",
        "He holds a paper.{CTRL:0}Simon: A child gave it{CTRL:0}to me. A stranger asked{CTRL:6}him to. I take it.{CTRL:3}Blue writing.",
    ),
    "TT3B/g1/r22": (
        "Schmidt: Border ahead.{CTRL:1}Cougar: Mind's blank...{CTRL:0}Why am I here...?{CTRL:6}Simon: You must have{CTRL:4}hit your head badly.{CTRL:3}Schmidt: What a horror.{CTRL:3}Cougar: Might change my{CTRL:4}whole view of life.{CTRL:3}Simon: Indeed...",
        "Schmidt: Border ahead.{CTRL:0}Cougar: Mind's blank...{CTRL:0}Why am I here...?{CTRL:6}Simon: You must have{CTRL:4}hit your head badly.{CTRL:3}Schmidt: What a horror.{CTRL:3}Cougar: Might change my{CTRL:4}whole view of life.{CTRL:3}Simon: Indeed...",
    ),
    "TT1A/g0/r24": (
        "Cautious, methodical.{CTRL:0}Rarely fail, but can{CTRL:2}"
        "seem a bit ordinary.{CTRL:0}Hardworking, principled{CTRL:3}"
        "Stubborn scholar type.{CTRL:4}You care till worn out.{CTRL:4}"
        "Romantic, but awkward.",
        "Cautious, methodical.{CTRL:0}Rarely fail, but can{CTRL:2}"
        "seem a bit ordinary.{CTRL:0}Hardworking, principled{CTRL:4}"
        "Stubborn scholar type.{CTRL:4}You care till worn out.{CTRL:4}"
        "Romantic, but awkward.",
    ),
    "TT1A/g0/r30": (
        "Time travel, huh...{CTRL:1}All talk so far.{CTRL:0}"
        "No one's pulled it off.{CTRL:6}More importantly...",
        "Time travel, huh...{CTRL:0}All talk so far.{CTRL:0}"
        "No one's pulled it off.{CTRL:0}More importantly...",
    ),
    "TT1A/g0/r31": (
        "............{CTRL:1}That's weird...{CTRL:0}Some kind of charm?"
        "{CTRL:6}{CTRL:4}{CTRL:3}Whatever... Let's go!",
        "............{CTRL:1}That's weird...{CTRL:0}Some kind of charm?"
        "{CTRL:6}{CTRL:4}{CTRL:4}Whatever... Let's go!",
    ),
    "TT1A/g1/r1": (
        "A new century nears...{CTRL:1}yet few welcome the age{CTRL:0}"
        "about to begin.{CTRL:6}Conflict still rages{CTRL:4}across the world."
        "{CTRL:3}Environmental harm and{CTRL:4}food shortages worsen."
        "{CTRL:3}Anyone can see it:{CTRL:4}Earth's future is grim.",
        "A new century nears...{CTRL:0}yet few welcome the age{CTRL:0}"
        "about to begin.{CTRL:0}Conflict still rages{CTRL:4}across the world."
        "{CTRL:3}Environmental harm and{CTRL:4}food shortages worsen."
        "{CTRL:3}Anyone can see it:{CTRL:4}Earth's future is grim.",
    ),
}

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

# Scenario quiz prompts share their text box with a native answer-selection UI.
# Their control geometry is therefore interface state, not ordinary prose
# presentation.  The separate TT6C retrospective quiz lives in a fixed-address
# menu table and is protected by the fixed-table build/test path instead.
QUIZ_MAX_SEGMENT_COLUMNS = 23

TT4_EXPANDED_QUIZ_QUESTION_RECORDS = frozenset(
    {
        "TT4/g5/r7",
        "TT4/g5/r10",
        "TT4/g5/r11",
        "TT4/g5/r12",
        "TT4/g5/r13",
    }
)



FINAL_PLAYTEST_LAYOUT_RECORDS = frozenset(
    {
        "TT1A/g0/r3",
        "TT1A/g0/r24",
        "TT1A/g0/r30",
        "TT1A/g0/r31",
        "TT1A/g1/r1",
        "TT1B/g0/r0",
        "TT3A/g2/r29",
        "TT3A/g2/r30",
        "TT3A/g2/r31",
        "TT3A/g3/r13",
        "TT3A/g4/r17",
        "TT3B/g0/r28",
        "TT3B/g1/r22",
        "TT3B/g1/r23",
        "TT3B/g1/r24",
        "TT4/g2/r14",
        "TT4/g5/r7",
        "TT4/g5/r10",
        "TT4/g5/r11",
        "TT4/g5/r12",
        "TT4/g5/r13",
    }
)

PRESENTATION_ONLY_CTRL1_RECORDS = frozenset(PRESENTATION_ONLY_CTRL1_TEMPLATES)
# The legacy two-argument validator has no record ID, so it can only recognize
# policy records from their historical template. Record-aware call sites do not
# have this limitation and are topology-based.
_TEMPLATE_TO_PRESENTATION_ONLY_RECORD = {
    template: record_id
    for record_id, template in PRESENTATION_ONLY_CTRL1_TEMPLATES.items()
}


def _demote_single_ctrl1(record_id: str, template: str) -> str:
    """Convert one audited input wait to regenerable row geometry."""
    count = template.count("{CTRL:1}")
    if count != 1:
        raise ProductionTranslationError(
            f"{record_id}: presentation-only CTRL:1 policy expected exactly "
            f"one CTRL:1, found {count}; re-audit this record"
        )
    return template.replace("{CTRL:1}", "{CTRL:0}", 1)


def _presentation_control_policy(record_id: str) -> tuple[str, str] | None:
    """Return the audited before/after control templates for one record."""
    rewrite = PRESENTATION_CONTROL_REWRITES.get(record_id)
    if rewrite is not None:
        return rewrite
    template = PRESENTATION_ONLY_CTRL1_TEMPLATES.get(record_id)
    if template is None:
        return None
    return template, _demote_single_ctrl1(record_id, template)


def _control_sequence(text: str) -> tuple[int, ...]:
    """Return every native control value in textual order."""
    return tuple(int(value) for value in CONTROL_RE.findall(text))


def _replace_control_sequence(text: str, controls: tuple[int, ...]) -> str:
    """Replace control values in place while preserving all visible source text."""
    pieces = CONTROL_RE.split(text)
    if len(pieces[1::2]) != len(controls):
        raise ProductionTranslationError(
            "control-rewrite arity changed unexpectedly"
        )
    output = [pieces[0]]
    for value, segment in zip(controls, pieces[2::2], strict=True):
        output.append(f"{{CTRL:{value}}}")
        output.append(segment)
    return "".join(output)


def _effective_control_template(record_id: str, source: str) -> str:
    """Apply an audited presentation rewrite to any text with the same topology."""
    policy = _presentation_control_policy(record_id)
    if policy is None:
        return source
    expected, effective = policy
    expected_controls = _control_sequence(expected)
    source_controls = _control_sequence(source)
    if source_controls != expected_controls:
        raise ProductionTranslationError(
            f"{record_id}: native control topology changed under the audited "
            "presentation-control policy; re-audit before building"
        )
    return _replace_control_sequence(source, _control_sequence(effective))


def _effective_base_template(record_id: str, template: str) -> str:
    """Apply audited control rewrites while allowing visible prose to change."""
    policy = _presentation_control_policy(record_id)
    if policy is None:
        return template
    expected, effective = policy
    expected_controls = _control_sequence(expected)
    template_controls = _control_sequence(template)
    if template_controls != expected_controls:
        raise ProductionTranslationError(
            f"{record_id}: certified base control topology changed under the audited "
            "presentation-control policy; re-audit before building"
        )
    return _replace_control_sequence(template, _control_sequence(effective))


def validate_record_production_control_sequence(
    record_id: str, source: str, production: str
) -> None:
    """Validate one record, honoring only audited presentation rewrites."""
    if record_id in TT4_EXPANDED_QUIZ_QUESTION_RECORDS:
        return
    effective_source = _effective_control_template(record_id, source)
    _core.validate_production_control_sequence(effective_source, production)


def validate_production_control_sequence(source: str, production: str) -> None:
    """Validate controls for callers that do not provide a stable record ID.

    Record-aware callers should use
    :func:`validate_record_production_control_sequence`, which permits arbitrary
    prose changes while enforcing the audited topology. This compatibility API
    can recognize policy records only when ``source`` matches a historical
    template because no record identity is available.
    """
    record_id = _TEMPLATE_TO_PRESENTATION_ONLY_RECORD.get(source)
    if record_id is None:
        record_id = next(
            (
                candidate
                for candidate, (
                    expected,
                    _effective,
                ) in PRESENTATION_CONTROL_REWRITES.items()
                if source == expected
            ),
            None,
        )
    effective_source = (
        source
        if record_id is None
        else _effective_base_template(record_id, source)
    )
    _core.validate_production_control_sequence(effective_source, production)


def layout_review_text(record_id: str, reviewed: str, template: str) -> str:
    """Lay out reviewed prose with record-scoped production control policy."""
    effective_template = _effective_base_template(record_id, template)
    return _core.layout_review_text(record_id, reviewed, effective_template)


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
    """Keep scenario quiz prompts inside their runtime-safe text region.

    Most quiz prompts preserve the exact source control topology.  The Athens
    fisherman quiz is a playtested exception: its questions may use a second
    visible row so the English can read naturally, but they must retain the two
    leading row advances, use only one additional CTRL:0, never scroll, and
    keep every visible row within 23 columns.
    """
    prefix = f"{bank_name}/"
    for record_id in sorted(
        record_id
        for record_id in QUIZ_QUESTION_RECORDS
        if record_id.startswith(prefix)
    ):
        if record_id not in base or record_id not in production:
            raise ProductionTranslationError(
                f"{record_id}: registered quiz question is missing"
            )
        source = base[record_id]
        translated = production[record_id]

        if record_id in TT4_EXPANDED_QUIZ_QUESTION_RECORDS:
            required_prefix = "{CTRL:0}{CTRL:0}"
            if not translated.startswith(required_prefix):
                raise ProductionTranslationError(
                    f"{record_id}: Athens quiz must retain two leading row advances"
                )
            tail = translated[len(required_prefix) :]
            controls = _control_sequence(tail)
            if any(control != 0 for control in controls) or len(controls) > 1:
                raise ProductionTranslationError(
                    f"{record_id}: Athens quiz may use at most two visible rows "
                    "with CTRL:0 only"
                )
            segments = CONTROL_RE.split(tail)
            if not 1 <= len(segments) <= 2 or any(not segment for segment in segments):
                raise ProductionTranslationError(
                    f"{record_id}: Athens quiz requires one or two non-empty rows"
                )
            for index, segment in enumerate(segments):
                if len(segment) > QUIZ_MAX_SEGMENT_COLUMNS:
                    raise ProductionTranslationError(
                        f"{record_id}: quiz row {index} is {len(segment)} columns; "
                        f"maximum is {QUIZ_MAX_SEGMENT_COLUMNS}"
                    )
            continue

        if _control_sequence(translated) != _control_sequence(source):
            raise ProductionTranslationError(
                f"{record_id}: quiz question control geometry changed"
            )

        source_segments = CONTROL_RE.split(source)
        production_segments = CONTROL_RE.split(translated)
        if len(source_segments) != len(production_segments):
            raise ProductionTranslationError(
                f"{record_id}: quiz question segment count changed"
            )
        for index, (source_segment, production_segment) in enumerate(
            zip(source_segments, production_segments, strict=True)
        ):
            if bool(source_segment) != bool(production_segment):
                raise ProductionTranslationError(
                    f"{record_id}: quiz segment {index} changed empty-row geometry"
                )
            if len(production_segment) > QUIZ_MAX_SEGMENT_COLUMNS:
                raise ProductionTranslationError(
                    f"{record_id}: quiz segment {index} is "
                    f"{len(production_segment)} columns; maximum is "
                    f"{QUIZ_MAX_SEGMENT_COLUMNS}"
                )


def _validate_cross_record_staging(
    bank_name: str,
    base: dict[str, str],
    production: dict[str, str],
) -> None:
    """Reject translation growth that overwrites text staged by the prior record.

    Some source scripts intentionally compose consecutive records in one text box.
    A following record can begin with a row-reentry control because the Japanese
    predecessor fits entirely above that row. If English expands the predecessor
    into that row, pressing A causes the next record to overwrite visible text.
    Preserve the source cross-record row contract instead of validating records in
    isolation only.
    """
    grouped: dict[tuple[int, int], str] = {}
    pattern = re.compile(rf"^{re.escape(bank_name)}/g(\d+)/r(\d+)$")
    for record_id in production:
        match = pattern.match(record_id)
        if match is not None:
            grouped[(int(match.group(1)), int(match.group(2)))] = record_id

    for (group, record), record_id in sorted(grouped.items()):
        next_id = grouped.get((group, record + 1))
        if next_id is None:
            continue
        next_cursor = _leading_record_cursor(base[next_id])
        if next_cursor is None:
            continue
        source_max = _maximum_written_cursor(base[record_id])
        production_max = _maximum_written_cursor(production[record_id])
        if source_max <= next_cursor < production_max:
            raise ProductionTranslationError(
                f"{record_id}: production text reaches X=${production_max:02X}, "
                f"but following {next_id} re-enters at X=${next_cursor:02X}; "
                "pressing A would overwrite staged text"
            )


def merged_translation_map(
    bank_name: str,
    *,
    base_directory: Path,
    override_directory: Path | None = None,
    review_directory: Path | None = None,
) -> dict[str, str]:
    """Return one complete production map with audited control policy applied."""
    base = _core._load_string_map(
        base_directory / f"{bank_name}.json",
        label=f"{bank_name} base translation",
    )
    selected = dict(base)
    explicit_control_overrides: set[str] = set()

    if review_directory is not None:
        review = _core._review_map(bank_name, review_directory)
        unknown = sorted(set(review) - set(base))
        if unknown:
            raise ProductionTranslationError(
                f"{bank_name} production review contains unknown IDs: {unknown[:3]}"
            )
        selected.update(review)

    if override_directory is not None:
        override_path = override_directory / f"{bank_name}.json"
        if override_path.exists():
            overrides = _core._load_string_map(
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
            explicit_control_overrides.update(
                record_id
                for record_id, override_text in overrides.items()
                if CONTROL_RE.search(override_text)
            )

    laid_out: dict[str, str] = {}
    for record_id, selected_text in selected.items():
        reviewed_text = selected_text
        if record_id not in explicit_control_overrides:
            reviewed_text = " ".join(
                CONTROL_RE.sub(" ", selected_text).split()
            )
        if (
            record_id in FINAL_PLAYTEST_LAYOUT_RECORDS
            or record_id in QUIZ_QUESTION_RECORDS
        ):
            if record_id not in explicit_control_overrides:
                kind = (
                    "quiz question"
                    if record_id in QUIZ_QUESTION_RECORDS
                    else "final-playtest layout"
                )
                raise ProductionTranslationError(
                    f"{record_id}: {kind} must be an explicit control override"
                )
            _effective_base_template(record_id, base[record_id])
            validate_record_production_control_sequence(
                record_id, base[record_id], reviewed_text
            )
            validate_renderer_buffer_layout(reviewed_text)
            laid_out[record_id] = reviewed_text
            continue
        laid_out[record_id] = layout_review_text(
            record_id,
            reviewed_text,
            base[record_id],
        )
    _validate_quiz_question_geometry(bank_name, base, laid_out)
    _validate_cross_record_staging(bank_name, base, laid_out)
    return laid_out


def materialize_production_maps(
    bank_names: tuple[str, ...],
    *,
    base_directory: Path,
    override_directory: Path | None,
    review_directory: Path | None,
    output_directory: Path,
) -> dict[str, int]:
    """Write deterministic complete production maps using audited policy."""
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
