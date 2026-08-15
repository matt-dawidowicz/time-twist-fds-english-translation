# NOV4 font-source safety

This note records the source-ownership rule exposed by the post-title repeating-background regression and the current fixed disk-prompt behavior.

## Recovered source ownership

NOV4's apparent eight-byte font-source geometry is not uniformly writable font data. The post-title graphics loader reads a normal 2bpp block from NOV4 file `$203D-$20FC`. Relative to `NOV4_FONT_BASE_OFFSET = $1B7D`, that range aliases eight-byte slots `$98-$AF`. The actual English 1bpp font-source range begins at file `$20FD` / slot `$B0` and ends after slot `$FE` at file `$2375`.

Therefore an active English glyph may use only runtime source slots `$B0-$FE`. Native lookup metadata may still describe other engine values, but those values must not become active English font writes without first recovering and redesigning the overlapping graphics ownership.

The historical failure used extended code 63, whose native lookup tile is `$AC`, as a compact `Side A` suffix. Slot `$AC` lies inside the direct 2bpp source range. The post-title Start-screen nametable fills the background with a runtime tile whose first bitplane comes from that source location, so installing the compact `A` glyph produced the repeated A-shaped background.

The current source intentionally leaves extended codes 45 and 63 inactive. The disk-change labels use ordinary-glyph `Part2` and `SideA`; they do not install private prompt ligatures.

`work/tests/test_nov4_font_source_safety.py` generalizes the regression guard from one protected tile to the complete recovered source ranges.

## Current disk-retry records

The short disk-set status at NOV2 file `$269A` is byte-aligned. Runtime save-state evidence superseded an earlier bit-3 interpretation. Its complete eight-byte record renders ordinary-glyph `Bad side.`.

The alternate eight-byte side heading at `$26CC` also renders `Bad side.`. The adjacent ten-byte `$26D4` record has room for ordinary `Wrong side.`, followed by `$26DE` `Try again.`. None of these records needs or uses the retired compact `de.` glyph.

These are size-neutral text changes only; they do not alter disk-state branches, requested-side variables, polling loops, or FDS BIOS calls.
