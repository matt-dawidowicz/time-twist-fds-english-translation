"""Validate materialized production prose without reimposing legacy brevity.

The review layer is unconstrained English. ``production_translation`` preserves
native semantic controls in order while regenerating control 0/4 row and scroll
geometry for English. Production validation therefore rejects implicit row
crossing and enforces source-control compatibility, four-row staging-buffer
safety, and renderer width for every record.

A small audited set of source CTRL:1 waits is presentation-only in production
English. Record-aware validation applies only those explicit exceptions; all
other native semantic controls remain mandatory.
"""

from __future__ import annotations

from .english import EnglishTextError, encode_english, validate_display_width
from .production_translation import (
    ProductionTranslationError,
    validate_record_production_control_sequence,
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
        validate_record_production_control_sequence(record_id, japanese, english)
        validate_renderer_buffer_layout(english)
        validate_display_width(english, allow_wrap=True)
    except (EnglishTextError, ProductionTranslationError) as error:
        raise EnglishTextError(f"{record_id}: {error}") from error
    return encode_english(english)
