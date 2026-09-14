"""Install the definitive historical IPS title exactly, then add our subtitle.

The external IPS is embedded byte-for-byte so production does not reconstruct or
reinterpret the TIME TWIST logo. The pipeline applies the exact patch to the
supported untouched Zenpen image, extracts the resulting NOV4 bytes, overlays
only the IPS-owned NOV4 differences onto the already-localized NOV4 bank, and
then adds ``On the Outskirts of History...`` in a final-phase-only CHR upload.

The subtitle deliberately reuses tile IDs that the IPS title uses only during
the moving/Nintendo phase. Those tiles are replaced only at the final-title
transition, so the IPS logo, swipe animation, clock geometry, and palette bytes
remain byte-identical to the historical patch.
"""

from __future__ import annotations

import base64
import hashlib

from PIL import Image

from .fds import FdsImage
from .title_assets import _draw_text, _tile_bytes, decode_title_rle, encode_title_rle
from .title_layout import (
    CLOCK_SOURCE_TILE,
    DEFAULT_SUBTITLE,
    FINAL_NAMETABLE_START,
    NOV3_LOAD_ADDRESS,
    NOV4_LOAD_ADDRESS,
    TITLE_TRANSITION_CALL_OFFSET,
    TITLE_TRANSITION_CALL_SOURCE,
    TitlePatchError,
)

BASE_ZENPEN_SHA256 = "B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916"
BASE_NOV4_SHA256 = "89F50DA5A0BD2CE318DD9DBBAF3CE976F353E5EC0AC6357FD91438CDAC927694"
PATCHED_NOV4_SHA256 = "ABDD4C52BE8859B6A70AC02AC7388925696596611CE03C0628F73B5C59B4C8D5"
DEFINITIVE_IPS_SHA256 = "915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2"

_DEFINITIVE_IPS_B64 = (
    "UEFUQ0gAqXgAB2gAOQRwAEEArA4C7c//Gdf/AgMaxf8bCwzM/8HkweXF/wIDDRwBxf8dDg8LDM//AgMNEB4fICEEIsMEIyTB"
    "/Q8lJsX/J8T+KML/KRAqACsFwf0swf0RBi0SLhgHLw4wMTIEMwQ0NTY3ODnC/zo7PAATBcH9PT4/QEHBz8HQwdHB0hRCQ0RF"
    "RkfB/UgSSQABw/9Kwf8IABMFSwYHTBEGwdPB1MHVwdbB101OT1BRUlMVVAgAAcX/CAlVVglXWFkWWsHYwf/B2cH/wdrB/VvB"
    "/Vy+v8HAwcEVwcIAAcX/F8QKwcMKwcQKCsHbw//B3MHFwcYWwcfByMHJFhbBysHLCQHP/8Hdwd7B38HgweEKwczGCsHNFwrB"
    "ztD/weLB48Hm+v9mZ2hpwf9oX2prX/j/kJGSk9z/lJWWl9z/mJmam5ydntj/oKGio6SlpqfY/6ipqqusra6v2P+wsbKztLW2"
    "t9n/uLm6u7y99v9lY2RkY8H/XV5dX2BdYWL+//7/7f/gAND/0AD+/8//Gdf/AgMaxf8bCwzT/wIDDRwBxf8dDg8LDM//AgMN"
    "EB4fICEEIsMEIyTB/Q8lJsX/J8T+KML/KRAqACsFwf0swf0RBi0SLhgHLw4wMTIEMwQ0NTY3ODnC/zo7PAATBcH9PT4/QEHB"
    "58HoGAcUQkNERUZHwf1IEkkAAcP/SsH/CAATBUsGB0wRBsHpwerB6wcUTU5PUFFSUxVUCAABxf8ICVVWCVdYWRZawxbB+xTB"
    "/VvB/Vy+v8HAwcEVwcIAAcX/F8QKwcMKwcTGCsH8wcXBxhbBx8HIwckWFsHKwcsJAdP/CgrBzMYKwc0XCsHOyv9sbct9bm/R"
    "/3zB/3BxcnN0dXZ3eHl6e3/R/4zB/4CBgoOEhYaHiImKwf+P0f+Ljct+jp/+//7//v/+//7//v/+/9f/2FXoqv8AAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAK+AABgDAwMDAwMDA/7+/v7+/v7+"
    "gICAgICAgIAAr58ACQAAAAAAAAAAAQCvrwAJAAAAAAEHH3/8AK++AGoDDwAAAP///wAAAAAAAAD///88PDw8PDw8POfn5+fn"
    "5+fnAAAAAICAwMD///////9/fwEBAQEBAQEB//////////8cHBwcHBwcHAcHBwcHBwcHAwMDAwMDA//+/v7+/v7+/v//AAAA"
    "AAAAALAvAOkAAMDw/H8fBwEAAACA4Pj+/wAAAAAAwPD8AAAAAAAAAIAHH3/88MAAAAAAAw8/////AAAAAACA4Pj///////9/"
    "H38fBwEAAAAA4Pj+///////wwAAAAAAAAD//////////Hh4PDwcHAwPz8/n5/Pz+/gAAAAD///8A//////8AAADAwMDAwMDA"
    "wH9/f39/f39/8PDw8PDw8PAfHx8fHx8fHzgcDgcDAQAA4PD4/P7///8AAAAAAAAA////////////Hx8AAAAAAAAAAAAAAAAA"
    "AA4ODg4ODg4OAwMDAwMDAwMAAAAAAAAADACxHgMMAAAAAACAgICAgAAAAAAAAAAADw8PDw4ODg4AAAIDAwMDA/PDAwMDAwMD"
    "Pv7+/v7+/v4ODg4ODg8PAwMDAwMDAQAAAAAAAAMPP/////////zwwwMPP/////w8/vzwwAAn5+eAgID///8BAQAAAAAA/v//"
    "AAAAh4fHx+cAAAAAAAEBAQAAAP///zw8AAAAAADP5+f+Pw/DwODg8AcBAAAAAICAAIDg+P4+Dg7//38fBwMDA4DA8Px/HwcB"
    "AAAAgOD4/v8AAAAAAMDw8AAAAAAAAACAAD9//3BwODgAAAA/Hx8PDwCAgMDg4HBwAAAAAICAwMAHH398cHBwcAAAAw8fHx8f"
    "AAAAAAAMPPz////////3x/zwwMDAwMDADz9/f39/f3/n93d3Pz8fH4GBwcHh4fHxAAAAAD8/Hxz//////+Dw8HB4ODj4+PgA"
    "wMDg4PAAAAAAgOD4/v//8///fx8HARAccHBwf39/cHDAwMDAwM/PzwAAAP///wcHAAAAAAD8/PwAAAAPDx8cHAAAAAAABwcH"
    "AAAAgMHh48MAAAAAAICAABwcD////wAABwcDAAD///8AAP////8AAP///wAA////AAD8/Pz8AAD///8HB////wAAAwMDAwMD"
    "/////v7+/v4AAP///4CAgP///wAAAAAAODj8+PAAAADg4PAAAAAAAHBwcHBzf39+Hx8fHx8cEAADDz/++OCAAP/88MAAAAAA"
    "/PycHBwcHBwHBwcHBwcHBw8PBwcDAwEB+fn9/f////8AAAAAAQEBAf//////////AQEAAAAAgID//////////+Dg8PB4eDw8"
    "Pz+fn8/P5+cODgcHAwAAAPj4/Pz//////j8PDw8PDw4HwfD4+Pn5+3Dw8PDwMAAAz89PDw/P//8HBwcHBwcHB/z8/Pz8/Pz8"
    "HDg4cHDg4MAHDw8fHz8/fwEDAwcHDg8f//7+/Pz4+PDHh44OHBz8/AEBAwMHBwcHAAAAAP///3D//////wCAwAAAAAD8/Pwc"
    "//////8HBwd4AAAAAAAAAAAAALQwASACAgMDAwMDA//////+/v7+wMDg4PDw+Ph/fz8/Hx8PDw4MDAgIAAAA+/////////8A"
    "AAAAAAQEDP//////////BwcHBwcGBgT8/Pz9/f///8CAgAAAAAABf/////////8fPDx4ePDw4PPn58/Pn58//gcDAwMHBw7z"
    "+fz+/vz8+AAAgMDgcDgc////fz8fDwcAAAAAgMDgcAAAAAAAAIDAwMDAwMDAwP9/f39/f39/fzw8PDw8PDz/5+fn5+fn5+fg"
    "4PCwuLi4vz8/Hx8PDw8PAQEBAQEBAf///////////9zczs7Hx8fDBwcDAwEBAADg4PDweHg8/z8/n5/Pz+fnDBwcPDx8fOz/"
    "9/fn58fHhwEDAwcHDw8e//7+/Pz5+fMAu2AAWeDAwICAAAAAP39///////8OHBw4OH9///jw8ODgwMCfDgcDAQD///8DAQAA"
    "AAAA/wAAgMDg8Pj4////fz8fD/8cHBwcnPz8fAcHBwcHB4fHv78AAAAAAAAAALvAAIfDwwAAAAAAAAAAAAAAAAAAAAEBAwMH"
    "B/7////+/vz8+OzMzIyMDAwPhwcHBwcHBwcePDx4ePDw//Pn58/Pn58/AAEBAwMHB//////+/vz8+fDg4MDAgID/nz8/f3//"
    "//8AAAAAAQMH/v///////vz4fHz8/PycHB/Hx4eHBwcHBw8PAAAAAAAAvE0AFQAAAPz4AAAAAAAAAAAAAAAAAACAgAC8aQBZ"
    "AAAAAAAAAAAA////AAAAAAAAAP///v0AAPDBjz944AAAAQ6wR5ggDgAA//9fUUYDAP8A/wAAAAEBAYHx/B4H/3+Pcw3iGQT5"
    "82dmDgwcGPqEycrS1KSowIAAvMgACkCAAAAAAAAAWF8AvNgACgAAAAAAAAAAAwEAvOgAygIBAAAAAAAAkMDgYHAwOBhfL5dX"
    "SyslFRg4MD85OT8xqEhQUFBQUFAAAAAAMCAEDAAAAAAAGBwMGBwM/BxsHBwVEgoKCgoKCj8wOBgYHAwOUFBIKCgkFBL8DBwY"
    "GDgwcwoKEhUVJStLBgcDAQAAAAAKCQQCAQAAAAAAgMDgeD8PAACAQCCYRzAAAD4gPiI+/wAAAAAAAAD/AAABAwce/PAAAAEC"
    "BBniDGfnwIAAAAAAUJAgQIAAAAABAAAAAAAAAA4BAAAAAAAA/wAAvbgAAwD/AAC94ABJgAAAAAAAAABwgAAAAAAAAAAA////"
    "AAAAAAAAAP////8AAPDw+DgcHAAAAADg4PDw//9wcDg/Hx//gMDA4ODw//78AAAA////+AC+LwAx/w4ODg4O////AwMDAwMA"
    "APz////g4OBw+H8AAACAgMDgcHBwcHBwcH8fHx8fHx8fHwC+cAALAP///wAAAAAAAABFT0Y="
)

_ZERO_TILE = bytes(16)
_SUBTITLE_TILE_ROW = 13
_SUBTITLE_Y = _SUBTITLE_TILE_ROW * 8
_MAX_ORIGINAL_TITLE_STREAM_END = 0x094D


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _definitive_ips() -> bytes:
    patch = base64.b64decode("".join(_DEFINITIVE_IPS_B64))
    if _sha256(patch) != DEFINITIVE_IPS_SHA256:
        raise TitlePatchError("embedded definitive title IPS hash drifted")
    return patch


def _apply_ips(source: bytes, patch: bytes) -> bytes:
    """Apply the embedded standard IPS patch without any pixel reconstruction."""
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
        raise TitlePatchError("unexpected bytes after definitive title IPS EOF")
    return bytes(output)


def _exact_ips_nov4(zenpen_raw: bytes) -> tuple[bytes, bytes]:
    """Return the untouched and exact IPS-patched NOV4 banks."""
    if _sha256(zenpen_raw) != BASE_ZENPEN_SHA256:
        raise TitlePatchError("Zenpen baseline does not match the definitive title source")
    base_image = FdsImage.from_bytes(zenpen_raw)
    base_nov4 = base_image.sides[0].find_file("NOV4").data
    if _sha256(base_nov4) != BASE_NOV4_SHA256:
        raise TitlePatchError("NOV4 baseline does not match the definitive title source")
    patched_image = FdsImage.from_bytes(_apply_ips(zenpen_raw, _definitive_ips()))
    patched_nov4 = patched_image.sides[0].find_file("NOV4").data
    if _sha256(patched_nov4) != PATCHED_NOV4_SHA256:
        raise TitlePatchError("exact IPS application did not reproduce the known NOV4")
    return base_nov4, patched_nov4


def _overlay_exact_ips_differences(data: bytes, base_nov4: bytes, patched_nov4: bytes) -> bytes:
    """Copy every byte changed by the historical IPS, preserving unrelated localization."""
    if len(data) != len(base_nov4) or len(patched_nov4) != len(base_nov4):
        raise TitlePatchError("NOV4 layout changed before definitive title installation")
    result = bytearray(data)
    overlap = []
    for index, (base_byte, patched_byte) in enumerate(zip(base_nov4, patched_nov4, strict=True)):
        if base_byte == patched_byte:
            continue
        if data[index] != base_byte:
            overlap.append(index)
            continue
        result[index] = patched_byte
    if overlap:
        first = overlap[0]
        raise TitlePatchError(f"definitive title IPS overlaps localized NOV4 at 0x{first:04X}")
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
        raise TitlePatchError("definitive IPS title stream lost its terminator")

    final_ids = set(final[:960])
    second_ids = set(second[:960])
    reusable = [
        tile_id
        for tile_id in range(CLOCK_SOURCE_TILE)
        if tile_id in second_ids and tile_id not in final_ids
    ]
    pattern_map, tile_pattern_indices = _subtitle_tiles(subtitle)
    needed = len(pattern_map)

    runs: list[tuple[int, int]] = []
    start = previous = None
    for tile_id in reusable:
        if start is None:
            start = previous = tile_id
        elif tile_id == previous + 1:
            previous = tile_id
        else:
            runs.append((start, previous + 1))
            start = previous = tile_id
    if start is not None and previous is not None:
        runs.append((start, previous + 1))
    selected = next((run for run in runs if run[1] - run[0] >= needed), None)
    if selected is None:
        raise TitlePatchError("definitive title has no contiguous final-phase subtitle tile run")
    first_tile = selected[0]
    tile_ids = list(range(first_tile, first_tile + needed))

    final_mut = bytearray(final)
    for tile_x, pattern_index in enumerate(tile_pattern_indices):
        if pattern_index >= 0:
            final_mut[_SUBTITLE_TILE_ROW * 32 + tile_x] = tile_ids[pattern_index]

    rebuilt_stream = b"".join((encode_title_rle(bytes(final_mut)), encode_title_rle(second), b"\xff"))
    stream_end = FINAL_NAMETABLE_START + len(rebuilt_stream)
    if stream_end > _MAX_ORIGINAL_TITLE_STREAM_END:
        raise TitlePatchError(
            f"subtitle title stream ends at 0x{stream_end:04X}, beyond safe 0x{_MAX_ORIGINAL_TITLE_STREAM_END:04X}"
        )

    glyph_data = b"".join(pattern_map[index] for index in range(needed))
    if len(glyph_data) != needed * 16 or needed > 0xFF:
        raise TitlePatchError("subtitle CHR payload has an invalid size")

    helper_offset = len(data)
    helper_address = NOV4_LOAD_ADDRESS + helper_offset
    helper_prefix = TITLE_TRANSITION_CALL_SOURCE + bytes.fromhex(
        "A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20"
    )
    helper_suffix = bytes.fromhex("68 85 FF 09 10 85 FF 8D 00 20 A5 1C 8D 01 20 60")
    glyph_address = NOV4_LOAD_ADDRESS + helper_offset + len(helper_prefix) + 11 + len(helper_suffix)
    ppu_address = 0x1000 + first_tile * 16
    upload = bytes((
        0xA0, ppu_address >> 8,
        0xA9, ppu_address & 0xFF,
        0xA2, needed,
        0x20, 0xAF, 0xEB,
        glyph_address & 0xFF,
        glyph_address >> 8,
    ))
    helper = helper_prefix + upload + helper_suffix
    if NOV4_LOAD_ADDRESS + helper_offset + len(helper) != glyph_address:
        raise TitlePatchError("subtitle helper source-address calculation drifted")

    loaded_end = glyph_address + len(glyph_data)
    if loaded_end > NOV3_LOAD_ADDRESS:
        raise TitlePatchError(
            f"subtitle helper would overlap resident NOV3: ${loaded_end:04X} > ${NOV3_LOAD_ADDRESS:04X}"
        )

    result = bytearray(data)
    result[FINAL_NAMETABLE_START:stream_end] = rebuilt_stream
    result[
        TITLE_TRANSITION_CALL_OFFSET : TITLE_TRANSITION_CALL_OFFSET + len(TITLE_TRANSITION_CALL_SOURCE)
    ] = bytes((0x20, helper_address & 0xFF, helper_address >> 8)) + b"\xea" * (
        len(TITLE_TRANSITION_CALL_SOURCE) - 3
    )
    result.extend(helper)
    result.extend(glyph_data)

    check_final, check_second_offset = decode_title_rle(result, FINAL_NAMETABLE_START)
    check_second, check_terminator = decode_title_rle(result, check_second_offset)
    if check_final != bytes(final_mut) or check_second != second:
        raise TitlePatchError("subtitle title-stream verification failed")
    if result[check_terminator] != 0xFF:
        raise TitlePatchError("subtitle title-stream terminator verification failed")
    return bytes(result)


def patched_nov4_exact_ips_title(
    data: bytes,
    zenpen_raw: bytes,
    *,
    subtitle: str = DEFAULT_SUBTITLE,
) -> bytes:
    """Install the exact historical logo patch and retain our English subtitle."""
    base_nov4, patched_nov4 = _exact_ips_nov4(zenpen_raw)
    exact = _overlay_exact_ips_differences(data, base_nov4, patched_nov4)
    return _install_subtitle(exact, subtitle)
