"""Recover and polish native title phases from the approved opening GIF.

The supplied animation is a nearest-neighbor, 4:3 display capture rather than
a native 256x240 framebuffer. This tool deterministically inverts that pixel
grid, separates the completed monochrome swipe from the colored final title,
removes the live blue clock-hand sprites by temporal consensus, and applies a
small reviewed native-pixel cleanup to the colored wordmark. The ROM builder
consumes only the two resulting indexed PNGs; it never resamples the display
GIF during a release build.
"""

from __future__ import annotations

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from PIL import Image

OPENING_SHA256 = (
    "56B1473C88D0F811F7C1DED2A45D51B248129D3D3C2937E8814D70C8D95C2273"
)
DISPLAY_SIZE = (763, 570)
NATIVE_SIZE = (256, 240)
FRAME_COUNT = 29
FRAME_DELAYS_MS = (
    1320,
    70,
    70,
    70,
    70,
    70,
    1130,
    70,
    530,
    70,
    70,
    70,
    70,
    60,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
    70,
)
SLIDE_FRAME_INDEX = 6
FINAL_FRAME_INDICES = tuple(range(10, 29))
# The capture is not an integer resize.  These phases are the unique minimum
# of an exhaustive round-trip search over the nearest-neighbor cell boundaries
# in the static title region.  In particular, a one-display-pixel vertical
# offset erases the clock numerals and folds the one-pixel TM strokes together.
X_PHASE = 0.81
Y_PHASE = 0.0
FINAL_LAST_ROW = 96
SLIDE_LAST_ROW = 95
FINAL_DISPLAY_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (243, 106, 255),
    (92, 0, 126),
)
SLIDE_DISPLAY_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
)

# Reviewed final-phase cleanup in native coordinates. These edits regularize
# the wordmark bevels and outlines, reconstruct the clock from its unobstructed
# GIF quadrant, and redraw the tiny TM as balanced 5x7 glyphs. The monochrome
# swipe remains its own distinct GIF-derived authority.
FIRST_T_LOWER_BEVEL_Y = 78
FIRST_T_LOWER_BEVEL_X = range(40, 49)
FIRST_T_TIP_BOX = (56, 26, 66, 30)
CLOCK_TRACE_CENTER_X = 126
CLOCK_TRACE_Y_SUM = 151
# Each string follows the clean lower-left clock quadrant from the GIF after
# removing face sprites/numerals. P/W/D/0 mean pink/white/dark-purple/black.
# The top/bottom pink tangent is completed across the same width visible in
# the display reference; majority recovery had retained only its center.
# Mirroring this clean quadrant restores the rim where the logo obscures it
# without replacing the reference raster with a mathematically drawn ellipse.
CLOCK_TRACE_ROWS = (
    (76, 109, "PWD000000000000000"),
    (77, 109, "PWD000000000000000"),
    (78, 109, "PWD000000000000000"),
    (79, 109, "PWD000000000000000"),
    (80, 109, "PWD000000000000000"),
    (81, 109, "PWWD00000000000000"),
    (82, 110, "PWD00000000000000"),
    (83, 110, "PWD00000000000000"),
    (84, 110, "PWWD0000000000000"),
    (85, 111, "PWD0000000000000"),
    (86, 111, "PWWD000000000000"),
    (87, 112, "PWD000000000000"),
    (88, 112, "PWWD00000000000"),
    (89, 113, "PWWD0000000000"),
    (90, 114, "PWWD000000000"),
    (91, 115, "PWWD00000000"),
    (92, 116, "PWWD0000000"),
    (93, 117, "PWWDDD0000"),
    (94, 118, "PWWWWDDDD"),
    (95, 119, "PPPWWWWW"),
    (96, 119, "PPPPPPPP"),
)
CLOCK_TRACE_COLORS = {"0": 0, "W": 1, "P": 2, "D": 3}
# Single-pixel diagonal ring traces touch only at their corners. These reviewed
# stair bridges retain the traced silhouette while making the pink outer rim
# and dark inner rim closed under native 4-neighbor pixel connectivity.
CLOCK_PINK_BRIDGES_LOWER_LEFT = (
    (109, 82),
    (110, 85),
    (111, 87),
    (112, 89),
    (113, 90),
    (114, 91),
    (115, 92),
    (116, 93),
    (117, 94),
    (118, 95),
)
CLOCK_DARK_BRIDGES_LOWER_LEFT = (
    (112, 80),
    (113, 83),
    (114, 85),
    (115, 87),
    (116, 88),
    (117, 89),
    (118, 90),
    (119, 91),
    (120, 92),
    (123, 93),
)
CLOCK_RIM_BRIDGE_PATCH = {
    (mirrored_x, mirrored_y): value
    for value, coordinates in (
        (2, CLOCK_PINK_BRIDGES_LOWER_LEFT),
        (3, CLOCK_DARK_BRIDGES_LOWER_LEFT),
    )
    for x, y in coordinates
    for mirrored_x in {x, 2 * CLOCK_TRACE_CENTER_X - x}
    for mirrored_y in {y, CLOCK_TRACE_Y_SUM - y}
}
CLOCK_NUMERAL_BOXES = (
    (124, 60, 131, 65),
    (112, 74, 116, 80),
    (137, 74, 141, 80),
    (125, 89, 130, 94),
)
S_ENTRY_PATCH = {
    **{(x, 61): 0 for x in range(180, 184)},
    **{(x, 62): 0 for x in range(179, 183)},
    (184, 61): 1,
    (185, 61): 1,
    (186, 61): 3,
    (183, 62): 1,
    (184, 62): 1,
    (185, 62): 3,
}
FINAL_OUTLINE_PATCH = {
    (54, 31): 1,
    # Remove the lone pink cell at the first T's upper-right tip.
    (64, 30): 3,
    # Finish the paired white/dark stairs inside the first T and W.
    (77, 59): 1,
    (77, 60): 1,
    (165, 68): 1,
    (165, 69): 1,
    (166, 68): 3,
    (166, 69): 3,
    (197, 45): 1,
    (187, 51): 1,
    (187, 52): 1,
    (168, 57): 1,
    **{(x, 62): 1 for x in range(179, 183)},
    **{(x, 63): 1 for x in range(179, 187)},
    (179, 64): 1,
    **{(x, 64): 3 for x in range(180, 186)},
    (188, 68): 1,
    (207, 71): 1,
    (208, 72): 1,
    **{(155, y): 1 for y in range(78, 88)},
}
TM_CLEAR_BOX = (216, 21, 235, 33)
TM_GLYPHS = (
    (("11111", "00100", "00100", "00100", "00100", "00100", "00100"), 219),
    (("10001", "11011", "10101", "10101", "10001", "10001", "10001"), 226),
)
TM_TOP = 23


def _sha256(path: Path) -> str:
    """Return an uppercase SHA-256 digest for one source asset."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _axis_cells(
    destination: int, source: int, phase: float
) -> list[list[int]]:
    """Map display coordinates into deterministic native-pixel cells."""
    cells = [[] for _ in range(source)]
    for coordinate in range(destination):
        native = min(
            source - 1,
            max(0, int((coordinate + phase) * source / destination)),
        )
        cells[native].append(coordinate)
    if any(not cell for cell in cells):
        raise ValueError("opening scale does not cover every native pixel")
    return cells


def _native_frame(frame: Image.Image) -> Image.Image:
    """Recover one 256x240 RGB frame by display-cell majority voting."""
    source = frame.convert("RGB")
    if source.size != DISPLAY_SIZE:
        raise ValueError(
            f"opening frame is {source.size}, expected {DISPLAY_SIZE}"
        )
    x_cells = _axis_cells(DISPLAY_SIZE[0], NATIVE_SIZE[0], X_PHASE)
    y_cells = _axis_cells(DISPLAY_SIZE[1], NATIVE_SIZE[1], Y_PHASE)
    source_pixels = source.load()
    if source_pixels is None:
        raise ValueError("opening frame does not expose pixels")
    result = Image.new("RGB", NATIVE_SIZE, (0, 0, 0))
    result_pixels = result.load()
    if result_pixels is None:
        raise ValueError("native frame does not expose pixels")
    for native_y, source_rows in enumerate(y_cells):
        for native_x, source_columns in enumerate(x_cells):
            counts = Counter(
                source_pixels[x, y]
                for y in source_rows
                for x in source_columns
            )
            highest = max(counts.values())
            result_pixels[native_x, native_y] = min(
                color for color, count in counts.items() if count == highest
            )
    return result


def _palette_index(color: tuple[int, int, int]) -> int:
    """Map the capture's phase palettes to their native 2bpp indices."""
    red, green, blue = color
    if color == (0, 0, 0):
        return 0
    # The blue clock hands are sprites, not background-title pixels.
    if blue - red > 100 and blue - green > 50:
        return 0
    if red > 220 and green > 220 and blue > 220:
        return 1
    if abs(red - green) < 3 and abs(green - blue) < 3:
        return 2 if red > 140 else 3
    if red > 150 and blue > 200:
        return 2
    if red < 120 and green < 40 and blue > 90:
        return 3
    raise ValueError(f"unsupported opening color {color}")


def _temporal_mode(frames: list[Image.Image]) -> Image.Image:
    """Recover the static final background beneath the moving hand sprites."""
    if not frames:
        raise ValueError("opening has no final-title frames")
    pixels = [frame.load() for frame in frames]
    if any(access is None for access in pixels):
        raise ValueError("opening frame does not expose pixels")
    result = Image.new("RGB", NATIVE_SIZE, (0, 0, 0))
    target = result.load()
    if target is None:
        raise ValueError("temporal title does not expose pixels")
    for y in range(NATIVE_SIZE[1]):
        for x in range(NATIVE_SIZE[0]):
            counts = Counter(access[x, y] for access in pixels)
            highest = max(counts.values())
            target[x, y] = min(
                color for color, count in counts.items() if count == highest
            )
    return result


def _indexed_final(frames: list[Image.Image]) -> Image.Image:
    """Return the static colored logo/TM authority without live sprites."""
    static = _temporal_mode(frames)
    source = static.load()
    if source is None:
        raise ValueError("static title does not expose pixels")
    result = Image.new("L", NATIVE_SIZE, 0)
    target = result.load()
    if target is None:
        raise ValueError("indexed title does not expose pixels")
    for y in range(FINAL_LAST_ROW + 1):
        for x in range(NATIVE_SIZE[0]):
            target[x, y] = _palette_index(source[x, y])
    return result


def _indexed_slide(frame: Image.Image) -> Image.Image:
    """Return the completed monochrome wordmark used by the swipe phase."""
    source = frame.load()
    if source is None:
        raise ValueError("slide title does not expose pixels")
    result = Image.new("L", NATIVE_SIZE, 0)
    target = result.load()
    if target is None:
        raise ValueError("indexed slide does not expose pixels")
    for y in range(SLIDE_LAST_ROW + 1):
        for x in range(NATIVE_SIZE[0]):
            if source[x, y] != (0, 0, 0):
                target[x, y] = 1
    return result


def _apply_reviewed_final_polish(indexed: Image.Image) -> Image.Image:
    """Apply the approved native-pixel colored-title cleanup."""
    if indexed.mode != "L" or indexed.size != NATIVE_SIZE:
        raise ValueError("final-title polish requires native indexed pixels")
    result = indexed.copy()
    pixels = result.load()
    if pixels is None:
        raise ValueError("native final title does not expose pixels")

    for x in FIRST_T_LOWER_BEVEL_X:
        pixels[x, FIRST_T_LOWER_BEVEL_Y] = 3

    clock_numerals = {
        (x, y)
        for left, top, right, bottom in CLOCK_NUMERAL_BOXES
        for y in range(top, bottom)
        for x in range(left, right)
        if pixels[x, y] == 1
    }

    for source_y, left, trace in CLOCK_TRACE_ROWS:
        if len(trace) != CLOCK_TRACE_CENTER_X - left + 1:
            raise ValueError("clock trace does not end at its center column")
        for y in (source_y, CLOCK_TRACE_Y_SUM - source_y):
            right = 2 * CLOCK_TRACE_CENTER_X - left
            for x in range(left, right + 1):
                pixels[x, y] = 0
            for offset, symbol in enumerate(trace):
                x = left + offset
                value = CLOCK_TRACE_COLORS[symbol]
                pixels[x, y] = value
                pixels[2 * CLOCK_TRACE_CENTER_X - x, y] = value
    for coordinate, value in CLOCK_RIM_BRIDGE_PATCH.items():
        pixels[coordinate] = value
    for coordinate in clock_numerals:
        pixels[coordinate] = 1

    for coordinate, value in S_ENTRY_PATCH.items():
        pixels[coordinate] = value
    for coordinate, value in FINAL_OUTLINE_PATCH.items():
        pixels[coordinate] = value

    left, top, right, bottom = TM_CLEAR_BOX
    for y in range(top, bottom):
        for x in range(left, right):
            pixels[x, y] = 0
    for glyph, glyph_left in TM_GLYPHS:
        for row, source_row in enumerate(glyph):
            for column, value in enumerate(source_row):
                if value == "1":
                    pixels[glyph_left + column, TM_TOP + row] = 1
    return result


def _with_display_palette(
    indexed: Image.Image,
    colors: tuple[tuple[int, int, int], ...],
) -> Image.Image:
    """Embed visible RGB colors without changing any native pixel index."""
    if indexed.mode != "L":
        raise ValueError("native title indices must use mode L before display")
    result = Image.new("P", indexed.size, 0)
    result.putdata(indexed.get_flattened_data())
    palette = [channel for color in colors for channel in color]
    palette.extend([0] * (768 - len(palette)))
    result.putpalette(palette)
    return result


def build_native_titles(
    opening_reference: Path,
) -> tuple[Image.Image, Image.Image]:
    """Return exact indexed final and slide authorities from the reviewed GIF."""
    if _sha256(opening_reference) != OPENING_SHA256:
        raise ValueError("opening GIF does not match the reviewed authority")
    with Image.open(opening_reference) as opening:
        if opening.size != DISPLAY_SIZE or opening.n_frames != FRAME_COUNT:
            raise ValueError("opening GIF dimensions or frame count changed")
        if opening.info.get("loop") != 0:
            raise ValueError("opening GIF must loop indefinitely")
        native_frames: list[Image.Image] = []
        delays: list[int] = []
        for index in range(opening.n_frames):
            opening.seek(index)
            delays.append(int(opening.info.get("duration", 0)))
            native_frames.append(_native_frame(opening.copy()))
    if tuple(delays) != FRAME_DELAYS_MS:
        raise ValueError("opening GIF frame timing changed")
    final = _apply_reviewed_final_polish(
        _indexed_final([native_frames[index] for index in FINAL_FRAME_INDICES])
    )
    slide = _indexed_slide(native_frames[SLIDE_FRAME_INDEX])
    if final.getbbox() != (22, 22, 238, 97):
        raise ValueError(f"unexpected final-title bounds {final.getbbox()}")
    if slide.getbbox() != (24, 25, 236, 87):
        raise ValueError(f"unexpected slide-title bounds {slide.getbbox()}")
    if set(final.get_flattened_data()) != {0, 1, 2, 3}:
        raise ValueError(
            "final title did not recover all four palette indices"
        )
    if set(slide.get_flattened_data()) != {0, 1}:
        raise ValueError("slide title is not strictly monochrome")
    return (
        _with_display_palette(final, FINAL_DISPLAY_PALETTE),
        _with_display_palette(slide, SLIDE_DISPLAY_PALETTE),
    )


def main() -> None:
    """Write the deterministic native assets selected by command-line paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--opening-reference",
        type=Path,
        default=Path(
            "work/title_assets/Time Twist approved English opening.gif"
        ),
    )
    parser.add_argument(
        "--final-output",
        type=Path,
        default=Path("work/title_assets/Time Twist approved native title.png"),
    )
    parser.add_argument(
        "--slide-output",
        type=Path,
        default=Path("work/title_assets/Time Twist approved native slide.png"),
    )
    args = parser.parse_args()
    final, slide = build_native_titles(args.opening_reference)
    for path, image in (
        (args.final_output, final),
        (args.slide_output, slide),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        print(path)


if __name__ == "__main__":
    main()
