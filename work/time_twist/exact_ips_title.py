"""Install the definitive historical IPS title and reviewed final-playtest polish.

The third-party IPS remains a maintainer-supplied private input and is never
embedded in or redistributed with this package. The pipeline loads the external
patch, verifies its SHA-256, applies it to the supported untouched Zenpen image,
extracts the resulting NOV4 bytes, overlays only the IPS-owned NOV4 differences
onto the already-localized NOV4 bank, then adds the reviewed six-tile final-logo
corrections and ``On the Outskirts of History...`` in one final-phase-only CHR
upload. The moving monochrome swipe remains the exact IPS artwork.

Set ``TIME_TWIST_DEFINITIVE_TITLE_IPS`` to the patch path when running from an
installed package. A source checkout also accepts the private fixture at
``work/private/TimeTwist-Zenpen-newlogo.ips``.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PIL import Image

from .fds import FdsImage
from .title_assets import (
    _draw_text,
    _tile_bytes,
    decode_title_rle,
    encode_title_rle,
)
from .title_layout import (
    CLOCK_SOURCE_TILE,
    DEFAULT_SUBTITLE,
    FINAL_NAMETABLE_START,
    NOV3_LOAD_ADDRESS,
    NOV4_LOAD_ADDRESS,
    TITLE_TRANSITION_CALL_OFFSET,
    TITLE_TRANSITION_CALL_SOURCE,
    TITLE_CHR_OFFSET,
    TitlePatchError,
)

BASE_ZENPEN_SHA256 = (
    "B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916"
)
BASE_NOV4_SHA256 = (
    "89F50DA5A0BD2CE318DD9DBBAF3CE976F353E5EC0AC6357FD91438CDAC927694"
)
PATCHED_NOV4_SHA256 = (
    "ABDD4C52BE8859B6A70AC02AC7388925696596611CE03C0628F73B5C59B4C8D5"
)
DEFINITIVE_IPS_SHA256 = (
    "915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2"
)
DEFINITIVE_IPS_ENV = "TIME_TWIST_DEFINITIVE_TITLE_IPS"
DEFINITIVE_IPS_FILENAME = "TimeTwist-Zenpen-newlogo.ips"

_ZERO_TILE = bytes(16)
_SUBTITLE_TILE_ROW = 13
_SUBTITLE_Y = _SUBTITLE_TILE_ROW * 8
_MAX_ORIGINAL_TITLE_STREAM_END = 0x094D

# Final-playtest pixel corrections to the definitive IPS wordmark. Each entry
# duplicates one IPS-owned tile into spare final-phase CHR, changes only the
# reviewed pixels, and remaps exactly one final nametable cell. The moving
# monochrome swipe remains byte-for-byte identical to the historical IPS.
_FINAL_LOGO_TILE_CORRECTIONS: tuple[tuple[int, int, bytes, bytes], ...] = (
    (
        0x066,
        0x03,
        bytes.fromhex("00000001071f7ffc000000000000030f"),
        bytes.fromhex("00000001071f7fff000000000000020e"),
    ),
    (
        0x0D6,
        0x04,
        bytes.fromhex("000000ffffff00000000000000ffffff"),
        bytes.fromhex("000000ffffff00010000000000ffffff"),
    ),
    (
        0x0D7,
        0x33,
        bytes.fromhex("00000080c1e1e3c30000000000808000"),
        bytes.fromhex("00000080c1e1e3c30000000000808101"),
    ),
    (
        0x0F1,
        0x14,
        bytes.fromhex("f0f0f0f0f0f0f0f01f1f1f1f1f1f1f1f"),
        bytes.fromhex("f0f0f0f0f0f070301f1f1f1f1f1f1f9f"),
    ),
    (
        0x123,
        0x08,
        bytes.fromhex("1c1c1c1c1c1c1c1c0707070707070707"),
        bytes.fromhex("1c1c1c1c1c1c1c1f0707070707070707"),
    ),
    (
        0x12B,
        0x16,
        bytes.fromhex("00000000000000ffffffffffffffffff"),
        bytes.fromhex("01010000000000ffffffffffffffffff"),
    ),
)


def _sha256(data: bytes) -> str:
    """Return an uppercase SHA-256 digest."""
    return hashlib.sha256(data).hexdigest().upper()


def _default_definitive_ips_path() -> Path:
    """Return the private-checkout location for the maintainer-supplied IPS."""
    return (
        Path(__file__).resolve().parents[2]
        / "work"
        / "private"
        / DEFINITIVE_IPS_FILENAME
    )


def _definitive_ips_path() -> Path:
    """Resolve the external definitive IPS without packaging or redistributing it."""
    configured = os.environ.get(DEFINITIVE_IPS_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return _default_definitive_ips_path()


def _definitive_ips() -> bytes:
    """Load and authenticate the maintainer-supplied definitive title IPS."""
    path = _definitive_ips_path()
    try:
        patch = path.read_bytes()
    except OSError as error:
        raise TitlePatchError(
            "definitive title IPS is missing; set "
            f"{DEFINITIVE_IPS_ENV} or place {DEFINITIVE_IPS_FILENAME} at {path}"
        ) from error
    if _sha256(patch) != DEFINITIVE_IPS_SHA256:
        raise TitlePatchError(
            "definitive title IPS hash does not match the reviewed maintainer input"
        )
    return patch


def _apply_ips(source: bytes, patch: bytes) -> bytes:
    """Apply the verified standard IPS patch without any pixel reconstruction."""
    if not patch.startswith(b"PATCH"):
        raise TitlePatchError("definitive title patch is not an IPS file")
    output = bytearray(source)
    offset = 5
    while True:
        if patch[offset : offset + 3] == b"EOF":
            offset += 3
            break
        if offset + 5 > len(patch):
            raise TitlePatchError("truncated definitive title IPS record")
        target = int.from_bytes(patch[offset : offset + 3], "big")
        size = int.from_bytes(patch[offset + 3 : offset + 5], "big")
        offset += 5
        if size:
            end = offset + size
            if end > len(patch):
                raise TitlePatchError("truncated definitive title IPS payload")
            payload = patch[offset:end]
            offset = end
        else:
            if offset + 3 > len(patch):
                raise TitlePatchError("truncated definitive title IPS RLE")
            run = int.from_bytes(patch[offset : offset + 2], "big")
            value = patch[offset + 2]
            offset += 3
            if run == 0:
                raise TitlePatchError("zero-length definitive title IPS RLE")
            payload = bytes((value,)) * run
        end = target + len(payload)
        if end > len(output):
            output.extend(b"\x00" * (end - len(output)))
        output[target:end] = payload
    if offset != len(patch):
        raise TitlePatchError(
            "unexpected bytes after definitive title IPS EOF"
        )
    return bytes(output)


def _exact_ips_nov4(zenpen_raw: bytes) -> tuple[bytes, bytes]:
    """Return the untouched and exact IPS-patched NOV4 banks."""
    if _sha256(zenpen_raw) != BASE_ZENPEN_SHA256:
        raise TitlePatchError(
            "Zenpen baseline does not match the definitive title source"
        )
    base_image = FdsImage.from_bytes(zenpen_raw)
    base_nov4 = base_image.sides[0].find_file("NOV4").data
    if _sha256(base_nov4) != BASE_NOV4_SHA256:
        raise TitlePatchError(
            "NOV4 baseline does not match the definitive title source"
        )
    patched_image = FdsImage.from_bytes(
        _apply_ips(zenpen_raw, _definitive_ips())
    )
    patched_nov4 = patched_image.sides[0].find_file("NOV4").data
    if _sha256(patched_nov4) != PATCHED_NOV4_SHA256:
        raise TitlePatchError(
            "exact IPS application did not reproduce the known NOV4"
        )
    return base_nov4, patched_nov4


def _overlay_exact_ips_differences(
    data: bytes, base_nov4: bytes, patched_nov4: bytes
) -> bytes:
    """Copy every byte changed by the historical IPS, preserving unrelated localization."""
    if len(data) != len(base_nov4) or len(patched_nov4) != len(base_nov4):
        raise TitlePatchError(
            "NOV4 layout changed before definitive title installation"
        )
    result = bytearray(data)
    overlap = []
    for index, (base_byte, patched_byte) in enumerate(
        zip(base_nov4, patched_nov4, strict=True)
    ):
        if base_byte == patched_byte:
            continue
        if data[index] != base_byte:
            overlap.append(index)
            continue
        result[index] = patched_byte
    if overlap:
        first = overlap[0]
        raise TitlePatchError(
            f"definitive title IPS overlaps localized NOV4 at 0x{first:04X}"
        )
    return bytes(result)


def _subtitle_tiles(subtitle: str) -> tuple[dict[int, bytes], list[int]]:
    """Rasterize the subtitle into one 8-pixel tile row using palette index 2."""
    width = sum(4 if character == " " else 6 for character in subtitle) - 1
    if width <= 0 or width > 256:
        raise TitlePatchError("title subtitle has an invalid width")
    image = Image.new("L", (256, 240), 0)
    _draw_text(image, subtitle, x=(256 - width) // 2, y=_SUBTITLE_Y, color=2)
    patterns: list[bytes] = []
    tile_patterns: list[bytes] = []
    for tile_x in range(32):
        pattern = _tile_bytes(image, tile_x, _SUBTITLE_TILE_ROW)
        tile_patterns.append(pattern)
        if pattern != _ZERO_TILE and pattern not in patterns:
            patterns.append(pattern)
    return {index: pattern for index, pattern in enumerate(patterns)}, [
        patterns.index(pattern) if pattern != _ZERO_TILE else -1
        for pattern in tile_patterns
    ]


def _install_subtitle(data: bytes, subtitle: str) -> bytes:
    """Add the English subtitle without changing any IPS logo/clock pixel."""
    final, second_offset = decode_title_rle(data, FINAL_NAMETABLE_START)
    second, terminator_offset = decode_title_rle(data, second_offset)
    if terminator_offset >= len(data) or data[terminator_offset] != 0xFF:
        raise TitlePatchError(
            "definitive IPS title stream lost its terminator"
        )

    final_ids = set(final[:960])
    second_ids = set(second[:960])
    reusable = [
        tile_id
        for tile_id in range(CLOCK_SOURCE_TILE)
        if tile_id in second_ids and tile_id not in final_ids
    ]
    pattern_map, tile_pattern_indices = _subtitle_tiles(subtitle)
    needed = len(pattern_map)
    if needed == 0:
        raise TitlePatchError("title subtitle contains no drawable glyphs")

    runs: list[tuple[int, int]] = []
    start: int | None = None
    previous: int | None = None
    for tile_id in reusable:
        if start is None or previous is None:
            start = previous = tile_id
            continue
        if tile_id == previous + 1:
            previous = tile_id
            continue
        runs.append((start, previous + 1))
        start = previous = tile_id
    if start is not None and previous is not None:
        runs.append((start, previous + 1))
    selected = next(
        (run for run in runs if run[1] - run[0] >= needed),
        None,
    )
    if selected is None:
        raise TitlePatchError(
            "definitive title has no contiguous final-phase subtitle tile run"
        )
    first_tile = selected[0]
    tile_ids = list(range(first_tile, first_tile + needed))
    correction_first_tile = first_tile + needed
    total_tiles = needed + len(_FINAL_LOGO_TILE_CORRECTIONS)
    if selected[1] - first_tile < total_tiles:
        raise TitlePatchError(
            "definitive title has no contiguous final-phase tile run for "
            "subtitle plus reviewed logo corrections"
        )

    final_mut = bytearray(final)
    for tile_x, pattern_index in enumerate(tile_pattern_indices):
        if pattern_index >= 0:
            final_mut[_SUBTITLE_TILE_ROW * 32 + tile_x] = tile_ids[
                pattern_index
            ]

    correction_data = bytearray()
    for correction_index, (
        nametable_index,
        source_tile,
        expected_pattern,
        corrected_pattern,
    ) in enumerate(_FINAL_LOGO_TILE_CORRECTIONS):
        if final_mut[nametable_index] != source_tile:
            raise TitlePatchError(
                f"definitive title cell 0x{nametable_index:03X} no longer uses "
                f"expected tile ${source_tile:02X}"
            )
        source_offset = TITLE_CHR_OFFSET + source_tile * 16
        if data[source_offset : source_offset + 16] != expected_pattern:
            raise TitlePatchError(
                f"definitive title tile ${source_tile:02X} changed under "
                "reviewed pixel correction"
            )
        final_mut[nametable_index] = correction_first_tile + correction_index
        correction_data.extend(corrected_pattern)

    rebuilt_stream = b"".join(
        (encode_title_rle(bytes(final_mut)), encode_title_rle(second), b"\xff")
    )
    stream_end = FINAL_NAMETABLE_START + len(rebuilt_stream)
    if stream_end > _MAX_ORIGINAL_TITLE_STREAM_END:
        raise TitlePatchError(
            f"subtitle title stream ends at 0x{stream_end:04X}, "
            f"beyond safe 0x{_MAX_ORIGINAL_TITLE_STREAM_END:04X}"
        )

    glyph_data = (
        b"".join(pattern_map[index] for index in range(needed))
        + bytes(correction_data)
    )
    if len(glyph_data) != total_tiles * 16 or total_tiles > 0xFF:
        raise TitlePatchError(
            "title final-phase CHR payload has an invalid size"
        )

    helper_offset = len(data)
    helper_address = NOV4_LOAD_ADDRESS + helper_offset
    helper_prefix = TITLE_TRANSITION_CALL_SOURCE + bytes.fromhex(
        "A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20"
    )
    helper_suffix = bytes.fromhex(
        "68 85 FF 09 10 85 FF 8D 00 20 A5 1C 8D 01 20 60"
    )
    glyph_address = (
        NOV4_LOAD_ADDRESS
        + helper_offset
        + len(helper_prefix)
        + 11
        + len(helper_suffix)
    )
    ppu_address = 0x1000 + first_tile * 16
    upload = bytes(
        (
            0xA0,
            ppu_address >> 8,
            0xA9,
            ppu_address & 0xFF,
            0xA2,
            total_tiles,
            0x20,
            0xAF,
            0xEB,
            glyph_address & 0xFF,
            glyph_address >> 8,
        )
    )
    helper = helper_prefix + upload + helper_suffix
    if NOV4_LOAD_ADDRESS + helper_offset + len(helper) != glyph_address:
        raise TitlePatchError(
            "subtitle helper source-address calculation drifted"
        )

    loaded_end = glyph_address + len(glyph_data)
    if loaded_end > NOV3_LOAD_ADDRESS:
        raise TitlePatchError(
            f"subtitle helper would overlap resident NOV3: "
            f"${loaded_end:04X} > ${NOV3_LOAD_ADDRESS:04X}"
        )

    result = bytearray(data)
    result[FINAL_NAMETABLE_START:stream_end] = rebuilt_stream
    result[
        TITLE_TRANSITION_CALL_OFFSET : TITLE_TRANSITION_CALL_OFFSET
        + len(TITLE_TRANSITION_CALL_SOURCE)
    ] = bytes((0x20, helper_address & 0xFF, helper_address >> 8)) + b"\xea" * (
        len(TITLE_TRANSITION_CALL_SOURCE) - 3
    )
    result.extend(helper)
    result.extend(glyph_data)

    check_final, check_second_offset = decode_title_rle(
        result, FINAL_NAMETABLE_START
    )
    check_second, check_terminator = decode_title_rle(
        result, check_second_offset
    )
    if check_final != bytes(final_mut) or check_second != second:
        raise TitlePatchError("subtitle title-stream verification failed")
    if result[check_terminator] != 0xFF:
        raise TitlePatchError(
            "subtitle title-stream terminator verification failed"
        )
    return bytes(result)


def patched_nov4_exact_ips_title(
    data: bytes,
    zenpen_raw: bytes,
    *,
    subtitle: str = DEFAULT_SUBTITLE,
) -> bytes:
    """Install the historical logo base plus approved final-phase corrections."""
    base_nov4, patched_nov4 = _exact_ips_nov4(zenpen_raw)
    exact = _overlay_exact_ips_differences(data, base_nov4, patched_nov4)
    return _install_subtitle(exact, subtitle)
