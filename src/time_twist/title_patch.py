"""Guarded NOV4 title installation and preview rendering helpers."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .title_assets import (
    _pixel_access,
    _render_indexed_nametable,
    _render_split_nametable,
    build_title_assets,
    decode_title_rle,
    decode_title_stream,
)
from .title_layout import (
    BACKGROUND_TAIL_UPLOAD_OFFSET,
    BOTTOM_CHR_SIZE,
    CLOCK_HAND_ORIGINS_OFFSET,
    CLOCK_HAND_ORIGINS_PATCH,
    CLOCK_METASPRITE_END,
    CLOCK_METASPRITE_START,
    CLOCK_SOURCE_END,
    CLOCK_SOURCE_OFFSET,
    DEFAULT_SUBTITLE,
    FINAL_DELTA_CHR_SIZE,
    GRAY_PALETTE,
    INITIAL_CHR_LOADER_SIZE,
    NINTENDO_CHR_SIZE,
    NINTENDO_FIRST_TILE,
    NOV3_LOAD_ADDRESS,
    NOV4_LOAD_ADDRESS,
    SLIDE_BACKGROUND_PALETTES,
    SLIDE_PALETTE_COLOR1_OFFSET,
    SLIDE_PALETTE_COLOR1_PATCH,
    SLIDE_PALETTE_COLOR1_SOURCE,
    SLIDE_PREP_CALL_OFFSET,
    SLIDE_PREP_CALL_SOURCE,
    SLIDE_PREP_SIZE,
    SLIDE_WHITE_COLOR,
    SPRITE_PALETTE,
    TITLE_CHR_OFFSET,
    TITLE_CHR_SIZE,
    TITLE_EXIT_HELPER,
    TITLE_EXIT_OFFSET,
    TITLE_EXIT_SIZE,
    TITLE_EXIT_SOURCE,
    TITLE_PALETTE,
    TITLE_POINTER_OFFSET,
    TITLE_TRANSITION_CALL_OFFSET,
    TITLE_TRANSITION_CALL_SOURCE,
    TITLE_TRANSITION_SIZE,
    TitleAssets,
    TitlePatchError,
)


def _pre_slide_restore_helper(slide_restore_address: int) -> bytes:
    """Return the state-3 helper that hides the Nintendo-to-title remap.

    The helper blanks the PPUMASK mirror/register, disables NMI, restores the
    title CHR over the Nintendo-owned tile IDs, installs the first native
    scroll origin, queues the native monochrome palette, then restores PPUCTRL
    and the PPUMASK mirror. The palette call must follow the FDS BIOS CHR
    upload: that upload can overwrite the palette staging buffer and update
    flag. The helper intentionally does not restore $2001 itself: the next NMI
    must first copy the new scroll origin and palette into the real PPU
    registers, then restore rendering from $1C. Restoring $2001 inside this
    helper shows one frame of the old Nintendo nametable with restored
    English-title CHR.
    """
    helper = (
        bytes.fromhex(
            "A5 1C 48 A9 00 85 1C 8D 01 20 "
            "A5 FF 48 29 7F 8D 00 20 "
            "A0 1B A9 00 A2 26 20 AF EB"
        )
        + slide_restore_address.to_bytes(2, "little")
        + bytes.fromhex(
            "A9 01 85 58 A9 F0 85 57 85 4D "
            "20 74 AB "
            "68 85 FF 09 10 85 FF 8D 00 20 "
            "68 85 1C EA EA EA 60"
        )
    )
    if len(helper) != SLIDE_PREP_SIZE:
        raise TitlePatchError(
            "pre-slide CHR restore helper has an unexpected size"
        )
    return helper


def patched_nov4_title(
    data: bytes,
    target: Path,
    *,
    slide_target: Path | None = None,
    subtitle: str = DEFAULT_SUBTITLE,
) -> bytes:
    """Return NOV4 with relocated English title assets and helper code.

    Args:
        data: Original NOV4 overlay accepted by :func:`_validate_source`.
        target: Approved native 256-by-240 indexed title image.
        slide_target: Approved native monochrome swipe authority. By default
            this is the named sibling asset beside ``target``.
        subtitle: Localized subtitle to retain under the wordmark.

    Returns:
        Expanded NOV4 bytes containing title assets and verified helper code.

    Raises:
        OSError: If the native title image cannot be read.
        TitlePatchError: If asset generation fails, helper sizes change, the
            expanded overlay would overlap NOV3, a source patch site differs,
            or any post-build verification fails.

    The function appends lower-title CHR, Nintendo overlay CHR, the exact
    final-phase CHR delta, four small 6502 helpers, and two compressed
    nametables. It rewrites only the
    recovered palette/call/pointer/origin sites and the background CHR region.
    The expanded overlay must finish below resident NOV3 at ``$D7B5``. Inputs
    and the native title file are not modified.
    """
    assets = build_title_assets(
        data,
        target,
        slide_target=slide_target,
        subtitle=subtitle,
    )
    bottom_chr_offset = len(data)
    nintendo_chr_offset = bottom_chr_offset + BOTTOM_CHR_SIZE
    final_delta_offset = nintendo_chr_offset + NINTENDO_CHR_SIZE
    initial_loader_offset = final_delta_offset + len(assets.final_delta_chr)
    slide_prep_offset = initial_loader_offset + INITIAL_CHR_LOADER_SIZE
    transition_offset = slide_prep_offset + SLIDE_PREP_SIZE
    exit_offset = transition_offset + TITLE_TRANSITION_SIZE
    title_stream_offset = exit_offset + TITLE_EXIT_SIZE

    def loaded_address(offset: int) -> int:
        """Convert a validated NOV4 file offset to its loaded CPU address.

        Args:
            offset: Offset inside the bank's loaded payload.

        Returns:
            CPU address obtained by adding the bank's load base.

        Note:
            The enclosing function validates the final expanded address against
            NOV3 residency after all appended regions have been laid out.
        """
        return NOV4_LOAD_ADDRESS + offset

    bottom_chr_address = loaded_address(bottom_chr_offset)
    nintendo_chr_address = loaded_address(nintendo_chr_offset)
    final_delta_address = loaded_address(final_delta_offset)
    initial_loader_address = loaded_address(initial_loader_offset)
    slide_prep_address = loaded_address(slide_prep_offset)
    transition_address = loaded_address(transition_offset)
    exit_address = loaded_address(exit_offset)
    title_stream_address = loaded_address(title_stream_offset)

    # The native loader has already copied the exact upper title into pattern
    # table 1. Temporarily overlay the Nintendo patterns on IDs $B0-$D5.  A
    # one-shot state-3 helper restores the underlying title patterns before
    # any slide pixels become visible. The helper and later title state read
    # the authoritative base CHR, so no serialized restore duplicate is needed.
    initial_loader = bytes.fromhex("A0 1B A9 00 A2 26 20 AF EB") + bytes(
        (nintendo_chr_address & 0xFF, nintendo_chr_address >> 8)
    )
    initial_loader += b"\x60"
    if len(initial_loader) != INITIAL_CHR_LOADER_SIZE:
        raise TitlePatchError("initial title loader has an unexpected size")

    # Blank the PPU/NMI while restoring the 38 Nintendo-temporary patterns
    # directly from the patched base CHR in this bank. Clear the PPUMASK mirror
    # before blanking the register so a pending NMI cannot restore rendering
    # during the blanked region. Queue the original state-3 monochrome palette
    # only after the FDS BIOS upload, which can clobber its staging buffer and
    # update flag. Restore the original $01F0 origin before NMI is restored,
    # but leave $2001 blank so the next NMI can install the new scroll,
    # palette, and nametable state before rendering becomes visible.
    slide_restore_address = loaded_address(
        TITLE_CHR_OFFSET + NINTENDO_FIRST_TILE * 16
    )
    slide_prep = _pre_slide_restore_helper(slide_restore_address)

    # State $17 uploads the minimal contiguous delta that turns the exact
    # monochrome slide table into the exact colored final table, installs the
    # independent exact lower set in pattern table 0, and enables NOV4's existing
    # scene/dialogue raster split.  That proven split occurs in the blank band
    # between PUSH START and the time machine, never through visible artwork.
    transition = bytes.fromhex("A9 01 8D E1 07 20 E0 6F")
    transition += bytes.fromhex("A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20")
    delta_tile_count = len(assets.final_delta_chr) // 16
    if (
        len(assets.final_delta_chr) != FINAL_DELTA_CHR_SIZE
        or len(assets.final_delta_chr) % 16
        or delta_tile_count > 0xFF
    ):
        raise TitlePatchError("final title CHR delta has an invalid size")
    delta_ppu_address = 0x1000 + assets.final_delta_first_tile * 16
    if not 0x1000 <= delta_ppu_address <= 0x1FFF:
        raise TitlePatchError(
            "final title CHR delta has an invalid PPU address"
        )
    if delta_tile_count:
        transition += bytes(
            (
                0xA0,
                delta_ppu_address >> 8,
                0xA9,
                delta_ppu_address & 0xFF,
                0xA2,
                delta_tile_count,
                0x20,
                0xAF,
                0xEB,
                final_delta_address & 0xFF,
                final_delta_address >> 8,
            )
        )
    else:
        transition += b"\xea" * 11
    transition += bytes.fromhex("A0 00 A9 00 A2 37 20 AF EB") + bytes(
        (bottom_chr_address & 0xFF, bottom_chr_address >> 8)
    )
    transition += bytes.fromhex(
        "68 85 FF 09 10 85 FF 8D 00 20 "
        "A9 00 85 4F 85 55 85 57 85 58 85 49 85 4A "
        "8D 70 07 8D 71 07 "
        "A9 FF 85 48 A9 10 85 56 "
        "A9 C0 8D 72 07 A9 3F 8D 73 07 "
        "A5 1C 8D 01 20 60"
    )
    if len(transition) != TITLE_TRANSITION_SIZE:
        raise TitlePatchError("title transition helper has an unexpected size")

    # Blank rendering, then disable the title-only raster split before handing
    # control to the game.  Keeping both the PPUMASK mirror and register blank
    # prevents the lower time-machine tile IDs from being rendered through the
    # upper logo CHR table during teardown.  Clear the saved menu-cancel pointer
    # as well so the post-title flow cannot inherit a stale destination.  The
    # menu engine may install a fresh pointer while constructing START; NOV2's
    # separate one-choice B guard handles that case without affecting
    # Back/Cancel on larger menus.
    # The helper ends with the original state change, so it intentionally does
    # not return to the replaced START-button branch.
    exit_helper = TITLE_EXIT_HELPER
    if len(exit_helper) != TITLE_EXIT_SIZE:
        raise TitlePatchError("title exit helper has an unexpected size")

    append = b"".join(
        (
            assets.bottom_chr,
            assets.nintendo_chr,
            assets.final_delta_chr,
            initial_loader,
            slide_prep,
            transition,
            exit_helper,
            assets.encoded_final,
            assets.encoded_second,
            b"\xff",
        )
    )
    if loaded_address(len(data) + len(append)) > NOV3_LOAD_ADDRESS:
        raise TitlePatchError(
            "expanded NOV4 would overlap resident NOV3 memory"
        )

    result = bytearray(data)
    result[
        SLIDE_PALETTE_COLOR1_OFFSET : SLIDE_PALETTE_COLOR1_OFFSET
        + len(SLIDE_PALETTE_COLOR1_SOURCE)
    ] = SLIDE_PALETTE_COLOR1_PATCH
    result[TITLE_POINTER_OFFSET : TITLE_POINTER_OFFSET + 4] = bytes(
        (0xA9, title_stream_address & 0xFF, 0xA2, title_stream_address >> 8)
    )
    result[
        BACKGROUND_TAIL_UPLOAD_OFFSET : BACKGROUND_TAIL_UPLOAD_OFFSET + 11
    ] = (
        bytes(
            (0x20, initial_loader_address & 0xFF, initial_loader_address >> 8)
        )
        + b"\xea" * 8
    )
    result[
        SLIDE_PREP_CALL_OFFSET : SLIDE_PREP_CALL_OFFSET
        + len(SLIDE_PREP_CALL_SOURCE)
    ] = bytes((0x20, slide_prep_address & 0xFF, slide_prep_address >> 8))
    # Preserve the original tail-call structure here.  The source branch JMPs
    # to $6119, whose RTS returns directly to the main engine.  Using JSR for
    # this detour leaves an extra return address on the stack, so $6119's RTS
    # falls back into the middle of NOV4 and crashes immediately after START.
    result[TITLE_EXIT_OFFSET : TITLE_EXIT_OFFSET + len(TITLE_EXIT_SOURCE)] = (
        bytes((0x4C, exit_address & 0xFF, exit_address >> 8))
        + b"\xea" * (len(TITLE_EXIT_SOURCE) - 3)
    )
    result[
        TITLE_TRANSITION_CALL_OFFSET : TITLE_TRANSITION_CALL_OFFSET
        + len(TITLE_TRANSITION_CALL_SOURCE)
    ] = bytes((0x20, transition_address & 0xFF, transition_address >> 8)) + (
        b"\xea" * (len(TITLE_TRANSITION_CALL_SOURCE) - 3)
    )
    # The recovered clock face is centered at about (127,78) in native pixels.
    # Move both original metasprite origins so their shared elbow lands on that
    # center. Frame layouts, tiles, order, and timing remain unchanged.
    result[
        CLOCK_HAND_ORIGINS_OFFSET : CLOCK_HAND_ORIGINS_OFFSET
        + len(CLOCK_HAND_ORIGINS_PATCH)
    ] = CLOCK_HAND_ORIGINS_PATCH
    result[TITLE_CHR_OFFSET : TITLE_CHR_OFFSET + TITLE_CHR_SIZE] = (
        assets.chr_data
    )
    result.extend(append)

    decoded_final, second_offset = decode_title_rle(
        result, title_stream_offset
    )
    decoded_second, terminator_offset = decode_title_rle(result, second_offset)
    decoded_combined, end = decode_title_stream(result, title_stream_offset)
    if decoded_final != assets.final_nametable:
        raise TitlePatchError(
            "relocated final title nametable failed verification"
        )
    if decoded_second != assets.second_nametable:
        raise TitlePatchError(
            "relocated second title nametable failed verification"
        )
    if terminator_offset >= len(result) or result[terminator_offset] != 0xFF:
        raise TitlePatchError("relocated title stream lost its $FF terminator")
    if (
        decoded_combined != assets.final_nametable + assets.second_nametable
        or end != len(result)
    ):
        raise TitlePatchError(
            "relocated combined title stream failed verification"
        )
    if result[bottom_chr_offset:nintendo_chr_offset] != assets.bottom_chr:
        raise TitlePatchError("exact lower-title tiles failed verification")
    if result[nintendo_chr_offset:final_delta_offset] != assets.nintendo_chr:
        raise TitlePatchError("Nintendo overlay tiles failed verification")
    if (
        result[final_delta_offset:initial_loader_offset]
        != assets.final_delta_chr
    ):
        raise TitlePatchError("final title CHR delta failed verification")
    if (
        result[
            SLIDE_PALETTE_COLOR1_OFFSET : SLIDE_PALETTE_COLOR1_OFFSET
            + len(SLIDE_PALETTE_COLOR1_PATCH)
        ]
        != SLIDE_PALETTE_COLOR1_PATCH
    ):
        raise TitlePatchError(
            "slide palette color-1 patch failed verification"
        )
    if (
        result[CLOCK_SOURCE_OFFSET:CLOCK_SOURCE_END]
        != data[CLOCK_SOURCE_OFFSET:CLOCK_SOURCE_END]
    ):
        raise TitlePatchError("clock-hand source bytes changed")
    if (
        result[CLOCK_METASPRITE_START:CLOCK_METASPRITE_END]
        != data[CLOCK_METASPRITE_START:CLOCK_METASPRITE_END]
    ):
        raise TitlePatchError("clock metasprite animation bytes changed")
    if (
        result[
            CLOCK_HAND_ORIGINS_OFFSET : CLOCK_HAND_ORIGINS_OFFSET
            + len(CLOCK_HAND_ORIGINS_PATCH)
        ]
        != CLOCK_HAND_ORIGINS_PATCH
    ):
        raise TitlePatchError(
            "clock-hand origin correction failed verification"
        )
    return bytes(result)


def render_slide_logo_frame(
    assets: TitleAssets,
    scroll_origin: int,
) -> Image.Image:
    """Reconstruct one exact 256-by-96 native swipe viewport.

    Args:
        assets: ROM-bound title CHR and nametables.
        scroll_origin: Nine-bit horizontal origin formed by ``$58:$57``.

    Returns:
        Attribute-masked geometry for the twelve moving tile rows. Visible
        pixels retain their native nonzero 2bpp value (1, 2, or 3); pixels
        whose selected runtime palette entry is black are returned as zero.

    Raises:
        TitlePatchError: If the origin is outside the two-nametable world.

    NT0 is the final map at $2000 and NT1 is the slide/Nintendo map at $2400.
    The resident NMI writes the low eight bits to PPUSCROLL and bit eight to
    PPUCTRL. Sampling their 512-pixel concatenation therefore models the
    actual wrap boundary without relying on a static mockup. Each physical
    nametable's attribute table is applied before scrolling. This is essential:
    the state-3 palette uses attribute palette 1 as a visibility mask, making
    origin $1F0 blank and revealing alternating strips as the origin settles.
    """
    if not 0 <= scroll_origin < 0x200:
        raise TitlePatchError("title scroll origin must be a nine-bit value")

    def runtime_mask(nametable: bytes) -> Image.Image:
        """Apply NOV4's state-3 attribute palettes to one physical map."""
        indexed = _render_indexed_nametable(
            nametable,
            assets.slide_chr,
        ).crop((0, 0, 256, 96))
        source = _pixel_access(indexed)
        masked = Image.new("L", indexed.size, 0)
        target = _pixel_access(masked)
        attributes = nametable[960:1024]
        for y in range(96):
            for x in range(256):
                attribute = attributes[(y // 32) * 8 + (x // 32)]
                shift = ((y // 16) & 1) * 4 + ((x // 16) & 1) * 2
                palette_id = (attribute >> shift) & 3
                pattern_index = source[x, y]
                if (
                    SLIDE_BACKGROUND_PALETTES[palette_id][pattern_index]
                    == SLIDE_WHITE_COLOR
                ):
                    target[x, y] = pattern_index
        return masked

    final = runtime_mask(assets.final_nametable)
    slide = runtime_mask(assets.second_nametable)
    world = Image.new("L", (512, 96), 0)
    world.paste(final, (0, 0))
    world.paste(slide, (256, 0))
    frame = Image.new("L", (256, 96), 0)
    first_width = min(256, 512 - scroll_origin)
    frame.paste(
        world.crop((scroll_origin, 0, scroll_origin + first_width, 96)),
        (0, 0),
    )
    if first_width < 256:
        frame.paste(
            world.crop((0, 0, 256 - first_width, 96)),
            (first_width, 0),
        )
    return frame


def render_monochrome_slide_frame(
    assets: TitleAssets,
    scroll_origin: int,
) -> Image.Image:
    """Colorize one attribute-masked swipe frame as black and white."""
    indexed = render_slide_logo_frame(assets, scroll_origin)
    image = Image.new("RGB", (256, 240), TITLE_PALETTE[0])
    source = _pixel_access(indexed)
    target = _pixel_access(image)
    for y in range(96):
        for x in range(256):
            if source[x, y]:
                target[x, y] = TITLE_PALETTE[1]
    return image


def render_title_background(assets: TitleAssets) -> Image.Image:
    """Render generated title assets as a full-color verification image.

    Args:
        assets: Generated title nametable and split CHR sets.

    Returns:
        A new 256-by-240 RGB image with attribute-table palette selection.

    This preview omits animated clock-hand sprites. Use
    :func:`overlay_clock_sprites` with a runtime capture to inspect a frame.
    """
    indexed = _render_split_nametable(
        assets.final_nametable,
        assets.background_chr,
        assets.bottom_chr,
    )
    attributes = assets.final_nametable[960:1024]
    source = _pixel_access(indexed)
    image = Image.new("RGB", indexed.size, TITLE_PALETTE[0])
    target = _pixel_access(image)
    for y in range(240):
        for x in range(256):
            attribute = attributes[(y // 32) * 8 + (x // 32)]
            shift = ((y // 16) & 1) * 4 + ((x // 16) & 1) * 2
            palette_id = (attribute >> shift) & 3
            palette = GRAY_PALETTE if palette_id == 3 else TITLE_PALETTE
            target[x, y] = palette[source[x, y]]
    return image


def overlay_clock_sprites(
    background: Image.Image,
    chr_dump: bytes,
    oam: bytes,
) -> Image.Image:
    """Overlay one captured clock-hand frame on a title preview.

    Args:
        background: Base title image; it is copied and never modified.
        chr_dump: Complete 8-KiB runtime NES pattern-table capture.
        oam: At least the first eight four-byte sprite records.

    Returns:
        A new RGB image with nontransparent hand pixels applied.

    Raises:
        TitlePatchError: If the CHR dump is not exactly 8 KiB or fewer than
            eight sprites are available.

    Horizontal/vertical flip bits and the NES OAM y-plus-one convention are
    honored. Sprite priority and palette-number bits are intentionally ignored
    because the captured hand uses one known verification palette.
    """
    if len(chr_dump) != 0x2000 or len(oam) < 0x20:
        raise TitlePatchError(
            "clock preview needs 8 KB CHR and eight OAM sprites"
        )
    image = background.copy().convert("RGB")
    pixels = _pixel_access(image)
    for sprite in range(8):
        y, tile_id, attributes, x = oam[sprite * 4 : sprite * 4 + 4]
        tile = chr_dump[tile_id * 16 : tile_id * 16 + 16]
        flip_x = bool(attributes & 0x40)
        flip_y = bool(attributes & 0x80)
        for row in range(8):
            source_y = 7 - row if flip_y else row
            low = tile[source_y]
            high = tile[source_y + 8]
            for column in range(8):
                source_x = 7 - column if flip_x else column
                shift = 7 - source_x
                value = ((low >> shift) & 1) | (((high >> shift) & 1) << 1)
                if value == 0:
                    continue
                screen_x = x + column
                screen_y = y + 1 + row
                if 0 <= screen_x < 256 and 0 <= screen_y < 240:
                    pixels[screen_x, screen_y] = SPRITE_PALETTE[value]
    return image
