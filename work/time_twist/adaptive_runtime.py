"""Discarded Adaptive255 NOV2 runtime patches kept for explicit diagnostics.

The maintained frozen-entropy path must not import this module. It remains only
so historical Adaptive255 candidate behavior can still be reproduced when a
caller explicitly requests ``adaptive_dictionary=True``.
"""

from __future__ import annotations

from .production_runtime_support import RuntimePatch


def _hex(value: str) -> bytes:
    """Return a hexadecimal representation of the supplied bytes."""
    return bytes.fromhex(value)


_PRODUCTION_TEXT_SCAN_LIMIT_PATCH = RuntimePatch(
    file_offset=0x2142,
    expected=_hex("C9 D4"),
    replacement=_hex("C9 E0"),
    label="production packed-text scan high-RAM limit",
)

_TOP_LEVEL_DECODER_INIT_BRANCH_PATCH = RuntimePatch(
    file_offset=0x2154,
    expected=_hex("A2 00 86 72 86 73"),
    replacement=_hex("4C FA 81 EA EA EA"),
    label="production decoder depth initialization branch",
)

_ADAPTIVE_DICTIONARY_BRANCH_PATCH = RuntimePatch(
    file_offset=0x2182,
    expected=_hex("4C BE 82"),
    replacement=_hex("4C E0 81"),
    label="adaptive dictionary zero-index escape branch",
)

_ADAPTIVE_DICTIONARY_STUB_PATCH = RuntimePatch(
    file_offset=0x21E0,
    expected=_hex(
        "18 69 20 4C 36 82 C9 25 B0 3C 4C 15 82 "
        "A5 3A C9 1E D0 05 A9 2E 4C B7 81 C9 1F"
    ),
    replacement=_hex(
        "A9 00 85 3A 20 0D 81 A5 3A D0 0C 8A 48 "
        "A2 08 20 28 83 CA D0 FA 68 AA 4C C5 82"
    ),
    label="adaptive dictionary 8-bit high-index reader",
)

_TOP_LEVEL_DECODER_INIT_STUB_PATCH = RuntimePatch(
    file_offset=0x21FA,
    expected=_hex("D0 05 A9 2F 4C B7 81 BD 48 87 C9 B5 D0 05 A9"),
    replacement=_hex("A2 00 86 71 86 72 86 73 A9 80 85 6C 4C 5E 81"),
    label="production decoder top-level initialization stub",
)

_NESTED_DICTIONARY_ENTER_PATCH = RuntimePatch(
    file_offset=0x22C5,
    expected=_hex("A9 FF 85 71"),
    replacement=_hex("E6 71 EA EA"),
    label="nested dictionary depth increment",
)

_NESTED_DICTIONARY_EXIT_PATCH = RuntimePatch(
    file_offset=0x2311,
    expected=_hex("A9 00 85 71"),
    replacement=_hex("C6 71 EA EA"),
    label="nested dictionary depth decrement",
)

ADAPTIVE_DICTIONARY_RUNTIME_PATCHES = (
    _PRODUCTION_TEXT_SCAN_LIMIT_PATCH,
    _TOP_LEVEL_DECODER_INIT_BRANCH_PATCH,
    _ADAPTIVE_DICTIONARY_BRANCH_PATCH,
    _ADAPTIVE_DICTIONARY_STUB_PATCH,
    _TOP_LEVEL_DECODER_INIT_STUB_PATCH,
    _NESTED_DICTIONARY_ENTER_PATCH,
    _NESTED_DICTIONARY_EXIT_PATCH,
)


def apply_adaptive_runtime_patches(data: bytearray) -> None:
    """Apply the historical Adaptive255 runtime patches in place."""
    for patch in ADAPTIVE_DICTIONARY_RUNTIME_PATCHES:
        patch.apply(data)
