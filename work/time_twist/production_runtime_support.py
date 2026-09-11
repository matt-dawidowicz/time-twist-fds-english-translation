"""Codec-neutral NOV2 runtime patches proven by the English build.

The frozen entropy runtime and the optional Adaptive255 experiment share a
small set of source-verified NOV2 fixes that are independent of either packed
text codec. Keep those patches here so the maintained entropy path does not
need to import the discarded adaptive runtime implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

NOV2_LOAD_ADDRESS = 0x6000


class ProductionRuntimeError(ValueError):
    """Report a source mismatch or malformed production runtime patch."""


@dataclass(frozen=True)
class RuntimePatch:
    """One source-verified size-neutral patch inside NOV2."""

    file_offset: int
    expected: bytes
    replacement: bytes
    label: str

    def __post_init__(self) -> None:
        """Validate the patch offset and size neutrality."""
        if self.file_offset < 0:
            raise ProductionRuntimeError(f"{self.label}: negative file offset")
        if len(self.expected) != len(self.replacement):
            raise ProductionRuntimeError(f"{self.label}: patch changed size")

    @property
    def cpu_address(self) -> int:
        """Return the loaded CPU address of the first patched byte."""
        return NOV2_LOAD_ADDRESS + self.file_offset

    def apply(self, data: bytearray) -> None:
        """Apply the patch, accepting an already-patched buffer idempotently."""
        end = self.file_offset + len(self.expected)
        if end > len(data):
            raise ProductionRuntimeError(
                f"{self.label}: NOV2 ends before file 0x{end:04X}"
            )
        current = bytes(data[self.file_offset : end])
        if current == self.replacement:
            return
        if current != self.expected:
            raise ProductionRuntimeError(
                f"{self.label}: source mismatch at file 0x{self.file_offset:04X} "
                f"/ CPU ${self.cpu_address:04X}: got {current.hex(' ').upper()}"
            )
        data[self.file_offset : end] = self.replacement


def _hex(value: str) -> bytes:
    """Return a hexadecimal representation of the supplied bytes."""
    return bytes.fromhex(value)


_EXTENDED_DICTIONARY_ENTRY_FIX = RuntimePatch(
    file_offset=0x21D3,
    expected=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
    replacement=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
    label="extended dictionary entry-point fix",
)

_DOLLAR_SIGN_TILE_LOOKUP_PATCH = RuntimePatch(
    file_offset=0x2378,
    expected=_hex("AC"),
    replacement=_hex("B0"),
    label="extended code 63 dollar-sign tile redirect",
)

_EIGHT_GLYPH_MENU_RENDERER_PATCHES = (
    RuntimePatch(
        file_offset=0x34BC,
        expected=_hex("A9 06"),
        replacement=_hex("A9 08"),
        label="eight-glyph menu renderer first row",
    ),
    RuntimePatch(
        file_offset=0x34E7,
        expected=_hex("A9 06"),
        replacement=_hex("A9 08"),
        label="eight-glyph menu renderer second row",
    ),
)

_EIGHT_GLYPH_SELECTION_SPAN_PATCH = RuntimePatch(
    file_offset=0x38A3,
    expected=_hex("38"),
    replacement=_hex("48"),
    label="eight-glyph selection bracket span",
)

PRODUCTION_RUNTIME_PATCHES = (
    _EXTENDED_DICTIONARY_ENTRY_FIX,
    _DOLLAR_SIGN_TILE_LOOKUP_PATCH,
    *_EIGHT_GLYPH_MENU_RENDERER_PATCHES,
    _EIGHT_GLYPH_SELECTION_SPAN_PATCH,
)


def patch_proven_nov2(data: bytes) -> bytes:
    """Apply only the proven codec-neutral English NOV2 runtime fixes."""
    result = bytearray(data)
    for patch in PRODUCTION_RUNTIME_PATCHES:
        patch.apply(result)
    return bytes(result)
