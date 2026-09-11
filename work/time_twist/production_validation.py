"""Validate materialized production prose without reimposing legacy brevity.

The review layer is unconstrained English. ``production_translation`` preserves
native semantic controls in order while regenerating control 0/4 row and scroll
geometry for English. Production validation
therefore rejects implicit row crossing and enforces source-control compatibility,
four-row staging-buffer safety, and renderer width for every record.

This proves token/layout safety, not scene aesthetics. Runtime certification
still reviews every changed record because added row/scroll continuations can alter timing even when the native
text buffer remains structurally safe.
"""

from __future__ import annotations

from .english import EnglishTextError, encode_english, validate_display_width
from .production_translation import (
    ProductionTranslationError,
    validate_production_control_sequence,
    validate_renderer_buffer_layout,
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
    try:
        validate_production_control_sequence(japanese, english)
        validate_renderer_buffer_layout(english)
        validate_display_width(english, allow_wrap=True)
    except (EnglishTextError, ProductionTranslationError) as error:
        raise EnglishTextError(f"{record_id}: {error}") from error
    return encode_english(english)
