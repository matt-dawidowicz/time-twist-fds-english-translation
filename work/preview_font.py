"""Render candidate 8x8 dialogue fonts for visual selection."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.()\"'-/:!?"
FONTS = (
    ("Consolas 8", Path(r"C:\Windows\Fonts\consola.ttf"), 8),
    ("Consolas Bold 8", Path(r"C:\Windows\Fonts\consolab.ttf"), 8),
    ("Lucida Console 8", Path(r"C:\Windows\Fonts\lucon.ttf"), 8),
)


def render_glyph(font: ImageFont.FreeTypeFont, char: str, threshold: int) -> Image.Image:
    """Rasterize one character as a thresholded 8x8 monochrome preview."""

    grayscale = Image.new("L", (8, 8), 0)
    draw = ImageDraw.Draw(grayscale)
    draw.text((1, 0), char, font=font, fill=255)
    return grayscale.point(lambda value: 255 if value >= threshold else 0)


def main() -> None:
    """Render the configured font sample sheet for visual inspection."""

    scale = 4
    columns = 16
    rows_per_font = (len(CHARACTERS) + columns - 1) // columns
    section_height = 20 + rows_per_font * 8 * scale
    output = Image.new("RGB", (columns * 8 * scale, len(FONTS) * section_height), "white")
    draw = ImageDraw.Draw(output)
    for font_index, (label, path, size) in enumerate(FONTS):
        y_base = font_index * section_height
        draw.text((2, y_base + 2), label, fill="black")
        font = ImageFont.truetype(path, size)
        for index, char in enumerate(CHARACTERS):
            glyph = render_glyph(font, char, 96).resize(
                (8 * scale, 8 * scale), Image.Resampling.NEAREST
            )
            x = (index % columns) * 8 * scale
            y = y_base + 20 + (index // columns) * 8 * scale
            output.paste(glyph, (x, y))
    path = Path("work/mesen_capture/rendered/english_font_candidates.png")
    output.save(path)
    print(path)


if __name__ == "__main__":
    main()
