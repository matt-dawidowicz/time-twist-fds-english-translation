# Part 1 to Part 2 startup handoff

This note documents the retail Zenpen-to-Kouhen progression boundary that sits
outside the ordinary gameplay-script scene-transition chain.

It closes the apparent gap between:

- final Zenpen gameplay scene row 6, which has no ordinary gameplay-script
  `E0` edge to row 7; and
- first Kouhen gameplay scene row 7, `TT4`.

## Final result

The normal retail architecture is:

```text
Zenpen scene 6 / TT3B ending
    |
    | 0F 05
    v
resident system sequence 5
    |
    | FDS/SAVE manager
    | LoadFiles + SAVEDATA WriteFile paths
    v
Zenpen Side-A SAVE state persists on disk
    |
    | power-cycle / title startup on TT1 Side A
    v
validate 80-byte SAVE at $0390
    |
    +-- invalid/uninitialized -> set persistent flag $E3
    |                        -> Part 2 filtered out
    |
    +-- valid --------------> $E3 remains clear
                              -> Part 2 survives filtering
    |
    v
NOV4 route 1
    |
    | menu descriptor 3 = Part 1 / Part 2
    v
choose Part 2
    |
    | $C059: E0 C7
    v
Kouhen / Side B / scene row 7
    |
    | row 7 = 47 57 FF FF
    v
TT4 + BG4/OBJ4
```

Kouhen Side A is not the normal continuation entry. Cold-booting it loads
`SON-KOUH`, the standalone direct-boot warning program.

## 1. Zenpen ending enters a resident SAVE/disk manager

The final Zenpen composition is scene row 6:

```text
45 46 55 FF
TT3A + TT3B + BG3/OB3
```

The exact final TT3B tail is:

```text
$A60B  B2
$A60C  10 39
$A60E  A1 78
$A610  10 3A
$A612  0F 05
```

`0F 05` is the verified `invoke_system_sequence 5` command. NOV2 state
`$22` dispatches sequence ID 5 through `$7E89` to resident VM bytecode at
`$7EB4`.

The resident sequence begins:

```text
$7EB4  64 EA
$7EB6  E4
$7EB7  0C D2 00 A5 05
$7EBC  E1
$7EBD  0F 06
$7EBF  64 EA
$7EC1  E4
$7EC2  E1
...
```

These `E1-E6` forms are engine-resident system forms, not source-used story
`E0` opcodes.

## 2. Engine-resident E-forms around SAVE

The native state-`$1E` dispatcher resolves the relevant forms as follows.

### `E4`: load title/SAVE files

`E4`:

1. copies the current 80-byte SAVE image from `$0390` to backup
   `$0720` and zeros `$0390`;
2. enters state `$1E` minor 3;
3. minor 3 jumps to NOV2 `$6065`;
4. `$606D` calls FDS BIOS `LoadFiles` at `$E1F8`.

Its load list at `$60E4` is:

```text
02 03 FF
```

On Zenpen Side A these are:

- file ID `$02`: `NOV4`;
- file ID `$03`: `SAVE`;
- `$FF`: terminator.

After a successful load, NOV2 validates the loaded SAVE and merges the
appropriate backed-up continuation block before returning to the resident VM.

### `E1`: write SAVEDATA

`E1` enters state `$1E` minor 5. Minor 5 jumps to NOV2 `$6097`.

At `$609F`:

```text
LDA #$09
JSR $E239
    .word $60CB
    .word $60E7
```

FDS BIOS `$E239` is `WriteFile`. File number 9 is the Zenpen Side-A
`SAVE` entry.

The file header at `$60E7` is:

```text
03                         file ID
53 41 56 45 44 41 54 41   "SAVEDATA"
90 03                      load address $0390
50 00                      size $0050 = 80 bytes
00                         program/data area
90 03                      source address $0390
00                         source area
```

Thus the native `E1` operation overwrites the disk's 80-byte SAVE file from
RAM `$0390`.

The `0C D2 00 A5 05` command between the first `E4` and `E1` performs
a comparison/condition projection. Its equal branch and ordinary fallthrough
both converge on the same following `E1`; it does not bypass the write.

System sequence 5 should therefore be described as the resident
**SAVE/disk-management transaction**, not as a direct scene transition and not
as a one-instruction "autosave" primitive.

## 3. Exact SAVE layout

The retail SAVE file is 80 bytes loaded at `$0390-$03DF`. The pristine file
is all zero bytes.

NOV2 `$9CBA` serializes:

```text
persistent flags $0480-$049F -> $0390-$03AF
exploration slots $07B3-$07BE -> $03B0-$03BB
runtime $C5-$D4              -> $03D0-$03DF
```

Therefore the current scene/progression byte `$CE` persists at:

```text
$CE -> $03D9
```

NOV2 `$9D16` performs the inverse restore.

Other verified SAVE fields include:

- checksum at `$03CD/$03CE`;
- checksum marker `$03CF=$A5`;
- title/system metadata `$03DD`;
- secondary title/system metadata `$03DE`.

The successful SAVE-processing callback at `$7B25-$7B43` writes
`$03DD=$55` and, when `$CE=$0B`, additionally writes `$03DE=$AA`.
Those bytes are title/system metadata. They are **not** the Part 2 visibility
bit.

## 4. Scene/progression index and title reload table

Every gameplay composition installs its own scene index in `$CE`.

Examples:

```text
TT3B / row 6 -> $CE = $06
TT4  / row 7 -> $CE = $07
```

NOV2's title/reload path at `$7B73-$7B95` converts a restored `$CE` value
back into a packed FDS transition operand through a resident lookup table:

| `$CE` | Packed target |
| ---: | ---: |
| 0 | `$00` |
| 1 | `$41` |
| 2 | `$42` |
| 3 | `$43` |
| 4 | `$44` |
| 5 | `$05` |
| 6 | `$06` |
| 7 | `$C7` |
| 8 | `$C8` |
| 9 | `$C9` |
| 10 | `$CA` |
| 11 | `$8B` |
| 12 | `$8C` |
| 13 | `$8D` |
| 14 | `$8E` |

So `$CE=7` maps directly to `$C7` = Kouhen / Side B / row 7.

The Zenpen ending does **not** increment `$CE` from 6 to 7. TT4 sets
`$CE=7` only after row 7 has actually loaded.

## 5. Title START pipeline

Pressing START in NOV4 exits the title animation through:

```text
LDA #$02
LDX #$03
JMP $6119
```

`$6119` installs the engine's major/minor state pair.

The recovered startup chain is:

```text
NOV4 title START
 -> major state 2 / minor 3
 -> NOV4 $A40E
 -> major state 8 / minor 0
 -> major state 5 setup sequence
 -> state 8 / minor 1
 -> validate SAVE
 -> resident VM $69C3: 51 01
 -> switch to NOV4 route 1 at $BFE2
```

State 8 / minor 1 validates SAVE with `JSR $9D76`.

On failure:

```text
LDA #$E3
STA $8D
JSR $9BCE
```

which sets persistent flag `$E3`.

On success it does **not** set `$E3`; it loads `$03DD/$03DE` into
`$D2/$D3` for other title/continuation state and then launches route 1.

## 6. The two title menus are distinct

NOV4's primary menu descriptor table at `$A25C` contains six menus.

Relevant entries are:

### Descriptor 2

```text
03 04 05 06
```

which names:

```text
Start
Load
Part 2
```

### Descriptor 3

```text
02 0B 0C
```

which names:

```text
Part 1
Part 2
```

The actual post-title handoff route at `$BFE2` opens **descriptor 3**, not
descriptor 2:

```text
$BFF4  29 03 01
```

The following two-target absolute dispatcher is:

```text
$BFF7  30 FE BF 51 C0

Part 1 -> $BFFE
Part 2 -> $C051
```

This distinction matters: the earlier draft conflated the
`Start / Load / Part 2` descriptor with the later `Part 1 / Part 2`
disk-part selector.

## 7. Exact Part 2 visibility predicate

Secondary record 1 at `$A27C` is:

```text
09 00 91 E3 92 01 E3 E4 00
```

For descriptor 3's two choices this splits into:

```text
Part 1 predicate:
00

Part 2 predicate:
91 E3 92 01 E3 E4 00
```

The actual retail predicate evaluator at `$99EA` was executed against this
exact Part 2 expression under all four `E3/E4` combinations:

| `E3` | `E4` | Part 2 result |
| ---: | ---: | --- |
| clear | clear | true |
| clear | set | true |
| set | clear | false |
| set | set | false |

Therefore the final visibility rule is:

```text
Part 2 visible iff persistent flag $E3 is clear
```

Although `E4` appears in the encoded expression and NOV4 updates it from
`$D2` immediately before the menu, it does not alter this expression's final
Boolean result. `$03DD/$D2/E4` must therefore remain documented as auxiliary
title/continuation state, not as the Part 2 unlock bit.

## 8. What E3 means

`$E3` is the title's **fresh/no-valid-SAVE suppressor**.

At startup:

- invalid/uninitialized SAVE -> NOV2 sets `E3`;
- valid SAVE -> this error flag is not set.

The Part 1 branch at `$BFFE` tests the same flag:

- `E3` set -> fresh-start path -> `E0 $41` -> Zenpen row 1;
- `E3` clear -> continuation/book/chapter path.

Fresh `E0 $41` eventually enters state 4 / minor 0. NOV2 `$9C0B` clears the
entire 32-byte persistent flag bank, including `E3`, before scene 1 is
initialized.

Thus `E3` is not a "Part 1 complete" flag.

## 9. Consequence: no special completion Boolean gates Part 2

The title path contains no separate test equivalent to:

```text
if scene == 6
or
if part1_complete
```

for the Part 2 menu choice.

The static native rule is instead:

```text
fresh / invalid SAVE -> E3 set -> Part 2 hidden
valid continuation state -> E3 clear -> Part 2 retained
```

This means the engine's Part 2 menu gate is **continuation-validity based**, not
completion-bit based.

The intended retail play flow still finishes Zenpen before entering Kouhen, and
the ending enters the resident SAVE/disk manager. But the menu predicate itself
does not encode a special "TO BE CONTINUED reached" Boolean.

A clean runtime test can usefully determine how early a deliberately created
valid Part 1 SAVE exposes the Part 2 selector, but that is now a certification
question rather than an unknown predicate format.

## 10. Selecting Part 2 explicitly executes E0 C7

The Part 2 branch begins at `$C051` and reaches:

```text
$C059  E0 C7
```

Using the verified packed `E0` operand:

```text
$C7 = %11000111
       ||------
       ||   row 7
       |+-- Side B
       +--- Kouhen / Part 2
```

So the title explicitly requests:

```text
Kouhen
Side B
scene row 7
```

NOV2 row 7 is:

```text
47 57 FF FF
```

Those file IDs physically reside on Kouhen Side B and compose:

- `TT4`;
- `BG4/OBJ4`.

TT4 then initializes:

```text
$CE = $07
```

which re-establishes normal gameplay progression state after the title handoff.

## 11. Kouhen Side A is the direct-boot negative path

Kouhen Side A contains `SON-KOUH`, loaded at `$DD1D`, rather than the
Zenpen resident title/VM stack.

`SON-KOUH` is a 739-byte standalone guard whose expected English warning is:

```text
PLEASE START WITH
PART 1
```

Normal Part 2 continuation therefore starts from the Zenpen title/engine,
selects Part 2, and requests **Kouhen Side B** through `E0 C7`.

## Machine-readable contract

`work/time_twist/part2_startup.py` owns:

- SAVE address mapping for persisted zero page;
- `$CE -> $03D9`;
- neutral title metadata at `$03DD/$03DE`;
- separate descriptor-2 and descriptor-3 menu identities;
- the exact Part 2 predicate bytes;
- the `E3` visibility rule;
- BIOS SAVEDATA file-number/header constants;
- `E0 C7`;
- row-7 file IDs.

`work/tools/audit_part2_startup_handoff.py` verifies against original Japanese
disks:

- final TT3B `0F 05`;
- resident sequence-5 entry;
- `LoadFiles` and `WriteFile` call sites;
- the exact `SAVEDATA` write header;
- SAVE build/restore/checksum routines;
- startup invalid-SAVE -> `E3`;
- NOV4 menu/filter bytes;
- the explicit `$C059: E0 C7`;
- physical row-7 files on Kouhen Side B;
- TT4's `$CE=7` initialization;
- Kouhen Side-A `SON-KOUH`.

## Remaining runtime certification

The low-level startup handoff is statically closed. Runtime certification is
still useful for:

```text
TO BE CONTINUED...
SAVE/disk-manager user-visible behavior
power-cycle
Part 2 selector visibility
Part 2 / Side B prompt
wrong-side/wrong-disk recovery
TT4 first scene
```

The particularly useful adversarial test is now:

> Create a valid Part 1 SAVE before the Zenpen ending, power-cycle, and check
> whether Part 2 is already visible.

Static analysis predicts that it should be, because the native menu gate checks
`E3` rather than a completion-specific flag.
