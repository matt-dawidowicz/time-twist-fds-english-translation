"""Render the replacement title assets without building or launching the ROM.

This script is a fast visual-review tool. It uses the same title-asset helpers
as the patcher so preview discrepancies point to asset/layout code rather than
an unrelated mockup pipeline.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from time_twist.title import (
    build_title_assets,
    overlay_clock_sprites,
    render_title_background,
)


SOURCE = Path("work/build/NOV4_accented_font_ui.bin")
REFERENCE = Path("work/title_assets/Time Twist full-screen logo reference.png")
CHR_CAPTURE = Path("work/mesen_capture/zenpen_title_chr.dmp")
CPU_CAPTURE = Path("work/mesen_capture/zenpen_title_cpu.dmp")
OUTPUT = Path("outputs/Time Twist exact split-title preview.png")


def main() -> None:
    """Build and save the current English title-screen preview image."""

    assets = build_title_assets(SOURCE.read_bytes(), REFERENCE)
    background = render_title_background(assets)

    cpu = CPU_CAPTURE.read_bytes()
    oam = bytearray(cpu[0x0200:0x0220])
    for sprite in range(8):
        offset = sprite * 4
        oam[offset] = (oam[offset] - 6) & 0xFF
        oam[offset + 3] = (oam[offset + 3] - 8) & 0xFF
    preview = overlay_clock_sprites(background, CHR_CAPTURE.read_bytes(), bytes(oam))
    preview = preview.resize((1024, 960), Image.Resampling.NEAREST)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    preview.save(OUTPUT)
    print(f"{OUTPUT} (exact background error: {assets.approximation_error})")


if __name__ == "__main__":
    main()
