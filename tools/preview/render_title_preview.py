"""Render the replacement title assets without building or launching the ROM.

This script is a fast visual-review tool. It uses the same title-asset helpers
as the patcher so preview discrepancies point to asset/layout code rather than
an unrelated mockup pipeline.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from time_twist.title import (
    SLIDE_SCROLL_ORIGINS,
    build_title_assets,
    overlay_clock_sprites,
    render_monochrome_slide_frame,
    render_title_background,
)

SOURCE = Path("work/build/NOV4_accented_font_ui.bin")
REFERENCE = Path("work/title_assets/Time Twist approved native title.png")
CHR_CAPTURE = Path("work/runtime_capture/zenpen_title_chr.dmp")
CPU_CAPTURE = Path("work/runtime_capture/zenpen_title_cpu.dmp")
OUTPUT = Path("outputs/Time Twist exact split-title preview.png")
SLIDE_OUTPUT_DIR = Path("outputs/title-slide-frames")
SLIDE_CONTACT_SHEET = Path(
    "outputs/Time Twist slide sequence contact sheet.png"
)


def main() -> None:
    """Build the patched title background and overlay captured clock sprites.

    Inputs:
        Reads the patched NOV4 bank, full-screen reference, CHR capture, and CPU
        capture configured by module constants.

    Outputs:
        Saves a 1024-by-960 nearest-neighbor preview and prints its exact
        background approximation error.

    Raises:
        OSError: If an input cannot be read or the preview cannot be written.
        time_twist.title.TitlePatchError: If source validation, asset generation,
            or background rendering fails.

    Side Effects:
        Creates the output directory as needed and replaces the preview PNG.

    Design:
        The eight clock sprites are shifted to match the title patch's placement
        before overlay.  Using the production asset helpers ensures visual errors
        identify real patch/layout code rather than a separate mockup pipeline.
    """
    assets = build_title_assets(SOURCE.read_bytes(), REFERENCE)
    background = render_title_background(assets)

    cpu = CPU_CAPTURE.read_bytes()
    oam = bytearray(cpu[0x0200:0x0220])
    for sprite in range(8):
        offset = sprite * 4
        oam[offset] = (oam[offset] - 8) & 0xFF
        oam[offset + 3] = (oam[offset + 3] - 16) & 0xFF
    preview = overlay_clock_sprites(
        background, CHR_CAPTURE.read_bytes(), bytes(oam)
    )
    preview = preview.resize((1024, 960), Image.Resampling.NEAREST)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    preview.save(OUTPUT)
    SLIDE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slide_frames = []
    for index, origin in enumerate(SLIDE_SCROLL_ORIGINS):
        frame = render_monochrome_slide_frame(assets, origin)
        frame.save(
            SLIDE_OUTPUT_DIR / f"frame-{index:02d}-scroll-{origin:03X}.png"
        )
        slide_frames.append(frame)

    representative = (0, 2, 5, 10, 15, 19, 20)
    sheet = Image.new("RGB", (4 * 256, 2 * 240), (0, 0, 0))
    for cell, frame_index in enumerate(representative):
        sheet.paste(
            slide_frames[frame_index],
            ((cell % 4) * 256, (cell // 4) * 240),
        )
    sheet.resize((2048, 960), Image.Resampling.NEAREST).save(
        SLIDE_CONTACT_SHEET
    )
    print(f"{OUTPUT} (exact background error: {assets.approximation_error})")
    print(f"{SLIDE_OUTPUT_DIR} ({len(slide_frames)} native slide frames)")
    print(SLIDE_CONTACT_SHEET)


if __name__ == "__main__":
    main()
