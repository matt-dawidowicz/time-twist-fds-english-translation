"""Apply the safe final-layer v65 twelve-month Fortune Teller patch."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "work"))

from time_twist.fds import FdsImage
from time_twist.tt1a_month_menu import (
    MONTH_GRID,
    month_text_ppu_address,
    parse_tt1a_primary_descriptors,
    patch_nov2_twelve_choice_geometry,
    patch_tt1a_month_descriptor,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.input.read_bytes()
    image = FdsImage.from_bytes(source)
    if len(image.sides) != 4:
        raise ValueError(f"expected four FDS sides, found {len(image.sides)}")

    nov2 = image.sides[0].find_file("NOV2")
    tt1a = image.sides[1].find_file("TT1A")
    nov2.data = patch_nov2_twelve_choice_geometry(nov2.data)
    tt1a.data = patch_tt1a_month_descriptor(tt1a.data)

    result = image.to_bytes()
    if len(result) != len(source):
        raise ValueError(
            f"image size changed from {len(source)} to {len(result)} bytes"
        )

    descriptors = parse_tt1a_primary_descriptors(tt1a.data)
    args.output.write_bytes(result)
    print(f"input_sha256={_sha256(source)}")
    print(f"output_sha256={_sha256(result)}")
    print(f"image_bytes={len(result)}")
    print(f"descriptors={descriptors!r}")
    print("month_grid:")
    for row in MONTH_GRID:
        print("  " + "  ".join(row))
    print("month_ppu_addresses:")
    for slot in range(12):
        print(f"  slot={slot:2d} ppu=${month_text_ppu_address(slot):04X}")


if __name__ == "__main__":
    main()
