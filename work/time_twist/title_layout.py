"""Recovered NOV4 layout, source guards, and title asset model."""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Recovered NOV4 memory/file layout and source guards
# ---------------------------------------------------------------------------

NOV4_LOAD_ADDRESS = 0xA200
NOV4_SOURCE_SIZE = 0x2375
TITLE_POINTER_OFFSET = 0x01BC
TITLE_POINTER_SOURCE = bytes.fromhex("A9 5E A2 A8")
PPUCTRL_INIT_OFFSET = 0x0176
PPUCTRL_INIT_SOURCE = bytes.fromhex("A5 FF 09 10 29 F7")
TITLE_EXIT_OFFSET = 0x022F
TITLE_EXIT_SOURCE = bytes.fromhex("A9 02 A2 03 4C 19 61")
BACKGROUND_TAIL_UPLOAD_OFFSET = 0x0296
BACKGROUND_TAIL_UPLOAD_SOURCE = bytes.fromhex(
    "A0 1F A9 B0 A2 04 20 AF EB 92 BA"
)
PHASE_ZERO_UPLOAD_OFFSET = 0x02AC
PHASE_ZERO_UPLOAD_SOURCE = bytes.fromhex("A0 0F A9 B0 A2 04 20 AF EB 92 BA")
SLIDE_PREP_CALL_OFFSET = 0x02E4
SLIDE_PREP_CALL_SOURCE = bytes.fromhex("20 74 AB")
TITLE_TRANSITION_CALL_OFFSET = 0x038E
TITLE_TRANSITION_CALL_SOURCE = bytes.fromhex("A9 01 8D E1 07 20 E0 6F")
SLIDE_PALETTE_COLOR1_OFFSET = 0x0995
SLIDE_PALETTE_COLOR1_SOURCE = bytes((0x0F,))
SLIDE_PALETTE_COLOR1_PATCH = bytes((0x30,))
FINAL_NAMETABLE_START = 0x065E
FINAL_NAMETABLE_END = 0x0809
SECOND_NAMETABLE_START = 0x0809
SECOND_NAMETABLE_END = 0x094C
TITLE_CHR_OFFSET = 0x09D2
TITLE_CHR_SIZE = 0x1000
CLOCK_SOURCE_TILE = 0xEC
CLOCK_SOURCE_OFFSET = TITLE_CHR_OFFSET + CLOCK_SOURCE_TILE * 16
CLOCK_SOURCE_END = TITLE_CHR_OFFSET + TITLE_CHR_SIZE
CLOCK_METASPRITE_START = 0x047A
CLOCK_METASPRITE_END = 0x059A
CLOCK_HAND_ORIGINS_OFFSET = 0x03CA
CLOCK_HAND_ORIGINS_SOURCE = bytes.fromhex("78 00 37 04 80 00 3F")
CLOCK_HAND_ORIGINS_PATCH = bytes.fromhex("6A 00 3A 04 72 00 42")
NOV3_LOAD_ADDRESS = 0xD7B5
SPLIT_TILE_ROW = 16
# Background slots below the clock-owned $EC-$FF tail are shared across two
# non-overlapping title phases. Patterns common to neither phase may reuse one
# ID because the final transition replaces their contiguous CHR delta.
TOP_TILE_COUNT = CLOCK_SOURCE_TILE
FINAL_DELTA_TILE_COUNT = 0x37
FINAL_DELTA_CHR_SIZE = FINAL_DELTA_TILE_COUNT * 16
BOTTOM_TILE_COUNT = 0x37
BOTTOM_CHR_SIZE = BOTTOM_TILE_COUNT * 16
BACKGROUND_TAIL_SIZE = 0
NINTENDO_FIRST_TILE = 0xB0
NINTENDO_TILE_COUNT = 0x26
NINTENDO_CHR_SIZE = NINTENDO_TILE_COUNT * 16
# The slide nametable contains its own reviewed monochrome wordmark. Its
# temporary Nintendo tile IDs are restored once, immediately before the swipe.
SLIDE_TITLE_TILE_COLUMNS = 32
INITIAL_CHR_LOADER_SIZE = 12
# The pre-slide helper restores the Nintendo-overlaid base-CHR range and the
# scroll origin, then queues the slide palette after the FDS BIOS upload so its
# staging state survives. It clears and later restores the $1C PPUMASK mirror
# but deliberately leaves $2001 blank. The next NMI applies the new palette and
# scroll/nametable state before copying $1C back to $2001; otherwise one frame
# can show the old Nintendo nametable through title CHR.
SLIDE_PREP_ORIGIN_AND_MASK_SIZE = 16
SLIDE_PREP_SIZE = 43 + SLIDE_PREP_ORIGIN_AND_MASK_SIZE
TITLE_TRANSITION_SIZE = 97
# Keep the screen blank while the title-only lower CHR table and raster split
# are dismantled.  Without the two PPUMASK stores below, the lower time-machine
# tile IDs are briefly rendered through the upper logo CHR table after START,
# producing a visibly scrambled machine.  Clear the $1C mirror first so an NMI
# between the two stores cannot restore the old visible mask.
TITLE_EXIT_HELPER = bytes.fromhex(
    "A9 00 85 1C 8D 01 20 8D 22 40 85 48 85 4F 85 9C "
    "A5 FF 09 10 85 FF 8D 00 20 "
    "A9 02 A2 03 4C 19 61"
)
TITLE_EXIT_SIZE = len(TITLE_EXIT_HELPER)

# Exact horizontal origins written by NOV4 states 3-5.  $57 supplies the fine
# scroll and bit zero of $58 selects the neighboring horizontal nametable.
SLIDE_SCROLL_ORIGINS = (
    0x1F0,
    0x01C,
    0x1D8,
    0x034,
    0x1C0,
    0x04C,
    0x1A8,
    0x064,
    0x190,
    0x07C,
    0x178,
    0x094,
    0x160,
    0x0AC,
    0x148,
    0x0C4,
    0x130,
    0x0DC,
    0x118,
    0x0F4,
    0x100,
)

FINAL_NAMETABLE_SOURCE_SHA256 = (
    "F01695FBF94A623BF2ADFD2172B6DB05415B33C0AB12DC4239B0C34167E06363"
)
SECOND_NAMETABLE_SOURCE_SHA256 = (
    "81DD3C65691C753EB28CC527C04E6561C0A4B67CF82D7848112028B8851E710E"
)
TITLE_CHR_SOURCE_SHA256 = (
    "B9D97C43F06079E83306A6573FAD96B3986FCEF5615BD1B0515D4E1EEF0E037C"
)
CLOCK_SOURCE_SHA256 = (
    "FE0FD6831D85105474682EB3E455B53BF64493278887F292C1904F4A875ACD2E"
)
CLOCK_METASPRITE_SHA256 = (
    "AC1BC81C837B32B7225319A86E5E5C41D20C3C081C33FB81FC6C742390458670"
)

# ---------------------------------------------------------------------------
# Rendering policy and NES palettes
# ---------------------------------------------------------------------------

DEFAULT_SUBTITLE = "On the Outskirts of History..."
DEFAULT_SLIDE_ASSET_NAME = "Time Twist approved native slide.png"
TITLE_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (243, 106, 255),
    (92, 0, 126),
)
GRAY_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (173, 173, 173),
    (102, 102, 102),
)
SPRITE_PALETTE = (
    (0, 0, 0),
    (255, 254, 255),
    (100, 176, 255),
    (21, 95, 217),
)
# State 3 queues the 32 bytes at ROM address $AB7B. The resident palette
# uploader writes that buffer backwards, so these are the four background
# palettes in the order the PPU actually sees them. Palette 1 is the moving
# logo's attribute-selected monochrome palette. The one-byte ROM patch at
# $AB95 makes all three nonzero pattern indices white, so the completed
# monochrome logo has exactly the final colored logo's visible geometry. The
# other three attribute palettes deliberately hide the still-unassembled parts
# of the two scrolled nametables.
SLIDE_BACKGROUND_PALETTES = (
    (0x0F, 0x0F, 0x0F, 0x0F),
    (0x0F, 0x30, 0x30, 0x30),
    (0x0F, 0x0F, 0x0F, 0x0F),
    (0x0F, 0x0F, 0x0F, 0x0F),
)
SLIDE_WHITE_COLOR = 0x30


class TitlePatchError(ValueError):
    """Report incompatible NOV4 data, invalid artwork, or exhausted title space.

    Title helpers raise this exception when fingerprints, dimensions, palette
    assumptions, tile budgets, or address ranges do not match the supported
    source.  These checks intentionally fail before returning patch bytes so an
    approximate preview cannot be mistaken for a safe ROM modification.
    """


@dataclass(frozen=True)
class TitleAssets:
    """All generated binary assets needed by :func:`patched_nov4_title`.

    Attributes:
        chr_data: Complete replacement for NOV4's original title CHR region.
        background_chr: Exact upper pattern table used by the final screen.
        slide_chr: Initial upper pattern table used by the monochrome swipe.
        final_delta_chr: Contiguous patterns uploaded to turn ``slide_chr``
            into ``background_chr`` during the final-title transition.
        final_delta_first_tile: First upper-table tile replaced by that delta.
        bottom_chr: Independent lower patterns loaded for the raster split.
        nintendo_chr: Temporary Nintendo-phase patterns for reserved tile IDs.
        restore_chr: Upper-title patterns restored over those temporary IDs.
            This remains the independently verified source slice; runtime
            helpers DMA the identical authoritative base-CHR location rather
            than serializing a duplicate copy into the appended payload.
        final_nametable: Decoded final title-screen nametable and attributes.
        second_nametable: Decoded slide/Nintendo nametable and attributes.
        encoded_final: Native RLE for ``final_nametable``.
        encoded_second: Native RLE for ``second_nametable``.
        approximation_error: Compatibility metric; zero for the exact split
            conversion.

    ``nintendo_chr`` and ``restore_chr`` intentionally share tile IDs across
    non-overlapping title phases. This temporal reuse avoids consuming
    additional pattern-table space without changing the clock-sprite tail.
    """

    chr_data: bytes
    background_chr: bytes
    slide_chr: bytes
    final_delta_chr: bytes
    final_delta_first_tile: int
    bottom_chr: bytes
    nintendo_chr: bytes
    restore_chr: bytes
    final_nametable: bytes
    second_nametable: bytes
    encoded_final: bytes
    encoded_second: bytes
    approximation_error: int
