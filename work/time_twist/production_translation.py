"""Project policy facade for canonical production-English materialization.

The low-level layout engine lives in :mod:`production_translation_core`.  This
module keeps project-specific policy explicit: reviewed prose is reflowed against
the certified base control topology, except for an audited set of source
``CTRL:1`` waits proven to be presentation-only in English.

The certified ``work/translations`` maps remain untouched.  Every presentation-
only exception is keyed by stable record ID and locked to the exact base template
that was reviewed, so a later source/template change fails closed and requires a
fresh audit rather than silently inheriting the exception.
"""

from __future__ import annotations

import json
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
# still largely empty. The exact certified base template is part of the policy
# so topology drift cannot silently broaden the exception.
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
# timing/pagination function is presentation-only in the reviewed English.
# Each rewrite is locked to the exact certified base record and replaces only
# the audited control token(s); prose and all other controls remain source-owned.
PRESENTATION_CONTROL_REWRITES: dict[str, tuple[str, str]] = {
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

FINAL_PLAYTEST_LAYOUT_RECORDS = frozenset(
    {
        "TT1A/g0/r3",
        "TT1A/g0/r24",
        "TT1A/g0/r30",
        "TT1A/g0/r31",
        "TT1A/g1/r1",
        "TT1B/g0/r0",
    }
)

PRESENTATION_ONLY_CTRL1_RECORDS = frozenset(PRESENTATION_ONLY_CTRL1_TEMPLATES)
# Some source records share the same exact certified template. If every such record
# has the same source-locked demotion policy, the legacy two-argument validator may
# safely use either representative because the effective control sequence is identical.
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
    """Return the exact base/effective templates for one audited record."""
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
    """Return the audited production template without mutating certified base data."""
    policy = _presentation_control_policy(record_id)
    if policy is None:
        return template
    expected, effective = policy
    if template != expected:
        raise ProductionTranslationError(
            f"{record_id}: certified base template changed under the audited "
            "presentation-control policy; re-audit before building"
        )
    return effective


def validate_record_production_control_sequence(
    record_id: str, source: str, production: str
) -> None:
    """Validate one record, honoring only audited presentation rewrites."""
    effective_source = _effective_control_template(record_id, source)
    _core.validate_production_control_sequence(effective_source, production)


def validate_production_control_sequence(source: str, production: str) -> None:
    """Validate controls, recognizing exact audited base templates for callers.

    Most call sites with a stable ID should use
    :func:`validate_record_production_control_sequence`. This two-argument
    compatibility API remains strict except when ``source`` exactly matches one
    locked certified base presentation template above.
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
        if record_id in FINAL_PLAYTEST_LAYOUT_RECORDS:
            if record_id not in explicit_control_overrides:
                raise ProductionTranslationError(
                    f"{record_id}: final-playtest layout must be an explicit "
                    "control override"
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
