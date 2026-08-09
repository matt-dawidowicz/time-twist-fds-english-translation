"""Render a labeled range of NES/FDS CHR tiles for reverse engineering."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw
from render_chr import render_chr


def main() -> None:
    """Render and label a selected range of CHR tile indices.

    Inputs:
        Accepts input/output paths plus a starting tile index, tile count,
        column count, scale, and optional monochrome conversion.

    Outputs:
        Writes an RGB PNG whose cells contain a scaled tile and its three-digit
        hexadecimal index, then prints the input/output mapping and dimensions.

    Raises:
        OSError: If the source cannot be read or the output cannot be written.
        ValueError: If dimensions derived from command-line values are invalid.

    Side Effects:
        Creates the output parent directory as needed and replaces the PNG.

    Note:
        Rendering stops cleanly at the first incomplete tile.  ``--monochrome``
        isolates NES color index 1, which is useful when locating text glyphs.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start", type=lambda value: int(value, 0), default=0)
    parser.add_argument(
        "--count", type=lambda value: int(value, 0), default=0x100
    )
    parser.add_argument("--columns", type=int, default=8)
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument(
        "--monochrome",
        action="store_true",
        help="render color-1 pixels white and every other color black",
    )
    args = parser.parse_args()

    data = args.input.read_bytes()
    tile_size = 8 * args.scale
    label_height = 16
    cell_height = tile_size + label_height
    rows = (args.count + args.columns - 1) // args.columns
    output = Image.new(
        "RGB", (args.columns * tile_size, rows * cell_height), "white"
    )
    draw = ImageDraw.Draw(output)

    for relative_index in range(args.count):
        tile_index = args.start + relative_index
        tile_data = data[tile_index * 16 : tile_index * 16 + 16]
        if len(tile_data) < 16:
            break
        tile = render_chr(tile_data, columns=1, scale=args.scale).convert(
            "RGB"
        )
        if args.monochrome:
            tile = tile.point(lambda value: 255 if value == 85 else 0)
        x = (relative_index % args.columns) * tile_size
        y = (relative_index // args.columns) * cell_height
        output.paste(tile, (x, y))
        draw.text(
            (x + 2, y + tile_size + 1), f"{tile_index:03X}", fill="black"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output)
    print(f"{args.input} -> {args.output} ({output.width}x{output.height})")


if __name__ == "__main__":
    main()
