# Title sequence architecture

> **Advanced title reference.** Routine translation contributors can skip this
> document. See [Architecture](ARCHITECTURE.md) and
> [the reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md#13-title-graphics-engine)
> before changing title tooling.

The definitive English `TIME TWIST` logo is now reconstructed from
`TimeTwist-Zenpen-newlogo.ips`, SHA-256
`915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2`,
applied to the supported untouched Japanese Zenpen image, SHA-256
`B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916`.
The IPS is the visual authority. The older GIF-derived reconstruction is
historical comparison material only.

Production still uses two checked-in native 256x240 indexed authorities:

- `work/title_assets/Time Twist approved native title.png` — the exact colored
  final logo recovered from the IPS-patched NOV4 final nametable and CHR;
- `work/title_assets/Time Twist approved native slide.png` — the exact visible
  silhouette of that same logo through the native 96-pixel swipe viewport,
  rendered monochrome for the sliding phase.

The subtitle remains exactly `On the Outskirts of History...`; it is not baked
into either authority. The builder redraws it at the established location with
the deterministic production pixel font. `PUSH START`, the time machine,
copyright, attributes, and lower title art remain ROM/code-owned.

## Definitive pixel contract

The final authority owns rows 0-96 and palette indices 0-3:

- 0 black;
- 1 white;
- 2 pink;
- 3 purple.

Its native nonzero bounds are `(9,23)-(245,96)` inclusive and it contains 7,998
nonzero pixels. The completed slide uses the same nonzero silhouette on rows
0-95, converted to white, with 7,982 nonzero pixels. Row 96 is final-state-only
because NOV4's moving swipe viewport is 96 pixels high.

The canonical pixel hashes are:

| Phase | Pixel SHA-256 |
| --- | --- |
| Final | `EA50A1888635F7A8FE863C61EB6D728CE260D281FABF3259E2FED700BC75CBA8` |
| Swipe | `7FA164F34514B568560F5FC4BE7186719A692EB1013E7B00A26DE9FAE61080AB` |

`work/rebuild_native_title_asset.py` reproduces both authorities directly from
the maintainer-supplied original Zenpen and definitive IPS. It does not resize,
trace, smooth, repair, reinterpret, or artistically normalize the logo.

## Runtime allocation

NOV4's title pattern table reserves IDs `$EC-$FF` as native clock-hand source.
Those bytes remain untouched. The IPS-derived final upper logo needs 172 unique
patterns; its monochrome swipe needs 83; their union is 239 patterns. Only 236
IDs exist below `$EC`, so the current temporal allocator needs just **three**
shared slots:

1. NOV4 initially contains the monochrome swipe patterns in those three IDs.
2. The final-title transition uploads a 3-tile / 48-byte replacement delta.
3. Applying the delta reconstructs the exact colored final table.

The independent lower title region still requires 55 patterns in pattern table
0. The existing raster split remains in the blank band below `PUSH START` and
above the time machine.

## Swipe and Nintendo overlay

The resident title state machine still uses the recovered 21 damped horizontal
scroll origins. NT0 and NT1 form the same 512-pixel scrolling world, and the
native attribute tables still provide the state-3 visibility mask. The only
visual change is the artwork being moved through that mechanism: both the
completed swipe and final title now use the definitive IPS logo geometry.

The temporary Nintendo opening still occupies IDs `$B0-$D5`. Before the swipe,
the helper blanks rendering, disables NMI, restores the title patterns, queues
the monochrome palette, restores the first scroll origin, and lets the next NMI
make the new state visible without a mixed-CHR frame.

At the final transition the helper:

1. blanks rendering and disables NMI;
2. uploads the 3-tile / 48-byte final delta to pattern table 1;
3. uploads the 55 lower-title patterns to pattern table 0;
4. enables the recovered raster split and restores rendering state.

## Clock alignment

The native clock sprite CHR, metasprite records, order, and timing remain
unchanged. The two origin records now use the exact coordinates from the
definitive IPS:

```text
source: 78 00 37 04 80 00 3F
patch:  68 00 39 04 70 00 41
```

That is a 16-pixel leftward and 2-pixel downward shift for both hand origins.
The later reconstructed `-14,+3` placement is retired because the IPS artwork
and its corresponding alignment are now the authority.

## Regression contract

Tests now lock:

- exact encoded PNG and pixel hashes for both authorities;
- exact final-logo bounds, palette, and 7,998-pixel geometry;
- exact slide/final silhouette identity through row 95 and 7,982 completed
  swipe pixels;
- the current subtitle placement and unchanged ROM-owned lower title art;
- the 3-tile final-phase reconstruction identity;
- all 21 native swipe origins and the blank first/completed last states;
- native attribute tables, Nintendo overlay restoration, clock source CHR, and
  clock metasprite preservation;
- the IPS clock-origin bytes;
- legal relocated RLE framing and the NOV3 residency boundary.

A final emulator playtest remains the visual promotion gate: cold boot,
Nintendo opening, full swipe, colored final logo, animated clock hands,
subtitle, `PUSH START`, and clean title exit must all be observed on the exact
candidate build.
