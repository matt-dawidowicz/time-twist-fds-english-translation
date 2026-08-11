# Title sequence architecture

This page is the concise architectural summary. For the full recovered memory
map, exact patch sites, appended-region layout, helper semantics, historical
failure modes, and test evidence, read the
[bug-fix and title-screen implementation guide](BUG_FIXES_AND_TITLE_IMPLEMENTATION.md#english-title-screen-reconstruction).

The title is owned by NOV4, loaded at `$A200`. The source overlay is `$2375`
bytes. The patched overlay must end below resident NOV3 at `$D7B5`.

## Native graphics

- Background CHR begins at NOV4 file offset `$09D2`.
- Tile IDs `$00-$EB` are the 236 title-safe background slots.
- Tile IDs `$EC-$FF` are the original clock-hand source tail and remain
  byte-identical.
- The final upper title uses exactly 236 patterns.
- The lower split set uses exactly 55 patterns.
- The raster split remains at tile row 16, below PUSH START.
- Both title nametables decode to exactly 1,024 bytes.

The production artwork is `work/title_assets/Time Twist approved native
title.png`. `title.py` rejects every non-native size, non-indexed mode, and
palette index above 3. It never resizes the production source.

## Nametables and swipe

The resident decoder writes the first decoded map to NT0 `$2000` and the
second to NT1 `$2400`. NT0 holds the final title. The first twelve tile rows of
NT1 are copied mechanically from the same final native pixels, including all
32 columns. Therefore the terminal monochrome frame at origin `$0100` and the
corresponding final geometry are identical by construction.

NOV4's original states 3-5 write these nine-bit horizontal origins:

```text
1F0 01C 1D8 034 1C0 04C 1A8 064 190 07C 178
094 160 0AC 148 0C4 130 0DC 118 0F4 100
```

`$57` supplies PPUSCROLL and bit zero of `$58` selects NT0/NT1. This is one
whole-screen origin; the title raster split is disabled during states 3-5.
The origins retain the original damped left/right motion toward `$0100`.
NT0's upper attributes select black palette 0 while NT1's upper attributes
select visible palette 1, so the scroll produces the native blank-to-
alternating-strip assembly rather than moving an already complete logo.

The stock state-3 palette hid native index 1, so its settled monochrome logo
lost the final title's white outline. The patch source-checks and changes NOV4
file offset `$0995` (CPU `$AB95`) from `$0F` to `$30`. Runtime palette 1 is now
`$0F,$30,$30,$30`: every nontransparent native logo pixel becomes white, while
the attribute mask still keeps unrevealed pixels black. The completed frame at
origin `$0100` is therefore byte-identical in geometry to the approved colored
logo before the palette/title-state transition.

## Nintendo reuse and restoration

The opening Nintendo art temporarily overlays 38 pattern IDs `$B0-$D5`.
Previously the English slide avoided those IDs by blacking columns 27-31,
which made the completed monochrome logo incomplete and caused a geometry
jump when NT0 replaced it.

The patch now hooks the original state-3 `JSR $AB74` at NOV4 file offset
`$02E4`. The appended helper preserves that monochrome-palette call, blanks
rendering/NMI, restores `$B0-$D5` from the patched base CHR, restores PPU state,
and returns before the untouched code arms origin `$01F0`. The original
12-pixel movement, state timing, later final-title transition, and title exit
remain in place.

## Verification helpers

`render_slide_logo_frame()` reconstructs the exact NT0/NT1 512-pixel world
from ROM-bound CHR and nametables. `render_title_preview.py` emits all 21 native
swipe frames plus a representative contact sheet and the final title preview.
These are deterministic static evidence, not substitutes for emulator proof.

## Runtime proof

The unpromoted Zenpen candidate with SHA-256
`10C893513CC97C3D8657DDF3BF1DC333DC9B0960D0061A227B5D89621F35769B`
was cold-booted twice in headless Mesen 2.2.1 for 1,150 frames. All 1,153
compared artifacts from the two runs were byte-identical. The moving assembly
occupies frames 896-915, the exact completed monochrome logo remains visible
through frame 979, the palette-only refinement occupies frames 980-983, the
final colored map fades in at frames 1020-1027, and preserved hand animation
is visible from frame 1029. Mesen stderr was empty. The capture harness retains
no FDS BIOS.
