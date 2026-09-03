"""Shared structural and English validation for scenario translation data."""

from __future__ import annotations

from .english import (
    EnglishTextError,
    control_values,
    encode_english,
    validate_display_width,
)
from .textcodec import PackedSymbol

PERSONALITY_QUESTION_IDS = frozenset(
    f"TT1A/g0/r{record}" for record in range(6, 21)
)

# CTRL:0 is the recovered dialogue-row advance used throughout scenario text.
# English may need additional row advances because its word order and average
# word length differ from Japanese. Do not treat that as permission to alter
# arbitrary timing/state controls: only explicitly reviewed records may insert
# additional CTRL:0 values, and all source controls must remain in order.
PRESENTATION_LINE_CONTROL = 0
PRESENTATION_BREAK_RECORD_IDS = frozenset(
    {
        # さいごにあおぞらをみたのは いつだっけ
        # Natural English needs two rows: "When was the last time" /
        # "I saw a blue sky?"
        "TT1B/g0/r1",
    }
)


def scenario_record_id(
    bank_name: str, group_index: int, record_index: int
) -> str:
    """Return the canonical stable ID for one scenario record."""
    return f"{bank_name}/g{group_index}/r{record_index}"


def _controls_preserve_source_with_presentation_breaks(
    english_controls: tuple[int, ...],
    source_controls: tuple[int, ...],
) -> bool:
    """Return whether English only inserts presentation row advances.

    Source controls must appear in their original order. Any English control
    that is not needed to match the next source control must be CTRL:0. This
    deliberately works at the same sequence level as the historical exact
    control check; it does not claim to recover semantic character offsets from
    the Japanese string.
    """
    source_index = 0
    for control in english_controls:
        if (
            source_index < len(source_controls)
            and control == source_controls[source_index]
        ):
            source_index += 1
            continue
        if control != PRESENTATION_LINE_CONTROL:
            return False
    return source_index == len(source_controls)


def encode_validated_english(
    record_id: str,
    english: object,
    japanese: str,
) -> tuple[PackedSymbol, ...]:
    """Validate one nonempty translation and return its native symbols.

    The shared policy covers type/nonempty checks, control safety, renderer
    width, the personality-question wrapping exception, and glyph encodability.
    Source control order remains exact for ordinary records. Explicitly audited
    records may insert additional CTRL:0 presentation row advances while still
    preserving every source control in order.
    """
    if not isinstance(english, str) or not english:
        raise EnglishTextError("English translation must be a nonempty string")
    english_controls = control_values(english)
    source_controls = control_values(japanese)
    if record_id in PRESENTATION_BREAK_RECORD_IDS:
        if not _controls_preserve_source_with_presentation_breaks(
            english_controls,
            source_controls,
        ):
            raise EnglishTextError(
                "control tags changed beyond audited presentation breaks"
            )
    elif english_controls != source_controls:
        raise EnglishTextError("control tags changed")
    validate_display_width(
        english,
        allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
    )
    return encode_english(english)
