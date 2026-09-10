"""Validate materialized production prose without reimposing legacy brevity.

The review layer is unconstrained English. ``production_translation`` restores
exact source control order and pads every automatic 24-column wrap at a word
boundary. Production validation therefore enforces those two structural facts
for every record rather than using the certified release's small allow-list of
known wrapping exceptions.

This proves token/layout safety, not scene aesthetics. Runtime certification
still reviews every changed record because an original control transition can
have scene-specific visual behavior after a newly added automatic row.
"""

from __future__ import annotations

from .english import (
    EnglishTextError,
    control_values,
    encode_english,
    validate_display_width,
)
from .textcodec import PackedSymbol


def encode_production_english(
    record_id: str,
    english: object,
    japanese: str,
) -> tuple[PackedSymbol, ...]:
    """Encode one materialized production record with source-control guards."""
    if not isinstance(english, str) or not english:
        raise EnglishTextError(
            f"{record_id}: English translation must be a nonempty string"
        )
    if control_values(english) != control_values(japanese):
        raise EnglishTextError(f"{record_id}: control tags changed")
    try:
        validate_display_width(english, allow_wrap=True)
    except EnglishTextError as error:
        raise EnglishTextError(f"{record_id}: {error}") from error
    return encode_english(english)
