# Gameplay graphics and scene engine

This note records the recovered graphics/runtime model for ordinary Time Twist gameplay. It supersedes the earlier assumption that `OB*`, `OBJ*`, and `BG*` were opaque graphics formats and separates the file-level CHR representation from the `$A200` scene data that consumes those tiles.

The current model is now substantially recovered:

- `OB*`/`OBJ*`/`BG*` files are raw NES 2bpp CHR loaded directly into CHR-RAM;
- NOV2's scene table selects the program overlays and matching graphics IDs;
- same-address `$A200` overlays intentionally inherit high tables from an earlier program file;
- `$A204` selects packed metasprite definitions rendered into standard OAM;
- `$A200` selects static metasprite placements;
- `$A202` selects actor spawn/layout records;
- `$A208` selects palette-definition records;
- `$A20C` selects hotspot rectangles;
- `$A21E` selects direct background nametable-patch descriptors and RLE streams.

The main remaining unknowns are now semantic rather than structural: the exact distinction between hotspot markers `$FD` and `$FE`, complete higher-level naming for several script/state tables, and the full meaning of palette tag bits beyond their verified destination-selection role.

For a repeatable source audit, run:

```powershell
python work/tools/audit_recovered_engine_surfaces.py `
  "Time Twist Zenpen (Japan).fds" `
  "Time Twist Kouhen (Japan).fds"
```

Use `--json` for a machine-readable inventory.

## 1. Gameplay CHR files are raw NES pattern data

Every graphics-family file in both Japanese halves satisfies the same structural rules:

- FDS file kind is `1` (character data);
- payload size is a multiple of 16 bytes;
- load address is 16-byte/tile aligned;
- bytes decode directly as standard NES 2bpp tiles;
- `OB*` and `OBJ*` load only into PPU pattern table 0 (`$0000-$0FFF`);
- `BG*` loads only into PPU pattern table 1 (`$1000-$1FFF`).

NOV2 initializes gameplay `PPUCTRL` to `$10` at CPU `$619C`:

```text
A9 10       LDA #$10
8D 00 20    STA $2000
85 FF       STA $FF
```

With 8x8 sprites, this selects sprite patterns from `$0000` and background patterns from `$1000`. The disk-file destinations therefore agree exactly with the filename families: `OB`/`OBJ` are object/sprite CHR and `BG` is background CHR.

The `OB` versus `OBJ` spelling is not a binary-format distinction. Both are the same direct CHR file type.

## 2. Complete graphics inventory

| File | FDS ID | Role | PPU destination | Tiles |
| --- | ---: | --- | --- | ---: |
| `OB1B` | `$51` | object | `$0000-$087F` | 136 |
| `BG1B` | `$51` | background | `$1100-$1BEF` | 175 |
| `OB1A` | `$52` | object overlay | `$0000-$00AF` | 11 |
| `BG1A` | `$52` | background overlay | `$1100-$158F` | 73 |
| `OBJ2` | `$53` | object | `$0000-$0A3F` | 164 |
| `BG2` | `$53` | background | `$1200-$1BBF` | 156 |
| `OB3` | `$55` | object | `$0000-$0A3F` | 164 |
| `BG3` | `$55` | background | `$1100-$1F9F` | 234 |
| `OBJ4` | `$57` | object | `$0000-$0A3F` | 164 |
| `BG4` | `$57` | background | `$1100-$1FFF` | 240 |
| `OBJ5` | `$59` | object | `$0000-$08AF` | 139 |
| `BG5` | `$59` | background | `$1200-$1E9F` | 202 |
| `OBJ52` | `$5A` | object overlay | `$0260-$077F` | 82 |
| `BG52` | `$5A` | background overlay | `$1250-$1D0F` | 172 |
| `OB6A` | `$5B` | object overlay | `$0000-$054F` | 85 |
| `BG6A` | `$5B` | background overlay | `$1100-$19AF` | 139 |
| `OB6B` | `$5C` | object overlay | `$0000-$06AF` | 107 |
| `BG6B` | `$5C` | background overlay | `$1100-$1EFF` | 224 |
| `OB6C` | `$5D` | object/base | `$0000-$09EF` | 159 |
| `BG6C` | `$5D` | background/base | `$1100-$1BDF` | 174 |
| `OBJ6D` | `$5E` | object | `$0000-$0A2F` | 163 |
| `BG6D` | `$5E` | background overlay | `$1840-$1B9F` | 54 |

Each graphics ID labels two files: one object file and one background file. Loading one graphics ID therefore installs the paired sprite/background CHR surfaces belonging to that scene phase.

## 3. NOV2 scene file-ID table

The graphics files are selected by NOV2 rather than discovered by filename at runtime.

At CPU `$7A3D-$7A54`, NOV2 copies four bytes from a table beginning at `$7BA5` into `$60DF-$60E2`. The loader wrapper at `$6000` then calls the FDS BIOS file loader with `$60DF` as its file-ID list.

The recovered 15 entries are:

| Index | File IDs and resolved components |
| ---: | --- |
| 0 | `00 00 00 00` |
| 1 | `$41` `TT1B`, `$42` `TT1A`, `$51` `OB1B/BG1B`, `$52` `OB1A/BG1A` |
| 2 | `$41` `TT1B`, `$51` `OB1B/BG1B` |
| 3 | `$43` `TT2`, `$53` `OBJ2/BG2` |
| 4 | `$43` `TT2`, `$44` `T22`, `$53` `OBJ2/BG2` |
| 5 | `$45` `TT3A`, `$55` `OB3/BG3` |
| 6 | `$45` `TT3A`, `$46` `TT3B`, `$55` `OB3/BG3` |
| 7 | `$47` `TT4`, `$57` `OBJ4/BG4` |
| 8 | no files (`FF FF FF FF`) |
| 9 | `$49` `TT5`, `$59` `OBJ5/BG5` |
| 10 | `$49` `TT5`, `$4A` `T25`, `$59` `OBJ5/BG5`, `$5A` `OBJ52/BG52` |
| 11 | `$4C` `TT6B`, `$4B` `TT6A`, `$5D` `OB6C/BG6C`, `$5B` `OB6A/BG6A` |
| 12 | `$4C` `TT6B`, `$5D` `OB6C/BG6C`, `$5C` `OB6B/BG6B` |
| 13 | `$4D` `TT6C`, `$5D` `OB6C/BG6C` |
| 14 | `$4E` `TT6D`, `$5E` `OBJ6D/BG6D` |

This table is the bridge between scenario overlays and graphics residency. A graphics bug should start by identifying the active scene-table index.

## 4. Same-address `$A200` overlays deliberately inherit data

Several scene entries load two kind-0 program files to the same CPU address `$A200`. The later, smaller file overwrites only its own length. The untouched high RAM still contains tables from the earlier larger file.

This is verified behavior, not accidental stale memory:

- `TT1A` overlays `TT1B` and inherits TT1B's high metasprite/map/actor tables;
- `T22` overlays `TT2` and inherits TT2's high tables;
- `TT3B` overlays `TT3A` and inherits TT3A's high tables.

This explains pointers in the small overlays that legally point beyond the small FDS file's own payload length. An isolated-file parser will misclassify those pointers as invalid; runtime analysis must compose the scene load list first.

The same principle applies to graphics: small CHR files such as `OB1A`, `BG1A`, `OBJ52`, `BG52`, `OB6A`, `BG6A`, `OB6B`, `BG6B`, and `BG6D` overwrite only the PPU ranges they own and inherit the rest of the already-loaded pattern table.

Do not normalize these files to standalone full tables. Their partial load addresses are part of the scene ABI.

## 5. `$A200` scene-header map

The active `$A200` overlay begins with a dense pointer header. The following meanings are now structurally recovered:

| Header address | Recovered purpose |
| --- | --- |
| `$A200` | static metasprite-placement table start; also metasprite-definition table end |
| `$A202` | actor spawn/layout table start |
| `$A204` | metasprite-definition table start |
| `$A208` | palette-definition table start |
| `$A20C` | hotspot-rectangle table start |
| `$A210/$A212` | fixed-menu secondary table bases |
| `$A214` | fixed-menu record-zero base; also hotspot-table end |
| `$A216` | scenario dictionary |
| `$A21A` | fixed-menu page-pointer table |
| `$A21C` | room/sequence/presentation-state table; higher-level semantics still incomplete |
| `$A21E` | gameplay background nametable-patch descriptor table |
| `$A220` | script/event pointer table; higher-level semantics still incomplete |
| `$A222` | active script/event stream start |
| `$A224` | scenario group-pointer table |
| `$A226` | scenario group-zero pointer |
| `$A22C` | actor-spawn table end; following animation/motion table start |
| `$A22E/$A230` | additional animation/motion lookup tables; exact higher-level naming incomplete |

`$A20E` is also consumed by the script/predicate/action machinery, but its full semantic name is intentionally left unresolved.

## 6. OAM and metasprite engine

NOV2 uses the standard NES OAM page at CPU `$0200`. At `$6154` it sets `$2003=0`, writes page `2` to `$4014`, and performs the normal OAM DMA.

The actor array begins at CPU `$04A0`, with 16 bytes per runtime actor. Actor byte `+8` is a 1-based metasprite definition index; zero means no metasprite.

### Packed metasprite definitions at `$A204`

The table starts at the pointer in `$A204/$A205` and ends at the pointer in `$A200/$A201`.

Each definition is:

```text
byte 0: complete record length in bytes
byte 1: width << 4 | height
then width * height row-major cells:
    $FF                 transparent cell; one byte
    tile, attributes    visible cell; two bytes
```

The attribute byte is written directly as the NES OAM attribute byte, so its palette/priority/flip bits have their normal hardware meaning.

NOV2 walks the selected definition, expands row/column offsets, stages `Y/tile/attributes/X`, and appends sprites to `$0200`. A camera-aware path subtracts the current scroll before OAM output and hides offscreen sprites with Y=`$F0`.

Exact parsed table sizes include:

| Scene owner | Range | Bytes | Definitions |
| --- | --- | ---: | ---: |
| `TT1B` | `$C803-$CA59` | 599 | 40 |
| `TT2` | `$C7AE-$CB6D` | 960 | 72 |
| `TT3A` | `$C79C-$CAF8` | 861 | 62 |
| `TT4` | `$CC89-$CF3B` | 691 | 45 |
| `TT5` | `$C467-$C907` | 1185 | 58 |
| `T25` | `$BBA2-$BDC0` | 543 | 37 |
| `TT6A` | `$B78D-$B8D6` | 330 | 21 |
| `TT6B` | `$BA01-$BC6F` | 623 | 32 |
| `TT6C` | `$C3D8-$C677` | 672 | 47 |
| `TT6D` | `$A65D-$A997` | 827 | 28 |

Every table parses exactly to its declared `$A200` end pointer.

## 7. Static metasprite placements at `$A200`

The bytes from the `$A200` pointer through the `$A202` pointer form a separate static placement table. It is selected by NOV2 state `$85`.

Each record is:

```text
byte 0: placement count
repeat count times:
    metasprite definition index
    X position in 8-pixel cells
    Y position in 8-pixel cells
```

NOV2 expands the referenced metasprite definition and multiplies the X/Y placement cells by 8. Expanded static sprite cells are staged in a separate runtime structure beginning around `$058A` before normal OAM emission.

Examples:

- TT1B: 24 placement records, 35 placements;
- TT2: 49 records, 66 placements;
- TT3A: 26 records, 36 placements;
- T25: 53 records, 106 placements;
- TT6C: 20 records, 66 placements.

TT1A/T22/TT3B inherit the corresponding base table exactly as they inherit their metasprite definitions.

## 8. Actor spawn/layout table at `$A202`

NOV2 `$8C88` reads the table whose start is in `$A202/$A203`. The table ends at the pointer in `$A22C/$A22D`.

Each selected record is:

```text
byte 0: actor descriptor count
repeat count times:
    actor/type ID
    X low byte
    X high byte
    Y byte
```

The runtime actor record is 16 bytes at `$04A0 + 16*n`. The spawn code converts the input coordinates to the engine's fixed-point representation. `$FF` values are handled as sentinels by the native code; do not reinterpret them as ordinary coordinates.

Known runtime fields include:

- `+0`: active/state (`0` terminates/free; `$0F` is a special inactive state);
- `+1`: actor/type ID;
- `+2/+3`: horizontal fixed-point position;
- `+4/+5`: vertical fixed-point position;
- `+6/+7` and `+9/+10`: animation/timer state;
- `+8`: metasprite definition index;
- `+0B/+0C`: signed motion deltas;
- `+0F`: additional actor state.

Examples of exact source tables:

- TT1B: 21 records / 40 actor descriptors;
- TT2: 28 / 50;
- TT3A: 20 / 35;
- TT4: 21 / 22;
- TT5: 21 / 26;
- T25: 25 / 30;
- TT6C: 43 / 102.

## 9. Gameplay background maps at `$A21E`

This is the largest former graphics unknown that is now structurally recovered.

`$A21E/$A21F` points to a table of variable-length **direct nametable tile-patch descriptors**. This is not the title RLE path and does not require an inferred metatile layer.

NOV2's selector begins at `$9E29`, the stream decoder at `$9F84`, and the PPU uploader at `$A049`.

### Descriptor header

Each descriptor begins with a compact two-byte length/type word:

```text
record_size = byte0 + ((byte1 & $3F) << 8)
variant_count = byte1 >> 6
```

The low 14 bits therefore give the complete descriptor byte length. The top two bits give the number of map variants; current data uses one or two variants.

The inline first variant begins after `2 * variant_count` header bytes. Additional variants use absolute little-endian stream pointers stored in the prefix. A duplicated pointer is legal; TT6D contains one such record.

### Map stream

Each selected stream begins:

```text
byte 0: left column to preserve/skip
byte 1: right column, inclusive
byte 2: starting nametable row
then RLE tile IDs
$FF: source-stream terminator
```

RLE is:

- `< $C0`: one literal tile ID;
- `$C0-$FE`: low six bits are repeat count; next byte is the tile ID;
- `$FF`: terminate the source stream.

The decoded tile count is always divisible by `right-left+1`, proving that each stream describes a rectangular tile patch. Recovered shapes include small patches, 16x10/18x12/32x12 regions, and complete 32x16 tile surfaces. One TT5 stream is an intentional empty `0,0,0,$FF` no-op.

The decoder uses `$07A5` as the leading preserved-column count, `$07A6` as the right-edge boundary, and `$07A7` as the starting row. It stages output near `$A094`. In that staging buffer `$FF` means preserve the existing PPU cell; this runtime sentinel is distinct from the source-stream `$FF` terminator.

Destination tables in NOV2 resolve to the real nametable bases `$2000/$2400/$2800/$2A00` and their attribute regions. This, together with the decoded rectangles and loaded CHR tile ranges, proves these are direct nametable tile patches.

### Exact scene-table extents

| Scene owner | Descriptor range | Records | Streams | Maximum tile |
| --- | --- | ---: | ---: | ---: |
| `TT1B` | `$BDA0-$C802` | 23 | 25 | `$BE` |
| `TT2` | `$BF30-$C7AD` | 23 | 25 | `$BB` |
| `TT3A` | `$BDD8-$C79B` | 29 | 32 | `$F9` |
| `TT4` | `$C4E4-$CC88` | 14 | 15 | `$FE` |
| `TT5` | `$BE4B-$C466` | 18 | 19 | `$E9` |
| `T25` | `$B685-$BBA1` | 8 | 9 | `$D0` |
| `TT6A` | `$B3C6-$B78C` | 7 | 8 | `$AE` |
| `TT6B` | `$B247-$BA00` | 9 | 12 | `$EF` |
| `TT6C` | `$BAF4-$C3D7` | 15 | 17 | `$BD` |
| `TT6D` | `$A4DB-$A65C` | 3 | 4 | `$B9` |

The maximum tile IDs line up with the graphics sets loaded for those scenes. TT1A/T22/TT3B inherit TT1B/TT2/TT3A map tables through the same-address overlay model.

The generic `$6787` RLE routine used elsewhere must not be conflated with this engine. Gameplay map selection/decompression/upload is the `$9E29/$9F84/$A049` path.

## 10. Hotspot rectangles at `$A20C`

`$A20C/$A20D` points to a count-prefixed table selected by NOV2 state `$BA`. The table ends at the pointer in `$A214/$A215`.

Each record is:

```text
byte 0: rectangle count
repeat count times:
    left / flag byte
    top
    right
    bottom-or-special
```

NOV2 converts the player/world position into grid coordinates, checks X and Y against the rectangle bounds, and masks the high bit of the left byte as a contextual flag.

The fourth byte normally behaves as the inclusive bottom bound. Values `$FD` and `$FE` are explicitly recognized as special return markers instead of ordinary Y bounds. Their distinct higher-level meanings are still unknown and should remain labeled as such.

Recovered nonempty tables include TT1B (23 rectangles), TT2 (11), T22 (23), TT3A (9), TT4 (9), and TT6B (7).

## 11. Palette engine at `$A208`

`$A208/$A209` points to the scene palette-definition records. NOV2 `$89EB` selects records using `$86` and `$87` and writes an internal palette image before copying it to staging RAM `$0300-$031F`.

The palette record unit is a three-byte color triple:

- the low six bits of each byte are the NES color value (`& $3F`);
- the high two bits of the first byte select the destination 3-color subpalette slot;
- the high two bits of the third byte mark whether the current record continues or ends.

One selector path updates the half associated with staging flag `$30|=$80`; the other uses `$30|=$40`. NMI later uploads the staged palette bytes to the PPU.

The binary structure and destination-selection mechanism are verified. The project does not yet assign more specific semantic names to every high-bit tag value because doing so is unnecessary for safe structural editing and has not been separately proven.

## 12. What is still unknown

The old broad statement “gameplay graphics are unknown” is no longer accurate. The remaining unknowns are narrower:

- exact gameplay meaning of hotspot special markers `$FD` versus `$FE`;
- complete semantic naming of `$A20E`'s script/predicate/action table;
- complete semantic naming of `$A21C`'s room/sequence/presentation-state table;
- higher-level semantics of the `$A220` event pointers and `$A22E/$A230` animation/motion tables beyond their structural roles;
- more specific naming of palette high-bit selector tags;
- whether any separate metatile abstraction exists in another path. The recovered `$A21E` background engine itself expands direct tile IDs and does not need one.

These are now appropriate targets for later reverse engineering. None blocks ordinary size-neutral CHR corrections, metasprite edits, actor placement audits, direct map-tile fixes, or palette-table analysis.

## 13. Safe editing rules

For a size-neutral CHR correction:

1. identify the active scene-load entry and graphics ID;
2. identify later partial overlays that may overwrite the tile;
3. patch exact 16-byte source tile data under a source guard;
4. preserve FDS kind, file ID, load address, and payload size;
5. verify all adjacent phases sharing the same base CHR.

For a metasprite edit, preserve the table boundaries or regenerate every record length and index contract. For a static placement or actor-spawn edit, preserve record counts unless the selector/caller behavior is also intentionally changed.

For a background-map edit, decode the selected `$A21E` descriptor variant, preserve its rectangle geometry unless intentionally changing it, rebuild the RLE stream within the descriptor's byte budget, and verify that every referenced tile is resident under that scene's CHR composition.

Relocation is a separate problem. Do not move tables merely because a nearby region looks unused; same-address overlays and inherited high tails make apparently free memory especially deceptive.

## 14. Evidence boundary

The recovered model is supported by independent static and runtime-facing facts:

- FDS file types and PPU load addresses identify direct CHR payloads;
- gameplay `PPUCTRL=$10` agrees with object/background pattern-table ownership;
- NOV2's scene file-ID table links programs and graphics sets;
- same-address scene composition explains inherited high pointers exactly;
- metasprite, placement, actor, hotspot, and map tables parse to their declared pointer boundaries without residual bytes;
- metasprite definitions feed standard OAM and page-2 DMA;
- background map streams expand to exact rectangles and feed real nametable PPU addresses;
- recovered tile IDs stay within the scene's composed background CHR coverage.

That is sufficient to promote these structural layers from **UNKNOWN** to **VERIFIED**. The remaining semantic questions above should stay explicitly labeled rather than being guessed into the build system.