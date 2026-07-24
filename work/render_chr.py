"""Render raw NES/FDS 2bpp CHR files as indexed tile sheets."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


PALETTE = (0, 85, 170, 255)


def render_chr(data: bytes, columns: int = 16, scale: int = 2) -> Image.Image:
    """Decode NES 2bpp CHR bytes into a scaled tile-sheet image."""

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
            (image.width * scale, image.height * scale), Image.Resampling.NEAREST
        )
    return image


def main() -> None:
    """Render a CHR binary selected on the command line to PNG."""

    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=16)
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--offset", type=lambda value: int(value, 0), default=0)
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
