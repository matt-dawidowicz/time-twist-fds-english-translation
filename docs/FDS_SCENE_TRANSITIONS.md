# FDS scene-transition map

This note closes the remaining low-level ambiguity around retail gameplay opcode
`E0`.

## Status

The packed transition operand is **VERIFIED** from the original Japanese Zenpen
and Kouhen disks plus the native NOV2 handler at `$79A7/$79E5`.

The retail command is:

```text
E0 packed_target
```

with:

```text
bit 7      target disk: 0 = Zenpen / Part 1, 1 = Kouhen / Part 2
bit 6      target FDS side: 0 = Side A, 1 = Side B
bits 5-0   NOV2 scene-load-table index
```

Thus:

```text
scene_index = packed_target & $3F
disk        = packed_target & $80
side        = packed_target & $40
```

## Native proof

The `E0` path stores the command locally and then interprets byte 1 in three
independent stages:

- `$79FC-$7A00`: `LDA (C5),Y / AND #$40` selects one of the two FDS-side
  paths;
- `$7A1C-$7A1F`: the sign test on the same operand selects the disk/part path;
- `$7A36-$7A54`: `AND #$3F`, two `ASL` operations, and indexed loads from
  `$7BA5` copy exactly four file IDs into `$60DF-$60E2`.

The bit-7 path also selects the byte `$32` rather than `$31`, consistent with
the Part 2 versus Part 1 disk prompt. More importantly, every retail transition
target's file IDs physically reside on the disk and side encoded by bits 7 and
6, independently confirming the interpretation.

## NOV2 scene-load table

`$7BA5` contains 15 four-byte rows. `$00` and `$FF` are empty/sentinel
entries.

| Row | Physical source | File IDs | Loaded files / composition |
| ---: | --- | --- | --- |
| 0 | empty | `00 00 00 00` | no gameplay overlay |
| 1 | Zenpen Side B | `41 42 51 52` | `TT1B + TT1A + BG1B/OB1B + BG1A/OB1A` |
| 2 | Zenpen Side B | `41 51 FF FF` | `TT1B + BG1B/OB1B` |
| 3 | Zenpen Side B | `43 53 FF FF` | `TT2 + BG2/OBJ2` |
| 4 | Zenpen Side B | `43 44 53 FF` | `TT2 + T22 + BG2/OBJ2` |
| 5 | Zenpen Side A | `45 55 FF FF` | `TT3A + BG3/OB3` |
| 6 | Zenpen Side A | `45 46 55 FF` | `TT3A + TT3B + BG3/OB3` |
| 7 | Kouhen Side B | `47 57 FF FF` | `TT4 + BG4/OBJ4` |
| 8 | empty | `FF FF FF FF` | no gameplay overlay |
| 9 | Kouhen Side B | `49 59 FF FF` | `TT5 + BG5/OBJ5` |
| 10 | Kouhen Side B | `49 4A 59 5A` | `TT5 + T25 + BG5/OBJ5 + BG52/OBJ52` |
| 11 | Kouhen Side A | `4C 4B 5D 5B` | `TT6B + TT6A + BG6C/OB6C + BG6A/OB6A` |
| 12 | Kouhen Side A | `4C 5D 5C FF` | `TT6B + BG6C/OB6C + BG6B/OB6B` |
| 13 | Kouhen Side A | `4D 5D FF FF` | `TT6C + BG6C/OB6C` |
| 14 | Kouhen Side A | `4E 5E FF FF` | `TT6D + BG6D/OBJ6D` |

Rows 0 and 8 are the only non-gameplay rows. The 13 real composed gameplay
scenes are rows 1-7 and 9-14.

## Retail `E0` call sites

There are 11 instruction-aligned retail calls. Every one is immediately
preceded by `B2 start_irq_raster_transition_mode_2`.

| Source row | Active source overlay | Address | Operand | Decoded target |
| ---: | --- | ---: | ---: | --- |
| 1 | `TT1A` | `$A44F` | `$42` | Zenpen Side B, row 2 |
| 2 | `TT1B` | `$AB79` | `$43` | Zenpen Side B, row 3 |
| 3 | `TT2` | `$AD03` | `$44` | Zenpen Side B, row 4 |
| 4 | `T22` | `$A6BD` | `$05` | Zenpen Side A, row 5 |
| 5 | `TT3A` | `$A96F` | `$06` | Zenpen Side A, row 6 |
| 7 | `TT4` | `$ADAA` | `$C9` | Kouhen Side B, row 9 |
| 9 | `TT5` | `$A759` | `$CA` | Kouhen Side B, row 10 |
| 10 | `T25` | `$A347` | `$8B` | Kouhen Side A, row 11 |
| 11 | `TT6A` | `$A737` | `$8C` | Kouhen Side A, row 12 |
| 12 | `TT6B` | `$A5A5` | `$8D` | Kouhen Side A, row 13 |
| 13 | `TT6C` | `$AAA6` | `$8E` | Kouhen Side A, row 14 |

Examples:

- `$42 = %01000010`: Zenpen, Side B, row 2.
- `$C9 = %11001001`: Kouhen, Side B, row 9.
- `$8E = %10001110`: Kouhen, Side A, row 14.

## Part 1 to Part 2 boundary

There is deliberately **no gameplay-script `E0` edge from row 6 to row 7**.

Row 6 is the final Zenpen gameplay composition. Row 7 is the initial Kouhen
gameplay composition. The transition between parts is handled by the title/disk
startup flow rather than by carrying the Zenpen gameplay VM directly into TT4.

This matches the retail play flow: Part 1 ends, and Part 2 startup performs its
own disk/side selection before entering the first Kouhen gameplay scene.

## False raw `E0` bytes

A raw byte scan finds additional `E0` values in script regions, but they are
not opcodes. They occur inside structures such as:

- `09` counted-block payload bytes;
- `60/61/64` flag-ID operands;
- `70` component masks;
- `D2` CHR-clone records;
- `30/31` branch target tables;
- `4x` predicate/branch data.

For example, TT4 `$A242 E0 01` is payload inside the preceding `09` counted
block, not a transition command. The audit therefore guards the 11 proven
instruction-aligned call sites rather than treating raw byte matches as code.

## Machine-readable contract

`work/time_twist/scene_transitions.py` owns the packed-byte decoder.

`work/tools/audit_retail_vm_semantics.py` now verifies against the original
retail disks:

- the native bit-decoding path at `$79E5-$7A54`;
- all 15 exact scene-load rows;
- all 11 retail `B2 E0 xx` call sites;
- the active source overlay at each call site;
- the physical disk/side location of every target file ID;
- the explicit row-6 to row-7 Part boundary with no direct `E0` edge.

The opcode registry now classifies `E0 fds_scene_transition` as **VERIFIED**.
