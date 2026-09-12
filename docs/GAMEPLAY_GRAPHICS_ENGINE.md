# Gameplay graphics engine

This note records the recovered file-level graphics model for ordinary Time Twist gameplay. It replaces the older assumption that `OB*`, `OBJ*`, and `BG*` were opaque or potentially unrelated formats.

The important result is narrower and more useful: **all recovered `OB*`/`OBJ*`/`BG*` files are raw NES 2bpp CHR payloads stored as FDS kind-1 character files and loaded directly into CHR-RAM.** There is no additional game-specific compression layer inside these files.

What remains scene-specific is the meaning of individual tile IDs, metasprite data, nametable/metatile layout, palette assignment, and the lifetime of partially overlaid CHR ranges.

For a repeatable source audit, run:

```powershell
python work/tools/audit_recovered_engine_surfaces.py `
  "Time Twist Zenpen (Japan).fds" `
  "Time Twist Kouhen (Japan).fds"
```

Use `--json` for a machine-readable inventory.

## 1. File-level format is recovered

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

With 8x8 sprites, that selects sprite patterns from `$0000` and background patterns from `$1000`. The disk-file destinations therefore agree exactly with the filename families: `OB`/`OBJ` are object/sprite CHR and `BG` is background CHR.

The `OB` versus `OBJ` spelling is **not** a binary-format distinction. Both are the same direct CHR file type.

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

Each graphics ID labels **two files**: one object file and one background file. Loading one graphics ID therefore installs the paired sprite/background CHR surfaces belonging to that scene phase.

## 3. NOV2 scene file-ID table

The graphics files are selected by NOV2 rather than discovered by filename at runtime.

At CPU `$7A3D-$7A54`, NOV2 copies four bytes from a table beginning at `$7BA5` into `$60DF-$60E2`. The loader wrapper at `$6000` then calls the FDS BIOS file loader with `$60DF` as its file-ID list.

The recovered 15 table entries are:

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

`$FF` terminates/empties unused list slots. The table is indexed from native scene state and is copied verbatim into the BIOS file list.

This table is the missing bridge between scenario overlays and graphics residency. A future graphics bug should start by identifying the active scene-table index, not by searching the disk for a similarly named file.

## 4. Partial CHR overlays are intentional

Several graphics files are not complete pattern-table replacements. Their nonzero load addresses or short lengths are evidence that the game deliberately composes phases from multiple loads.

### TT1A over TT1B

Scene entry 1 loads `$51` and then `$52`.

- `OB1B` supplies object tiles `$00-$87`.
- `OB1A` overwrites only tiles `$00-$0A`.
- `BG1B` supplies background tiles `$10-$BE`.
- `BG1A` overwrites only `$10-$58`.

The remainder of the `1B` CHR therefore stays resident under the `1A` overlay.

### T25 / secondary TT5 graphics

Scene entry 10 loads `$59` and then `$5A`.

- `OBJ5` establishes the base object table.
- `OBJ52` begins at PPU `$0260` (tile `$26`) and overwrites only `$26-$77`.
- `BG5` establishes the base background range.
- `BG52` begins at `$1250` (tile `$25`) and overwrites only `$25-$D0`.

Treating `OBJ52` or `BG52` as a standalone complete table would therefore produce missing graphics outside those ranges.

### TT6A/TT6B over TT6C graphics

Entries 11 and 12 load the `$5D` 6C pair before the smaller 6A/6B sets. The later files replace only the ranges they own and inherit the untouched tail from the 6C base.

### TT6D retains earlier background CHR outside `$1840-$1B9F`

`BG6D` contains only 54 tiles and begins at `$1840`. It cannot represent a complete background pattern table by itself. Its correct runtime appearance therefore depends on already-resident background patterns outside that range.

This is the strongest reason not to “normalize” the graphics files by rebasing them to `$0000`/`$1000` or padding them into standalone tables. Their load addresses are part of the scene-composition ABI.

## 5. What these files do *not* contain

The file-level graphics format is now recovered, but several higher layers remain separate reverse-engineering targets.

The raw CHR files do **not** by themselves tell us:

- which nametable cells use each background tile;
- whether a scene uses metatiles and where those metatile definitions live;
- metasprite/OAM composition for object tiles;
- palette IDs and per-scene palette tables;
- collision or hotspot metadata associated with graphical objects;
- all state transitions that intentionally depend on previously resident partial CHR.

Those structures must live in NOV2, NOV3, or the active `$A200` scenario overlay because there are no corresponding gameplay FDS nametable files in these families.

So the old unknown has been split into two much more precise statements:

1. **VERIFIED:** `OB*`/`OBJ*`/`BG*` file representation, PPU destinations, file-ID selection, and partial-overwrite behavior.
2. **STILL TO RECOVER:** the scene-specific map/metasprite/palette metadata that consumes those tile IDs.

## 6. Safe editing rules

A direct tile-art correction is substantially easier now, but it still needs source guards.

For a size-neutral edit inside one existing graphics file:

1. identify the active scene-load entry and the exact file ID;
2. render the original 16-byte tile(s) with `work/render_chr.py`;
3. verify the target tile is not intentionally inherited/overwritten by a later graphics ID;
4. patch exact source bytes or a guarded region;
5. keep the FDS kind, load address, size, and file ID unchanged;
6. verify object/background rendering in the real scene and in adjacent phases sharing the same base CHR.

For an expansion or relocation, additionally prove:

- the new PPU destination does not overwrite live pattern IDs;
- all partial overlay dependencies remain valid;
- the FDS side still fits;
- scene-load order still establishes every tile that later phases assume is resident.

Unlike the title allocator, ordinary gameplay graphics do not currently have a generic relocation layer. Prefer size-neutral tile replacement until the consuming nametable/metasprite structures are recovered.

## 7. Evidence boundary

The direct-CHR interpretation is not based only on filenames. It is supported by all of the following independent facts:

- every family member is FDS kind 1;
- every payload is tile-aligned and fits wholly in NES pattern-table address space;
- decoding the bytes directly as 2bpp produces coherent object or background artwork;
- NOV2 gameplay `PPUCTRL=$10` selects the corresponding object/background tables;
- same-ID object/background pairs appear together in NOV2's scene file-ID table;
- short/nonzero-origin files line up exactly with layered scene load sets.

That is sufficient to promote the file-level model from **UNKNOWN** to **VERIFIED**. The scene-map/metasprite/palette layers remain separate work.