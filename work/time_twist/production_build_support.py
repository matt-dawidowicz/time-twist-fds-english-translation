"""Shared production-translation build primitives independent of runtime codec.

The frozen entropy builder and the discarded Adaptive255 candidate both consume
the same reviewed production maps. Keep source-map validation, stable-ID
materialization, semantic record comparison, and digest formatting here so the
maintained entropy path does not depend on an obsolete runtime implementation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .production_validation import encode_production_english
from .scenario import ScenarioBank, render_symbols
from .scenario_validation import scenario_record_id
from .textcodec import PackedSymbol

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]


class ProductionBuildError(ValueError):
    """Report a failed production source guard, translation, or round-trip."""


def sha256(data: bytes) -> str:
    """Return the uppercase SHA-256 digest for the supplied data."""
    return hashlib.sha256(data).hexdigest().upper()


def semantic_record(
    record: tuple[PackedSymbol, ...] | list[PackedSymbol],
) -> tuple[tuple[object, int], ...]:
    """Drop decoder bit positions while preserving token kind and value."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def load_translation_map(path: Path) -> dict[str, str]:
    """Load and validate one complete production translation map."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductionBuildError(
            f"cannot load production map: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise ProductionBuildError(f"production map is not an object: {path}")
    result: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value:
            raise ProductionBuildError(
                f"production map must contain nonempty string pairs: {path}"
            )
        result[key] = value
    return result


def encoded_groups(
    bank: ScenarioBank,
    bank_name: str,
    translations: dict[str, str],
) -> ScenarioGroups:
    """Validate stable IDs and encode reviewed English in source group order."""
    records_by_id = {
        scenario_record_id(
            bank_name, record.group_index, record.record_index
        ): record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    missing = sorted(set(records_by_id) - set(translations))
    if unknown or missing:
        raise ProductionBuildError(
            f"{bank_name} production IDs differ from source; "
            f"unknown={unknown[:1]}, missing={missing[:1]}"
        )

    encoded: dict[str, tuple[PackedSymbol, ...]] = {}
    for record_id, record in records_by_id.items():
        japanese = render_symbols(record.symbols, bank.dictionary)
        encoded[record_id] = encode_production_english(
            record_id,
            translations[record_id],
            japanese,
        )

    return tuple(
        tuple(
            encoded[
                scenario_record_id(
                    bank_name,
                    group_index,
                    record.record_index,
                )
            ]
            for record in bank.records
            if record.group_index == group_index
        )
        for group_index in range(len(bank.group_addresses))
    )
