"""Project-wide scenario bank identity and source-layout helpers."""

from __future__ import annotations

import re
from pathlib import Path

from . import scenario_validation as _scenario_validation
from .textcodec import SymbolKind, split_records
from .ui import FIXED_RECORD_TABLE_SPECS

PERSONALITY_QUESTION_IDS = _scenario_validation.PERSONALITY_QUESTION_IDS

KNOWN_SCENARIO_BANKS = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
)


def source_dictionary_reference_floor(bank_name: str, data: bytes) -> int:
    """Return the largest source dictionary slot used outside scenario groups."""
    spec = FIXED_RECORD_TABLE_SPECS.get(bank_name)
    if spec is None:
        return 0
    records, actual_end = split_records(
        data,
        offset=spec.start,
        limit=len(spec.records),
    )
    if actual_end != spec.end:
        raise ValueError(
            f"{bank_name} fixed source table ended at 0x{actual_end:04X}; "
            f"expected 0x{spec.end:04X}"
        )
    return max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )


def infer_bank_name(path: Path, explicit: str | None = None) -> str:
    """Return a validated scenario bank name from an explicit value or filename."""
    if explicit is not None:
        candidate = explicit.upper()
        if candidate not in KNOWN_SCENARIO_BANKS:
            raise ValueError(f"unknown scenario bank name: {explicit}")
        return candidate

    stem = path.stem.upper()
    matches = [
        bank
        for bank in KNOWN_SCENARIO_BANKS
        if re.search(rf"(?:^|_){re.escape(bank)}(?:_|$)", stem)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"cannot infer one scenario bank from {path.name!r}; "
            "pass --bank-name explicitly"
        )
    return matches[0]
