"""Project-wide bank names, dictionary reservations, and path inference."""

from __future__ import annotations

import re
from pathlib import Path

from . import scenario_validation as _scenario_validation
from .english import encode_english
from .textcodec import PackedSymbol, SymbolKind, split_records
from .ui import (
    T22_FIXED_TEXT_END_OFFSET,
    T22_FIXED_TEXT_RECORDS,
    T22_FIXED_TEXT_START_OFFSET,
    T22_REQUIRED_DICTIONARY_TEXT,
    T25_FIXED_TEXT_END_OFFSET,
    T25_FIXED_TEXT_RECORDS,
    T25_FIXED_TEXT_START_OFFSET,
    TT1B_FIXED_TEXT_END_OFFSET,
    TT1B_FIXED_TEXT_RECORDS,
    TT1B_FIXED_TEXT_START_OFFSET,
    TT1B_REQUIRED_DICTIONARY_TEXT,
    TT2_FIXED_TEXT_END_OFFSET,
    TT2_FIXED_TEXT_RECORDS,
    TT2_FIXED_TEXT_START_OFFSET,
    TT3A_FIXED_TEXT_END_OFFSET,
    TT3A_FIXED_TEXT_RECORDS,
    TT3A_FIXED_TEXT_START_OFFSET,
    TT3B_FIXED_TEXT_END_OFFSET,
    TT3B_FIXED_TEXT_RECORDS,
    TT3B_FIXED_TEXT_START_OFFSET,
    TT4_FIXED_TEXT_END_OFFSET,
    TT4_FIXED_TEXT_RECORDS,
    TT4_FIXED_TEXT_START_OFFSET,
    TT5_FIXED_TEXT_END_OFFSET,
    TT5_FIXED_TEXT_RECORDS,
    TT5_FIXED_TEXT_START_OFFSET,
    TT6A_FIXED_TEXT_END_OFFSET,
    TT6A_FIXED_TEXT_RECORDS,
    TT6A_FIXED_TEXT_START_OFFSET,
    TT6B_FIXED_TEXT_END_OFFSET,
    TT6B_FIXED_TEXT_RECORDS,
    TT6B_FIXED_TEXT_START_OFFSET,
    TT6C_FIXED_TEXT_END_OFFSET,
    TT6C_FIXED_TEXT_RECORDS,
    TT6C_FIXED_TEXT_START_OFFSET,
)


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

BANK_REQUIRED_DICTIONARY_TEXT = {
    "TT1B": TT1B_REQUIRED_DICTIONARY_TEXT,
    "TT2": ("CROWD", "Bishop"),
    "T22": T22_REQUIRED_DICTIONARY_TEXT,
    "TT3B": ("Cougar",),
    # TT6C repeats this name in its fixed-address retrospective quiz. Its
    # five-byte record cannot hold the six literal glyphs, so reserve the same
    # dictionary token even if scenario-corpus scoring would otherwise evict it.
    "TT6C": ("Cougar",),
    "TT4": (
        "Cerberus: ",
        "Soldier: ",
        "Fisher: ",
        "Man: ",
        "Me: ",
        "Merchant: ",
        "Devil: ",
        "Dario: ",
        "Girl: ",
        "Youth: ",
        "Priest: ",
    ),
    "TT5": ("Tom: ",),
}

_FIXED_SOURCE_TABLES = {
    "TT1B": (
        TT1B_FIXED_TEXT_START_OFFSET,
        TT1B_FIXED_TEXT_END_OFFSET,
        len(TT1B_FIXED_TEXT_RECORDS),
    ),
    "TT2": (
        TT2_FIXED_TEXT_START_OFFSET,
        TT2_FIXED_TEXT_END_OFFSET,
        len(TT2_FIXED_TEXT_RECORDS),
    ),
    "T22": (
        T22_FIXED_TEXT_START_OFFSET,
        T22_FIXED_TEXT_END_OFFSET,
        len(T22_FIXED_TEXT_RECORDS),
    ),
    "TT3A": (
        TT3A_FIXED_TEXT_START_OFFSET,
        TT3A_FIXED_TEXT_END_OFFSET,
        len(TT3A_FIXED_TEXT_RECORDS),
    ),
    "TT3B": (
        TT3B_FIXED_TEXT_START_OFFSET,
        TT3B_FIXED_TEXT_END_OFFSET,
        len(TT3B_FIXED_TEXT_RECORDS),
    ),
    "TT4": (
        TT4_FIXED_TEXT_START_OFFSET,
        TT4_FIXED_TEXT_END_OFFSET,
        len(TT4_FIXED_TEXT_RECORDS),
    ),
    "TT5": (
        TT5_FIXED_TEXT_START_OFFSET,
        TT5_FIXED_TEXT_END_OFFSET,
        len(TT5_FIXED_TEXT_RECORDS),
    ),
    "T25": (
        T25_FIXED_TEXT_START_OFFSET,
        T25_FIXED_TEXT_END_OFFSET,
        len(T25_FIXED_TEXT_RECORDS),
    ),
    "TT6A": (
        TT6A_FIXED_TEXT_START_OFFSET,
        TT6A_FIXED_TEXT_END_OFFSET,
        len(TT6A_FIXED_TEXT_RECORDS),
    ),
    "TT6B": (
        TT6B_FIXED_TEXT_START_OFFSET,
        TT6B_FIXED_TEXT_END_OFFSET,
        len(TT6B_FIXED_TEXT_RECORDS),
    ),
    "TT6C": (
        TT6C_FIXED_TEXT_START_OFFSET,
        TT6C_FIXED_TEXT_END_OFFSET,
        len(TT6C_FIXED_TEXT_RECORDS),
    ),
}


def required_dictionary_entries(
    bank_name: str,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Encode dictionary entries reserved by a bank's fixed-address text."""
    return tuple(
        encode_english(text)
        for text in BANK_REQUIRED_DICTIONARY_TEXT.get(bank_name, ())
    )


def source_dictionary_reference_floor(bank_name: str, data: bytes) -> int:
    """Return the largest source dictionary slot used by fixed-address text.

    Scenario dialogue is not the only consumer of a bank dictionary. Several
    command/object/quiz tables live outside the ordinary group streams and are
    referenced by absolute address. This function decodes the verified source
    table and returns its largest one-based dictionary reference so scenario
    parsing can include those entries when it establishes the fixed tail.
    """
    table = _FIXED_SOURCE_TABLES.get(bank_name)
    if table is None:
        return 0
    start, expected_end, record_count = table
    records, actual_end = split_records(data, offset=start, limit=record_count)
    if actual_end != expected_end:
        raise ValueError(
            f"{bank_name} fixed source table ended at 0x{actual_end:04X}; "
            f"expected 0x{expected_end:04X}"
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
    """Return a validated scenario bank name from an explicit value or filename.

    Accepted filenames include extracted names such as
    ``side1_01_TT1A_A200.bin`` and generated names such as
    ``TT1A_fixed_footprint.bin``. Ambiguous or unknown names are rejected rather
    than silently selecting an underscore-delimited token.
    """
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
