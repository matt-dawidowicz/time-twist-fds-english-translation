"""Build and install the English title card in the NOV4 overlay.

NOV4 contains the title-state 6502 program, two RLE-compressed nametables,
background CHR, and the source tiles/metasprites for the animated clock hands.
The English logo needs more distinct patterns than the original one-table
layout, so this module reuses the game's existing mid-screen pattern-table
split and relocates the title stream plus small helper routines.

The conversion is deterministic and revision-guarded.  Source size, selected
instructions, asset boundaries, and hashes must match before any patch is
returned.  Post-build checks decode relocated streams and prove that clock
animation bytes remain unchanged.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .font import PIXEL_FONT_5X7

# ---------------------------------------------------------------------------
# Recovered NOV4 memory/file layout and source guards
# ---------------------------------------------------------------------------

NOV4_LOAD_ADDRESS = 0xA200
NOV4_SOURCE_SIZE = 0x2375
TITLE_POINTER_OFFSET = 0x01BC
TITLE_POINTER_SOURCE = bytes.fromhex("A9 5E A2 A8")
PPUCTRL_INIT_OFFSET = 0x0176
PPUCTRL_INIT_SOURCE = bytes.fromhex("A5 FF 09 10 29 F7")
TITLE_EXIT_OFFSET = 0x022F
TITLE_EXIT_SOURCE = bytes.fromhex("A9 02 A2 03 4C 19 61")
BACKGROUND_TAIL_UPLOAD_OFFSET = 0x0296
BACKGROUND_TAIL_UPLOAD_SOURCE = bytes.fromhex(
    "A0 1F A9 B0 A2 04 20 AF EB 92 BA"
)
PHASE_ZERO_UPLOAD_OFFSET = 0x02AC
PHASE_ZERO_UPLOAD_SOURCE = bytes.fromhex("A0 0F A9 B0 A2 04 20 AF EB 92 BA")
SLIDE_PREP_CALL_OFFSET = 0x02E4
SLIDE_PREP_CALL_SOURCE = bytes.fromhex("20 74 AB")
TITLE_TRANSITION_CALL_OFFSET = 0x038E
TITLE_TRANSITION_CALL_SOURCE = bytes.fromhex("A9 01 8D E1 07 20 E0 6F")
SLIDE_PALETTE_COLOR1_OFFSET = 0x0995
SLIDE_PALETTE_COLOR1_SOURCE = bytes((0x0F,))
SLIDE_PALETTE_COLOR1_PATCH = bytes((0x30,))
FINAL_NAMETABLE_START = 0x065E
FINAL_NAMETABLE_END = 0x0809
SECOND_NAMETABLE_START = 0x0809
SECOND_NAMETABLE_END = 0x094C
TITLE_CHR_OFFSET = 0x09D2
TITLE_CHR_SIZE = 0x1000
CLOCK_SOURCE_TILE = 0xEC
CLOCK_SOURCE_OFFSET = TITLE_CHR_OFFSET + CLOCK_SOURCE_TILE * 16
CLOCK_SOURCE_END = TITLE_CHR_OFFSET + TITLE_CHR_SIZE
CLOCK_METASPRITE_START = 0x047A
CLOCK_METASPRITE_END = 0x059A
CLOCK_HAND_ORIGINS_OFFSET = 0x03CA
CLOCK_HAND_ORIGINS_SOURCE = bytes.fromhex("78 00 37 04 80 00 3F")
CLOCK_HAND_ORIGINS_PATCH = bytes.fromhex("68 00 2F 04 70 00 37")
NOV3_LOAD_ADDRESS = 0xD7B5
SPLIT_TILE_ROW = 16
# Every background slot below the clock-owned $EC-$FF tail is now used.  The
# approved native artwork is deliberately tile-harmonized to this exact limit.
TOP_TILE_COUNT = CLOCK_SOURCE_TILE
BOTTOM_TILE_COUNT = 0x37
BOTTOM_CHR_SIZE = BOTTOM_TILE_COUNT * 16
BACKGROUND_TAIL_SIZE = 0
NINTENDO_FIRST_TILE = 0xB0
NINTENDO_TILE_COUNT = 0x26
NINTENDO_CHR_SIZE = NINTENDO_TILE_COUNT * 16
# The slide nametable contains the complete native wordmark.  Its temporary
# Nintendo tile IDs are restored once, immediately before the original swipe.
SLIDE_TITLE_TILE_COLUMNS = 32
INITIAL_CHR_LOADER_SIZE = 12
# The pre-slide helper must restore the scroll origin before rendering is
# visible again.  Its sixteen helper bytes are paid for by removing a duplicate
# 608-byte restore copy: both title states now DMA the authoritative, already
# patched base CHR at $B6D2.  It clears and later restores the $1C PPUMASK
# mirror but deliberately leaves $2001 blank.  The next NMI applies the new
# scroll/nametable state before copying $1C back to $2001; otherwise one frame
# can show the old Nintendo nametable with the restored English-title CHR.
# Keep the aggregate NOV4 payload at 12,214 bytes; a prior payload growth trial
# caused FDS Disk Error 24.
SLIDE_PREP_ORIGIN_AND_MASK_SIZE = 16
SLIDE_PREP_SIZE = 43 + SLIDE_PREP_ORIGIN_AND_MASK_SIZE
RESTORE_WORKSPACE_SIZE = NINTENDO_CHR_SIZE - SLIDE_PREP_ORIGIN_AND_MASK_SIZE
TITLE_TRANSITION_SIZE = 97
# Keep the screen blank while the title-only lower CHR table and raster split
# are dismantled.  Without the two PPUMASK stores below, the lower time-machine
# tile IDs are briefly rendered through the upper logo CHR table after START,
# producing a visibly scrambled machine.  Clear the $1C mirror first so an NMI
# between the two stores cannot restore the old visible mask.
TITLE_EXIT_HELPER = bytes.fromhex(
    "A9 00 85 1C 8D 01 20 8D 22 40 85 48 85 4F 85 9C "
    "A5 FF 09 10 85 FF 8D 00 20 "
    "A9 02 A2 03 4C 19 61"
)
TITLE_EXIT_SIZE = len(TITLE_EXIT_HELPER)

# Exact horizontal origins written by NOV4 states 3-5.  $57 supplies the fine
# scroll and bit zero of $58 selects the neighboring horizontal nametable.
SLIDE_SCROLL_ORIGINS = (
    0x1F0,
    0x01C,
    0x1D8,
    0x034,
    0x1C0,
    0x04C,
    0x1A8,
    0x064,
    0x190,
    0x07C,
    0x178,
    0x094,
    0x160,
    0x0AC,
    0x148,
    0x0C4,
    0x130,
    0x0DC,
    0x118,
    0x0F4,
    0x100,
)

FINAL_NAMETABLE_SOURCE_SHA256 = (
    "F01695FBF94A623BF2ADFD2172B6DB05415B33C0AB12DC4239B0C34167E06363"
)
SECOND_NAMETABLE_SOURCE_SHA256 = (
    "81DD3C65691C753EB28CC527C04E6561C0A4B67CF82D7848112028B8851E710E"
)
TITLE_CHR_SOURCE_SHA256 = (
    "B9D97C43F06079E83306A6573FAD96B3986FCEF5615BD1B0515D4E1EEF0E037C"
)
CLOCK_SOURCE_SHA256 = (
    "FE0FD6831D85105474682EB3E455B53BF64493278887F292C1904F4A875ACD2E"
)
CLOCK_METASPRITE_SHA256 = (
    "AC1BC81C837B32B7225319A86E5E5C41D20C3C081C33FB81FC6C742390458670"
)

# ---------------------------------------------------------------------------
# Rendering policy and NES palettes
# ---------------------------------------------------------------------------

DEFAULT_SUBTITLE = "On the Outskirts of History..."
TITLE_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (243, 106, 255),
    (92, 0, 126),
)
GRAY_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (173, 173, 173),
    (102, 102, 102),
)
SPRITE_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (100, 176, 255),
    (21, 95, 217),
)
# State 3 queues the 32 bytes at ROM address $AB7B. The resident palette
# uploader writes that buffer backwards, so these are the four background
# palettes in the order the PPU actually sees them. Palette 1 is the moving
# logo's attribute-selected monochrome palette. The one-byte ROM patch at
# $AB95 makes all three nonzero pattern indices white, so the completed
# monochrome logo has exactly the final colored logo's visible geometry. The
# other three attribute palettes deliberately hide the still-unassembled parts
# of the two scrolled nametables.
SLIDE_BACKGROUND_PALETTES = (
    (0x0F, 0x0F, 0x0F, 0x0F),
    (0x0F, 0x30, 0x30, 0x30),
    (0x0F, 0x0F, 0x0F, 0x0F),
    (0x0F, 0x0F, 0x0F, 0x0F),
)
SLIDE_WHITE_COLOR = 0x30


class TitlePatchError(ValueError):
    """Report incompatible NOV4 data, invalid artwork, or exhausted title space.

    Title helpers raise this exception when fingerprints, dimensions, palette
    assumptions, tile budgets, or address ranges do not match the supported
    source.  These checks intentionally fail before returning patch bytes so an
    approximate preview cannot be mistaken for a safe ROM modification.
    """


@dataclass(frozen=True)
class TitleAssets:
    """All generated binary assets needed by :func:`patched_nov4_title`.

    Attributes:
        chr_data: Complete replacement for NOV4's original title CHR region.
        background_chr: Exact upper pattern table used after initialization.
        bottom_chr: Independent lower patterns loaded for the raster split.
        nintendo_chr: Temporary Nintendo-phase patterns for reserved tile IDs.
        restore_chr: Upper-title patterns restored over those temporary IDs.
            This remains the independently verified source slice; runtime
            helpers DMA the identical authoritative base-CHR location rather
            than serializing a duplicate copy into the appended payload.
        final_nametable: Decoded final title-screen nametable and attributes.
        second_nametable: Decoded slide/Nintendo nametable and attributes.
        encoded_final: Native RLE for ``final_nametable``.
        encoded_second: Native RLE for ``second_nametable``.
        approximation_error: Compatibility metric; zero for the exact split
            conversion.

    ``nintendo_chr`` and ``restore_chr`` intentionally share tile IDs across
    non-overlapping title phases. This temporal reuse avoids consuming
    additional pattern-table space without changing the clock-sprite tail.
    """

    chr_data: bytes
    background_chr: bytes
    bottom_chr: bytes
    nintendo_chr: bytes
    restore_chr: bytes
    final_nametable: bytes
    second_nametable: bytes
    encoded_final: bytes
    encoded_second: bytes
    approximation_error: int


def _sha256(data: bytes) -> str:
    """Fingerprint a recovered byte region for compatibility checks.

    Args:
        data: Exact bytes from the source bank or captured asset region.

    Returns:
        The 64-character SHA-256 hexadecimal digest in uppercase.
    """
    return hashlib.sha256(data).hexdigest().upper()


def _pixel_access(image: Image.Image) -> Any:
    """Return Pillow's mode-dependent pixel accessor or fail explicitly."""
    pixels = image.load()
    if pixels is None:
        raise TitlePatchError("Pillow image does not expose pixel access")
    return pixels


def decode_title_rle(
    data: bytes,
    start: int,
    *,
    size: int = 1024,
) -> tuple[bytes, int]:
    """Decode an exact-size NOV4 count-prefix stream.

    Args:
        data: Complete NOV4 data or another buffer containing the stream.
        start: Byte offset of the first encoded value.
        size: Required decoded byte count, normally one 1,024-byte nametable.

    Returns:
        Decoded bytes and the input offset immediately after the final encoded
        value. This fixed-size form does not consume an ``$FF`` terminator.

    Raises:
        TitlePatchError: If the stream ends early, terminates before ``size``,
            contains an invalid run, or expands past the target.
    """
    output = bytearray()
    offset = start
    while len(output) < size:
        if offset >= len(data):
            raise TitlePatchError("title nametable stream ended early")
        value = data[offset]
        offset += 1
        if value == 0xFF:
            raise TitlePatchError(
                f"title nametable terminated after {len(output)} of {size} bytes"
            )
        if value >= 0xC0:
            count = value - 0xC0
            if count == 0 or offset >= len(data):
                raise TitlePatchError("invalid title nametable run")
            output.extend((data[offset],) * count)
            offset += 1
        else:
            output.append(value)
        if len(output) > size:
            raise TitlePatchError(
                "title nametable run exceeds its 1 KB target"
            )
    return bytes(output), offset


def decode_title_stream(data: bytes, start: int) -> tuple[bytes, int]:
    """Decode a complete ``$FF``-terminated NOV4 title stream.

    Args:
        data: Buffer containing the compressed stream.
        start: Byte offset of its first encoded value.

    Returns:
        All decoded bytes and the offset immediately after the terminator.

    Raises:
        TitlePatchError: If no terminator is present, a run is invalid, or the
            decoded output exceeds the defensive 64-KiB limit.

    Unlike :func:`decode_title_rle`, this form does not impose a nametable
    boundary and is used to verify combined relocated streams.
    """
    output = bytearray()
    offset = start
    while True:
        if offset >= len(data):
            raise TitlePatchError("title stream has no $FF terminator")
        value = data[offset]
        offset += 1
        if value == 0xFF:
            return bytes(output), offset
        if value >= 0xC0:
            count = value & 0x3F
            if count == 0 or offset >= len(data):
                raise TitlePatchError("invalid title nametable run")
            output.extend((data[offset],) * count)
            offset += 1
        else:
            output.append(value)
        if len(output) > 0x10000:
            raise TitlePatchError("title stream expands beyond its safe limit")


def encode_title_rle(data: bytes) -> bytes:
    """Encode bytes using NOV4's count-prefix run format.

    Args:
        data: Decoded nametable or stream fragment.

    Returns:
        Encoded bytes without the stream-level ``$FF`` terminator.

    Values at or above ``$C0`` must always use a run prefix because the decoder
    cannot distinguish them from literal run markers. Runs are split at 62
    bytes because ``$FF`` is reserved for stream termination.
    """
    output = bytearray()
    offset = 0
    while offset < len(data):
        value = data[offset]
        run = 1
        while offset + run < len(data) and data[offset + run] == value:
            run += 1
        remaining = run
        while remaining:
            # $FF is the native decoder's end-of-stream marker, so the
            # largest legal run prefix is $FE (62 bytes), not $FF.
            chunk = min(remaining, 62)
            if value >= 0xC0 or chunk >= 3:
                output.extend((0xC0 + chunk, value))
            else:
                output.extend((value,) * chunk)
            remaining -= chunk
        offset += run
    return bytes(output)


def _render_indexed_nametable(
    nametable: bytes, chr_data: bytes
) -> Image.Image:
    """Render one nametable through a single NES pattern table.

    Args:
        nametable: At least 960 tile IDs; attribute bytes are ignored.
        chr_data: NES 2bpp patterns addressed by those tile IDs.

    Returns:
        A 256-by-240 ``L`` image whose pixel values are palette indices 0-3.

    Raises:
        IndexError: If a referenced tile is missing from ``chr_data``.
    """
    image = Image.new("L", (256, 240), 0)
    pixels = _pixel_access(image)
    for tile_y in range(30):
        for tile_x in range(32):
            tile_id = nametable[tile_y * 32 + tile_x]
            tile = chr_data[tile_id * 16 : tile_id * 16 + 16]
            for y in range(8):
                low = tile[y]
                high = tile[y + 8]
                for x in range(8):
                    shift = 7 - x
                    pixels[tile_x * 8 + x, tile_y * 8 + y] = (
                        (low >> shift) & 1
                    ) | (((high >> shift) & 1) << 1)
    return image


def _render_split_nametable(
    nametable: bytes,
    top_chr: bytes,
    bottom_chr: bytes,
) -> Image.Image:
    """Render a nametable with NOV4's recovered mid-screen CHR split.

    Args:
        nametable: Decoded title nametable.
        top_chr: Pattern table used above :data:`SPLIT_TILE_ROW`.
        bottom_chr: Compact lower pattern set loaded into table 0.

    Returns:
        Indexed 256-by-240 title image.

    Raises:
        TitlePatchError: If ``bottom_chr`` exceeds one NES pattern table.

    Missing lower slots are padded with blank patterns for deterministic
    preview behavior.
    """
    if len(bottom_chr) > TITLE_CHR_SIZE:
        raise TitlePatchError("bottom title CHR exceeds one NES pattern table")
    padded_bottom = bottom_chr + bytes(TITLE_CHR_SIZE - len(bottom_chr))
    top = _render_indexed_nametable(nametable, top_chr)
    bottom = _render_indexed_nametable(nametable, padded_bottom)
    top.paste(
        bottom.crop((0, SPLIT_TILE_ROW * 8, 256, 240)), (0, SPLIT_TILE_ROW * 8)
    )
    return top


def _target_to_indices(path: Path) -> Image.Image:
    """Load the approved native NES title authority without resampling it.

    Args:
        path: Exact 256-by-240 indexed title asset.

    Returns:
        A 256-by-240 indexed image using the title/gray palette conventions.

    Raises:
        OSError: If Pillow cannot read the image.
        TitlePatchError: If dimensions, mode, or palette indices differ from
            the reviewed native contract.

    The production path intentionally performs no crop, resize, color
    distance, or hand-erasure operation.  Those subjective steps were used
    once while reconstructing Image 2; their reviewed result is now the source
    of truth.  The clock interior in that asset is already clear for the live
    hand sprites.
    """
    with Image.open(path) as source:
        if source.size != (256, 240) or source.mode not in {"L", "P"}:
            raise TitlePatchError(
                "title authority must be a 256x240 indexed PNG"
            )
        result = (
            source.convert("L")
            if source.mode == "L"
            else Image.new("L", source.size)
        )
        if source.mode == "P":
            result.putdata(source.get_flattened_data())
        else:
            result = source.copy()
    values = set(result.get_flattened_data())
    if not values <= {0, 1, 2, 3}:
        raise TitlePatchError("title authority uses indices outside 0-3")
    if any(result.crop((0, 96, 256, 240)).get_flattened_data()):
        raise TitlePatchError("native title authority must own only rows 0-95")
    return result


def _remove_reference_hand(image: Image.Image) -> None:
    """Erase the frozen hand from a downscaled legacy logo crop.

    Args:
        image: Mutable indexed title image using background color zero.

    Side Effects:
        Clears recovered hand polygons and two quantization remnants in place.
    """
    clock = ImageDraw.Draw(image)
    clock.polygon(((114, 77), (118, 82), (134, 68), (131, 64)), fill=0)
    clock.polygon(((129, 64), (134, 69), (138, 64), (135, 60)), fill=0)
    # Nearest-neighbor reduction leaves two isolated blue-edge pixels that
    # quantize as purple after the larger hand shapes have been removed.
    clock.point(((120, 72), (133, 70)), fill=0)


def _remove_full_reference_hand(image: Image.Image) -> None:
    """Erase the frozen hand from a full-screen reference.

    Args:
        image: Mutable indexed title image using background color zero.

    Side Effects:
        Draws three black cleanup strokes directly into ``image``.
    """
    clock = ImageDraw.Draw(image)
    clock.line(((122, 74), (132, 65)), fill=0, width=4)
    clock.line(((120, 82), (133, 68)), fill=0, width=4)
    clock.line(((133, 68), (138, 63)), fill=0, width=4)


def _draw_clock_numerals(image: Image.Image) -> None:
    """Redraw compact ``12``, ``9``, ``3``, and ``6`` clock labels.

    Args:
        image: Mutable indexed title image.

    Side Effects:
        Clears the four numeral boxes and writes white index-1 pixels in place.

    This helper is used only for the heavily downscaled legacy crop. A
    full-screen reference keeps its authoritative numeral pixels.
    """
    clock = ImageDraw.Draw(image)
    for bounds in (
        (124, 48, 140, 58),
        (109, 63, 118, 76),
        (145, 63, 154, 76),
        (126, 83, 139, 92),
    ):
        clock.rectangle(bounds, fill=0)

    glyphs = {
        "12": (
            "1011111",
            "1010001",
            "1000110",
            "1011000",
            "1011111",
        ),
        "9": (
            "1111",
            "1001",
            "1001",
            "1111",
            "0001",
            "1111",
        ),
        "3": (
            "1111",
            "0001",
            "0011",
            "0001",
            "0001",
            "1111",
        ),
        "6": (
            "11111",
            "10000",
            "11111",
            "10001",
            "11111",
        ),
    }
    positions = {
        "12": (129, 51),
        "9": (113, 66),
        "3": (148, 66),
        "6": (130, 83),
    }
    for label, pattern in glyphs.items():
        origin_x, origin_y = positions[label]
        for row, source_row in enumerate(pattern):
            for column, value in enumerate(source_row):
                if value == "1":
                    image.putpixel((origin_x + column, origin_y + row), 1)


def _draw_text(
    image: Image.Image,
    text: str,
    *,
    x: int,
    y: int,
    color: int,
) -> None:
    """Rasterize deterministic 5x7 text into an indexed image.

    Args:
        image: Mutable Pillow image with integer palette indices.
        text: Text supported by :data:`time_twist.font.PIXEL_FONT_5X7`.
        x: Leftmost pixel of the first character.
        y: Top pixel of every glyph.
        color: Palette index written for set pixels.

    Raises:
        TitlePatchError: If ``text`` contains an unsupported character.

    Side Effects:
        Writes glyph pixels directly into ``image``. Characters advance six
        pixels; spaces advance four and draw nothing.
    """
    pixels = _pixel_access(image)
    cursor = x
    for character in text:
        if character == " ":
            cursor += 4
            continue
        try:
            pattern = PIXEL_FONT_5X7[character]
        except KeyError as error:
            raise TitlePatchError(
                f"title subtitle has no pixel glyph for {character!r}"
            ) from error
        for row, source_row in enumerate(pattern):
            for column, value in enumerate(source_row):
                if value == "1":
                    pixels[cursor + column, y + row] = color
        cursor += 6


def _tile_bytes(image: Image.Image, tile_x: int, tile_y: int) -> bytes:
    """Encode one indexed image cell as an NES 2bpp tile.

    Args:
        image: Image whose pixel values are in the range 0-3.
        tile_x: Horizontal eight-pixel cell index.
        tile_y: Vertical eight-pixel cell index.

    Returns:
        Sixteen bytes: eight low-plane rows followed by eight high-plane rows.
    """
    pixels = _pixel_access(image)
    low = bytearray(8)
    high = bytearray(8)
    for y in range(8):
        for x in range(8):
            value = pixels[tile_x * 8 + x, tile_y * 8 + y]
            low[y] |= (value & 1) << (7 - x)
            high[y] |= ((value >> 1) & 1) << (7 - x)
    return bytes((*low, *high))


@cache
def _pattern_values(pattern: bytes) -> tuple[int, ...]:
    """Decode one NES 2bpp tile to 64 row-major palette indices.

    Args:
        pattern: Sixteen-byte low-plane/high-plane tile.

    Returns:
        Cached immutable values in the range 0-3.

    Raises:
        IndexError: If ``pattern`` is shorter than 16 bytes.
    """
    values: list[int] = []
    for y in range(8):
        for x in range(8):
            shift = 7 - x
            values.append(
                ((pattern[y] >> shift) & 1)
                | (((pattern[y + 8] >> shift) & 1) << 1)
            )
    return tuple(values)


_COLOR_DISTANCE = tuple(
    tuple(
        0 if a == b else (1_000_000 if a == 1 else (4 if b == 1 else 1))
        for b in range(4)
    )
    for a in range(4)
)


@cache
def _pattern_distance(left: bytes, right: bytes) -> int:
    """Score color mismatch between two tiles.

    Args:
        left: Source/target tile whose white pixels must be protected.
        right: Candidate representative tile.

    Returns:
        Weighted per-pixel error. Replacing a white source pixel receives a
        prohibitive penalty; other pink/purple differences remain finite.
    """
    return sum(
        _COLOR_DISTANCE[a][b]
        for a, b in zip(
            _pattern_values(left), _pattern_values(right), strict=True
        )
    )


def _values_to_pattern(values: list[int]) -> bytes:
    """Encode 64 row-major palette indices as one NES 2bpp tile.

    Args:
        values: Exactly 64 integers whose low two bits select colors.

    Returns:
        Sixteen-byte low-plane/high-plane tile.

    Raises:
        IndexError: If fewer than 64 values are supplied.
    """
    low = bytearray(8)
    high = bytearray(8)
    for y in range(8):
        for x in range(8):
            value = values[y * 8 + x]
            low[y] |= (value & 1) << (7 - x)
            high[y] |= ((value >> 1) & 1) << (7 - x)
    return bytes((*low, *high))


def _refine_title_centers(
    centers: list[bytes],
    exact_patterns: set[bytes],
    represented_patterns: set[bytes],
    weighted_frequency: Counter[bytes],
    *,
    iterations: int = 8,
) -> list[bytes]:
    """Refine lossy logo tiles into deterministic weighted consensus tiles.

    Args:
        centers: Initial unique representative patterns.
        exact_patterns: Representatives that must never be changed.
        represented_patterns: Full target pattern set.
        weighted_frequency: On-screen use count for every represented pattern.
        iterations: Maximum deterministic refinement passes.

    Returns:
        The same number of unique centers, with fixed patterns retained.

    Raises:
        TitlePatchError: If refinement runs out of candidates or changes the
            requested center count.

    Reusing a whole source tile for several different diagonal edges can copy
    unrelated pink or purple pixels into the logo.  The exact lower-title and
    clock tiles stay fixed; each remaining cluster instead receives the 2bpp
    tile that minimizes its total per-pixel color error.  This uses the same
    number of CHR slots while avoiding those visibly borrowed fragments.
    """
    target_count = len(centers)
    fixed = sorted(exact_patterns)
    dynamic = [center for center in centers if center not in exact_patterns]

    for _ in range(iterations):
        all_centers = fixed + dynamic
        dynamic_index = {center: index for index, center in enumerate(dynamic)}
        clusters: list[list[bytes]] = [[] for _ in dynamic]
        for pattern in sorted(represented_patterns):
            center = min(
                all_centers,
                key=lambda candidate: (
                    _pattern_distance(pattern, candidate),
                    candidate,
                ),
            )
            index = dynamic_index.get(center)
            if index is not None:
                clusters[index].append(pattern)

        refined: list[bytes] = []
        for old_center, cluster in zip(dynamic, clusters, strict=True):
            if not cluster:
                refined.append(old_center)
                continue
            expanded = [
                (
                    pattern,
                    _pattern_values(pattern),
                    weighted_frequency[pattern],
                )
                for pattern in cluster
            ]
            values = [
                min(
                    range(4),
                    key=lambda candidate: (
                        sum(
                            weight * _COLOR_DISTANCE[source[pixel]][candidate]
                            for _, source, weight in expanded
                        ),
                        candidate,
                    ),
                )
                for pixel in range(64)
            ]
            refined.append(_values_to_pattern(values))

        unique_dynamic = sorted(set(refined) - set(fixed))
        all_centers = fixed + unique_dynamic
        while len(all_centers) < target_count:
            minimum_distance = {
                pattern: min(
                    _pattern_distance(pattern, center)
                    for center in all_centers
                )
                for pattern in represented_patterns
            }
            candidates = represented_patterns - set(all_centers)
            if not candidates:
                raise TitlePatchError(
                    "title-center refinement exhausted candidates"
                )
            selected = max(
                candidates,
                key=lambda candidate: (
                    sum(
                        max(
                            0,
                            minimum_distance[pattern]
                            - _pattern_distance(pattern, candidate),
                        )
                        * weighted_frequency[pattern]
                        for pattern in represented_patterns
                    ),
                    candidate,
                ),
            )
            unique_dynamic.append(selected)
            all_centers.append(selected)
        new_dynamic = sorted(unique_dynamic)[: target_count - len(fixed)]
        if new_dynamic == sorted(dynamic):
            dynamic = new_dynamic
            break
        dynamic = new_dynamic

    result = fixed + dynamic
    if len(result) != target_count or len(set(result)) != target_count:
        raise TitlePatchError(
            "title-center refinement changed the CHR tile count"
        )
    return result


def _validate_source(data: bytes) -> None:
    """Validate every revision-specific NOV4 assumption before patching.

    Args:
        data: Candidate unmodified NOV4 overlay.

    Raises:
        TitlePatchError: If size, instructions, pointers, stream framing,
            nametable hashes, CHR hashes, clock source, or metasprite animation
            differs from the recovered Japanese revision.

    The function performs no mutation. These strict guards prevent absolute
    offsets and injected 6502 helpers from being applied to an unknown build.
    """
    if len(data) != NOV4_SOURCE_SIZE:
        raise TitlePatchError(
            f"NOV4 must be the original 0x{NOV4_SOURCE_SIZE:X}-byte layout"
        )
    if (
        data[TITLE_POINTER_OFFSET : TITLE_POINTER_OFFSET + 4]
        != TITLE_POINTER_SOURCE
    ):
        raise TitlePatchError(
            "NOV4 title pointer code does not match the source"
        )
    instruction_checks = (
        (PPUCTRL_INIT_OFFSET, PPUCTRL_INIT_SOURCE, "PPUCTRL setup"),
        (TITLE_EXIT_OFFSET, TITLE_EXIT_SOURCE, "title exit"),
        (
            BACKGROUND_TAIL_UPLOAD_OFFSET,
            BACKGROUND_TAIL_UPLOAD_SOURCE,
            "background tail upload",
        ),
        (
            PHASE_ZERO_UPLOAD_OFFSET,
            PHASE_ZERO_UPLOAD_SOURCE,
            "phase-zero upload",
        ),
        (
            SLIDE_PREP_CALL_OFFSET,
            SLIDE_PREP_CALL_SOURCE,
            "pre-slide palette call",
        ),
        (
            TITLE_TRANSITION_CALL_OFFSET,
            TITLE_TRANSITION_CALL_SOURCE,
            "title transition call",
        ),
        (
            SLIDE_PALETTE_COLOR1_OFFSET,
            SLIDE_PALETTE_COLOR1_SOURCE,
            "slide palette color 1",
        ),
    )
    for offset, expected, label in instruction_checks:
        if data[offset : offset + len(expected)] != expected:
            raise TitlePatchError(f"NOV4 {label} does not match the source")
    if (
        data[
            CLOCK_HAND_ORIGINS_OFFSET : CLOCK_HAND_ORIGINS_OFFSET
            + len(CLOCK_HAND_ORIGINS_SOURCE)
        ]
        != CLOCK_HAND_ORIGINS_SOURCE
    ):
        raise TitlePatchError(
            "NOV4 clock-hand origins do not match the source"
        )
    combined, combined_end = decode_title_stream(data, FINAL_NAMETABLE_START)
    if (
        combined
        != (
            decode_title_rle(data, FINAL_NAMETABLE_START)[0]
            + decode_title_rle(data, SECOND_NAMETABLE_START)[0]
        )
        or combined_end != SECOND_NAMETABLE_END + 1
    ):
        raise TitlePatchError(
            "NOV4 title stream framing does not match the source"
        )
    checks = (
        (
            data[FINAL_NAMETABLE_START:FINAL_NAMETABLE_END],
            FINAL_NAMETABLE_SOURCE_SHA256,
            "final nametable",
        ),
        (
            data[SECOND_NAMETABLE_START:SECOND_NAMETABLE_END],
            SECOND_NAMETABLE_SOURCE_SHA256,
            "second nametable",
        ),
        (
            data[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE],
            TITLE_CHR_SOURCE_SHA256,
            "title CHR",
        ),
        (
            data[CLOCK_SOURCE_OFFSET:CLOCK_SOURCE_END],
            CLOCK_SOURCE_SHA256,
            "clock-hand tile source",
        ),
        (
            data[CLOCK_METASPRITE_START:CLOCK_METASPRITE_END],
            CLOCK_METASPRITE_SHA256,
            "clock metasprite animation",
        ),
    )
    for source_bytes, expected_hash, description in checks:
        if _sha256(source_bytes) != expected_hash:
            raise TitlePatchError(
                f"NOV4 {description} does not match the recovered source"
            )


def build_title_assets(
    data: bytes,
    target: Path,
    *,
    subtitle: str = DEFAULT_SUBTITLE,
) -> TitleAssets:
    """Build exact English title assets without modifying the source bytes.

    Args:
        data: Original, revision-checked NOV4 overlay.
        target: Approved native 256-by-240 indexed title image.
        subtitle: Localized subtitle redrawn with the deterministic pixel font.

    Returns:
        Exact CHR, nametable, RLE, Nintendo-phase, and restore assets.

    Raises:
        OSError: If ``target`` cannot be read.
        TitlePatchError: If NOV4 is unknown, the subtitle is unsupported or
            wider than the screen, exact pattern counts differ, temporary tile
            IDs are exhausted, or clock-source preservation fails.

    ``target`` is the reviewed native title authority; production never
    resamples a display screenshot. The supplied subtitle is always redrawn by
    the deterministic pixel font.
    The returned upper/lower pattern sets must match their recovered capacity,
    Nintendo-phase tiles receive reversible host IDs, and the original clock
    tile tail is preserved byte-for-byte. The function does not write files or
    mutate ``data``.
    """
    _validate_source(data)
    final_nametable, final_end = decode_title_rle(data, FINAL_NAMETABLE_START)
    second_nametable, second_end = decode_title_rle(
        data, SECOND_NAMETABLE_START
    )
    if final_end != FINAL_NAMETABLE_END or second_end != SECOND_NAMETABLE_END:
        raise TitlePatchError("NOV4 title nametable boundaries changed")
    source_chr = data[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE]
    original_final = _render_indexed_nametable(final_nametable, source_chr)
    original_second = _render_indexed_nametable(second_nametable, source_chr)
    recovered = _target_to_indices(target)

    final_target = original_final.copy()
    final_pixels = _pixel_access(final_target)
    recovered_pixels = _pixel_access(recovered)
    for y in range(96):
        for x in range(256):
            final_pixels[x, y] = recovered_pixels[x, y]

    # The native asset ends at row 91.  Keep the established four-pixel gap and
    # redraw the retained wording from code so it cannot drift with the logo.
    for y in range(92, 106):
        for x in range(256):
            final_pixels[x, y] = 0
    subtitle_width = (
        sum(4 if character == " " else 6 for character in subtitle) - 1
    )
    if subtitle_width > 256:
        raise TitlePatchError("title subtitle is wider than the screen")
    _draw_text(
        final_target,
        subtitle,
        x=(256 - subtitle_width) // 2,
        y=96,
        color=2,
    )

    # The second nametable shares a horizontal scroll with the final one.
    # Its Japanese title tile occupancy cannot be reused as an English mask:
    # the two wordmarks have different letter geometry, which turns a scroll
    # frame into unrelated fragments.  Instead, copy a tile-aligned leading
    # segment of the actual English logo.  The native swipe reveals the
    # remaining columns from the neighboring final nametable.
    #
    # All 32 columns are copied.  State 3 restores the 38 Nintendo-temporary
    # CHR IDs before the first swipe frame, so the slide may use every safe
    # background ID below the clock-owned $EC-$FF tail.
    slide_target = Image.new("L", (256, 240), 0)
    for tile_y in range(12):
        for tile_x in range(SLIDE_TITLE_TILE_COLUMNS):
            left = tile_x * 8
            top = tile_y * 8
            slide_target.paste(
                final_target.crop((left, top, left + 8, top + 8)), (left, top)
            )

    # The exact upper title and exact lower machine/text art need 291 distinct
    # patterns together, more than one NES background table can contain.  NOV4
    # already owns a two-stage FDS timer split for normal scene/dialogue
    # rendering.  Reuse that native mechanism at the blank band between PUSH
    # START and the time machine: table 1 supplies rows 0-15 and table 0
    # supplies rows 16-29.  Both sets now fit independently with no clustering,
    # substitutions, or lost border/color pixels.
    top_frequency: Counter[bytes] = Counter(
        _tile_bytes(final_target, tile_x, tile_y)
        for tile_y in range(SPLIT_TILE_ROW)
        for tile_x in range(32)
    )
    top_frequency.update(
        _tile_bytes(slide_target, tile_x, tile_y)
        for tile_y in range(12)
        for tile_x in range(32)
    )
    bottom_frequency: Counter[bytes] = Counter(
        _tile_bytes(final_target, tile_x, tile_y)
        for tile_y in range(SPLIT_TILE_ROW, 30)
        for tile_x in range(32)
    )
    top_patterns = set(top_frequency)
    bottom_patterns = set(bottom_frequency)
    if len(top_patterns) != TOP_TILE_COUNT:
        raise TitlePatchError(
            f"exact upper title needs {len(top_patterns)} tiles, expected {TOP_TILE_COUNT}"
        )
    if len(bottom_patterns) != BOTTOM_TILE_COUNT:
        raise TitlePatchError(
            f"exact lower title needs {len(bottom_patterns)} tiles, expected {BOTTOM_TILE_COUNT}"
        )

    nintendo_frequency: Counter[bytes] = Counter(
        _tile_bytes(original_second, tile_x, tile_y)
        for tile_y in range(12, 30)
        for tile_x in range(32)
    )
    nintendo_patterns = sorted(
        nintendo_frequency,
        key=lambda pattern: (-nintendo_frequency[pattern], pattern),
    )
    if len(nintendo_patterns) != NINTENDO_TILE_COUNT:
        raise TitlePatchError("Nintendo logo tile count changed")
    ordered_top_patterns = sorted(
        top_patterns,
        key=lambda pattern: (-top_frequency[pattern], pattern),
    )
    center_to_id = dict(
        zip(ordered_top_patterns, range(TOP_TILE_COUNT), strict=True)
    )
    if (
        len(center_to_id) != TOP_TILE_COUNT
        or len(set(center_to_id.values())) != TOP_TILE_COUNT
    ):
        raise TitlePatchError("exact upper-title ID assignment is incomplete")

    # NOV4 copies the first $EC source tiles into background table 1 before it
    # constructs the hand sprites in table 0 from the untouched $EC-$FF tail.
    # All 236 exact upper patterns deliberately fill the slots below $EC, so
    # the original
    # animated-hand source remains byte-identical.
    background_chr = bytearray(source_chr)
    background_chr[: CLOCK_SOURCE_TILE * 16] = bytes(CLOCK_SOURCE_TILE * 16)
    for pattern, tile_id in center_to_id.items():
        background_chr[tile_id * 16 : (tile_id + 1) * 16] = pattern

    bottom_to_id = {
        pattern: tile_id
        for tile_id, pattern in enumerate(sorted(bottom_patterns))
    }
    bottom_chr = b"".join(
        pattern
        for pattern, _ in sorted(
            bottom_to_id.items(), key=lambda item: item[1]
        )
    )
    if len(bottom_chr) != BOTTOM_CHR_SIZE:
        raise TitlePatchError("exact lower-title CHR has an unexpected size")

    nintendo_chr = bytearray(NINTENDO_CHR_SIZE)
    nintendo_to_id = {
        pattern: NINTENDO_FIRST_TILE + index
        for index, pattern in enumerate(nintendo_patterns)
    }
    for pattern, tile_id in nintendo_to_id.items():
        block_offset = (tile_id - NINTENDO_FIRST_TILE) * 16
        nintendo_chr[block_offset : block_offset + 16] = pattern
    restore_chr = background_chr[
        NINTENDO_FIRST_TILE
        * 16 : (NINTENDO_FIRST_TILE + NINTENDO_TILE_COUNT)
        * 16
    ]

    patched_chr = bytearray(background_chr)
    if (
        patched_chr[CLOCK_SOURCE_TILE * 16 :]
        != source_chr[CLOCK_SOURCE_TILE * 16 :]
    ):
        raise TitlePatchError(
            "title conversion altered the clock source tiles"
        )

    patched_final = bytearray(final_nametable)
    patched_second = bytearray(second_nametable)
    for tile_y in range(30):
        for tile_x in range(32):
            pattern = _tile_bytes(final_target, tile_x, tile_y)
            if tile_y < SPLIT_TILE_ROW:
                tile_id = center_to_id[pattern]
            else:
                tile_id = bottom_to_id[pattern]
            patched_final[tile_y * 32 + tile_x] = tile_id
    for tile_y in range(12):
        for tile_x in range(32):
            pattern = _tile_bytes(slide_target, tile_x, tile_y)
            patched_second[tile_y * 32 + tile_x] = center_to_id[pattern]
    for tile_y in range(12, 30):
        for tile_x in range(32):
            pattern = _tile_bytes(original_second, tile_x, tile_y)
            patched_second[tile_y * 32 + tile_x] = nintendo_to_id[pattern]

    encoded_final = encode_title_rle(bytes(patched_final))
    encoded_second = encode_title_rle(bytes(patched_second))
    return TitleAssets(
        chr_data=bytes(patched_chr),
        background_chr=bytes(background_chr),
        bottom_chr=bottom_chr,
        nintendo_chr=bytes(nintendo_chr),
        restore_chr=bytes(restore_chr),
        final_nametable=bytes(patched_final),
        second_nametable=bytes(patched_second),
        encoded_final=encoded_final,
        encoded_second=encoded_second,
        approximation_error=0,
    )


def _pre_slide_restore_helper(slide_restore_address: int) -> bytes:
    """Return the state-3 helper that hides the Nintendo-to-title remap.

    The helper preserves the native monochrome-palette setup, blanks the
    PPUMASK mirror/register, disables NMI, restores the title CHR over the
    Nintendo-owned tile IDs, installs the first native scroll origin, then
    restores PPUCTRL and the PPUMASK mirror. It intentionally does not restore
    $2001 itself: the next NMI must first copy the new scroll origin into the
    real PPU registers, then restore rendering from $1C. Restoring $2001 inside
    this helper shows one frame of the old Nintendo nametable with restored
    English-title CHR.
    """
    helper = (
        bytes.fromhex(
            "20 74 AB "
            "A5 1C 48 A9 00 85 1C 8D 01 20 "
            "A5 FF 48 29 7F 8D 00 20 "
            "A0 1B A9 00 A2 26 20 AF EB"
        )
        + slide_restore_address.to_bytes(2, "little")
        + bytes.fromhex(
            "A9 01 85 58 A9 F0 85 57 85 4D "
            "68 85 FF 09 10 85 FF 8D 00 20 "
            "68 85 1C EA EA EA 60"
        )
    )
    if len(helper) != SLIDE_PREP_SIZE:
        raise TitlePatchError(
            "pre-slide CHR restore helper has an unexpected size"
        )
    return helper


def patched_nov4_title(
    data: bytes,
    target: Path,
    *,
    subtitle: str = DEFAULT_SUBTITLE,
) -> bytes:
    """Return NOV4 with relocated English title assets and helper code.

    Args:
        data: Original NOV4 overlay accepted by :func:`_validate_source`.
        target: Approved native 256-by-240 indexed title image.
        subtitle: Localized subtitle to retain under the wordmark.

    Returns:
        Expanded NOV4 bytes containing title assets and verified helper code.

    Raises:
        OSError: If the native title image cannot be read.
        TitlePatchError: If asset generation fails, helper sizes change, the
            expanded overlay would overlap NOV3, a source patch site differs,
            or any post-build verification fails.

    The function appends lower-title CHR, Nintendo overlay CHR, a fixed
    size-neutral workspace, four small 6502 helpers, and two compressed
    nametables.  It rewrites only the
    recovered palette/call/pointer/origin sites and the background CHR region.
    The expanded overlay must finish below resident NOV3 at ``$D7B5``. Inputs
    and the native title file are not modified.
    """
    assets = build_title_assets(data, target, subtitle=subtitle)
    bottom_chr_offset = len(data)
    nintendo_chr_offset = bottom_chr_offset + BOTTOM_CHR_SIZE
    restore_workspace_offset = nintendo_chr_offset + NINTENDO_CHR_SIZE
    initial_loader_offset = restore_workspace_offset + RESTORE_WORKSPACE_SIZE
    slide_prep_offset = initial_loader_offset + INITIAL_CHR_LOADER_SIZE
    transition_offset = slide_prep_offset + SLIDE_PREP_SIZE
    exit_offset = transition_offset + TITLE_TRANSITION_SIZE
    title_stream_offset = exit_offset + TITLE_EXIT_SIZE

    def loaded_address(offset: int) -> int:
        """Convert a validated NOV4 file offset to its loaded CPU address.

        Args:
            offset: Offset inside the bank's loaded payload.

        Returns:
            CPU address obtained by adding the bank's load base.

        Note:
            The enclosing function validates the final expanded address against
            NOV3 residency after all appended regions have been laid out.
        """
        return NOV4_LOAD_ADDRESS + offset

    bottom_chr_address = loaded_address(bottom_chr_offset)
    nintendo_chr_address = loaded_address(nintendo_chr_offset)
    initial_loader_address = loaded_address(initial_loader_offset)
    slide_prep_address = loaded_address(slide_prep_offset)
    transition_address = loaded_address(transition_offset)
    exit_address = loaded_address(exit_offset)
    title_stream_address = loaded_address(title_stream_offset)

    # The native loader has already copied the exact upper title into pattern
    # table 1. Temporarily overlay the Nintendo patterns on IDs $B0-$D5.  A
    # one-shot state-3 helper restores the underlying title patterns before
    # any slide pixels become visible. The helper and later title state read
    # the authoritative base CHR, so no serialized restore duplicate is needed.
    initial_loader = bytes.fromhex("A0 1B A9 00 A2 26 20 AF EB") + bytes(
        (nintendo_chr_address & 0xFF, nintendo_chr_address >> 8)
    )
    initial_loader += b"\x60"
    if len(initial_loader) != INITIAL_CHR_LOADER_SIZE:
        raise TitlePatchError("initial title loader has an unexpected size")

    # Preserve the original state-3 monochrome-palette call, then blank the
    # PPU/NMI while restoring the 38 Nintendo-temporary patterns directly from
    # the patched base CHR in this bank. Clear the PPUMASK mirror before
    # blanking the register so a pending NMI cannot restore rendering during
    # the blanked region. Restore the original $01F0 origin before NMI is
    # restored, but leave $2001 blank so the next NMI can install the new
    # scroll/nametable state before rendering becomes visible.
    slide_restore_address = loaded_address(
        TITLE_CHR_OFFSET + NINTENDO_FIRST_TILE * 16
    )
    slide_prep = _pre_slide_restore_helper(slide_restore_address)

    # State $17 restores the exact upper patterns from the same authoritative
    # patched base CHR, installs the independent exact lower set in pattern
    # table 0, and enables NOV4's existing
    # scene/dialogue raster split.  That proven split occurs in the blank band
    # between PUSH START and the time machine, never through visible artwork.
    transition = bytes.fromhex("A9 01 8D E1 07 20 E0 6F")
    transition += bytes.fromhex("A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20")
    transition += bytes.fromhex("A0 1B A9 00 A2 26 20 AF EB") + bytes(
        (slide_restore_address & 0xFF, slide_restore_address >> 8)
    )
    transition += bytes.fromhex("A0 00 A9 00 A2 37 20 AF EB") + bytes(
        (bottom_chr_address & 0xFF, bottom_chr_address >> 8)
    )
    transition += bytes.fromhex(
        "68 85 FF 09 10 85 FF 8D 00 20 "
        "A9 00 85 4F 85 55 85 57 85 58 85 49 85 4A "
        "8D 70 07 8D 71 07 "
        "A9 FF 85 48 A9 10 85 56 "
        "A9 C0 8D 72 07 A9 3F 8D 73 07 "
        "A5 1C 8D 01 20 60"
    )
    if len(transition) != TITLE_TRANSITION_SIZE:
        raise TitlePatchError("title transition helper has an unexpected size")

    # Blank rendering, then disable the title-only raster split before handing
    # control to the game.  Keeping both the PPUMASK mirror and register blank
    # prevents the lower time-machine tile IDs from being rendered through the
    # upper logo CHR table during teardown.  Clear the saved menu-cancel pointer
    # as well so the post-title flow cannot inherit a stale destination.  The
    # menu engine may install a fresh pointer while constructing START; NOV2's
    # separate one-choice B guard handles that case without affecting
    # Back/Cancel on larger menus.
    # The helper ends with the original state change, so it intentionally does
    # not return to the replaced START-button branch.
    exit_helper = TITLE_EXIT_HELPER
    if len(exit_helper) != TITLE_EXIT_SIZE:
        raise TitlePatchError("title exit helper has an unexpected size")

    append = b"".join(
        (
            assets.bottom_chr,
            assets.nintendo_chr,
            bytes(RESTORE_WORKSPACE_SIZE),
            initial_loader,
            slide_prep,
            transition,
            exit_helper,
            assets.encoded_final,
            assets.encoded_second,
            b"\xff",
        )
    )
    if loaded_address(len(data) + len(append)) > NOV3_LOAD_ADDRESS:
        raise TitlePatchError(
            "expanded NOV4 would overlap resident NOV3 memory"
        )

    result = bytearray(data)
    result[
        SLIDE_PALETTE_COLOR1_OFFSET : SLIDE_PALETTE_COLOR1_OFFSET
        + len(SLIDE_PALETTE_COLOR1_SOURCE)
    ] = SLIDE_PALETTE_COLOR1_PATCH
    result[TITLE_POINTER_OFFSET : TITLE_POINTER_OFFSET + 4] = bytes(
        (0xA9, title_stream_address & 0xFF, 0xA2, title_stream_address >> 8)
    )
    result[
        BACKGROUND_TAIL_UPLOAD_OFFSET : BACKGROUND_TAIL_UPLOAD_OFFSET + 11
    ] = (
        bytes(
            (0x20, initial_loader_address & 0xFF, initial_loader_address >> 8)
        )
        + b"\xea" * 8
    )
    result[
        SLIDE_PREP_CALL_OFFSET : SLIDE_PREP_CALL_OFFSET
        + len(SLIDE_PREP_CALL_SOURCE)
    ] = bytes((0x20, slide_prep_address & 0xFF, slide_prep_address >> 8))
    # Preserve the original tail-call structure here.  The source branch JMPs
    # to $6119, whose RTS returns directly to the main engine.  Using JSR for
    # this detour leaves an extra return address on the stack, so $6119's RTS
    # falls back into the middle of NOV4 and crashes immediately after START.
    result[TITLE_EXIT_OFFSET : TITLE_EXIT_OFFSET + len(TITLE_EXIT_SOURCE)] = (
        bytes((0x4C, exit_address & 0xFF, exit_address >> 8))
        + b"\xea" * (len(TITLE_EXIT_SOURCE) - 3)
    )
    result[
        TITLE_TRANSITION_CALL_OFFSET : TITLE_TRANSITION_CALL_OFFSET
        + len(TITLE_TRANSITION_CALL_SOURCE)
    ] = bytes((0x20, transition_address & 0xFF, transition_address >> 8)) + (
        b"\xea" * (len(TITLE_TRANSITION_CALL_SOURCE) - 3)
    )
    # The approved face is centered at about (125,67) in native pixels. Move
    # both original metasprite origins by -16,-8 so their shared elbow lands on
    # that center. Frame layouts, tiles, order, and timing remain unchanged.
    result[
        CLOCK_HAND_ORIGINS_OFFSET : CLOCK_HAND_ORIGINS_OFFSET
        + len(CLOCK_HAND_ORIGINS_PATCH)
    ] = CLOCK_HAND_ORIGINS_PATCH
    result[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE] = (
        assets.chr_data
    )
    result.extend(append)

    decoded_final, second_offset = decode_title_rle(
        result, title_stream_offset
    )
    decoded_second, terminator_offset = decode_title_rle(result, second_offset)
    decoded_combined, end = decode_title_stream(result, title_stream_offset)
    if decoded_final != assets.final_nametable:
        raise TitlePatchError(
            "relocated final title nametable failed verification"
        )
    if decoded_second != assets.second_nametable:
        raise TitlePatchError(
            "relocated second title nametable failed verification"
        )
    if terminator_offset >= len(result) or result[terminator_offset] != 0xFF:
        raise TitlePatchError("relocated title stream lost its $FF terminator")
    if (
        decoded_combined != assets.final_nametable + assets.second_nametable
        or end != len(result)
    ):
        raise TitlePatchError(
            "relocated combined title stream failed verification"
        )
    if result[bottom_chr_offset:nintendo_chr_offset] != assets.bottom_chr:
        raise TitlePatchError("exact lower-title tiles failed verification")
    if (
        result[nintendo_chr_offset:restore_workspace_offset]
        != assets.nintendo_chr
    ):
        raise TitlePatchError("Nintendo overlay tiles failed verification")
    if result[restore_workspace_offset:initial_loader_offset] != bytes(
        RESTORE_WORKSPACE_SIZE
    ):
        raise TitlePatchError("pre-slide workspace failed verification")
    if (
        result[
            SLIDE_PALETTE_COLOR1_OFFSET : SLIDE_PALETTE_COLOR1_OFFSET
            + len(SLIDE_PALETTE_COLOR1_PATCH)
        ]
        != SLIDE_PALETTE_COLOR1_PATCH
    ):
        raise TitlePatchError(
            "slide palette color-1 patch failed verification"
        )
    if (
        result[CLOCK_SOURCE_OFFSET:CLOCK_SOURCE_END]
        != data[CLOCK_SOURCE_OFFSET:CLOCK_SOURCE_END]
    ):
        raise TitlePatchError("clock-hand source bytes changed")
    if (
        result[CLOCK_METASPRITE_START:CLOCK_METASPRITE_END]
        != data[CLOCK_METASPRITE_START:CLOCK_METASPRITE_END]
    ):
        raise TitlePatchError("clock metasprite animation bytes changed")
    if (
        result[
            CLOCK_HAND_ORIGINS_OFFSET : CLOCK_HAND_ORIGINS_OFFSET
            + len(CLOCK_HAND_ORIGINS_PATCH)
        ]
        != CLOCK_HAND_ORIGINS_PATCH
    ):
        raise TitlePatchError(
            "clock-hand origin correction failed verification"
        )
    return bytes(result)


def render_slide_logo_frame(
    assets: TitleAssets,
    scroll_origin: int,
) -> Image.Image:
    """Reconstruct one exact 256-by-96 native swipe viewport.

    Args:
        assets: ROM-bound title CHR and nametables.
        scroll_origin: Nine-bit horizontal origin formed by ``$58:$57``.

    Returns:
        Attribute-masked geometry for the twelve moving tile rows. Visible
        pixels retain their native nonzero 2bpp value (1, 2, or 3); pixels
        whose selected runtime palette entry is black are returned as zero.

    Raises:
        TitlePatchError: If the origin is outside the two-nametable world.

    NT0 is the final map at $2000 and NT1 is the slide/Nintendo map at $2400.
    The resident NMI writes the low eight bits to PPUSCROLL and bit eight to
    PPUCTRL. Sampling their 512-pixel concatenation therefore models the
    actual wrap boundary without relying on a static mockup. Each physical
    nametable's attribute table is applied before scrolling. This is essential:
    the state-3 palette uses attribute palette 1 as a visibility mask, making
    origin $1F0 blank and revealing alternating strips as the origin settles.
    """
    if not 0 <= scroll_origin < 0x200:
        raise TitlePatchError("title scroll origin must be a nine-bit value")

    def runtime_mask(nametable: bytes) -> Image.Image:
        """Apply NOV4's state-3 attribute palettes to one physical map."""
        indexed = _render_indexed_nametable(
            nametable,
            assets.background_chr,
        ).crop((0, 0, 256, 96))
        source = _pixel_access(indexed)
        masked = Image.new("L", indexed.size, 0)
        target = _pixel_access(masked)
        attributes = nametable[960:1024]
        for y in range(96):
            for x in range(256):
                attribute = attributes[(y // 32) * 8 + (x // 32)]
                shift = ((y // 16) & 1) * 4 + ((x // 16) & 1) * 2
                palette_id = (attribute >> shift) & 3
                pattern_index = source[x, y]
                if (
                    SLIDE_BACKGROUND_PALETTES[palette_id][pattern_index]
                    == SLIDE_WHITE_COLOR
                ):
                    target[x, y] = pattern_index
        return masked

    final = runtime_mask(assets.final_nametable)
    slide = runtime_mask(assets.second_nametable)
    world = Image.new("L", (512, 96), 0)
    world.paste(final, (0, 0))
    world.paste(slide, (256, 0))
    frame = Image.new("L", (256, 96), 0)
    first_width = min(256, 512 - scroll_origin)
    frame.paste(
        world.crop((scroll_origin, 0, scroll_origin + first_width, 96)),
        (0, 0),
    )
    if first_width < 256:
        frame.paste(
            world.crop((0, 0, 256 - first_width, 96)),
            (first_width, 0),
        )
    return frame


def render_monochrome_slide_frame(
    assets: TitleAssets,
    scroll_origin: int,
) -> Image.Image:
    """Colorize one attribute-masked swipe frame as black and white."""
    indexed = render_slide_logo_frame(assets, scroll_origin)
    image = Image.new("RGB", (256, 240), TITLE_PALETTE[0])
    source = _pixel_access(indexed)
    target = _pixel_access(image)
    for y in range(96):
        for x in range(256):
            if source[x, y]:
                target[x, y] = TITLE_PALETTE[1]
    return image


def render_title_background(assets: TitleAssets) -> Image.Image:
    """Render generated title assets as a full-color verification image.

    Args:
        assets: Generated title nametable and split CHR sets.

    Returns:
        A new 256-by-240 RGB image with attribute-table palette selection.

    This preview omits animated clock-hand sprites. Use
    :func:`overlay_clock_sprites` with a runtime capture to inspect a frame.
    """
    indexed = _render_split_nametable(
        assets.final_nametable,
        assets.background_chr,
        assets.bottom_chr,
    )
    attributes = assets.final_nametable[960:1024]
    source = _pixel_access(indexed)
    image = Image.new("RGB", indexed.size, TITLE_PALETTE[0])
    target = _pixel_access(image)
    for y in range(240):
        for x in range(256):
            attribute = attributes[(y // 32) * 8 + (x // 32)]
            shift = ((y // 16) & 1) * 4 + ((x // 16) & 1) * 2
            palette_id = (attribute >> shift) & 3
            palette = GRAY_PALETTE if palette_id == 3 else TITLE_PALETTE
            target[x, y] = palette[source[x, y]]
    return image


def overlay_clock_sprites(
    background: Image.Image,
    chr_dump: bytes,
    oam: bytes,
) -> Image.Image:
    """Overlay one captured clock-hand frame on a title preview.

    Args:
        background: Base title image; it is copied and never modified.
        chr_dump: Complete 8-KiB runtime NES pattern-table capture.
        oam: At least the first eight four-byte sprite records.

    Returns:
        A new RGB image with nontransparent hand pixels applied.

    Raises:
        TitlePatchError: If the CHR dump is not exactly 8 KiB or fewer than
            eight sprites are available.

    Horizontal/vertical flip bits and the NES OAM y-plus-one convention are
    honored. Sprite priority and palette-number bits are intentionally ignored
    because the captured hand uses one known verification palette.
    """
    if len(chr_dump) != 0x2000 or len(oam) < 0x20:
        raise TitlePatchError(
            "clock preview needs 8 KB CHR and eight OAM sprites"
        )
    image = background.copy().convert("RGB")
    pixels = _pixel_access(image)
    for sprite in range(8):
        y, tile_id, attributes, x = oam[sprite * 4 : sprite * 4 + 4]
        tile = chr_dump[tile_id * 16 : tile_id * 16 + 16]
        flip_x = bool(attributes & 0x40)
        flip_y = bool(attributes & 0x80)
        for row in range(8):
            source_y = 7 - row if flip_y else row
            low = tile[source_y]
            high = tile[source_y + 8]
            for column in range(8):
                source_x = 7 - column if flip_x else column
                shift = 7 - source_x
                value = ((low >> shift) & 1) | (((high >> shift) & 1) << 1)
                if value == 0:
                    continue
                screen_x = x + column
                screen_y = y + 1 + row
                if 0 <= screen_x < 256 and 0 <= screen_y < 240:
                    pixels[screen_x, screen_y] = SPRITE_PALETTE[value]
    return image
