# Title sequence architecture

> **Advanced title reference.** Routine translation contributors can skip this
> document. See [Architecture](ARCHITECTURE.md) for the conceptual model and
> [Contributing code](../CONTRIBUTING_CODE.md) before changing title tooling.

The English opening is derived from the reviewed animation in
`work/title_assets/Time Twist approved English opening.gif`. The GIF is a
763x570 nearest-neighbor display capture with 29 frames. It contains two
different pieces of background art:

- the completed white `TIME TWIST` swipe;
- the colored final logo, clock face, and `TM`.

They are intentionally not forced into one silhouette. The subtitle is exact:
`On the Outskirts of History...`.

## Pixel authorities

`work/rebuild_native_title_asset.py` validates the GIF hash, dimensions, frame
count, loop flag, and every frame delay. It then inverts the display scaling by
majority vote within each native 256x240 pixel cell. An exhaustive round-trip
search locks the non-integer capture phases at `x=0.81`, `y=0.0`; this is what
preserves the one-pixel clock numerals, `TM`, and wordmark outline. The
conversion never uses an image resizer or lossy palette matching.

The script writes two indexed authorities:

| Phase | ROM-bound asset | Nonzero bounds | Pixel SHA-256 |
| --- | --- | --- | --- |
| Final | `Time Twist approved native title.png` | `(22,22)-(237,96)` | `083F2C1AD128196CAB1528D4F871EB4156896B6A47F1D87C41A898A9A6DC92E4` |
| Swipe | `Time Twist approved native slide.png` | `(24,25)-(235,86)` | `34FF7674E69C187BBF504C126F5F1F4ACBEF93823633C2EB00D5E4558FFC95BB` |

The final background uses the temporal mode of 19 colored-title frames. That
removes only the moving blue hand sprites; the static logo pixels remain
unchanged before a reviewed native-pixel cleanup regularizes the lower T
bevel, reference-traced clock rim, W/I/S outlines, and tiny TM. The clock uses
the unobstructed lower-left GIF quadrant mirrored across both axes, then closes
the dark inner stair corners while preserving the GIF's one-pixel black
outline outside the pink rim, including where the clock overlaps the wordmark.
The swipe comes from the completed monochrome frame. Production builds consume
the two PNGs and do not resample the GIF.

The final authority may own rows 0-96 and indices 0-3. The slide may own rows
0-95 and only indices 0-1. `title_assets.py` rejects every other size, mode,
palette, or ownership range.

## Subtitle and retained game art

The builder copies the final authority through row 96, clears rows 97-111, and
draws `On the Outskirts of History...` at `(42,102)` with the deterministic
5x7 font. This leaves five blank rows below the logo and three blank rows above
the original `PUSH START`, which begins at row 112. The time machine, copyright
line, attributes, and lower title art continue to come from the supported NOV4.

## Exact two-phase CHR allocation

NOV4's title pattern table reserves IDs `$EC-$FF` for the original animated
clock-hand source. The 236 IDs `$00-$EB` are available to the upper background.
The union of the exact swipe and final upper patterns needs 291 IDs, 55 more
than can coexist.

The allocator therefore gives 55 contiguous IDs two temporal meanings:

1. NOV4 initially contains the exact slide patterns in those IDs.
2. The final-title transition uploads 55 replacement patterns (880 bytes) to
   the same IDs while rendering and NMI are blanked.
3. Every other upper pattern keeps one fixed ID across both phases.

No pattern is clustered, substituted, or merged. Applying the stored delta to
`slide_chr` reconstructs `background_chr` byte-for-byte. The `$EC-$FF` clock
tail remains byte-identical in both tables.

The lower screen still uses NOV4's recovered mid-screen split at tile row 16.
Its exact 55-pattern set is independent of the upper title table, and the
split falls in the blank band below `PUSH START`.

## Swipe, Nintendo overlay, and transition

The resident decoder writes the final map to NT0 `$2000` and the slide/Nintendo
map to NT1 `$2400`. States 3-5 retain the original 21 damped horizontal scroll
origins. The two physical attribute tables continue to mask and reveal pieces
of the 512-pixel NT0/NT1 world.

The Nintendo opening temporarily overlays 38 IDs `$B0-$D5`. Before the swipe,
the 59-byte helper blanks the PPUMASK mirror and register, disables NMI,
restores those IDs directly from the base slide CHR, installs the first scroll
origin, queues the monochrome palette, and restores control state. The palette
is deliberately queued after the FDS BIOS CHR upload, which can overwrite its
staging state. The following NMI applies the new palette and scroll before
rendering returns.

At the final transition, the 97-byte helper:

1. blanks rendering and disables NMI;
2. uploads the 55-tile final delta to pattern table 1;
3. uploads the 55 lower-title patterns to pattern table 0;
4. enables the recovered raster split and restores rendering state.

The slide palette remains `$0F,$30,$30,$30`, so every nonzero swipe pixel is
white while the original attribute mask still controls visibility.

## Clock alignment

The source clock tiles, metasprite records, order, and timing are untouched.
Only the two metasprite origins change:

```text
source: 78 00 37 04 80 00 3F
patch:  6A 00 3A 04 72 00 42
```

That moves both origins 14 pixels left and 3 pixels down, aligning the shared
elbow with the recovered clock pivot near native coordinate `(127,78)`.

## Verification

Fixture-free tests regenerate both PNG authorities from the GIF and lock their
pixel and file hashes. Separate semantic masks lock the four clock numerals,
the `TM`, and the white letter boundary. Private-overlay integration tests
additionally verify:

- both exact phase renders and the 55-tile reconstruction identity;
- all 21 native swipe origins and per-nametable attribute masking;
- Nintendo overlay/restoration and final-delta upload addresses;
- the relocated two-nametable RLE stream and single `$FF` terminator;
- source fingerprints at every patched NOV4 site;
- byte preservation of clock CHR and metasprite data;
- the expanded NOV4 end address remains below resident NOV3 at `$D7B5`.

An emulator capture is still required before promotion. The playtest gate must
cover cold boot, the full Nintendo/swipe/final sequence, clock rotation,
subtitle spacing, `PUSH START`, and title exit with no mixed-CHR flash.
