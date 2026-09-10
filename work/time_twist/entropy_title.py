"""Entropy-candidate title wrapper with the runtime-proven tile-zero seam fix.

The established title builder remains unchanged.  After it produces the exact
reviewed title, this module applies a pure upper-CHR tile-ID permutation:

* tile 0 is reserved as blank in both title phases;
* the 53 transition tiles move from IDs 0..52 to 1..53;
* fixed upper patterns are compacted into IDs 54..235;
* only nametable rows rendered through the upper pattern table are remapped;
* the final-delta upload target moves from PPU $1000 to $1010.

No pattern pixels change.  The transformation exists solely to prevent tile 0
from leaking a visible horizontal pattern at the native mid-screen CHR switch.
"""

from __future__ import annotations

from pathlib import Path

from .title_assets import decode_title_rle, encode_title_rle
from .title_layout import (
    BOTTOM_CHR_SIZE,
    CLOCK_SOURCE_TILE,
    DEFAULT_SUBTITLE,
    FINAL_DELTA_CHR_SIZE,
    FINAL_DELTA_TILE_COUNT,
    INITIAL_CHR_LOADER_SIZE,
    NINTENDO_CHR_SIZE,
    NOV3_LOAD_ADDRESS,
    NOV4_LOAD_ADDRESS,
    SLIDE_PREP_SIZE,
    SPLIT_TILE_ROW,
    TITLE_CHR_OFFSET,
    TITLE_CHR_SIZE,
    TITLE_EXIT_SIZE,
    TITLE_TRANSITION_SIZE,
    TitlePatchError,
)
from .title_patch import patched_nov4_title

_ZERO_TILE = bytes(16)
_SLIDE_VISIBLE_ROWS = 12
_NAMETABLE_WIDTH = 32


def _seam_safe_permutation(slide_chr: bytes) -> dict[int, int]:
    """Return the old-to-new upper tile permutation with blank fixed at ID 0."""
    upper = slide_chr[: CLOCK_SOURCE_TILE * 16]
    if len(upper) != CLOCK_SOURCE_TILE * 16:
        raise TitlePatchError("upper title CHR is truncated")
    tiles = tuple(
        upper[offset : offset + 16]
        for offset in range(0, len(upper), 16)
    )
    blank_ids = [index for index, tile in enumerate(tiles) if tile == _ZERO_TILE]
    if len(blank_ids) != 1:
        raise TitlePatchError(
            f"expected one assigned blank upper tile, found {len(blank_ids)}"
        )
    blank = blank_ids[0]
    if blank < FINAL_DELTA_TILE_COUNT:
        raise TitlePatchError("blank upper tile unexpectedly belongs to delta IDs")

    mapping = {
        old: old + 1 for old in range(FINAL_DELTA_TILE_COUNT)
    }
    mapping[blank] = 0
    next_fixed = FINAL_DELTA_TILE_COUNT + 1
    for old in range(FINAL_DELTA_TILE_COUNT, CLOCK_SOURCE_TILE):
        if old == blank:
            continue
        mapping[old] = next_fixed
        next_fixed += 1
    if set(mapping) != set(range(CLOCK_SOURCE_TILE)):
        raise TitlePatchError("seam-safe title permutation is incomplete")
    if set(mapping.values()) != set(range(CLOCK_SOURCE_TILE)):
        raise TitlePatchError("seam-safe title permutation is not bijective")
    return mapping


def _permute_upper_chr(slide_chr: bytes, mapping: dict[int, int]) -> bytes:
    result = bytearray(slide_chr)
    for old, new in mapping.items():
        source = slide_chr[old * 16 : (old + 1) * 16]
        result[new * 16 : (new + 1) * 16] = source
    if result[:16] != _ZERO_TILE:
        raise TitlePatchError("seam-safe title did not leave tile 0 blank")
    if result[CLOCK_SOURCE_TILE * 16 :] != slide_chr[CLOCK_SOURCE_TILE * 16 :]:
        raise TitlePatchError("seam-safe title altered the clock tile tail")
    return bytes(result)


def _remap_rows(
    nametable: bytes,
    mapping: dict[int, int],
    *,
    rows: int,
) -> bytes:
    result = bytearray(nametable)
    limit = rows * _NAMETABLE_WIDTH
    if limit > len(result):
        raise TitlePatchError("title nametable is too short for remapped rows")
    for index in range(limit):
        old = result[index]
        if old not in mapping:
            raise TitlePatchError(
                f"upper title nametable uses unmapped tile ${old:02X}"
            )
        result[index] = mapping[old]
    return bytes(result)


def patched_nov4_entropy_title(
    data: bytes,
    target: Path,
    *,
    slide_target: Path | None = None,
    subtitle: str = DEFAULT_SUBTITLE,
) -> bytes:
    """Build the reviewed title and then apply the tile-zero seam correction."""
    patched = patched_nov4_title(
        data,
        target,
        slide_target=slide_target,
        subtitle=subtitle,
    )

    title_stream_offset = (
        len(data)
        + BOTTOM_CHR_SIZE
        + NINTENDO_CHR_SIZE
        + FINAL_DELTA_CHR_SIZE
        + INITIAL_CHR_LOADER_SIZE
        + SLIDE_PREP_SIZE
        + TITLE_TRANSITION_SIZE
        + TITLE_EXIT_SIZE
    )
    final_nametable, second_offset = decode_title_rle(
        patched,
        title_stream_offset,
    )
    second_nametable, terminator_offset = decode_title_rle(
        patched,
        second_offset,
    )
    if terminator_offset >= len(patched) or patched[terminator_offset] != 0xFF:
        raise TitlePatchError("patched title stream lost its terminator")

    slide_chr = patched[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE]
    mapping = _seam_safe_permutation(slide_chr)
    remapped_chr = _permute_upper_chr(slide_chr, mapping)
    remapped_final = _remap_rows(
        final_nametable,
        mapping,
        rows=SPLIT_TILE_ROW,
    )
    remapped_second = _remap_rows(
        second_nametable,
        mapping,
        rows=_SLIDE_VISIBLE_ROWS,
    )

    result = bytearray(patched)
    result[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE] = remapped_chr

    transition_offset = (
        len(data)
        + BOTTOM_CHR_SIZE
        + NINTENDO_CHR_SIZE
        + FINAL_DELTA_CHR_SIZE
        + INITIAL_CHR_LOADER_SIZE
        + SLIDE_PREP_SIZE
    )
    old_target = bytes(
        (0xA0, 0x10, 0xA9, 0x00, 0xA2, FINAL_DELTA_TILE_COUNT, 0x20, 0xAF, 0xEB)
    )
    new_target = bytes(
        (0xA0, 0x10, 0xA9, 0x10, 0xA2, FINAL_DELTA_TILE_COUNT, 0x20, 0xAF, 0xEB)
    )
    transition_end = transition_offset + TITLE_TRANSITION_SIZE
    transition = bytes(result[transition_offset:transition_end])
    occurrences = transition.count(old_target)
    if occurrences != 1:
        raise TitlePatchError(
            f"expected one title delta upload target, found {occurrences}"
        )
    transition = transition.replace(old_target, new_target, 1)
    result[transition_offset:transition_end] = transition

    rebuilt_stream = b"".join(
        (
            encode_title_rle(remapped_final),
            encode_title_rle(remapped_second),
            b"\xFF",
        )
    )
    del result[title_stream_offset:]
    result.extend(rebuilt_stream)
    if NOV4_LOAD_ADDRESS + len(result) > NOV3_LOAD_ADDRESS:
        raise TitlePatchError("seam-safe title would overlap resident NOV3")

    check_final, check_second_offset = decode_title_rle(
        result,
        title_stream_offset,
    )
    check_second, check_end = decode_title_rle(result, check_second_offset)
    if check_final != remapped_final or check_second != remapped_second:
        raise TitlePatchError("seam-safe title nametable verification failed")
    if check_end >= len(result) or result[check_end] != 0xFF:
        raise TitlePatchError("seam-safe title terminator verification failed")
    if result[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + 16] != _ZERO_TILE:
        raise TitlePatchError("seam-safe title tile 0 verification failed")
    return bytes(result)
