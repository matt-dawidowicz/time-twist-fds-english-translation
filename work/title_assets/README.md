# Title artwork authority

The approved English opening has three checked-in layers:

- `Time Twist approved English opening.gif` is the reviewed 763x570,
  29-frame display animation and regeneration provenance.
- `Time Twist approved native title.png` is the reviewed colored final
  background at 256x240. It uses indices 0-3 and owns rows 0-96.
- `Time Twist approved native slide.png` is the exact completed monochrome
  swipe recovered at 256x240. It uses indices 0-1 and owns rows 0-95.

Both PNGs embed their display palettes, so ordinary image viewers show the
intended colors. The palette metadata does not alter the ROM-bound index at
any pixel.

The final indices are:

- 0: black
- 1: white
- 2: pink
- 3: purple

The ROM builder consumes both native PNGs. Subtitle, `PUSH START`, machine art,
and copyright remain ROM/code-owned. The blue clock hand is intentionally
absent from the final background; NOV4 continues to animate it with the
original sprite CHR and metasprite tables.

`work/rebuild_native_title_asset.py` locks the GIF's SHA-256, dimensions,
frame count, loop flag, and all frame delays. It inverts the nearest-neighbor
display grid by native-cell majority vote with exhaustively calibrated capture
phases, takes the completed white swipe as its own authority, and uses temporal
consensus across the colored frames to remove the moving hand sprites without
repainting static title pixels. It then applies the reviewed native-pixel
cleanup to the lower T bevel, reference-traced clock rim, W/I/S outlines, and
balanced TM. The first T's upper cap receives one reviewed color correction,
and the clock's three traced bands receive native stair bridges so they are
closed under four-neighbor pixel connectivity. Regression tests independently
lock those edits, the thin `12`/`9`/`3`/`6` clock strokes, the `TM`, and the
white wordmark boundary.

The older high-resolution title PNGs remain historical comparison inputs. They
are not production title authorities and are never resampled by release-build.
