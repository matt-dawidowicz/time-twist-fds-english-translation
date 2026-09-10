"""Source-verified runtime hardening for the production English build.

This module keeps proven UI/font fixes separate from the staged adaptive text
codec.  The default patch path remains the runtime-tested 68-entry English
format.  Passing ``adaptive_dictionary=True`` additionally installs the
production 255-entry dictionary escape, bounded nested-dictionary support, and
the high-RAM text-scan boundary needed by spill-relocated production banks.

Two earlier RC3/RC4 experiments attempted to install a variable-width menu
renderer by using $9391-$93B0 as code/scratch storage. Runtime screenshots
proved that assumption unsafe: $9390-$93AF is live NES palette data, so those
builds corrupted UI graphics. That experiment is intentionally removed here.
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


# The English extended-token decoder has already read the six-bit value into
# $3A. Entering at $82BE would clear $3A and consume another five bits. $82C5
# is the first instruction after the native index reader and therefore expands
# the already-decoded dictionary entry 32-68 correctly.
_EXTENDED_DICTIONARY_ENTRY_FIX = RuntimePatch(
    file_offset=0x21D3,
    expected=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
    replacement=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
    label="extended dictionary entry-point fix",
)


# Extended code 63 originally resolves through NOV2's $835E-$8378 lookup table
# to tile $AC. NOV4 source slot $AC overlaps title graphics and cannot safely
# hold an English glyph. The runtime-tested Start$ diagnostic proved that
# redirecting only this final lookup byte to tile $B0 renders a clean dollar
# sign while leaving the protected title-graphics source region untouched.
_DOLLAR_SIGN_TILE_LOOKUP_PATCH = RuntimePatch(
    file_offset=0x2378,
    expected=_hex("AC"),
    replacement=_hex("B0"),
    label="extended code 63 dollar-sign tile redirect",
)


# NOV2 initializes sixteen bytes at $8747 before decoding a menu label. The
# renderer consumes alternating bytes for the two tile rows, so the staging
# buffer already holds eight glyphs. The original renderer simply stops after
# six iterations on each row. Raising only those two loop counts exposes all
# eight existing glyph slots while preserving every other menu/UI behavior.
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


# The native right-arrow routine starts from the left-arrow coordinate in $14
# and adds $38: six 8-pixel glyph cells plus one 8-pixel bracket allowance.
# With the text blitter raised to eight glyphs, the equivalent fixed span is
# $48: eight glyph cells plus the same bracket allowance.
_EIGHT_GLYPH_SELECTION_SPAN_PATCH = RuntimePatch(
    file_offset=0x38A3,
    expected=_hex("38"),
    replacement=_hex("48"),
    label="eight-glyph selection bracket span",
)


# ---------------------------------------------------------------------------
# Staged adaptive production dictionary: entries 69-255 + nested grammar
# ---------------------------------------------------------------------------
# Packed-text scanning originally stops when the stream pointer reaches the
# $D400 page. Production banks may spill packed groups and their dictionary
# into otherwise-unused PRG RAM above the source overlay. The FDS PRG window
# ends at $DFFF, so $E000 is the correct exclusive high bound.
_PRODUCTION_TEXT_SCAN_LIMIT_PATCH = RuntimePatch(
    file_offset=0x2142,
    expected=_hex("C9 D4"),
    replacement=_hex("C9 E0"),
    label="production packed-text scan high-RAM limit",
)


# Every top-level decode must begin with dictionary depth zero. The native
# entry initialized X/$72/$73 and relied on $71 as a boolean that callers did
# not consistently clear. Redirect only the true top-level entry at $8154 to a
# dead English-code stub; dictionary return resumes at $815A and therefore does
# not clear nesting depth while an expansion is still active.
_TOP_LEVEL_DECODER_INIT_BRANCH_PATCH = RuntimePatch(
    file_offset=0x2154,
    expected=_hex("A2 00 86 72 86 73"),
    replacement=_hex("4C FA 81 EA EA EA"),
    label="production decoder depth initialization branch",
)


# Native dictionary prefix 1110xxxxx reaches $82BE when xxxxx is the five-bit
# one-based index. Index zero is invalid in ordinary source text. Redirect that
# branch to a stub in $81E0-$81F9, a region rendered unreachable by the proven
# $81D3 English 32-68 decoder patch. No live palette, table, or scratch RAM is
# commandeered.
_ADAPTIVE_DICTIONARY_BRANCH_PATCH = RuntimePatch(
    file_offset=0x2182,
    expected=_hex("4C BE 82"),
    replacement=_hex("4C E0 81"),
    label="adaptive dictionary zero-index escape branch",
)


# Stub semantics:
#   * read the native five-bit dictionary index into $3A;
#   * nonzero indices continue unchanged at $82C5;
#   * zero saves X, reads eight more stream bits into $3A, restores X, and
#     continues at $82C5.
# The production encoder emits only canonical high payloads 69-255. X must be
# preserved because the caller uses it as the decoded menu/text output index.
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


# $81FA-$8208 is the continuation of the same unreachable Japanese extended
# glyph branch. It reconstructs the original top-level initialization and also
# clears $71 before jumping past the overwritten bytes to $815E.
_TOP_LEVEL_DECODER_INIT_STUB_PATCH = RuntimePatch(
    file_offset=0x21FA,
    expected=_hex("D0 05 A9 2F 4C B7 81 BD 48 87 C9 B5 D0 05 A9"),
    replacement=_hex("A2 00 86 71 86 72 86 73 A9 80 85 6C 4C 5E 81"),
    label="production decoder top-level initialization stub",
)


# The native dictionary expander used $71 as a boolean: set to $FF on entry,
# clear to zero after one expansion. The 6502 already pushes the previous text
# pointer triplet ($6A/$6B/$6C) for every dictionary call, so replacing that
# boolean with a depth counter makes backward-only nested entries unwind
# correctly without changing the stack representation. Production compression
# caps grammar depth well below the 8-bit counter and practical CPU-stack limit.
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


# $9390-$93AF is live palette data. Do not place code, tables, or scratch
# storage there. RC3/RC4 did so experimentally and produced visible corruption.
PALETTE_DATA_RANGE = range(0x3390, 0x33B0)

PRODUCTION_RUNTIME_PATCHES = (
    _EXTENDED_DICTIONARY_ENTRY_FIX,
    _DOLLAR_SIGN_TILE_LOOKUP_PATCH,
    *_EIGHT_GLYPH_MENU_RENDERER_PATCHES,
    _EIGHT_GLYPH_SELECTION_SPAN_PATCH,
)


def patch_nov2(data: bytes, *, adaptive_dictionary: bool = False) -> bytes:
    """Return NOV2 with proven fixes and optional adaptive codec patches."""
    result = bytearray(data)
    for patch in PRODUCTION_RUNTIME_PATCHES:
        patch.apply(result)
    if adaptive_dictionary:
        for patch in ADAPTIVE_DICTIONARY_RUNTIME_PATCHES:
            patch.apply(result)
    return bytes(result)


def patch_fds_image(
    raw: bytes,
    *,
    adaptive_dictionary: bool = False,
) -> bytes:
    """Patch NOV2 in a complete FDS image without changing its payload size."""
    image = FdsImage.from_bytes(raw)
    if len(image.sides) <= NOV2_SIDE_INDEX:
        raise ProductionRuntimeError("FDS image has no Zenpen side A")
    nov2 = image.sides[NOV2_SIDE_INDEX].find_file(NOV2_FILENAME)
    original_size = len(nov2.data)
    nov2.data = patch_nov2(
        nov2.data,
        adaptive_dictionary=adaptive_dictionary,
    )
    if len(nov2.data) != original_size:
        raise ProductionRuntimeError("NOV2 production hardening changed size")
    return image.to_bytes()
