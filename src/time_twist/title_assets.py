"""Deterministic English-title asset generation and native RLE codecs."""

from __future__ import annotations

import hashlib
from collections import Counter
from functools import cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .font import PIXEL_FONT_5X7
from .title_layout import (
    BACKGROUND_TAIL_UPLOAD_OFFSET,
    BACKGROUND_TAIL_UPLOAD_SOURCE,
    BOTTOM_CHR_SIZE,
    BOTTOM_TILE_COUNT,
    CLOCK_HAND_ORIGINS_OFFSET,
    CLOCK_HAND_ORIGINS_SOURCE,
    CLOCK_METASPRITE_END,
    CLOCK_METASPRITE_SHA256,
    CLOCK_METASPRITE_START,
    CLOCK_SOURCE_END,
    CLOCK_SOURCE_OFFSET,
    CLOCK_SOURCE_SHA256,
    CLOCK_SOURCE_TILE,
    DEFAULT_SLIDE_ASSET_NAME,
    DEFAULT_SUBTITLE,
    FINAL_DELTA_TILE_COUNT,
    FINAL_NAMETABLE_END,
    FINAL_NAMETABLE_SOURCE_SHA256,
    FINAL_NAMETABLE_START,
    NINTENDO_CHR_SIZE,
    NINTENDO_FIRST_TILE,
    NINTENDO_TILE_COUNT,
    NOV4_SOURCE_SIZE,
    PHASE_ZERO_UPLOAD_OFFSET,
    PHASE_ZERO_UPLOAD_SOURCE,
    PPUCTRL_INIT_OFFSET,
    PPUCTRL_INIT_SOURCE,
    SECOND_NAMETABLE_END,
    SECOND_NAMETABLE_SOURCE_SHA256,
    SECOND_NAMETABLE_START,
    SLIDE_PALETTE_COLOR1_OFFSET,
    SLIDE_PALETTE_COLOR1_SOURCE,
    SLIDE_PREP_CALL_OFFSET,
    SLIDE_PREP_CALL_SOURCE,
    SPLIT_TILE_ROW,
    TITLE_CHR_OFFSET,
    TITLE_CHR_SIZE,
    TITLE_CHR_SOURCE_SHA256,
    TITLE_EXIT_OFFSET,
    TITLE_EXIT_SOURCE,
    TITLE_POINTER_OFFSET,
    TITLE_POINTER_SOURCE,
    TITLE_TRANSITION_CALL_OFFSET,
    TITLE_TRANSITION_CALL_SOURCE,
    TOP_TILE_COUNT,
    TitleAssets,
    TitlePatchError,
)


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


def _target_to_indices(
    path: Path,
    *,
    last_owned_row: int = 96,
) -> Image.Image:
    """Load the approved native NES title authority without resampling it.

    Args:
        path: Exact 256-by-240 indexed title asset.
        last_owned_row: Final inclusive row the authority may occupy.

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
    if not 0 <= last_owned_row < 240:
        raise TitlePatchError("native title authority row limit is invalid")
    if any(
        result.crop((0, last_owned_row + 1, 256, 240)).get_flattened_data()
    ):
        raise TitlePatchError(
            "native title authority owns pixels below its approved rows"
        )
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
    slide_target: Path | None = None,
    subtitle: str = DEFAULT_SUBTITLE,
) -> TitleAssets:
    """Build exact English title assets without modifying the source bytes.

    Args:
        data: Original, revision-checked NOV4 overlay.
        target: Approved native 256-by-240 indexed title image.
        slide_target: Approved native monochrome swipe image. By default this
            is the named sibling asset beside ``target``.
        subtitle: Localized subtitle redrawn with the deterministic pixel font.

    Returns:
        Exact CHR, nametable, RLE, Nintendo-phase, and restore assets.

    Raises:
        OSError: If either native title authority cannot be read.
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
    if slide_target is None:
        slide_target = target.with_name(DEFAULT_SLIDE_ASSET_NAME)
    recovered_slide = _target_to_indices(slide_target, last_owned_row=95)
    if not set(recovered_slide.get_flattened_data()) <= {0, 1}:
        raise TitlePatchError(
            "native slide authority must be strictly monochrome"
        )

    final_target = original_final.copy()
    final_pixels = _pixel_access(final_target)
    recovered_pixels = _pixel_access(recovered)
    for y in range(97):
        for x in range(256):
            final_pixels[x, y] = recovered_pixels[x, y]

    # The recovered colored wordmark ends on row 96. Keep a five-pixel gap and
    # redraw the retained wording from code so it cannot drift with the logo.
    # PUSH START begins on row 112 in the original final nametable.
    for y in range(97, 112):
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
        y=102,
        color=2,
    )

    # The GIF contains a genuinely different completed monochrome swipe, not
    # merely a white rendering of the colored final logo. Preserve that
    # reviewed phase as its own pixel authority.
    slide_target_image = recovered_slide.copy()

    # The exact upper title and exact lower machine/text art need 291 distinct
    # patterns together, more than one NES background table can contain.  NOV4
    # already owns a two-stage FDS timer split for normal scene/dialogue
    # rendering.  Reuse that native mechanism at the blank band between PUSH
    # START and the time machine: table 1 supplies rows 0-15 and table 0
    # supplies rows 16-29.  Both sets now fit independently with no clustering,
    # substitutions, or lost border/color pixels.
    final_frequency: Counter[bytes] = Counter(
        _tile_bytes(final_target, tile_x, tile_y)
        for tile_y in range(SPLIT_TILE_ROW)
        for tile_x in range(32)
    )
    slide_frequency: Counter[bytes] = Counter(
        _tile_bytes(slide_target_image, tile_x, tile_y)
        for tile_y in range(12)
        for tile_x in range(32)
    )
    bottom_frequency: Counter[bytes] = Counter(
        _tile_bytes(final_target, tile_x, tile_y)
        for tile_y in range(SPLIT_TILE_ROW, 30)
        for tile_x in range(32)
    )
    final_patterns = set(final_frequency)
    slide_patterns = set(slide_frequency)
    upper_union = final_patterns | slide_patterns
    bottom_patterns = set(bottom_frequency)
    if len(final_patterns) > TOP_TILE_COUNT:
        raise TitlePatchError(
            f"exact final upper title needs {len(final_patterns)} tiles, "
            f"but only {TOP_TILE_COUNT} are available"
        )
    if len(slide_patterns) > TOP_TILE_COUNT:
        raise TitlePatchError(
            f"exact slide title needs {len(slide_patterns)} tiles, "
            f"but only {TOP_TILE_COUNT} are available"
        )
    if len(upper_union) > TOP_TILE_COUNT * 2:
        raise TitlePatchError(
            "exact title phases exceed the two-phase upper CHR capacity"
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
    shared_patterns = final_patterns & slide_patterns
    slide_only = sorted(
        slide_patterns - shared_patterns,
        key=lambda pattern: (-slide_frequency[pattern], pattern),
    )
    final_only = sorted(
        final_patterns - shared_patterns,
        key=lambda pattern: (-final_frequency[pattern], pattern),
    )
    delta_tile_count = max(0, len(upper_union) - TOP_TILE_COUNT)
    if delta_tile_count != FINAL_DELTA_TILE_COUNT:
        raise TitlePatchError(
            f"exact title phases need a {delta_tile_count}-tile delta, "
            f"expected {FINAL_DELTA_TILE_COUNT}"
        )
    if delta_tile_count > min(len(slide_only), len(final_only)):
        raise TitlePatchError(
            "exact title phases cannot share the available upper CHR IDs"
        )
    slide_delta_patterns = slide_only[:delta_tile_count]
    final_delta_patterns = final_only[:delta_tile_count]
    fixed_patterns = sorted(
        shared_patterns,
        key=lambda pattern: (
            -(final_frequency[pattern] + slide_frequency[pattern]),
            pattern,
        ),
    )
    fixed_patterns.extend(slide_only[delta_tile_count:])
    fixed_patterns.extend(final_only[delta_tile_count:])
    if len(fixed_patterns) > TOP_TILE_COUNT - delta_tile_count:
        raise TitlePatchError("upper-title fixed CHR assignment overflowed")

    fixed_to_id = {
        pattern: delta_tile_count + index
        for index, pattern in enumerate(fixed_patterns)
    }
    slide_to_id = {
        pattern: index for index, pattern in enumerate(slide_delta_patterns)
    }
    slide_to_id.update(
        (pattern, fixed_to_id[pattern])
        for pattern in slide_patterns
        if pattern in fixed_to_id
    )
    final_to_id = {
        pattern: index for index, pattern in enumerate(final_delta_patterns)
    }
    final_to_id.update(
        (pattern, fixed_to_id[pattern])
        for pattern in final_patterns
        if pattern in fixed_to_id
    )
    if (
        set(slide_to_id) != slide_patterns
        or set(final_to_id) != final_patterns
    ):
        raise TitlePatchError("exact upper-title ID assignment is incomplete")

    # NOV4 copies the first $EC source tiles into background table 1 before it
    # constructs the hand sprites in table 0 from the untouched $EC-$FF tail.
    # Exact phase patterns occupy only slots below $EC, so the original
    # animated-hand source remains byte-identical.
    slide_chr = bytearray(source_chr)
    slide_chr[: CLOCK_SOURCE_TILE * 16] = bytes(CLOCK_SOURCE_TILE * 16)
    for pattern, tile_id in fixed_to_id.items():
        slide_chr[tile_id * 16 : (tile_id + 1) * 16] = pattern
    for pattern, tile_id in zip(
        slide_delta_patterns, range(delta_tile_count), strict=True
    ):
        slide_chr[tile_id * 16 : (tile_id + 1) * 16] = pattern

    background_chr = bytearray(slide_chr)
    for pattern, tile_id in zip(
        final_delta_patterns, range(delta_tile_count), strict=True
    ):
        background_chr[tile_id * 16 : (tile_id + 1) * 16] = pattern
    final_delta_chr = bytes(background_chr[: delta_tile_count * 16])

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
    restore_chr = slide_chr[
        NINTENDO_FIRST_TILE
        * 16 : (NINTENDO_FIRST_TILE + NINTENDO_TILE_COUNT)
        * 16
    ]

    clock_tail = source_chr[CLOCK_SOURCE_TILE * 16 :]
    if (
        slide_chr[CLOCK_SOURCE_TILE * 16 :] != clock_tail
        or background_chr[CLOCK_SOURCE_TILE * 16 :] != clock_tail
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
                tile_id = final_to_id[pattern]
            else:
                tile_id = bottom_to_id[pattern]
            patched_final[tile_y * 32 + tile_x] = tile_id
    for tile_y in range(12):
        for tile_x in range(32):
            pattern = _tile_bytes(slide_target_image, tile_x, tile_y)
            patched_second[tile_y * 32 + tile_x] = slide_to_id[pattern]
    for tile_y in range(12, 30):
        for tile_x in range(32):
            pattern = _tile_bytes(original_second, tile_x, tile_y)
            patched_second[tile_y * 32 + tile_x] = nintendo_to_id[pattern]

    encoded_final = encode_title_rle(bytes(patched_final))
    encoded_second = encode_title_rle(bytes(patched_second))
    return TitleAssets(
        chr_data=bytes(slide_chr),
        background_chr=bytes(background_chr),
        slide_chr=bytes(slide_chr),
        final_delta_chr=final_delta_chr,
        final_delta_first_tile=0,
        bottom_chr=bottom_chr,
        nintendo_chr=bytes(nintendo_chr),
        restore_chr=bytes(restore_chr),
        final_nametable=bytes(patched_final),
        second_nametable=bytes(patched_second),
        encoded_final=encoded_final,
        encoded_second=encoded_second,
        approximation_error=0,
    )
