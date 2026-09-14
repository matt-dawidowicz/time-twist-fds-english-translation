# Title artwork authority

The authoritative English `TIME TWIST` wordmark comes from the historical
`TimeTwist-Zenpen-newlogo.ips` patch. The patch is not treated as a production
binary overlay: its rendered native pixels are the source of truth, and the
modern title builder repacks those pixels through the recovered NOV4 runtime.

Definitive provenance:

- untouched Japanese Zenpen SHA-256:
  `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916`;
- definitive logo IPS SHA-256:
  `915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2`.

The production authorities are:

- `Time Twist approved native title.png` — exact 256x240 indexed colored logo
  extracted from the patched NOV4 final title; rows 0-96 are owned;
- `Time Twist approved native slide.png` — the same logo silhouette rendered
  monochrome in the native 96-pixel swipe viewport; rows 0-95 are owned.

The final palette indices are black, white, pink, and purple. The slide uses
black and white only. The final authority contains 7,998 nonzero pixels; the
completed slide contains 7,982 because native swipe rendering does not include
row 96.

Canonical hashes:

| Asset | File SHA-256 | Pixel SHA-256 |
| --- | --- | --- |
| Final | `220E1755BEBFCEFCA408D5E18A323FC6AE9EDEB03C3B01CA22B30163A2E0016F` | `EA50A1888635F7A8FE863C61EB6D728CE260D281FABF3259E2FED700BC75CBA8` |
| Slide | `5218681DB3BC8F7631DC69BFB0B6A3C242B55B8018D3319CF9EC94C14DF10CA8` | `7FA164F34514B568560F5FC4BE7186719A692EB1013E7B00A26DE9FAE61080AB` |

`work/rebuild_native_title_asset.py` takes maintainer-supplied copies of the
original Zenpen FDS and definitive IPS, validates both hashes, applies the IPS,
extracts NOV4, decodes the patched final title, and reproduces these two PNGs.
It performs no image resampling, smoothing, hand tracing, or subjective pixel
cleanup.

The subtitle `On the Outskirts of History...`, `PUSH START`, machine art, and
copyright are intentionally not baked into these files. They remain code/ROM
owned. The live blue clock hands are also absent from the background; NOV4
continues to animate the original sprite CHR and metasprite tables, using the
exact clock-origin adjustment from the definitive IPS.

`Time Twist approved English opening.gif` and the older high-resolution title
references remain historical comparison/provenance artifacts only. They are no
longer production pixel authorities and are not used to regenerate a release.
