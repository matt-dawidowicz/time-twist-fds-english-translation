"""Project-wide bank names, dictionary reservations, and path inference."""

from __future__ import annotations

import re
from pathlib import Path

from .english import encode_english
from .ui import T22_REQUIRED_DICTIONARY_TEXT, TT1B_REQUIRED_DICTIONARY_TEXT

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
    # TT6C repeats this name in its fixed-address retrospective quiz.  Its
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


PERSONALITY_QUESTION_IDS = frozenset(
    f"TT1A/g0/r{record}" for record in range(6, 21)
)


def required_dictionary_entries(
    bank_name: str,
) -> tuple[tuple[object, ...], ...]:
    """Encode dictionary entries reserved by a bank's fixed-address text."""
    return tuple(
        encode_english(text)
        for text in BANK_REQUIRED_DICTIONARY_TEXT.get(bank_name, ())
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
