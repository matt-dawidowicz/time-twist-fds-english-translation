"""Render available monospaced 8x8 font candidates for visual selection."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.()\"'-/:!?"
FONT_CANDIDATES = (
    ("DejaVu Sans Mono 8", "DejaVuSansMono.ttf", 8),
    ("Liberation Mono 8", "LiberationMono-Regular.ttf", 8),
    ("Consolas 8", "consola.ttf", 8),
    ("Consolas Bold 8", "consolab.ttf", 8),
    ("Lucida Console 8", "lucon.ttf", 8),
)


def font_search_paths(filename: str) -> tuple[Path | str, ...]:
    """Return portable name-based and common operating-system font locations."""
    paths: list[Path | str] = [filename]
    windows = os.environ.get("WINDIR")
    if windows:
        paths.append(Path(windows) / "Fonts" / filename)
    paths.extend(
        (
            Path("/usr/share/fonts/truetype/dejavu") / filename,
            Path("/usr/share/fonts/truetype/liberation2") / filename,
            Path("/Library/Fonts") / filename,
            Path.home() / "Library" / "Fonts" / filename,
        )
    )
    return tuple(paths)


def load_available_fonts() -> tuple[tuple[str, ImageFont.FreeTypeFont], ...]:
    """Load each distinct available candidate without requiring a specific OS."""
    loaded: list[tuple[str, ImageFont.FreeTypeFont]] = []
    for label, filename, size in FONT_CANDIDATES:
        for candidate in font_search_paths(filename):
            try:
                font = ImageFont.truetype(candidate, size)
            except OSError:
                continue
            loaded.append((label, font))
            break
    if not loaded:
        raise OSError("no configured monospaced font candidate is available")
    return tuple(loaded)


def render_glyph(
    font: ImageFont.FreeTypeFont, char: str, threshold: int
) -> Image.Image:
    """Rasterize one font character as an 8-by-8 monochrome candidate."""
    grayscale = Image.new("L", (8, 8), 0)
    draw = ImageDraw.Draw(grayscale)
    draw.text((1, 0), char, font=font, fill=255)
    return grayscale.point(lambda value: 255 if value >= threshold else 0)


def main() -> None:
    """Render every available candidate into one portable sample sheet."""
    fonts = load_available_fonts()
    scale = 4
    columns = 16
    rows_per_font = (len(CHARACTERS) + columns - 1) // columns
    section_height = 20 + rows_per_font * 8 * scale
    output = Image.new(
        "RGB", (columns * 8 * scale, len(fonts) * section_height), "white"
    )
    draw = ImageDraw.Draw(output)
    for font_index, (label, font) in enumerate(fonts):
        y_base = font_index * section_height
        draw.text((2, y_base + 2), label, fill="black")
        for index, char in enumerate(CHARACTERS):
            glyph = render_glyph(font, char, 96).resize(
                (8 * scale, 8 * scale), Image.Resampling.NEAREST
            )
            x = (index % columns) * 8 * scale
            y = y_base + 20 + (index // columns) * 8 * scale
            output.paste(glyph, (x, y))
    path = Path("work/mesen_capture/rendered/english_font_candidates.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    output.save(path)
    print(path)


if __name__ == "__main__":
    main()
