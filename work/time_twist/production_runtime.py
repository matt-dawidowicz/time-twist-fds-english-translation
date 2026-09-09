"""Source-verified runtime hardening for the production English build.

This module stages two runtime fixes discovered only through emulator playtesting:

* the extended English dictionary escape must enter the dictionary expander at
  $82C5, after the native five-bit index reader, rather than at $82BE; and
* the variable-width menu renderer recovered during August testing must be
  restored with a zero-count guard so English labels such as ``Intercom`` are
  drawn to their actual width without the historical 256-iteration underflow.

The patches are deliberately size-neutral and fail closed when the input NOV2
bytes do not match the reviewed current-main implementation.  They are kept in
a separate production module while the full retranslation branch is under
runtime certification; once proven, the same logic can be folded into the
canonical NOV2 builder.
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


# Main currently redirects reclaimed 110xxxxxx values to $82BE.  $82BE is the
# native dictionary-token entry point and immediately clears $3A before reading
# a new five-bit index, destroying the already-decoded 32-68 index.  $82C5 is
# the first instruction after that native index reader and consumes the index
# already stored in $3A.
_EXTENDED_DICTIONARY_ENTRY_FIX = RuntimePatch(
    file_offset=0x21D3,
    expected=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
    replacement=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
    label="extended dictionary entry-point fix",
)


# The following ranges recover the previously reverse-engineered variable-width
# menu geometry.  They use the ten-byte scratch table at $93A7-$93B0, record
# decoded label widths, support all ten logical choice indices, and position
# text/arrows from actual label geometry instead of the old six/eight-character
# assumptions.
#
# The renderer setup at $94B6 differs from the earlier experimental binary: it
# includes a zero guard.  The original dynamic code used TXA/LSR as a DEC/BNE
# loop count; X=0 therefore became $00 and underflowed to $FF, causing 256 PPU
# writes.  The guarded form preserves X/2 when nonzero and falls back to six
# iterations only for the zero case.
_VARIABLE_WIDTH_MENU_PATCHES = (
    RuntimePatch(
        0x0A2E,
        _hex("A4 98 88 F0 60 A9 04 85 A1 4C B8 7D"),
        _hex("A4 32 B9 A7 93 18 69 08 65 14 60 EA"),
        "menu geometry helper $6A2E",
    ),
    RuntimePatch(
        0x0D8A,
        _hex("0A A8 B1 C5 85 3C C8 B1 C5 85 3D A5 3C 85 C5 A5 3D 85 C6 4C FF 69"),
        _hex("4C 3A 6C A4 32 C0 04 90 0A 98 29 03 A8 B9 A7 93 69 4F 60 A9 40 60"),
        "choice row/column helper $6D8A",
    ),
    RuntimePatch(
        0x0DDC,
        _hex("B1 C5 85 3C C8 B1 C5 85 3D A5 3C 85 C5 A5 3D 85 C6 4C FF 69"),
        _hex("4C 3C 6C A5 98 38 E5 99 A8 8A 0A 0A 99 A7 93 A9 00 85 69 60"),
        "choice width recorder $6DDC",
    ),
    RuntimePatch(
        0x3391,
        _hex("0F 21 36 0F 0F 0F 0F 0F 0F 16 0F 0F 0F 0F 0F 0F 0C 17 36 0F 0F 0F 0F 0F 0F 0F 0F 0F 0F 0F 0F 0F"),
        _hex("A5 9B C5 C5 D0 07 A5 9C C5 C6 D0 01 60 A9 04 85 A1 A9 22 4C 09 61 00 00 00 00 00 00 00 00 00 00"),
        "menu redraw hook and width scratch $9391",
    ),
    RuntimePatch(
        0x3458,
        _hex("01 60 A9 C0 A0 10 99 47 87 88 D0 FA A9 00 85 71 20 54 81 A9 00 85 69 60"),
        _hex("01 60 A9 C0 A0 24 99 47 87 88 D0 FA A9 00 85 71 20 54 81 20 DF 6D 60 EA"),
        "menu width table initialization $9458",
    ),
    RuntimePatch(
        0x349E,
        _hex("10 A9 51 18 65 3C 85 3C A9 22 65 3D 85 3D 4C BC 94 A9 49 18 65 3C 85 3C A9 22 65 3D 85 3D A9 06 85 31 A2 00"),
        _hex("0D 29 03 A8 B9 A7 93 4A 4A 4A 69 4B D0 02 A9 49 65 3C 85 3C A9 22 85 3D 8A 4A D0 02 A9 06 85 31 A2 00 EA EA"),
        "variable-width left renderer with zero guard $949E",
    ),
    RuntimePatch(
        0x34E5,
        _hex("A2 01 A9 06 85 31"),
        _hex("8A 4A 85 31 A2 01"),
        "variable-width right renderer $94E5",
    ),
    RuntimePatch(
        0x3885,
        _hex("A5 32 C9 04 90 05 A9 80 4C 92 98 A9 40 85 14"),
        _hex("20 8D 6D 85 14 EA EA EA EA EA EA EA EA EA EA"),
        "left-arrow geometry hook $9885",
    ),
    RuntimePatch(
        0x389F,
        _hex("A5 14 18 69 38 85 14"),
        _hex("20 2E 6A 85 14 EA EA"),
        "right-arrow geometry hook $989F",
    ),
    RuntimePatch(
        0x39E1,
        _hex("4C 2E 6A"),
        _hex("4C 91 93"),
        "menu redraw dispatch $99E1",
    ),
)

PRODUCTION_RUNTIME_PATCHES = (
    _EXTENDED_DICTIONARY_ENTRY_FIX,
    *_VARIABLE_WIDTH_MENU_PATCHES,
)


def patch_nov2(data: bytes) -> bytes:
    """Return NOV2 with all production runtime patches applied."""
    result = bytearray(data)
    for patch in PRODUCTION_RUNTIME_PATCHES:
        patch.apply(result)
    return bytes(result)


def patch_fds_image(raw: bytes) -> bytes:
    """Patch NOV2 in a complete two- or four-side FDS image.

    The FDS parser/rebuilder preserves every other file and keeps side sizes
    fixed.  Only side 0's uniquely named ``NOV2`` payload is replaced.
    """
    image = FdsImage.from_bytes(raw)
    if len(image.sides) <= NOV2_SIDE_INDEX:
        raise ProductionRuntimeError("FDS image has no Zenpen side A")
    nov2 = image.sides[NOV2_SIDE_INDEX].find_file(NOV2_FILENAME)
    original_size = len(nov2.data)
    nov2.data = patch_nov2(nov2.data)
    if len(nov2.data) != original_size:
        raise ProductionRuntimeError("NOV2 production hardening changed size")
    return image.to_bytes()
