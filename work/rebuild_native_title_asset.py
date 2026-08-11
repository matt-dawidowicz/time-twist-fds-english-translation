"""Reproduce the reviewed native title authority from the two design sources.

The production ROM builder consumes only the resulting 256x240 indexed PNG.
This script documents the one-time, deliberate reconstruction from Image 2:
inverse 4:3 display mapping, a four-pixel placement correction that preserves
the existing subtitle/lower composition, exact live-hand clearing, and ten
bevel-only pixel harmonizations needed to fit the clock-safe CHR budget.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

TITLE_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (243, 106, 255),
    (92, 0, 126),
)
NATIVE_SIZE = (256, 240)
VISIBLE_SIZE = (256, 224)
PLACEMENT = (-4, -4)
TM_GUARD = (210, 0, 256, 32)

# These ten fill pixels make eight tile patterns identical to existing ones.
# Every edit is index 2 <-> 3: silhouette and white-outline membership remain
# byte-for-byte identical to the unbudgeted native reconstruction.
BEVEL_EDITS = {
    (175, 15): 2,
    (95, 36): 2,
    (53, 38): 2,
    (53, 39): 2,
    (52, 55): 3,
    (46, 69): 2,
    (47, 69): 3,
    (183, 71): 2,
    (48, 72): 2,
    (71, 72): 3,
}


def _reference_to_indices(path: Path) -> Image.Image:
    """Inverse-map one display reference to exact title palette indices."""
    source = (
        Image.open(path)
        .convert("RGB")
        .resize(
            VISIBLE_SIZE,
            Image.Resampling.NEAREST,
        )
    )
    result = Image.new("L", NATIVE_SIZE, 0)
    for y in range(VISIBLE_SIZE[1]):
        for x in range(VISIBLE_SIZE[0]):
            pixel = source.getpixel((x, y))
            if pixel[2] - pixel[0] > 100 and pixel[2] - pixel[1] > 60:
                continue
            result.putpixel(
                (x, y),
                min(
                    range(4),
                    key=lambda index: sum(
                        (left - right) ** 2
                        for left, right in zip(
                            pixel, TITLE_PALETTE[index], strict=True
                        )
                    ),
                ),
            )
    return result


def build_native_title(
    design_reference: Path, legacy_reference: Path
) -> Image.Image:
    """Return the exact reviewed 256x240 indexed production authority."""
    desired = _reference_to_indices(design_reference)
    # Image 2 contains one frozen NW-to-SE sprite frame. The chromatic blue
    # core is removed above; this exact native stroke clears its bright fringe.
    ImageDraw.Draw(desired).line((116, 58, 135, 84), fill=0, width=3)
    legacy = _reference_to_indices(legacy_reference)
    result = Image.new("L", NATIVE_SIZE, 0)
    shift_x, shift_y = PLACEMENT
    for y in range(98):
        for x in range(256):
            if y < TM_GUARD[3] and x >= TM_GUARD[0]:
                continue
            target_x = x + shift_x
            target_y = y + shift_y
            if 0 <= target_x < 256 and 0 <= target_y < 92:
                result.putpixel((target_x, target_y), desired.getpixel((x, y)))

    # TM was explicitly outside the requested redesign.
    x0, y0, x1, y1 = TM_GUARD
    result.paste(legacy.crop(TM_GUARD), (x0, y0, x1, y1))

    raw = result.copy()
    for coordinate, value in BEVEL_EDITS.items():
        before = result.getpixel(coordinate)
        if {before, value} != {2, 3}:
            raise ValueError(
                f"unexpected bevel source at {coordinate}: {before}"
            )
        result.putpixel(coordinate, value)
    for before, after in zip(
        raw.get_flattened_data(), result.get_flattened_data(), strict=True
    ):
        if (before == 0) != (after == 0) or (before == 1) != (after == 1):
            raise ValueError(
                "budget edits changed silhouette or white outline"
            )
    return result


def main() -> None:
    """Write the deterministic native asset selected by command-line paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--design-reference",
        type=Path,
        default=Path(
            "work/title_assets/Time Twist polished design reference.png"
        ),
    )
    parser.add_argument(
        "--legacy-reference",
        type=Path,
        default=Path(
            "work/title_assets/Time Twist full-screen logo reference.png"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("work/title_assets/Time Twist approved native title.png"),
    )
    args = parser.parse_args()
    image = build_native_title(args.design_reference, args.legacy_reference)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
