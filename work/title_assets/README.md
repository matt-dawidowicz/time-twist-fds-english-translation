# Title artwork authority

`Time Twist approved native title.png` is the only image consumed by the ROM
builder. It is a 256x240 indexed PNG whose values are exactly:

- 0: black
- 1: white
- 2: pink
- 3: purple

Rows 96-239 are black because the asset owns only the wordmark and retained
TM. Subtitle, PUSH START, machine art, and copyright remain ROM/code-owned.
The blue clock hand is intentionally absent; NOV4 continues to animate it with
the original sprite CHR and metasprite tables.

`Time Twist polished design reference.png` is the supplied Image 2 design
reference. `work/rebuild_native_title_asset.py` records the deliberate native
reconstruction: inverse 4:3 mapping, a `(-4,-4)` placement chosen to preserve
the established lower composition, the exact frozen-hand mask, and ten
pink/purple bevel edits. Those edits reduce the finished upper title from 244
to exactly 236 unique 8x8 patterns without changing a single silhouette or
white-outline pixel.

The older high-resolution title PNGs remain historical comparison inputs. They
are not production title authorities and are never resampled by release-build.
