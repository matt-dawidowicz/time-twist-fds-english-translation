"""Patch fixed-address UI text and small verified program fragments.

Normal dialogue is rebuilt through :mod:`time_twist.scenario`; this module owns
text that is referenced directly by 6502 code or stored in separate overlays.
Most replacements must preserve a complete table and every individual packed
record boundary.  Short code patches compare exact source bytes before
writing, and larger tables use SHA-256 revision guards.

Public ``patched_*`` functions are pure: they accept one extracted FDS file as
``bytes`` and return replacement bytes or raise :class:`UiPatchError`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from . import ui_fixed_tables as _fixed_tables
from .compression import symbol_bit_length
from .english import encode_english
from .font import render_glyph
from .textcodec import (
    BitReader,
    PackedSymbol,
    SymbolKind,
    decode_symbol,
    pack_records,
    split_records,
)
from .ui_fixed_tables import (
    T22_FIXED_TEXT_END_OFFSET,
    T22_FIXED_TEXT_RECORDS,
    T22_FIXED_TEXT_SOURCE_SHA256,
    T22_FIXED_TEXT_START_OFFSET,
    T25_FIXED_TEXT_END_OFFSET,
    T25_FIXED_TEXT_RECORDS,
    T25_FIXED_TEXT_SOURCE_SHA256,
    T25_FIXED_TEXT_START_OFFSET,
    TT1A_BLOOD_TYPE_PATCHES,
    TT1A_CONFIRMATION_PATCHES,
    TT1A_MONTH_PATCHES,
    TT1B_FIXED_TEXT_END_OFFSET,
    TT1B_FIXED_TEXT_RECORDS,
    TT1B_FIXED_TEXT_SOURCE_SHA256,
    TT1B_FIXED_TEXT_START_OFFSET,
    TT2_DICTIONARY_ENTRIES,
    TT2_DICTIONARY_POINTER_OFFSET,
    TT2_FIXED_TEXT_END_OFFSET,
    TT2_FIXED_TEXT_RECORDS,
    TT2_FIXED_TEXT_SOURCE_SHA256,
    TT2_FIXED_TEXT_START_OFFSET,
    TT2_LOAD_ADDRESS,
    TT3A_FIXED_TEXT_END_OFFSET,
    TT3A_FIXED_TEXT_RECORDS,
    TT3A_FIXED_TEXT_SOURCE_SHA256,
    TT3A_FIXED_TEXT_START_OFFSET,
    TT3B_FIXED_TEXT_END_OFFSET,
    TT3B_FIXED_TEXT_RECORDS,
    TT3B_FIXED_TEXT_SOURCE_SHA256,
    TT3B_FIXED_TEXT_START_OFFSET,
    TT4_FIXED_TEXT_END_OFFSET,
    TT4_FIXED_TEXT_RECORDS,
    TT4_FIXED_TEXT_SOURCE_SHA256,
    TT4_FIXED_TEXT_START_OFFSET,
    TT5_FIXED_TEXT_END_OFFSET,
    TT5_FIXED_TEXT_RECORDS,
    TT5_FIXED_TEXT_SOURCE_SHA256,
    TT5_FIXED_TEXT_START_OFFSET,
    TT6A_FIXED_TEXT_END_OFFSET,
    TT6A_FIXED_TEXT_RECORDS,
    TT6A_FIXED_TEXT_SOURCE_SHA256,
    TT6A_FIXED_TEXT_START_OFFSET,
    TT6B_FIXED_TEXT_END_OFFSET,
    TT6B_FIXED_TEXT_RECORDS,
    TT6B_FIXED_TEXT_SOURCE_SHA256,
    TT6B_FIXED_TEXT_START_OFFSET,
    TT6C_FIXED_TEXT_END_OFFSET,
    TT6C_FIXED_TEXT_RECORDS,
    TT6C_FIXED_TEXT_SOURCE_SHA256,
    TT6C_FIXED_TEXT_START_OFFSET,
)

# These table declarations are looked up dynamically by ``project.py`` while
# constructing per-bank dictionary reservations, so retain them on the public
# ``time_twist.ui`` facade even though the local patchers do not reference them.
TT1B_REQUIRED_DICTIONARY_TEXT = _fixed_tables.TT1B_REQUIRED_DICTIONARY_TEXT
FIXED_UI_DICTIONARY_ENTRY_COUNT = _fixed_tables.FIXED_UI_DICTIONARY_ENTRY_COUNT
T22_REQUIRED_DICTIONARY_TEXT = _fixed_tables.T22_REQUIRED_DICTIONARY_TEXT


class UiPatchError(ValueError):
    """Report an incompatible source, fixed-slot overrun, or unsafe UI patch.

    UI patch helpers raise this exception before returning modified bytes when
    source fingerprints, instruction patterns, encoded sizes, or bank capacity
    differ from verified assumptions. Callers should inspect the source
    version or shorten/recompress text instead of forcing a partial write.
    """


COMPONENT_LOAD_ADDRESSES: Mapping[str, int] = MappingProxyType(
    {
        # Verified from NOV2's FDS block-3 file header.
        "NOV2": 0x6000,
    }
)


@dataclass(frozen=True)
class SourceVerifiedPatch:
    """Describe one immutable, size-neutral component instruction patch."""

    component: str
    file_offset: int
    cpu_address: int
    expected: bytes
    replacement: bytes
    label: str

    def __post_init__(self) -> None:
        """Validate size and established file-offset/CPU-address metadata."""
        if self.file_offset < 0:
            raise UiPatchError(
                f"{self.component} {self.label} has a negative file offset"
            )
        load_address = COMPONENT_LOAD_ADDRESSES.get(self.component)
        if load_address is None:
            raise UiPatchError(
                f"{self.component} {self.label} has no verified component "
                "load address"
            )
        expected_cpu_address = load_address + self.file_offset
        if self.cpu_address != expected_cpu_address:
            raise UiPatchError(
                f"{self.component} {self.label} declares CPU "
                f"${self.cpu_address:04X}, expected ${expected_cpu_address:04X} "
                f"from load ${load_address:04X} + file "
                f"0x{self.file_offset:04X}"
            )
        if len(self.expected) != len(self.replacement):
            raise UiPatchError(
                f"{self.component} {self.label} patch changed size"
            )

    def apply_to(self, data: bytearray) -> None:
        """Validate and install this patch into a mutable component copy."""
        end = self.file_offset + len(self.expected)
        if len(data) < end or data[self.file_offset : end] != self.expected:
            raise UiPatchError(
                f"{self.component} {self.label} at file 0x{self.file_offset:04X} "
                f"/ CPU ${self.cpu_address:04X} does not match source"
            )
        data[self.file_offset : end] = self.replacement


# ---------------------------------------------------------------------------
# Shared NOV2/NOV4 prompts and input behavior
# ---------------------------------------------------------------------------

START_PROMPT_OFFSET = 0x2651
NOV4_START_PROMPT_OFFSET = 0x0095
ORIGINAL_START_PROMPT = bytes.fromhex("28 12 F5 A2 CD F4")
ENGLISH_START_PROMPT = pack_records([encode_english("Start ")])

# NOV4 owns the title screen's saved-game choice.  The five-glyph Japanese
# label means "from a save".  Its six-byte fixed record accepts ``Load`` plus
# two invisible trailing spaces without moving following title-program data.
NOV4_LOAD_PROMPT_OFFSET = 0x009B
ORIGINAL_NOV4_LOAD_PROMPT = bytes.fromhex("37 71 9B 16 6F A0")
ENGLISH_NOV4_LOAD_PROMPT = pack_records([encode_english("Load  ")])

# NOV2 also owns a separate short load record.  It is not the title menu's
# visible saved-game choice, but must remain English if that path is reached.
SAVE_PROMPT_OFFSET = 0x2648
ORIGINAL_SAVE_PROMPT = bytes.fromhex("37 71 9B FA")
ENGLISH_SAVE_PROMPT = pack_records([encode_english("Save")])

LOAD_PROMPT_OFFSET = 0x2657
ORIGINAL_LOAD_PROMPT = bytes.fromhex("AB 71 93 FA")
ENGLISH_LOAD_PROMPT = pack_records([encode_english("Load")])

# NOV2 composes its disk-change message from five independently packed
# records: game half, requested side, and the instruction line. Keeping each
# replacement exactly the same size preserves the surrounding program data.
DISK_PROMPT_PATCHES = (
    (0x260D, bytes.fromhex("C6 DB A3 B5 8F A0"), "Part 1"),
    (0x2613, bytes.fromhex("24 27 2D 63 E8"), "Part2"),
    (0x2618, bytes.fromhex("F0 1E E2 1B 6C FA"), "{CTRL:0}SideA"),
    (0x261E, bytes.fromhex("F1 9A DC 43 6D 9F 40"), "{CTRL:0}Side B"),
    (
        0x2625,
        bytes.fromhex("F1 E0 DD 52 65 A4 3E 3C A0 7E 80"),
        "{CTRL:0}{CTRL:0}Insert now.",
    ),
)

# Returning the same mounted disk/side at a side-change prompt can display this
# older NOV2 status record before the shared retry instruction at $86DE. Earlier
# static analysis treated the record as bit-aligned and translated only the
# inner bits, but runtime save-state evidence shows the visible renderer starts at
# byte $269A. Leaving the high three source bits untouched made the first line
# render as Latin-glyph garbage while the second line correctly said
# ``Try again.``.
#
# ``Wrong side.`` needs a compact ``de.`` ligature to fit this eight-byte slot,
# but runtime testing showed that the squeezed tile looks visibly cramped in
# the disk-retry box.  Use the fully readable ordinary-glyph fallback
# ``Bad side.`` for this size-locked heading; the longer ten-byte disk-number
# record below still uses ordinary packed ``Wrong side.`` where there is room.
DISK_SET_ERROR_OFFSET = 0x269A
DISK_SET_ERROR_SOURCE = bytes.fromhex("C9 69 8C 1C DD 52 7F 40")
DISK_SET_ERROR_ENGLISH = "Bad side."


def _patched_disk_set_error_message(data: bytes) -> bytes:
    """Translate NOV2's byte-aligned same-side retry heading.

    Runtime save states from the double disk-swap path show that the first visible
    line is read from byte $269A, then the shared retry line at $86DE is drawn.
    Use ordinary glyphs only.  The exact ``Wrong side.`` wording requires a
    private compact suffix in this eight-byte record, and playtest
    screenshots showed that suffix was too visually cramped.
    """
    replacement = pack_records([encode_english(DISK_SET_ERROR_ENGLISH)])
    if len(replacement) != len(DISK_SET_ERROR_SOURCE):
        raise UiPatchError("disk-set error changed packed size")

    end = DISK_SET_ERROR_OFFSET + len(DISK_SET_ERROR_SOURCE)
    if (
        len(data) < end
        or data[DISK_SET_ERROR_OFFSET:end] != DISK_SET_ERROR_SOURCE
    ):
        raise UiPatchError("disk-set error record does not match source")

    result = bytearray(data)
    result[DISK_SET_ERROR_OFFSET:end] = replacement
    return bytes(result)


def _encode_disk_prompt(english: str) -> tuple[PackedSymbol, ...]:
    """Encode one size-locked disk prompt without moving NOV2 data.

    The native five-bit dictionary limit is unrelated to these fixed records:
    the short labels are direct packed streams beside executable NOV2 code.
    ``Part2`` and ``SideA`` are deliberately compact ordinary-glyph labels so
    they fit the immutable records without repurposing a tile that title
    rendering uses. All disk prompts use the normal English encoder.
    """
    return encode_english(english)


def _encode_side_number_error(english: str) -> tuple[PackedSymbol, ...]:
    """Encode one source-locked same-side retry record normally.

    The visible eight-byte same-side retry heading uses the readable ``Bad
    side.`` fallback.  The longer ``Wrong side.`` record has room for ordinary
    English glyphs and is encoded by its caller without a compact ligature.
    """
    return encode_english(english)


# NOV2 has multiple disk-error text paths. Returning the same already-mounted
# side at a side-change prompt can reach compact eight-byte status records;
# without these replacements the English font renders their Japanese packed
# bytes as alphabet soup. Runtime testing showed that the private compact
# ``Wrong side.`` suffix was too cramped in those eight-byte slots, so these
# headings use the ordinary-glyph fallback ``Bad side.``. A later wrong-disk
# recovery path uses the following records and remains translated separately.
SIDE_NUMBER_ERROR_PATCHES = (
    (
        0x26CC,
        bytes.fromhex("0F 71 9A DC 14 0E 4F E8"),
        "Bad side.",
    ),
    (
        0x26DE,
        bytes.fromhex("F1 BF DF EF F7 FB F0 E6 DC 7D"),
        "{CTRL:0}Try again.",
    ),
)

# The adjacent ``disk number`` record has a ten-byte source slot and can hold
# ordinary packed ``Wrong side.`` cleanly.  Keep that exact wording where the
# binary layout allows it.
DISK_NUMBER_ERROR_PATCHES = (
    (
        0x26D4,
        bytes.fromhex("C9 69 8C 1F 7E A5 B9 9D C7 D0"),
        "Wrong side.",
    ),
)

WRONG_DISK_PATCHES = (
    (
        0x26E8,
        bytes.fromhex("43 0B AA 3F 7F 92 D3 18 3E 17 E8"),
        "Wrong disk! ",
    ),
    (
        0x26F3,
        bytes.fromhex("F1 BF DF EF F7 E6 EA 93 2A 94 81 78 CF A0"),
        "{CTRL:0}Try another side",
    ),
)
WAIT_PROMPT_OFFSET = 0x25D9
ORIGINAL_WAIT_PROMPT = bytes.fromhex("2F 33 30 FE 37 FB F1 1E 40 7C 79 40 FD")
ENGLISH_WAIT_PROMPT = pack_records([encode_english("Please wait... ")])

# ---------------------------------------------------------------------------
# Kouhen direct-boot guard (SON-KOUH)
# ---------------------------------------------------------------------------

# Kouhen's 739-byte startup program is used only when the second game is
# booted directly.  It draws a Japanese warning from 21 private 1bpp tiles and
# an RLE-compressed nametable fragment; none of that text passes through the
# normal scenario decoder.  Preserve the program, vectors, addresses, and
# exact file size while replacing only those two assets.  The English wording
# describes the required action more clearly than a literal "load from the
# first-part disk": Kouhen must inherit live state from Zenpen and is not a
# standalone boot disk.
KOUHEN_BOOT_GUARD_SOURCE_SHA256 = (
    "EE32CD2462B224A55B875694D8C34A362754A92630DCDB1A40451AA331C43847"
)
KOUHEN_BOOT_GUARD_SIZE = 0x02E3
KOUHEN_BOOT_GUARD_TILEMAP_OFFSET = 0x01EC
KOUHEN_BOOT_GUARD_TILEMAP_END = 0x0227
KOUHEN_BOOT_GUARD_CHR_OFFSET = 0x0233
KOUHEN_BOOT_GUARD_TILE_COUNT = 21
KOUHEN_BOOT_GUARD_BLANK_TILE = 0x14
KOUHEN_BOOT_GUARD_PPU_START = 0x20D0
KOUHEN_BOOT_GUARD_DECODED_SIZE = 414
KOUHEN_BOOT_GUARD_LINES = (
    (11, "Please start with"),
    (13, "Part 1"),
)
KOUHEN_BOOT_GUARD_TILE_CHARACTERS = (
    "P",
    "l",
    "e",
    "a",
    "s",
    "t",
    "r",
    "w",
    "i",
    "h",
    "1",
)

# NOV2 normally fills unused menu-buffer cells with $AC.  The menu renderer
# treats $AC as transparent, so an opaque common-space tile is still needed
# there.  Dialogue is handled separately below: making all 24 dialogue tail
# cells opaque caused the typewriter cadence to process them as silent
# characters.
NOV2_BLANK_TILE = 0xC0
NOV2_OPAQUE_CLEAR_PATCHES = (
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x345B,
        cpu_address=0x945B,
        expected=bytes((0xAC,)),
        replacement=bytes((NOV2_BLANK_TILE,)),
        label="menu choice clear",
    ),
)

# NOV2's scroll uploader must retain this indexed load.  It copies the valid
# bottom dialogue row to the nametable before the text buffer shifts.  An
# earlier clear attempt replaced the load with ``LDA #$C0 / NOP``; that erased
# complete sentences at CTRL:3/CTRL:4 transitions (including the chant and the
# narration line immediately after it).  Keep the bytes here as a regression
# guard, not as a patch target.  Dialogue tails remain transparent $AC so they
# are skipped without producing a row of invisible typewriter sounds.
NOV2_DIALOGUE_ROW_COPY = (
    0x2571,
    bytes.fromhex("B9 D7 87"),
)

# The menu input dispatcher enters its B-button action at $99DC.  The
# original code correctly returns when no Back destination was saved, but a
# one-choice menu can save its own address as that destination.  Pressing B
# then closes and redraws the same menu, making the top border slide through
# the START label.
#
# NOV2 has no expandable space: it occupies $6000-$A1FF, immediately below
# NOV4.  Reuse the twelve bytes at $6A2E-$6A39 by redirecting three duplicate
# state-table JMPs to identical handlers that already exist.  The replacement
# B action keeps the original $9C=0 guard at $99DC intact, then:
#
# * returns through the existing RTS at $6A93 when the menu has one choice;
# * performs the original action-4/state-$22 transition for larger menus.
#
# Thus the post-title START menu ignores B without changing Back/Cancel on
# normal multi-choice menus.
NOV2_SINGLE_CHOICE_B_PATCHES = (
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x0A0D,
        cpu_address=0x6A0D,
        expected=bytes.fromhex("31 6A 34 6A"),
        replacement=bytes.fromhex("40 6A 40 6A"),
        label="duplicate state handlers 1-2",
    ),
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x0A13,
        cpu_address=0x6A13,
        expected=bytes.fromhex("34 6A"),
        replacement=bytes.fromhex("40 6A"),
        label="duplicate state handler 4",
    ),
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x0A17,
        cpu_address=0x6A17,
        expected=bytes.fromhex("37 6A"),
        replacement=bytes.fromhex("73 6B"),
        label="duplicate state handler 6",
    ),
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x0A25,
        cpu_address=0x6A25,
        expected=bytes.fromhex("F0 07"),
        replacement=bytes.fromhex("F0 19"),
        label="shared state-return branch",
    ),
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x0A2E,
        cpu_address=0x6A2E,
        expected=bytes.fromhex("4C 01 61 4C 01 61 4C 01 61 4C DB 89"),
        replacement=bytes.fromhex("A4 98 88 F0 60 A9 04 85 A1 4C B8 7D"),
        label="single-choice B guard helper",
    ),
    SourceVerifiedPatch(
        component="NOV2",
        file_offset=0x39E1,
        cpu_address=0x99E1,
        expected=bytes.fromhex("A9 04 85 A1 A9 22 4C 09 61"),
        replacement=bytes.fromhex("4C 2E 6A EA EA EA EA EA EA"),
        label="B action detour",
    ),
)

# English scenario banks use extended glyph values 37-62 for punctuation,
# digits, and the seven uncommon uppercase letters. Values 0-36 are therefore
# unreachable in translated text. Redirect that unused nine-bit range to
# dictionary entries 32-68 without changing the native 1-31 encoding. The
# replacement exactly occupies NOV2's original Japanese extended-glyph branch.
NOV2_EXTENDED_DICTIONARY_PATCH = SourceVerifiedPatch(
    component="NOV2",
    file_offset=0x21D3,
    cpu_address=0x81D3,
    expected=bytes.fromhex("A5 3A C9 04 90 07 C9 20 B0 09 4C ED 81"),
    replacement=bytes.fromhex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
    label="extended English dictionary decoder",
)


def _encode_kouhen_guard_rle(values: bytes) -> bytes:
    """Encode a SON-KOUH startup nametable fragment.

    Args:
        values: Decoded tile IDs in PPU upload order.

    Returns:
        Native count-prefix data terminated by ``$FF``.

    Runs are split at 62 because ``$FF`` terminates the decoder. Single-byte
    remainders use literals because they are shorter than a two-byte run.
    """
    encoded = bytearray()
    index = 0
    while index < len(values):
        value = values[index]
        run = 1
        while index + run < len(values) and values[index + run] == value:
            run += 1

        remaining = run
        while remaining:
            # $FF terminates this decoder, so the largest legal run prefix is
            # $FE: 62 copies.  A final single byte is cheaper as a literal.
            chunk = min(remaining, 62)
            if chunk == 1:
                encoded.append(value)
            else:
                encoded.extend((0xC0 | chunk, value))
            remaining -= chunk
        index += run
    encoded.append(0xFF)
    return bytes(encoded)


def _kouhen_boot_guard_assets() -> tuple[bytes, bytes]:
    """Build the Kouhen direct-boot message tilemap and private glyphs.

    Returns:
        A fixed-size, padded RLE stream and direct-upload 1bpp glyph rows.

    Raises:
        UiPatchError: If the message exhausts private tile IDs, falls outside
            the recovered nametable fragment, or cannot fit the original RLE
            allocation.
        FontPatchError: If a message character has no deterministic glyph.

    Glyph bits are inverted relative to NOV4's stored font because SON-KOUH
    uploads its private patterns directly instead of expanding inverse rows.
    """
    tile_by_character = {
        character: tile
        for tile, character in enumerate(KOUHEN_BOOT_GUARD_TILE_CHARACTERS)
    }
    if len(tile_by_character) >= KOUHEN_BOOT_GUARD_BLANK_TILE:
        raise UiPatchError("Kouhen boot message uses too many private tiles")

    tilemap = bytearray(
        [KOUHEN_BOOT_GUARD_BLANK_TILE] * KOUHEN_BOOT_GUARD_DECODED_SIZE
    )
    nametable_start = KOUHEN_BOOT_GUARD_PPU_START - 0x2000
    for row, text in KOUHEN_BOOT_GUARD_LINES:
        column = (32 - len(text)) // 2
        start = row * 32 + column - nametable_start
        end = start + len(text)
        if start < 0 or end > len(tilemap):
            raise UiPatchError(
                "Kouhen boot message is outside its nametable fragment"
            )
        tilemap[start:end] = bytes(
            (
                KOUHEN_BOOT_GUARD_BLANK_TILE
                if character == " "
                else tile_by_character[character]
            )
            for character in text
        )

    stream = _encode_kouhen_guard_rle(bytes(tilemap))
    stream_size = (
        KOUHEN_BOOT_GUARD_TILEMAP_END - KOUHEN_BOOT_GUARD_TILEMAP_OFFSET
    )
    if len(stream) > stream_size:
        raise UiPatchError(
            f"Kouhen boot tilemap needs {len(stream)} bytes but has {stream_size}"
        )
    # The decoder stops at the first $FF; additional terminators safely retain
    # the fixed address of the following CHR upload routine.
    stream = stream.ljust(stream_size, b"\xff")

    glyphs = bytearray(KOUHEN_BOOT_GUARD_TILE_COUNT * 8)
    for character, tile in tile_by_character.items():
        # The dialogue font stores zeroes as ink because NOV4 expands inverse
        # 1bpp patterns.  SON-KOUH uploads its private tiles directly, so flip
        # the bits to obtain white glyphs on its black background.
        glyph = bytes(value ^ 0xFF for value in render_glyph(character))
        glyphs[tile * 8 : (tile + 1) * 8] = glyph
    return stream, bytes(glyphs)


def patched_kouhen_boot_guard(data: bytes) -> bytes:
    """Translate Kouhen's direct-boot warning without changing program code.

    Args:
        data: Original 739-byte SON-KOUH component.

    Returns:
        A same-size copy with only the RLE tilemap and private glyph rows
        replaced.

    Raises:
        UiPatchError: If size or SHA-256 does not match the recovered source,
            or generated assets exceed their fixed locations.
    """
    if len(data) != KOUHEN_BOOT_GUARD_SIZE:
        raise UiPatchError(
            f"SON-KOUH has size {len(data)}, expected {KOUHEN_BOOT_GUARD_SIZE}"
        )
    if (
        hashlib.sha256(data).hexdigest().upper()
        != KOUHEN_BOOT_GUARD_SOURCE_SHA256
    ):
        raise UiPatchError("SON-KOUH does not match the known Japanese source")

    stream, glyphs = _kouhen_boot_guard_assets()
    chr_end = KOUHEN_BOOT_GUARD_CHR_OFFSET + len(glyphs)
    result = bytearray(data)
    result[KOUHEN_BOOT_GUARD_TILEMAP_OFFSET:KOUHEN_BOOT_GUARD_TILEMAP_END] = (
        stream
    )
    result[KOUHEN_BOOT_GUARD_CHR_OFFSET:chr_end] = glyphs
    return bytes(result)


def _patched_start_prompt(data: bytes, offset: int, component: str) -> bytes:
    """Replace one unique packed start prompt at a recovered offset.

    Args:
        data: Extracted component bytes.
        offset: Expected start of the Japanese packed record.
        component: Human-readable name used in diagnostics.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If source/replacement sizes differ, the input is short,
            expected bytes differ, or the source prompt is not globally unique.
    """
    if len(ENGLISH_START_PROMPT) != len(ORIGINAL_START_PROMPT):
        raise UiPatchError("translated start prompt changed packed size")
    end = offset + len(ORIGINAL_START_PROMPT)
    if len(data) < end:
        raise UiPatchError(
            f"{component} is too short for the recovered start prompt"
        )
    if data[offset:end] != ORIGINAL_START_PROMPT:
        raise UiPatchError(
            f"{component} start prompt does not match the known source bytes"
        )
    if data.count(ORIGINAL_START_PROMPT) != 1:
        raise UiPatchError(f"{component} start prompt source is not unique")

    result = bytearray(data)
    result[offset:end] = ENGLISH_START_PROMPT
    return bytes(result)


def _patched_load_prompt(data: bytes) -> bytes:
    """Translate the saved-game ``Load`` label in NOV2.

    Args:
        data: NOV2 bytes containing the recovered Japanese load record.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If the known source record is absent or the replacement
            would change the following data's address.
    """
    if len(ENGLISH_LOAD_PROMPT) != len(ORIGINAL_LOAD_PROMPT):
        raise UiPatchError("translated load prompt changed packed size")
    end = LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT)
    if len(data) < end or data[LOAD_PROMPT_OFFSET:end] != ORIGINAL_LOAD_PROMPT:
        raise UiPatchError("NOV2 load prompt does not match the known source")
    result = bytearray(data)
    result[LOAD_PROMPT_OFFSET:end] = ENGLISH_LOAD_PROMPT
    return bytes(result)


def _patched_save_prompt(data: bytes) -> bytes:
    """Replace NOV2's separate saved-game command label with ``Save``.

    Args:
        data: NOV2 bytes containing the verified four-byte Japanese record.

    Returns:
        A same-size copy with the system-menu command translated.

    Raises:
        UiPatchError: If the source record is absent or the replacement would
            move following NOV2 data.
    """
    if len(ENGLISH_SAVE_PROMPT) != len(ORIGINAL_SAVE_PROMPT):
        raise UiPatchError("save prompt changed packed size")
    end = SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT)
    if len(data) < end or data[SAVE_PROMPT_OFFSET:end] != ORIGINAL_SAVE_PROMPT:
        raise UiPatchError("NOV2 save prompt does not match the known source")
    result = bytearray(data)
    result[SAVE_PROMPT_OFFSET:end] = ENGLISH_SAVE_PROMPT
    return bytes(result)


def _patched_nov4_load_prompt(data: bytes) -> bytes:
    """Replace NOV4's visible saved-game title choice with ``Load``.

    Args:
        data: NOV4 bytes containing the verified six-byte Japanese record.

    Returns:
        A same-size copy with the title-menu saved-game choice translated.

    Raises:
        UiPatchError: If the source record is absent or the replacement would
            move following title-program data.
    """
    if len(ENGLISH_NOV4_LOAD_PROMPT) != len(ORIGINAL_NOV4_LOAD_PROMPT):
        raise UiPatchError("NOV4 load prompt changed packed size")
    end = NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT)
    if (
        len(data) < end
        or data[NOV4_LOAD_PROMPT_OFFSET:end] != ORIGINAL_NOV4_LOAD_PROMPT
    ):
        raise UiPatchError("NOV4 load prompt does not match the known source")
    result = bytearray(data)
    result[NOV4_LOAD_PROMPT_OFFSET:end] = ENGLISH_NOV4_LOAD_PROMPT
    return bytes(result)


def _patched_disk_prompts(data: bytes) -> bytes:
    """Translate every normal NOV2 FDS side-change record.

    Args:
        data: NOV2 bytes containing all recovered prompt slots.

    Returns:
        A same-size copy with each prompt replaced independently.

    Raises:
        UiPatchError: If a replacement changes size, a slot is missing, or its
            source bytes differ.
        EnglishTextError: If configured English cannot be encoded.
    """
    result = bytearray(data)
    for offset, original, english in DISK_PROMPT_PATCHES:
        replacement = pack_records([_encode_disk_prompt(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"disk prompt at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end:
            raise UiPatchError(
                "NOV2 is too short for the recovered disk prompt"
            )
        if result[offset:end] != original:
            raise UiPatchError(
                f"NOV2 disk prompt at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _patched_side_number_error_message(data: bytes) -> bytes:
    """Translate NOV2's same-side retry messages.

    Args:
        data: NOV2 bytes containing the recovered side-number warning slots.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If any slot size or source bytes differ.
        EnglishTextError: If configured English cannot be encoded.
    """
    result = bytearray(data)
    for offset, original, english in SIDE_NUMBER_ERROR_PATCHES:
        replacement = pack_records([_encode_side_number_error(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"side-number error at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end or result[offset:end] != original:
            raise UiPatchError(
                f"side-number error at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    for offset, original, english in DISK_NUMBER_ERROR_PATCHES:
        replacement = pack_records([encode_english(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"disk-number error at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end or result[offset:end] != original:
            raise UiPatchError(
                f"disk-number error at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _patched_wrong_disk_message(data: bytes) -> bytes:
    """Translate each NOV2 wrong-disk fallback record.

    Args:
        data: NOV2 bytes containing the recovered warning slots.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If any slot size or source bytes differ.
        EnglishTextError: If configured English cannot be encoded.
    """
    result = bytearray(data)
    for offset, original, english in WRONG_DISK_PATCHES:
        replacement = pack_records([encode_english(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"wrong-disk message at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end or result[offset:end] != original:
            raise UiPatchError(
                f"wrong-disk message at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _patched_wait_prompt(data: bytes) -> bytes:
    """Translate ``しばらく おまちください`` in its fixed NOV2 slot.

    Args:
        data: NOV2 bytes.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If packed sizes differ or source bytes are unknown.
    """
    if len(ENGLISH_WAIT_PROMPT) != len(ORIGINAL_WAIT_PROMPT):
        raise UiPatchError("translated wait prompt changed packed size")
    end = WAIT_PROMPT_OFFSET + len(ORIGINAL_WAIT_PROMPT)
    if len(data) < end or data[WAIT_PROMPT_OFFSET:end] != ORIGINAL_WAIT_PROMPT:
        raise UiPatchError("NOV2 wait prompt does not match the known source")
    result = bytearray(data)
    result[WAIT_PROMPT_OFFSET:end] = ENGLISH_WAIT_PROMPT
    return bytes(result)


def _patched_opaque_text_clears(data: bytes) -> bytes:
    """Clear complete menu tails without breaking dialogue row copies.

    Args:
        data: NOV2 bytes with the recovered rendering instructions.

    Returns:
        A same-size copy with selected clear-mode operands changed.

    Raises:
        UiPatchError: If a patch byte or the protected dialogue-copy sequence
            differs from the known source.

    The protected sequence is checked but not changed. This guards against a
    broad rendering fix that previously restored menu rows at the cost of
    ordinary dialogue replacement.
    """
    result = bytearray(data)
    for patch in NOV2_OPAQUE_CLEAR_PATCHES:
        patch.apply_to(result)
    dialogue_offset, dialogue_source = NOV2_DIALOGUE_ROW_COPY
    end = dialogue_offset + len(dialogue_source)
    if len(result) < end or result[dialogue_offset:end] != dialogue_source:
        raise UiPatchError(
            f"NOV2 dialogue row copy at 0x{dialogue_offset:04X} does not match source"
        )
    return bytes(result)


def _patched_single_choice_b_guard(data: bytes) -> bytes:
    """Make B a no-op only while a one-choice menu is active.

    Args:
        data: NOV2 bytes containing the recovered input branches.

    Returns:
        A same-size copy with guarded branch/code fragments installed.

    Raises:
        UiPatchError: If a replacement changes size or a source instruction
            differs.

    Multi-choice Back/Cancel behavior is deliberately left untouched.
    """
    result = bytearray(data)
    for patch in NOV2_SINGLE_CHOICE_B_PATCHES:
        patch.apply_to(result)
    return bytes(result)


def _patched_extended_dictionary_decoder(data: bytes) -> bytes:
    """Enable dictionary references 32-68 in unused English glyph codes."""
    result = bytearray(data)
    NOV2_EXTENDED_DICTIONARY_PATCH.apply_to(result)
    return bytes(result)


def patched_nov2_ui(data: bytes) -> bytes:
    """Apply the complete, ordered NOV2 interface patch set.

    Args:
        data: Compatible NOV2 component bytes.

    Returns:
        A same-size copy containing wait/disk/side-error/wrong-disk/start/load
        translations, opaque menu-tail clearing, and the one-choice B guard.

    Raises:
        UiPatchError: If any revision guard or size invariant fails.
        EnglishTextError: If configured prompt text cannot be encoded.

    Patch order is intentional because every helper validates the bytes it
    owns while leaving disjoint regions available to later helpers.
    """
    with_wait_prompt = _patched_wait_prompt(data)
    with_disk_prompts = _patched_disk_prompts(with_wait_prompt)
    with_disk_set_error = _patched_disk_set_error_message(with_disk_prompts)
    with_side_number_error = _patched_side_number_error_message(
        with_disk_set_error
    )
    with_wrong_disk_message = _patched_wrong_disk_message(
        with_side_number_error
    )
    with_start_prompt = _patched_start_prompt(
        with_wrong_disk_message, START_PROMPT_OFFSET, "NOV2"
    )
    with_save_prompt = _patched_save_prompt(with_start_prompt)
    with_load_prompt = _patched_load_prompt(with_save_prompt)
    with_opaque_clears = _patched_opaque_text_clears(with_load_prompt)
    with_extended_dictionary = _patched_extended_dictionary_decoder(
        with_opaque_clears
    )
    return _patched_single_choice_b_guard(with_extended_dictionary)


def patched_nov4_ui(data: bytes) -> bytes:
    """Patch the live-menu NOV4 copy of ``さいしょから`` with ``START``.

    Args:
        data: Compatible NOV4 component bytes.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If the prompt is missing, nonunique, or size-incompatible.

    The Japanese and English records both occupy six packed bytes, so neither
    the following NOV4 data nor any FDS file offsets move.
    """
    with_start_prompt = _patched_start_prompt(
        data, NOV4_START_PROMPT_OFFSET, "NOV4"
    )
    return _patched_nov4_load_prompt(with_start_prompt)


def patched_tt1a_ui(data: bytes) -> bytes:
    """Translate TT1A blood-type, month, and confirmation choices.

    Args:
        data: TT1A scenario/program bank containing the Japanese slots.

    Returns:
        A same-size copy preserving every subsequent fixed address.

    Raises:
        UiPatchError: If a configured replacement changes packed size, the
            bank is short, or a source slot differs.
        EnglishTextError: If configured choice text cannot be encoded.
    """
    result = bytearray(data)
    for offset, original, english in (
        *TT1A_BLOOD_TYPE_PATCHES,
        *TT1A_MONTH_PATCHES,
        *TT1A_CONFIRMATION_PATCHES,
    ):
        # Mixed case often packs more tightly than an all-caps Japanese-era
        # label.  Fill the recovered record allocation with invisible spaces
        # instead of making capitalization depend on a hand-counted suffix.
        symbols = encode_english(english)
        common_space = encode_english(" ")[0]
        while len(pack_records((symbols,))) < len(original):
            symbols = (*symbols, common_space)
        replacement = pack_records((symbols,))
        if len(replacement) != len(original):
            raise UiPatchError(
                f"TT1A choice label at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end:
            raise UiPatchError("TT1A is too short for the fixed choice tables")
        if result[offset:end] != original:
            raise UiPatchError(
                f"TT1A choice label at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _tt2_dictionary(data: bytes) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode the bank dictionary shared by all fixed UI table patchers.

    Args:
        data: Rebuilt scenario bank whose pointer at ``$0016`` is valid.

    Returns:
        Exactly :data:`TT2_DICTIONARY_ENTRIES` aligned dictionary records.

    Raises:
        UiPatchError: If the bank is too short or its dictionary pointer lies
            outside the bank.
        PackedTextError: If the dictionary stream is truncated.

    The historical function name remains for compatibility, but the layout is
    shared by TT1B, T22, TT3-TT6, and T25 after scenario insertion.
    """
    pointer_end = TT2_DICTIONARY_POINTER_OFFSET + 2
    if len(data) < pointer_end:
        raise UiPatchError("TT2 is too short for its dictionary pointer")
    address = int.from_bytes(
        data[TT2_DICTIONARY_POINTER_OFFSET:pointer_end], "little"
    )
    offset = address - TT2_LOAD_ADDRESS
    if offset < 0 or offset >= len(data):
        raise UiPatchError("TT2 dictionary pointer is outside the bank")
    reader = BitReader(data, offset * 8)
    records: list[tuple[PackedSymbol, ...]] = []
    while len(records) < TT2_DICTIONARY_ENTRIES:
        record: list[PackedSymbol] = []
        while True:
            symbol = decode_symbol(reader)
            if symbol.kind is SymbolKind.SEPARATOR:
                reader.align_to_next_byte()
                records.append(tuple(record))
                break
            record.append(symbol)
    return tuple(records)


def _encode_with_dictionary(
    text: str,
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[PackedSymbol, ...]:
    """Encode one label using the cheapest matching flat dictionary entries.

    Args:
        text: Supported English label without record separators.
        dictionary: Ordered flat English dictionary already present in the
            rebuilt bank.

    Returns:
        The minimum-bit symbol sequence for ``text`` under that dictionary.

    Raises:
        EnglishTextError: If ``text`` contains an unsupported character/tag.

    Dynamic programming chooses, at each literal position, between emitting
    the next symbol and any dictionary entry that matches the remaining text.
    The cost is measured in native bits, so the result is the shortest symbol
    sequence for the fixed dictionary rather than a greedy word replacement.
    Ties retain Python's tuple-order minimum, making identical input
    deterministic.
    """
    source = encode_english(text)
    normalized_dictionary = tuple(
        tuple(
            PackedSymbol(symbol.kind, symbol.value, 0, 0) for symbol in entry
        )
        for entry in dictionary
    )
    best: list[tuple[int, tuple[PackedSymbol, ...]] | None] = [None] * (
        len(source) + 1
    )
    best[len(source)] = (0, ())
    for position in range(len(source) - 1, -1, -1):
        suffix = best[position + 1]
        if suffix is None:
            raise UiPatchError(
                "dictionary encoder reached an impossible suffix state"
            )
        choices = [
            (
                symbol_bit_length(source[position]) + suffix[0],
                (source[position], *suffix[1]),
            )
        ]
        for index, entry in enumerate(normalized_dictionary, start=1):
            end = position + len(entry)
            if tuple(source[position:end]) != entry:
                continue
            tail = best[end]
            if tail is None:
                raise UiPatchError(
                    "dictionary encoder reached an impossible tail state"
                )
            choices.append(
                (
                    9 + tail[0],
                    (
                        PackedSymbol(SymbolKind.DICTIONARY, index, 0, 0),
                        *tail[1],
                    ),
                )
            )
        best[position] = min(choices, key=lambda choice: choice[0])
    encoded = best[0]
    if encoded is None:
        raise UiPatchError("dictionary encoder produced no result")
    return encoded[1]


def _encode_at_exact_record_size(
    text: str,
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    target_size: int,
) -> bytes:
    """Encode one label without changing the following record's address.

    Args:
        text: Visible English label.
        dictionary: Bank dictionary used for compression.
        target_size: Exact packed allocation of the original record.

    Returns:
        One packed record of exactly ``target_size`` bytes.

    Raises:
        UiPatchError: If the shortest representation already exceeds the slot
            or zero-or-more trailing spaces cannot reach the exact allocation.
        EnglishTextError: If the label cannot be encoded.

    The renderer does not display trailing common-space tiles. Add as many
    as are necessary to consume the record's original byte allocation after
    the shortest dictionary-aware encoding has been chosen.
    """
    encoded = _encode_with_dictionary(text, dictionary)
    common_space = encode_english(" ")[0]
    while len(pack_records((encoded,))) < target_size:
        encoded = (*encoded, common_space)
    packed = pack_records((encoded,))
    if len(packed) != target_size:
        raise UiPatchError(
            f"fixed label {text!r} needs {len(packed)} bytes but its slot is "
            f"{target_size} bytes"
        )
    return packed


def _parse_fixed_label_fallbacks(
    specification: str,
) -> Mapping[int, str]:
    """Decode one compact, audited fixed-label fallback specification."""
    return MappingProxyType(
        {
            int(index): label
            for item in specification.split("|")
            for index, _, label in (item.partition("="),)
        }
    )


# The full-word tuples are the canonical release target. These compact labels
# remain only for the standalone, size-neutral ``ui-patch`` compatibility path,
# whose old two-to-six-byte record slots and native 31-entry dictionary cannot
# represent every full label at once. The canonical release repacks the
# recovered page-indexed tables and does not select these fallbacks.
FIXED_TEXT_BLOCKED_FALLBACKS: Mapping[str, Mapping[int, str]] = (
    MappingProxyType(
        {
            "T22": _parse_fixed_label_fallbacks(
                "0=SE|3=AS|6=Jailer|7=WMN|8=RB|9=KY|11=OF|14=GT|15=PS|17=Chino|"
                "18=WL|20=HL|21=JAL|23=B|24=PPR|25=BCK|27=Jeanne|28=Bishop|29=Lugot|"
                "30=CROWD|31=PRIS"
            ),
            "T25": _parse_fixed_label_fallbacks(
                "0=SE|4=SK|5=SOL|6=COFE|7=OFR|8=MANR|10=WGN|13=LINC|22=GT|25=DRAW|"
                "27=2ND|29=P|30=AS|36=COY|37=RV|39=COY1|40=COY2|41=COY3"
            ),
            "TT1B": _parse_fixed_label_fallbacks(
                "0=Look|3=Sky|5=Museum|6=Sign|7=Body|9=West|14=Pot|23=Praise|25=Eyes|"
                "26=Nose|27=Ears|28=Chest|30=Map|31=North|32=House|37=Picture|42=Back|"
                "43=Simon|45=Ask|46=Church|47=Priest|48=Member|50=Devil"
            ),
            "TT2": _parse_fixed_label_fallbacks(
                "0=SE|2=GT|4=AS|5=SN|8=PIER|9=BOD|10=GLS|13=DR|14=RB|15=KY|22=BT|23=ON|"
                "24=OF|26=DAM|27=JERUS|28=CRI|29=100|30=PAC|31=MER|32=COM|33=ACT|34=CRK|"
                "35=GDE|36=ZOI|37=GEL|38=GLD|40=VINCI|41=CST|42=PAL|45=THA|46=TLS|49=Chino|51=WT|"
                "53=Lugot|"
                "56=AL|57=Guard|58=CROWD|59=BLD|61=TN|63=WMN|65=Bishop|66=Jeanne"
            ),
            "TT3A": _parse_fixed_label_fallbacks(
                "0=SE|2=GT|6=BOD|7=POCKT|8=PLI|13=WL|16=PS|19=FL|21=RAL|22=Frankie|26=SHT|"
                "27=RB|28=MATT|31=SHWR|32=WR|33=TUN|34=SL|35=FR|36=BCK|37=SOL|42=FNC|43=WD|"
                "44=BCH|46=SIM|51=GRT|52=CRM|53=BRN|55=JN|56=N|58=W|60=FNT|61=BT|62=SW|64=S|"
                "66=PP|67=BCK|69=Old man|70=Gestapo|71=GHETO|72=RESID|73=RESIST|74=REGSTR|"
                "80=DLN|81=BELMO|82=PHIL|84=MONTY|85=PTTN|86=EISEN|87=ROOSVLT|88=CHRCHL|"
                "89=MACARTH|90=YS|92=BRM|94=WMN"
            ),
            "TT3B": _parse_fixed_label_fallbacks(
                "0=SE|2=GT|7=SIM|8=WMN|11=Schmidt|13=Fight|16=AS|17=RD|18=TX|19=Hitler|"
                "20=Cougar"
            ),
            "TT4": _parse_fixed_label_fallbacks(
                "0=SE|4=S|7=STAT|8=PRST|9=HD|18=CONT|19=O|21=BL|22=GV|27=BLD|28=MRCH|30=BOD|"
                "31=SL|32=BY|33=H|35=TMPL|38=DAR|39=YTH|42=LVL|45=RB|51=N|53=W|54=GRL|55=MOM|"
                "57=DOKU|58=JIAO|61=RD|62=TK|63=SOL|64=SP|66=BCK|68=SOCR|69=PYTH|71=HEROD|"
                "72=HOM|73=SE|76=NIC|77=POL|78=ARIS|79=IMEL|80=JAKAR|81=SPAR|82=DAEDAL|"
                "83=HERAC|84=NAPOL|85=GORBY|86=AGAM|87=KAN|88=PARTSN|89=AISNO|90=PARTH|"
                "91=STR|92=MEL|96=COFE"
            ),
            "TT5": _parse_fixed_label_fallbacks(
                "0=SE|2=AS|5=BL|8=RUIN|9=TRACK|10=N|12=W|13=GT|17=MN|18=WD|19=DRAW|22=CT|"
                "23=YS|30=COT|34=4B|35=6B|36=8B|37=10B|38=25|39=26|40=27|41=28|42=1P|43=2P|"
                "44=3P|45=4P|46=60 CM|47=65 CM|48=70 CM|49=75 CM|50=30M|51=60M|52=90M|"
                "53=120M|54=TM|55=TRDR|57=CAV|59=WT|60=BK|61=DEWI|62=STOWE|63=AKINO|64=MARY|"
                "66=KILAU|68=RUSH|69=OIWA|70=PROJ|73=CAM|74=AIR|76=BCK|77=ANS|78=PROB|79=CW|"
                "80=SHP|81=PG|84=3|88=7|89=8|92=0|93=1|94=2|95=3|96=4|97=5|99=6|100=7|101=8|"
                "102=9|107=SM|108=MANR|111=STAT"
            ),
            "TT6A": _parse_fixed_label_fallbacks(
                "0=SE|1=AS|2=SM|6=SK|7=BOD|8=JOS|11=SL|12=VL|13=DR|17=WL|18=TRGH|19=RP|"
                "22=HL|23=R H|24=L HSE|25=RV|28=BL|30=BRC|31=NECK|32=WT|36=TOOL|37=BD|"
                "38=ON BD"
            ),
            "TT6B": _parse_fixed_label_fallbacks(
                "0=SE|1=AS|2=SM|6=JOS|8=BOD|9=SL|10=GLR|12=TONG|17=CML|19=N|21=W|22=S|"
                "23=FWD|24=BCK|28=TRGH|29=HR|30=SHP|31=CW|33=WIS|34=KNOW|36=BAL|37=JHV|"
                "39=JORDN|40=SYR|43=SOLO|44=SAM|45=JAC|46=ISC|47=SADM|48=ABRAM|49=SATN|"
                "50=CST|51=ZORO|58=PRSE"
            ),
            "TT6C": _parse_fixed_label_fallbacks(
                "0=SE|1=D|3=GT|4=JR|6=AS|10=JOS|12=B|14=MY BOD|15=KSH|16=BOD|17=TBELT|"
                "22=GND|23=HL|24=PNL|25=YS|26=LD|27=N|29=W|30=S|31=RD|33=P|34=TX|35=OT|"
                "36=4|37=5|38=6|39=7|40=Cougar|43=Berger|44=GLZR|45=SMT|46=TAVN|47=TLR|"
                "48=CATH|49=MYLEN|50=LRA|51=ISABL|52=MOROC|53=REBEC|55=TRAD|56=AUST|57=FRAN|"
                "58=SWIS|59=BELG|60=PLANT|62=DOKU|63=SENBR|64=DAEDL|65=CENTA|66=ATL|67=CERBR|"
                "70=TM|71=JM|72=SRW|73=COY|74=REIN|80=MAGDA|81=NZR|82=BETH|83=JERUS|84=BISH|"
                "86=HITLR|88=JEAN|89=ALEX|90=LINC|93=R"
            ),
        }
    )
)


@dataclass(frozen=True)
class FixedRecordTableSpec:
    """Describe one source-locked scenario menu table for full repacking."""

    start: int
    end: int
    source_sha256: str
    records: tuple[str, ...]


FIXED_RECORD_TABLE_SPECS: Mapping[str, FixedRecordTableSpec] = (
    MappingProxyType(
        {
            bank_name: FixedRecordTableSpec(
                start=getattr(
                    _fixed_tables, f"{bank_name}_FIXED_TEXT_START_OFFSET"
                ),
                end=getattr(
                    _fixed_tables, f"{bank_name}_FIXED_TEXT_END_OFFSET"
                ),
                source_sha256=getattr(
                    _fixed_tables,
                    f"{bank_name}_FIXED_TEXT_SOURCE_SHA256",
                ),
                records=getattr(
                    _fixed_tables, f"{bank_name}_FIXED_TEXT_RECORDS"
                ),
            )
            for bank_name in (
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
            )
        }
    )
)

FIXED_RECORD_TABLE_POINTER_OFFSET = 0x14
FIXED_RECORD_PAGE_POINTER_OFFSET = 0x1A
FIXED_RECORD_FOLLOWING_POINTER_OFFSETS = (0x10, 0x12)
FIXED_RECORDS_PER_PAGE = 32


def fixed_record_table_page_pointer_bytes(bank_name: str) -> int:
    """Return the native page-index byte count following one menu table."""
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    return 2 * ((len(spec.records) - 1) // FIXED_RECORDS_PER_PAGE)


def fixed_record_table_combined_capacity(
    data: bytes,
    *,
    bank_name: str,
    load_address: int,
    group_zero_offset: int,
    dictionary_end_offset: int,
) -> int:
    """Measure bytes jointly available to the menu and scenario compressor."""
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    following_address = int.from_bytes(
        data[
            FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[
                0
            ] : FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[0]
            + 2
        ],
        "little",
    )
    following_offset = following_address - load_address
    if not spec.end <= following_offset <= group_zero_offset:
        raise UiPatchError(
            f"{bank_name} following table pointer is outside the recovered prefix"
        )
    return (following_offset - spec.start) + (
        dictionary_end_offset - group_zero_offset
    )


def relocated_fixed_record_table_bank(
    data: bytes,
    *,
    bank_name: str,
    load_address: int,
    group_zero_offset: int,
    records: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[bytes, int]:
    """Repack a complete full-word menu table and shift its following data.

    The renderer addresses record zero through header word ``$A214`` and uses
    the page-pointer table at ``$A21A`` for records 32, 64, and 96. The two
    data tables between that page index and scenario group zero are movable
    and have their only recovered base pointers at ``$A210`` and ``$A212``.
    Repacking therefore changes four header words while leaving the fixed tail
    and complete overlay size untouched.
    """
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    if len(records) != len(spec.records):
        raise UiPatchError(
            f"{bank_name} expected {len(spec.records)} fixed records, "
            f"got {len(records)}"
        )
    source = data[spec.start : spec.end]
    if len(source) != spec.end - spec.start:
        raise UiPatchError(
            f"{bank_name} is too short for its fixed text table"
        )
    if hashlib.sha256(source).hexdigest().upper() != spec.source_sha256:
        raise UiPatchError(
            f"{bank_name} fixed text table does not match the known source"
        )

    def header_offset(pointer_offset: int) -> int:
        """Convert one recovered header word to a file-relative offset."""
        address = int.from_bytes(
            data[pointer_offset : pointer_offset + 2],
            "little",
        )
        return address - load_address

    if header_offset(FIXED_RECORD_TABLE_POINTER_OFFSET) != spec.start:
        raise UiPatchError(f"{bank_name} fixed-table base pointer changed")
    if header_offset(FIXED_RECORD_PAGE_POINTER_OFFSET) != spec.end:
        raise UiPatchError(f"{bank_name} fixed-table page pointer changed")

    page_pointer_bytes = fixed_record_table_page_pointer_bytes(bank_name)
    old_following_offset = header_offset(
        FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[0]
    )
    if old_following_offset != spec.end + page_pointer_bytes:
        raise UiPatchError(
            f"{bank_name} fixed-table page index has an unexpected size"
        )
    second_following_offset = header_offset(
        FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[1]
    )
    if not old_following_offset <= second_following_offset < group_zero_offset:
        raise UiPatchError(
            f"{bank_name} secondary table pointer is outside its recovered block"
        )

    original_starts = _record_starts(source, len(spec.records))
    expected_source_pages = b"".join(
        (load_address + spec.start + original_starts[index]).to_bytes(
            2,
            "little",
        )
        for index in range(
            FIXED_RECORDS_PER_PAGE, len(records), FIXED_RECORDS_PER_PAGE
        )
    )
    actual_source_pages = data[spec.end : old_following_offset]
    if actual_source_pages != expected_source_pages:
        raise UiPatchError(f"{bank_name} fixed-table page index changed")

    secondary_low = load_address + old_following_offset
    secondary_high = load_address + group_zero_offset
    if any(
        secondary_low
        <= int.from_bytes(data[offset : offset + 2], "little")
        < secondary_high
        for offset in range(old_following_offset, group_zero_offset - 1)
    ):
        raise UiPatchError(
            f"{bank_name} secondary prefix contains an unrelocated internal pointer"
        )

    packed_records = pack_records(records)
    record_starts = _record_starts(packed_records, len(records))
    new_page_offset = spec.start + len(packed_records)
    new_pages = b"".join(
        (load_address + spec.start + record_starts[index]).to_bytes(
            2,
            "little",
        )
        for index in range(
            FIXED_RECORDS_PER_PAGE, len(records), FIXED_RECORDS_PER_PAGE
        )
    )
    if len(new_pages) != page_pointer_bytes:
        raise UiPatchError(f"{bank_name} rebuilt page index changed size")
    new_following_offset = new_page_offset + len(new_pages)
    delta = new_following_offset - old_following_offset
    new_group_zero_offset = group_zero_offset + delta
    if new_group_zero_offset <= new_following_offset:
        raise UiPatchError(f"{bank_name} relocated prefix is malformed")

    prefix = bytearray(data[: spec.start])
    prefix.extend(packed_records)
    prefix.extend(new_pages)
    prefix.extend(data[old_following_offset:group_zero_offset])
    if len(prefix) != new_group_zero_offset:
        raise UiPatchError(
            f"{bank_name} relocated prefix size is inconsistent"
        )
    prefix[
        FIXED_RECORD_PAGE_POINTER_OFFSET : FIXED_RECORD_PAGE_POINTER_OFFSET + 2
    ] = (load_address + new_page_offset).to_bytes(2, "little")
    for pointer_offset in FIXED_RECORD_FOLLOWING_POINTER_OFFSETS:
        old_address = int.from_bytes(
            data[pointer_offset : pointer_offset + 2],
            "little",
        )
        prefix[pointer_offset : pointer_offset + 2] = (
            old_address + delta
        ).to_bytes(2, "little")

    if len(prefix) > len(data):
        raise UiPatchError(f"{bank_name} relocated prefix exceeds the bank")
    relocated = bytes(prefix) + data[len(prefix) :]
    if len(relocated) != len(data):
        raise UiPatchError(f"{bank_name} relocation changed the bank size")
    return relocated, new_group_zero_offset


def _patched_fixed_record_table(
    data: bytes,
    *,
    start: int,
    end: int,
    source_sha256: str,
    records: tuple[str, ...],
    component: str,
) -> bytes:
    """Translate a fixed table while preserving every record boundary.

    Args:
        data: Rebuilt scenario bank with its final English dictionary.
        start: File offset of the fixed table.
        end: Exclusive fixed-table boundary.
        source_sha256: Expected hash of the complete Japanese source table.
        records: English replacements in exact record order.
        component: Bank name used in diagnostics.

    Returns:
        A same-size bank copy preserving the complete fixed-table footprint and
        every record start.

    Raises:
        UiPatchError: If the table is missing/unknown, record framing differs,
            any translation cannot fit its exact slot, or total size changes.
        PackedTextError: If source or replacement packing is invalid.
        EnglishTextError: If configured text cannot be encoded.

    The complete Japanese table is hash-checked, decoded into byte-aligned
    record slots, and rebuilt with the bank's already-generated English
    dictionary.  Each replacement is independently padded to its original slot
    size before the complete table is written back.
    """
    source = data[start:end]
    if len(source) != end - start:
        raise UiPatchError(
            f"{component} is too short for its fixed text table"
        )
    if hashlib.sha256(source).hexdigest().upper() != source_sha256:
        raise UiPatchError(
            f"{component} fixed text table does not match the known source"
        )

    original_records, parsed_end = split_records(source, limit=len(records))
    if parsed_end != len(source):
        raise UiPatchError(
            f"{component} fixed text table has unexpected trailing bytes"
        )
    original_sizes = tuple(
        split_records(source, offset=offset, limit=1)[1] - offset
        for offset in _record_starts(source, len(original_records))
    )
    dictionary = _tt2_dictionary(data)
    replacement_records: list[bytes] = []
    for index, (text, size) in enumerate(
        zip(records, original_sizes, strict=True)
    ):
        try:
            replacement_records.append(
                _encode_at_exact_record_size(text, dictionary, size)
            )
        except UiPatchError:
            fallback = FIXED_TEXT_BLOCKED_FALLBACKS.get(component, {}).get(
                index
            )
            if fallback is None:
                raise
            replacement_records.append(
                _encode_at_exact_record_size(fallback, dictionary, size)
            )
    replacement = b"".join(replacement_records)
    if len(replacement) != len(source):
        raise UiPatchError(
            f"translated {component} fixed text table changed size "
            f"({len(source)} -> {len(replacement)})"
        )
    result = bytearray(data)
    result[start:end] = replacement
    return bytes(result)


def _record_starts(data: bytes, count: int) -> tuple[int, ...]:
    """Locate each record start in an aligned packed table.

    Args:
        data: Packed table beginning at record zero.
        count: Number of records to locate.

    Returns:
        ``count`` byte offsets relative to ``data``.

    Raises:
        PackedTextError: If fewer than ``count`` complete records exist.
    """
    starts: list[int] = []
    offset = 0
    for _ in range(count):
        starts.append(offset)
        _, offset = split_records(data, offset=offset, limit=1)
    return tuple(starts)


def patched_tt2_ui(data: bytes) -> bytes:
    """Translate TT2's fixed command, object, and history-quiz table.

    Args:
        data: Rebuilt TT2 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the Japanese table is unknown or any record cannot
            occupy its exact original slot.
    """
    return _patched_fixed_record_table(
        data,
        start=TT2_FIXED_TEXT_START_OFFSET,
        end=TT2_FIXED_TEXT_END_OFFSET,
        source_sha256=TT2_FIXED_TEXT_SOURCE_SHA256,
        records=TT2_FIXED_TEXT_RECORDS,
        component="TT2",
    )


def patched_tt1b_ui(data: bytes) -> bytes:
    """Translate TT1B's fixed command, object, and interaction table.

    Args:
        data: Rebuilt TT1B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the Japanese table is unknown or any record cannot
            occupy its exact original slot.
    """
    return _patched_fixed_record_table(
        data,
        start=TT1B_FIXED_TEXT_START_OFFSET,
        end=TT1B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT1B_FIXED_TEXT_SOURCE_SHA256,
        records=TT1B_FIXED_TEXT_RECORDS,
        component="TT1B",
    )


def patched_t22_ui(data: bytes) -> bytes:
    """Translate T22's fixed command and object-name table.

    Args:
        data: Rebuilt T22 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=T22_FIXED_TEXT_START_OFFSET,
        end=T22_FIXED_TEXT_END_OFFSET,
        source_sha256=T22_FIXED_TEXT_SOURCE_SHA256,
        records=T22_FIXED_TEXT_RECORDS,
        component="T22",
    )


def patched_tt3a_ui(data: bytes) -> bytes:
    """Translate TT3A's fixed command, object, and history-quiz table.

    Args:
        data: Rebuilt TT3A bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT3A_FIXED_TEXT_START_OFFSET,
        end=TT3A_FIXED_TEXT_END_OFFSET,
        source_sha256=TT3A_FIXED_TEXT_SOURCE_SHA256,
        records=TT3A_FIXED_TEXT_RECORDS,
        component="TT3A",
    )


def patched_tt3b_ui(data: bytes) -> bytes:
    """Translate TT3B's fixed command, object, and battle-action table.

    Args:
        data: Rebuilt TT3B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT3B_FIXED_TEXT_START_OFFSET,
        end=TT3B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT3B_FIXED_TEXT_SOURCE_SHA256,
        records=TT3B_FIXED_TEXT_RECORDS,
        component="TT3B",
    )


def patched_tt4_ui(data: bytes) -> bytes:
    """Translate TT4's fixed command, treatment, and quiz table.

    Args:
        data: Rebuilt TT4 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT4_FIXED_TEXT_START_OFFSET,
        end=TT4_FIXED_TEXT_END_OFFSET,
        source_sha256=TT4_FIXED_TEXT_SOURCE_SHA256,
        records=TT4_FIXED_TEXT_RECORDS,
        component="TT4",
    )


def patched_tt5_ui(data: bytes) -> bytes:
    """Translate TT5's fixed command, puzzle, and history-quiz table.

    Args:
        data: Rebuilt TT5 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT5_FIXED_TEXT_START_OFFSET,
        end=TT5_FIXED_TEXT_END_OFFSET,
        source_sha256=TT5_FIXED_TEXT_SOURCE_SHA256,
        records=TT5_FIXED_TEXT_RECORDS,
        component="TT5",
    )


def patched_t25_ui(data: bytes) -> bytes:
    """Translate T25's fixed mansion and flooded-island action table.

    Args:
        data: Rebuilt T25 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=T25_FIXED_TEXT_START_OFFSET,
        end=T25_FIXED_TEXT_END_OFFSET,
        source_sha256=T25_FIXED_TEXT_SOURCE_SHA256,
        records=T25_FIXED_TEXT_RECORDS,
        component="T25",
    )


def patched_tt6a_ui(data: bytes) -> bytes:
    """Translate TT6A's fixed donkey-action and Nazareth object table.

    Args:
        data: Rebuilt TT6A bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT6A_FIXED_TEXT_START_OFFSET,
        end=TT6A_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6A_FIXED_TEXT_SOURCE_SHA256,
        records=TT6A_FIXED_TEXT_RECORDS,
        component="TT6A",
    )


def patched_tt6b_ui(data: bytes) -> bytes:
    """Translate TT6B's fixed travel, quiz, and animal-action table.

    Args:
        data: Rebuilt TT6B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT6B_FIXED_TEXT_START_OFFSET,
        end=TT6B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6B_FIXED_TEXT_SOURCE_SHA256,
        records=TT6B_FIXED_TEXT_RECORDS,
        component="TT6B",
    )


def patched_tt6c_ui(data: bytes) -> bytes:
    """Translate TT6C's fixed finale-action and retrospective-quiz table.

    Args:
        data: Rebuilt TT6C bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """
    return _patched_fixed_record_table(
        data,
        start=TT6C_FIXED_TEXT_START_OFFSET,
        end=TT6C_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6C_FIXED_TEXT_SOURCE_SHA256,
        records=TT6C_FIXED_TEXT_RECORDS,
        component="TT6C",
    )
