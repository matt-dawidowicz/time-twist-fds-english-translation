# NOV4 font-source safety

This note records the source-ownership rule exposed by the post-title repeating-background regression and the current fixed disk-prompt behavior.

## Recovered source ownership

NOV4's apparent eight-byte font-source geometry is not uniformly writable font data. The post-title graphics loader reads a normal 2bpp block from NOV4 file `$203D-$20FC`. Relative to `NOV4_FONT_BASE_OFFSET = $1B7D`, that range aliases eight-byte slots `$98-$AF`. The actual English 1bpp font-source range begins at file `$20FD` / slot `$B0` and ends after slot `$FE` at file `$2375`.

Therefore an active English glyph may use only runtime source slots `$B0-$FE`. Native lookup metadata may still describe other engine values, but those values must not become active English font writes without first recovering and redesigning the overlapping graphics ownership.

The historical failure used extended code 63, whose native lookup tile is `$AC`, as a compact `Side A` suffix. Slot `$AC` lies inside the direct 2bpp source range. The post-title Start-screen nametable fills the background with a runtime tile whose first bitplane comes from that source location, so installing the compact `A` glyph produced the repeated A-shaped background.

The current source intentionally leaves extended codes 45 and 63 inactive. The disk-change labels use ordinary-glyph `Part2` and `SideA`; they do not install private prompt ligatures.

`work/tests/test_nov4_font_source_safety.py` generalizes the regression guard from one protected tile to the complete recovered source ranges.

## Current disk-retry records

Runtime save-state comparison at a genuine side-change request showed NOV2
drawing file `$26D4`, then `$26DE`: the primary same-side retry is **`Wrong side.`
/ `Try again.`**. It does not use the wrong-disk instruction pair. The compact
headings are separate records and must not be the only accepted result in a
playtest checklist.

| NOV2 file offset | Packed bytes | English text | Role |
| --- | ---: | --- | --- |
| `$269A` | 8 | `Bad side.` | Disk-set status |
| `$26CC` | 8 | `Bad side.` | Alternate compact side heading |
| `$26D4` | 10 | `Wrong side.` | Observed primary same-side heading |
| `$26DE` | 10 | `{CTRL:0}Try again.` | Same-side retry instruction |
| `$26E8` | 11 | `Wrong disk! ` | Wrong-disk heading |
| `$26F3` | 14 | `{CTRL:0}Try another side` | Wrong-disk instruction |

The `$269A` status is byte-aligned; runtime evidence superseded the early bit-3
interpretation. The whole eight-byte record is guarded and replaced. Its compact
`Bad side.` text uses ordinary glyphs; no record needs the cramped `de.` ligature.

These are size-neutral text replacements. Disk-state branches, requested-side
variables, polling loops, and FDS BIOS calls retain their source behavior.

The recorded path evidence identifies the expected messages; it does not certify
a new candidate. Use [DISK-02 and DISK-04](PLAYTEST_MATRIX.md) for separate
wrong-disk and same-side recovery tests, recording the mounted/requested side,
message reached, repeated retry, and successful recovery.
