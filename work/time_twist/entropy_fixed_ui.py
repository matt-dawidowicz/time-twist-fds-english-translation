"""Entropy ownership for fixed decoder-visible Time Twist text.

The entropy NOV2 runtime replaces the native packed-text decoder globally.
Therefore every packed-text stream that can reach that decoder must use the
same entropy grammar.  Scenario groups, dictionaries, and the large relocated
menu tables already satisfy that rule; NOV4's title/menu text and TT1A's small
fixed selector table historically did not.

This module owns those exceptional fixed-address surfaces.  It deliberately
keeps their existing byte allocations and pointers, packs records contiguously
inside each independently addressed stream, and pads only after the final
record.  No runtime format flag or address heuristic is needed.
"""

from __future__ import annotations

import hashlib

from .english import encode_english
from .entropy_codec import pack_entropy_stream, unpack_entropy_stream
from .entropy_compression import expand_entropy_dictionary, expand_entropy_record
from .textcodec import PackedSymbol, SymbolKind
from .ui_fixed_tables import (
    TT1A_BLOOD_TYPE_PATCHES,
    TT1A_CONFIRMATION_PATCHES,
    TT1A_MONTH_PATCHES,
)


class EntropyFixedTextError(ValueError):
    """Report source drift, capacity exhaustion, or failed semantic validation."""


# ---------------------------------------------------------------------------
# TT1A: 19 directly selected choice records in one scanner-visible stream.
# ---------------------------------------------------------------------------

TT1A_LOAD_ADDRESS = 0xA200
TT1A_TABLE_START = 0x025B
TT1A_TABLE_END = 0x02AB
TT1A_TABLE_CAPACITY = TT1A_TABLE_END - TT1A_TABLE_START
TT1A_TABLE_SOURCE_SHA256 = (
    "A32AF053FB86837B730491965F213FFADE180A1C57F468EB83DFD2A02491E9A3"
)
TT1A_TABLE_POINTERS = {
    0x0C: 0xA45B,
    0x10: 0xA4AB,
    0x12: 0xA4C2,
    0x14: 0xA45B,
    0x1A: 0xA4AB,
    0x26: 0xA4C2,
}
TT1A_CHOICE_TEXT = tuple(
    english
    for _offset, _source, english in (
        *TT1A_BLOOD_TYPE_PATCHES,
        *TT1A_MONTH_PATCHES,
        *TT1A_CONFIRMATION_PATCHES,
    )
)


# ---------------------------------------------------------------------------
# NOV4: title menu plus its one internal text group and dictionary reservation.
# ---------------------------------------------------------------------------

NOV4_LOAD_ADDRESS = 0xA200
NOV4_SOURCE_SIZE = 0x2375
NOV4_MENU_START = 0x0085
NOV4_MENU_END = 0x010B
NOV4_GROUP_START = 0x1E5B
NOV4_GROUP_END = 0x1E97
NOV4_DICTIONARY_START = 0x1E97
NOV4_DICTIONARY_END = 0x1EB3
NOV4_MENU_SOURCE_SHA256 = (
    "163AC345AF33B442E6937C1ABDCB0F9E66EFCB491E54CED2082F9FFD5B822708"
)
NOV4_GROUP_SOURCE_SHA256 = (
    "C863116781D27BAF8B0F733C474BB12A626C47086D953CDE944D1A63471EE7DF"
)
NOV4_DICTIONARY_SOURCE_SHA256 = (
    "7D4245DAC9F1EBF43067F19F2A8EAD4A0A00B7674A055AB52D437E2DC66979F5"
)
NOV4_POINTERS = {
    0x14: 0xA285,  # menu table base
    0x1A: 0xA30B,  # first byte after the 26-record menu allocation
    0x16: 0xC097,  # dictionary base
    0x18: 0xC0B3,  # first byte after dictionary reservation
    0x24: 0xC097,  # group table; no extra group pointers exist
    0x26: 0xC05B,  # internal group zero
}
NOV4_MENU_TEXT = (
    "New",
    "Bookshelf",
    "Epilogue",
    "Start",
    "Load",
    "Part 2",
    "Book 1",
    "Book 2",
    "Book 3",
    "Book 4",
    "Part 1",
    "Part 2",
    *(f"Chapter {index}" for index in range(1, 15)),
)
NOV4_GROUP_TEXT = (
    "Welcome",
    "Disk Select",
    "Book Select",
    "Start Select",
    "Disk Register",
    "Thank you",
    "Title demo test.",
)
# Four short, literal definitions are enough to make every NOV4 fixed stream
# fit its original reservation.  Keeping this dictionary local also avoids
# widening the global entropy grammar to Japanese-only extended values 0-36.
NOV4_DICTIONARY_TEXT = ("Book", "Part", "Chapter", " Select")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _semantic(record: tuple[PackedSymbol, ...] | list[PackedSymbol]):
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _word(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise EntropyFixedTextError(f"word at 0x{offset:04X} is outside component")
    return int.from_bytes(data[offset : offset + 2], "little")


def _assert_pointers(data: bytes, expected: dict[int, int], label: str) -> None:
    for offset, address in expected.items():
        actual = _word(data, offset)
        if actual != address:
            raise EntropyFixedTextError(
                f"{label} pointer at 0x{offset:04X} is ${actual:04X}; "
                f"expected ${address:04X}"
            )


def _fit(payload: bytes, capacity: int, label: str) -> bytes:
    if len(payload) > capacity:
        raise EntropyFixedTextError(
            f"{label} needs {len(payload)} bytes but only {capacity} are reserved"
        )
    return payload + bytes(capacity - len(payload))


def _dictionary_records() -> tuple[tuple[PackedSymbol, ...], ...]:
    return tuple(encode_english(text) for text in NOV4_DICTIONARY_TEXT)


def _compress_with_nov4_dictionary(text: str) -> tuple[PackedSymbol, ...]:
    """Replace deterministic longest literal phrases with NOV4 dictionary refs."""
    literal = encode_english(text)
    phrases = _dictionary_records()
    output: list[PackedSymbol] = []
    position = 0
    while position < len(literal):
        matches = [
            (len(phrase), index)
            for index, phrase in enumerate(phrases, start=1)
            if phrase and literal[position : position + len(phrase)] == phrase
        ]
        if not matches:
            output.append(literal[position])
            position += 1
            continue
        width, index = max(matches)
        output.append(PackedSymbol(SymbolKind.DICTIONARY, index, 0, 0))
        position += width
    return tuple(output)


def nov4_entropy_payloads() -> tuple[bytes, bytes, bytes]:
    """Return deterministic raw menu, internal-group, and dictionary streams."""
    menu = pack_entropy_stream(
        tuple(_compress_with_nov4_dictionary(text) for text in NOV4_MENU_TEXT)
    )
    group = pack_entropy_stream(
        tuple(_compress_with_nov4_dictionary(text) for text in NOV4_GROUP_TEXT)
    )
    dictionary = pack_entropy_stream(_dictionary_records())
    return menu, group, dictionary


def tt1a_entropy_payload() -> bytes:
    """Return the complete 19-record TT1A choice stream with one final pad."""
    return pack_entropy_stream(tuple(encode_english(text) for text in TT1A_CHOICE_TEXT))


def _audit_nov4(data: bytes) -> None:
    dictionary = unpack_entropy_stream(
        data[NOV4_DICTIONARY_START:NOV4_DICTIONARY_END],
        record_count=len(NOV4_DICTIONARY_TEXT),
    )
    expected_dictionary = _dictionary_records()
    if tuple(map(_semantic, dictionary)) != tuple(map(_semantic, expected_dictionary)):
        raise EntropyFixedTextError("NOV4 entropy dictionary failed semantic audit")
    expansions = expand_entropy_dictionary(dictionary)

    for label, start, end, expected_text in (
        ("menu", NOV4_MENU_START, NOV4_MENU_END, NOV4_MENU_TEXT),
        ("internal group", NOV4_GROUP_START, NOV4_GROUP_END, NOV4_GROUP_TEXT),
    ):
        decoded = unpack_entropy_stream(
            data[start:end],
            record_count=len(expected_text),
        )
        for index, (record, text) in enumerate(zip(decoded, expected_text, strict=True)):
            expanded = expand_entropy_record(record, expansions)
            if _semantic(expanded) != _semantic(encode_english(text)):
                raise EntropyFixedTextError(
                    f"NOV4 entropy {label} record {index} failed semantic audit"
                )


def _audit_tt1a(data: bytes) -> None:
    decoded = unpack_entropy_stream(
        data[TT1A_TABLE_START:TT1A_TABLE_END],
        record_count=len(TT1A_CHOICE_TEXT),
    )
    for index, (record, text) in enumerate(zip(decoded, TT1A_CHOICE_TEXT, strict=True)):
        if _semantic(record) != _semantic(encode_english(text)):
            raise EntropyFixedTextError(
                f"TT1A entropy choice record {index} failed semantic audit"
            )


def patched_nov4_entropy_text(data: bytes) -> bytes:
    """Convert every NOV4 stream consumed by the global entropy decoder.

    This runs after the size-neutral font patch and before title expansion.  The
    font patch intentionally remains first because it validates a whole-bank
    source hash; weakening that source guard merely to accommodate a new text
    intermediate would reduce safety.
    """
    if len(data) != NOV4_SOURCE_SIZE:
        raise EntropyFixedTextError(
            f"NOV4 entropy text requires the 0x{NOV4_SOURCE_SIZE:X}-byte base bank"
        )
    _assert_pointers(data, NOV4_POINTERS, "NOV4")
    menu, group, dictionary = nov4_entropy_payloads()
    replacements = (
        (
            NOV4_MENU_START,
            NOV4_MENU_END,
            NOV4_MENU_SOURCE_SHA256,
            _fit(menu, NOV4_MENU_END - NOV4_MENU_START, "NOV4 menu"),
            "NOV4 menu",
        ),
        (
            NOV4_GROUP_START,
            NOV4_GROUP_END,
            NOV4_GROUP_SOURCE_SHA256,
            _fit(group, NOV4_GROUP_END - NOV4_GROUP_START, "NOV4 internal group"),
            "NOV4 internal group",
        ),
        (
            NOV4_DICTIONARY_START,
            NOV4_DICTIONARY_END,
            NOV4_DICTIONARY_SOURCE_SHA256,
            _fit(
                dictionary,
                NOV4_DICTIONARY_END - NOV4_DICTIONARY_START,
                "NOV4 dictionary",
            ),
            "NOV4 dictionary",
        ),
    )

    states = []
    for start, end, source_hash, replacement, label in replacements:
        current = data[start:end]
        if current == replacement:
            states.append("entropy")
        elif _sha256(current) == source_hash:
            states.append("source")
        else:
            raise EntropyFixedTextError(
                f"{label} does not match either the verified Japanese source or "
                "the deterministic entropy replacement; do not apply native NOV4 "
                "UI text patches before the entropy conversion"
            )
    if len(set(states)) != 1:
        raise EntropyFixedTextError("NOV4 entropy text is only partially converted")
    if states[0] == "entropy":
        _audit_nov4(data)
        return data

    result = bytearray(data)
    for start, end, _source_hash, replacement, _label in replacements:
        result[start:end] = replacement
    patched = bytes(result)
    _assert_pointers(patched, NOV4_POINTERS, "NOV4")
    _audit_nov4(patched)
    return patched


def patched_tt1a_entropy_ui(data: bytes) -> bytes:
    """Replace TT1A's native aligned selector records with one entropy stream."""
    _assert_pointers(data, TT1A_TABLE_POINTERS, "TT1A")
    payload = tt1a_entropy_payload()
    replacement = _fit(payload, TT1A_TABLE_CAPACITY, "TT1A choice table")
    current = data[TT1A_TABLE_START:TT1A_TABLE_END]
    if current == replacement:
        _audit_tt1a(data)
        return data
    if _sha256(current) != TT1A_TABLE_SOURCE_SHA256:
        raise EntropyFixedTextError(
            "TT1A fixed choice table does not match the verified Japanese source; "
            "the native TT1A UI patch must not run on the entropy build path"
        )
    result = bytearray(data)
    result[TT1A_TABLE_START:TT1A_TABLE_END] = replacement
    patched = bytes(result)
    _assert_pointers(patched, TT1A_TABLE_POINTERS, "TT1A")
    _audit_tt1a(patched)
    return patched


def entropy_fixed_text_coverage() -> dict[str, dict[str, int]]:
    """Expose the fixed-stream coverage invariant in release manifests/tests."""
    menu, group, dictionary = nov4_entropy_payloads()
    tt1a = tt1a_entropy_payload()
    return {
        "NOV4_menu": {
            "records": len(NOV4_MENU_TEXT),
            "packed_bytes": len(menu),
            "capacity_bytes": NOV4_MENU_END - NOV4_MENU_START,
        },
        "NOV4_internal": {
            "records": len(NOV4_GROUP_TEXT),
            "packed_bytes": len(group),
            "capacity_bytes": NOV4_GROUP_END - NOV4_GROUP_START,
        },
        "NOV4_dictionary": {
            "records": len(NOV4_DICTIONARY_TEXT),
            "packed_bytes": len(dictionary),
            "capacity_bytes": NOV4_DICTIONARY_END - NOV4_DICTIONARY_START,
        },
        "TT1A_choices": {
            "records": len(TT1A_CHOICE_TEXT),
            "packed_bytes": len(tt1a),
            "capacity_bytes": TT1A_TABLE_CAPACITY,
        },
    }
