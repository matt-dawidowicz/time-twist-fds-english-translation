"""Render a production-font specimen for visual regression review."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from time_twist.font import render_glyph

SAMPLES = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "abcdefghijklmnopqrstuvwxyz",
    "0123456789",
    "September 25, 1995",
    "I've been meaning to come here.",
    "Your personality is…",
    "Pépé, are you all right?",
    "Yes—Jesus Christ!",
    "The Gestapo are nearby.",
    "Pay $120 now.",
)


def main() -> None:
    """Render the authoritative font with visible baseline/descender guides."""
    scale = 6
    tile_size = 8
    label_height = 12
    margin = 10
    max_characters = max(map(len, SAMPLES))
    width = (max_characters * tile_size + margin * 2) * scale
    row_height = tile_size * scale + label_height
    height = margin * scale * 2 + len(SAMPLES) * row_height

    image = Image.new("RGB", (width, height), (246, 218, 163))
    draw = ImageDraw.Draw(image)
    label_font = ImageFont.load_default()

    for line_number, text in enumerate(SAMPLES):
        top = margin * scale + line_number * row_height
        draw.text(
            (4, top - 11),
            str(line_number + 1),
            fill=(80, 70, 65),
            font=label_font,
        )

        # Row 6 is the common baseline; row 7 is reserved for descenders.
        draw.line(
            (0, top + 6 * scale, width - 1, top + 6 * scale),
            fill=(218, 184, 132),
        )
        draw.line(
            (0, top + 7 * scale, width - 1, top + 7 * scale),
            fill=(232, 202, 154),
        )

        for character_number, character in enumerate(text):
            glyph = render_glyph(character)
            left = margin * scale + character_number * tile_size * scale
            for y, row in enumerate(glyph):
                for x in range(8):
                    if row & (1 << (7 - x)):
                        continue
                    draw.rectangle(
                        (
                            left + x * scale,
                            top + y * scale,
                            left + (x + 1) * scale - 1,
                            top + (y + 1) * scale - 1,
                        ),
                        fill=(25, 17, 18),
                    )

    output = Path("work/build/production_font_preview.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    print(output)


if __name__ == "__main__":
    main()
