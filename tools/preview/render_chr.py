"""Render raw NES/FDS 2bpp CHR files as indexed tile sheets."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

PALETTE = (0, 85, 170, 255)


def render_chr(data: bytes, columns: int = 16, scale: int = 2) -> Image.Image:
    """Decode complete NES/FDS 2bpp CHR tiles into a grayscale sheet.

    Args:
        data: Pattern-table bytes; each complete tile occupies sixteen bytes.
        columns: Number of tiles per output row.
        scale: Positive integer nearest-neighbor enlargement factor.

    Returns:
        A mode-``L`` Pillow image using four evenly spaced grayscale values.

    Raises:
        ZeroDivisionError: If ``columns`` is zero.
        ValueError: If dimensions implied by negative values are invalid.

    Assumptions:
        The first eight bytes of each tile are bitplane 0 and the next eight are
        bitplane 1.  Trailing bytes that do not form a complete tile are ignored.
    """
    tile_count = len(data) // 16
    rows = (tile_count + columns - 1) // columns
    image = Image.new("L", (columns * 8, rows * 8), 0)
    pixels = image.load()

    for tile_index in range(tile_count):
        tile = data[tile_index * 16 : tile_index * 16 + 16]
        tile_x = (tile_index % columns) * 8
        tile_y = (tile_index // columns) * 8
        for y in range(8):
            low = tile[y]
            high = tile[y + 8]
            for x in range(8):
                shift = 7 - x
                value = ((low >> shift) & 1) | (((high >> shift) & 1) << 1)
                pixels[tile_x + x, tile_y + y] = PALETTE[value]

    if scale != 1:
        image = image.resize(
            (image.width * scale, image.height * scale),
            Image.Resampling.NEAREST,
        )
    return image


def main() -> None:
    """Render selected CHR byte ranges to PNG tile sheets.

    Inputs:
        Accepts one or more binary paths, a required output directory, and
        optional column count, scale, byte offset, and byte length.

    Outputs:
        Writes one PNG per input using the input stem and prints dimensions.

    Raises:
        OSError: If an input cannot be read or an output cannot be written.
        ValueError: If numeric arguments or resulting image dimensions are
            invalid.

    Side Effects:
        Creates the output directory as needed and replaces same-named PNGs.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=16)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument(
        "--offset", type=lambda value: int(value, 0), default=0
    )
    parser.add_argument("--length", type=lambda value: int(value, 0))
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in args.inputs:
        output_path = args.output_dir / f"{input_path.stem}.png"
        data = input_path.read_bytes()[args.offset :]
        if args.length is not None:
            data = data[: args.length]
        image = render_chr(data, args.columns, args.scale)
        image.save(output_path)
        print(f"{input_path} -> {output_path} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
