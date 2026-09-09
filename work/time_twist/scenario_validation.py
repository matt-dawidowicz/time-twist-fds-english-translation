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

# The native renderer can continue a long control-free segment on the next
# 24-tile row when the byte stream places a blank tile exactly at the wrap
# boundary.  This is not a blanket permission to overflow: a later control can
# reuse the wrapped row and overwrite text.  Production IDs enter this set only
# after their exact control topology and padded wrap have been reviewed.
PRODUCTION_SAFE_WRAP_IDS = frozenset(
    {
        "TT1B/g0/r1",
    }
)


def scenario_record_id(
    bank_name: str, group_index: int, record_index: int
) -> str:
    """Return the canonical stable ID for one scenario record."""
    return f"{bank_name}/g{group_index}/r{record_index}"


def encode_validated_english(
    record_id: str,
    english: object,
    japanese: str,
) -> tuple[PackedSymbol, ...]:
    """Validate one nonempty translation and return its native symbols.

    The shared policy covers type/nonempty checks, exact control-tag order,
    renderer width, explicitly reviewed wrapping exceptions, and glyph
    encodability. Callers add only their command-specific error context.
    """
    if not isinstance(english, str) or not english:
        raise EnglishTextError("English translation must be a nonempty string")
    if control_values(english) != control_values(japanese):
        raise EnglishTextError("control tags changed")
    validate_display_width(
        english,
        allow_wrap=(
            record_id in PERSONALITY_QUESTION_IDS
            or record_id in PRODUCTION_SAFE_WRAP_IDS
        ),
    )
    return encode_english(english)
