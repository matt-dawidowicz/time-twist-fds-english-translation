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
    """Rasterize one font character as an 8-by-8 monochrome candidate.

    Args:
        font: Loaded Pillow FreeType font at the intended source size.
        char: Single character to draw.
        threshold: Inclusive grayscale cutoff converted to white.

    Returns:
        An 8-by-8 mode-``L`` image containing only values 0 and 255.

    Design:
        The fixed ``(1, 0)`` origin mirrors the original exploratory comparison.
        This is a visual selection tool, not the authoritative ROM glyph encoder.
    """

    grayscale = Image.new("L", (8, 8), 0)
    draw = ImageDraw.Draw(grayscale)
    draw.text((1, 0), char, font=font, fill=255)
    return grayscale.point(lambda value: 255 if value >= threshold else 0)


def main() -> None:
    """Render every configured system-font candidate into one sample sheet.

    Inputs:
        Reads the Windows font files listed in :data:`FONTS`.

    Outputs:
        Saves ``work/mesen_capture/rendered/english_font_candidates.png`` and
        prints that path.

    Raises:
        OSError: If a font cannot be loaded or the PNG cannot be written.

    Side Effects:
        Replaces the preview PNG.  Its parent directory must already exist.
    """

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
