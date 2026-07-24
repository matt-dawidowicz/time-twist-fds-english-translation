"""Render the installed 8x8 pixel glyphs without launching an emulator."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from time_twist.font import render_glyph


SAMPLES = (
    "PART1  SIDE B  INSERT NOW",
    "September 25, 1995",
    "Do you prefer consommé",
    "News: Dr. Simon spoke",
    "The quick brown fox.",
)


def main() -> None:
    scale = 4
    margin = 8
    width = (max(map(len, SAMPLES)) * 8 + margin * 2) * scale
    height = (len(SAMPLES) * 10 + margin * 2) * scale
    image = Image.new("RGB", (width, height), (246, 218, 163))
    pixels = image.load()
    ink = (25, 17, 18)

    for line_number, text in enumerate(SAMPLES):
        cell_y = margin + line_number * 10
        for character_number, char in enumerate(text):
            glyph = render_glyph(char)
            cell_x = margin + character_number * 8
            for y, row in enumerate(glyph):
                for x in range(8):
                    if not row & (1 << (7 - x)):
                        for dy in range(scale):
                            for dx in range(scale):
                                pixels[
                                    (cell_x + x) * scale + dx,
                                    (cell_y + y) * scale + dy,
                                ] = ink

    output = Path("work/build/mixed_case_font_preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    print(output)


if __name__ == "__main__":
    main()
