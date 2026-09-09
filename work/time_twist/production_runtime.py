"""Source-verified runtime hardening for the production English build.

This module stages only runtime changes that have survived emulator evidence.
Two earlier RC3/RC4 experiments attempted to install a variable-width menu
renderer by using $9391-$93B0 as code/scratch storage.  Runtime screenshots
proved that assumption unsafe: $9390-$93AF is live NES palette data, so those
builds corrupted UI graphics.  That experiment is intentionally removed here.

The retained fixes are:

* the extended English dictionary escape enters the dictionary expander at
  $82C5, after the native five-bit index reader, rather than at $82BE; and
* the existing menu text blitter copies eight characters instead of six.  The
  native staging buffer is already sixteen bytes wide (two bytes per glyph), so
  this raises the visible text limit to eight without changing menu geometry,
  palette data, scratch RAM, cursor code, or automatic dialogue wrapping.

The eight-character change is deliberately conservative while the final
production renderer is being reverse-engineered.  It is sufficient to exercise
``Intercom`` without reintroducing the RC3/RC4 palette/layout regression.
"""

from __future__ import annotations

from dataclasses import dataclass

from .fds import FdsImage

NOV2_SIDE_INDEX = 0
NOV2_FILENAME = "NOV2"
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
        current = bytes(data[self.file_offset:end])
        if current == self.replacement:
            return
        if current != self.expected:
            raise ProductionRuntimeError(
                f"{self.label}: source mismatch at file 0x{self.file_offset:04X} "
                f"/ CPU ${self.cpu_address:04X}: got {current.hex(' ').upper()}"
            )
        data[self.file_offset:end] = self.replacement


def _hex(value: str) -> bytes:
    return bytes.fromhex(value)


# The English extended-token decoder has already read the six-bit value into
# $3A.  Entering at $82BE would clear $3A and consume another five bits.  $82C5
# is the first instruction after the native index reader and therefore expands
# the already-decoded dictionary entry 32-68 correctly.
_EXTENDED_DICTIONARY_ENTRY_FIX = RuntimePatch(
    file_offset=0x21D3,
    expected=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
    replacement=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
    label="extended dictionary entry-point fix",
)


# NOV2 initializes sixteen bytes at $8747 before decoding a menu label.  The
# renderer consumes alternating bytes for the two tile rows, so the staging
# buffer already holds eight glyphs.  The original renderer simply stops after
# six iterations on each row.  Raising only those two loop counts exposes all
# eight existing glyph slots while preserving every other menu/UI behavior.
_EIGHT_GLYPH_MENU_RENDERER_PATCHES = (
    RuntimePatch(
        file_offset=0x34BB,
        expected=_hex("A9 06"),
        replacement=_hex("A9 08"),
        label="eight-glyph menu renderer first row",
    ),
    RuntimePatch(
        file_offset=0x34E6,
        expected=_hex("A9 06"),
        replacement=_hex("A9 08"),
        label="eight-glyph menu renderer second row",
    ),
)

# $9390-$93AF is live palette data.  Do not place code, tables, or scratch
# storage there.  RC3/RC4 did so experimentally and produced visible corruption.
PALETTE_DATA_RANGE = range(0x3390, 0x33B0)

PRODUCTION_RUNTIME_PATCHES = (
    _EXTENDED_DICTIONARY_ENTRY_FIX,
    *_EIGHT_GLYPH_MENU_RENDERER_PATCHES,
)


def patch_nov2(data: bytes) -> bytes:
    """Return NOV2 with all proven production runtime patches applied."""
    result = bytearray(data)
    for patch in PRODUCTION_RUNTIME_PATCHES:
        patch.apply(result)
    return bytes(result)


def patch_fds_image(raw: bytes) -> bytes:
    """Patch NOV2 in a complete two- or four-side FDS image."""
    image = FdsImage.from_bytes(raw)
    if len(image.sides) <= NOV2_SIDE_INDEX:
        raise ProductionRuntimeError("FDS image has no Zenpen side A")
    nov2 = image.sides[NOV2_SIDE_INDEX].find_file(NOV2_FILENAME)
    original_size = len(nov2.data)
    nov2.data = patch_nov2(nov2.data)
    if len(nov2.data) != original_size:
        raise ProductionRuntimeError("NOV2 production hardening changed size")
    return image.to_bytes()
