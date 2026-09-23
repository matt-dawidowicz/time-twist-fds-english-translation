# Part 1 to Part 2 startup handoff

This note documents the retail Zenpen-to-Kouhen progression boundary that sits
outside the ordinary gameplay-script scene-transition chain.

It closes the apparent gap between:

- final Zenpen gameplay scene row 6, which has no `E0` edge to row 7; and
- first Kouhen gameplay scene row 7, `TT4`.

## Result

The retail flow is:

```text
Zenpen scene 6 / TT3B ending
    |
    | 0F 05 -> resident system sequence 5
    v
resident FDS/SAVE completion path
    |
    | persisted Zenpen SAVE remains on disk
    v
power-cycle / title startup on TT1 Side A
    |
    | validate SAVE
    | expose title menu: Start / Load / Part 2
    v
choose Part 2
    |
    | NOV4 $C059: E0 C7
    v
request TT2 / Kouhen Side B
    |
    | scene-load row 7 = 47 57 FF FF
    v
TT4 + BG4/OBJ4
```

Kouhen Side A is not the normal continuation entry. Cold-booting it loads
`SON-KOUH`, the standalone direct-boot warning program.

## 1. Zenpen does not automatically swap into Kouhen

The final Zenpen composition is scene row 6:

```text
45 46 55 FF
TT3A + TT3B + BG3/OB3
```

The final TT3B script tail is:

```text
$A60C  B2
$A60D  10 39
$A60F  A1 78
$A611  10 3A
$A613  0F 05
```

`0F 05` is the verified `invoke_system_sequence 5` VM command. NOV2 state
`$22` dispatches sequence 5 through `$7E89`, which redirects the VM to the
resident bytecode sequence at `$7EB4`.

That resident sequence begins:

```text
$7EB4  64 EA
$7EB6  E4
$7EB7  0C D2 00 A5 05
$7EBC  E1
$7EBD  0F 06
$7EBF  64 EA
$7EC1  E4
$7EC2  E1
$7EC3  54 C7 7E
$7EC6  53
```

These resident `E4/E1` forms are native internal FDS/SAVE machinery rather
than source-used story opcodes. Their exact low-level execution path is guarded,
but this document does not assign unnecessary story-facing names to them.

The important architectural result is that Zenpen ends through the resident
completion/SAVE flow rather than through `E0 C7` or any other direct
gameplay-script jump into Kouhen.

## 2. Current scene/progression index is persisted in SAVE

Each gameplay composition writes its row number to zero-page `$CE`.

Examples:

```text
TT3B / scene 6:
    ... CE 00 06

TT4 / scene 7:
    ... CE 00 07
```

NOV2 `$9CBA` builds the 80-byte SAVE image. Among other fields it copies:

```text
zero page $C5-$D4 -> SAVE $03D0-$03DF
```

Therefore:

```text
$CE -> $03D9
```

NOV2 `$9D16` performs the inverse copy on restore.

The same SAVE block also contains:

- checksum at `$03CD/$03CE`;
- checksum marker `$03CF=$A5`;
- persisted title marker `$03DD`;
- secondary marker `$03DE`.

The pristine retail `SAVE` file is 80 zero bytes loaded at `$0390`.

## 3. SAVE validation creates the title-side validity state

At startup NOV2 `$6995` calls the checksum validator `$9D76`.

If validation fails:

```text
LDA #$E3
STA $8D
JSR $9BCE
```

which sets persistent flag `$E3`.

If validation succeeds, NOV2 instead loads:

```text
$03DD -> $D2
$03DE -> $D3
```

Thus the title has two independent facts available:

1. `E3` says the SAVE is invalid/unavailable;
2. `D2` carries the persisted `$03DD` marker from a valid SAVE.

## 4. Successful persisted-save path writes the title marker

NOV2 `$7B25-$7B43` is the successful persisted-save callback.

After validating or reconstructing the SAVE image, it writes:

```text
$03DD = $55
```

and, when the current scene index is `$0B`, additionally writes:

```text
$03DE = $AA
```

It then copies the relevant coordinate/state region and recomputes the SAVE
checksum.

The `$03DD` byte is therefore the persisted nonzero marker consumed by the
title's Part 2 gate. The name **Part 2 marker** in the tooling describes this
verified consumer relationship; it does not claim that every native use of the
byte has been exhaustively named.

## 5. NOV4's title menu explicitly contains Part 2

NOV4 header pointers include:

| Header field | Address |
| --- | ---: |
| indexed predicate table | `$A251` |
| primary menu table | `$A25C` |
| secondary menu/filter table | `$A27C` |
| menu text | `$A285` |
| label table | `$A30B` |
| initial title bytecode | `$A30F` |

The primary menu table at `$A25C` is count-prefixed. Menu 3 is:

```text
03 04 05 06
```

The three one-based text records are:

```text
4  Start
5  Load
6  Part 2
```

The title bytecode opens that menu with:

```text
$BFF4  29 03 01
```

The following `30` selection dispatcher has three absolute targets:

```text
Start  -> $BFFE
Load   -> $C051
Part 2 -> $C059
```

## 6. Part 2 eligibility is a real native predicate

Secondary filter 1 at `$A27C` is:

```text
09 00 91 E3 92 01 E3 E4 00
```

Decoded through the recovered NOV2 predicate/menu-filter machinery, the entries
for the three title choices are:

| Choice | Condition |
| --- | --- |
| Start | unconditional |
| Load | NOT `E3` |
| Part 2 | NOT `E3` AND `E4` |

Immediately before menu 3, NOV4 executes the native conditional:

```text
$BFEB  0C D2 00 00 07
```

This compares `$D2` with zero. When `$D2` is nonzero, execution falls
through:

```text
$BFF0  61 E4
$BFF2  61 EA
```

When `$D2` is zero, the relative branch skips those two flag writes and lands
at `$BFF2`/the subsequent menu path as defined by the native relative-PC
semantics.

For the Part 2 choice, the material condition is therefore:

```text
SAVE checksum valid
AND
$03DD != 0
```

Equivalently:

```text
NOT E3
AND
E4
```

The tooling represents this rule as
`part2_is_available(save_valid=..., persisted_marker=...)`.

## 7. Selecting Part 2 explicitly executes `E0 C7`

The third target from the Start / Load / Part 2 dispatcher is:

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

So the title does not infer the first Kouhen scene from chapter order. It
explicitly requests:

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

TT4 begins by writing:

```text
$CE = $07
```

which re-establishes the normal gameplay scene/progression index after the title
handoff.

## 8. The title also owns explicit chapter-entry transitions

NOV4 contains a separate chapter-selection path.

Part 1 chapter entries:

```text
E0 41
E0 42
E0 43
E0 44
E0 05
E0 06
```

correspond to scene rows 1-6.

Part 2 chapter entries:

```text
E0 C7
E0 C8
E0 C9
E0 CA
E0 8B
E0 8C
E0 8D
E0 8E
```

correspond to rows 7-14.

Row 8 is an empty load-table row in the retail image, but it remains represented
in this native title chapter table. This is engine/title capability and should
not be confused with a real gameplay overlay.

## 9. Disk and side validation

For `E0 C7`, the ordinary transition engine:

1. selects the Side-B FDS descriptor because bit 6 is set;
2. patches the expected game code from `TT1` to `TT2` because bit 7 is set;
3. masks the operand with `#$3F` to obtain scene row 7;
4. copies row 7's file IDs to the BIOS load list;
5. invokes the FDS BIOS loading wrapper.

The native loader explicitly recognizes the disk-header game codes `TT1` and
`TT2`. The established wrong-disk/wrong-side UI is therefore part of this
same transition path rather than a title-specific substitute.

## 10. Why Kouhen Side A is different

Kouhen Side A contains `SON-KOUH`, loaded at `$DD1D`, rather than the
Zenpen resident title/VM stack.

`SON-KOUH` is a 739-byte standalone direct-boot guard. Its reset entry begins:

```text
$DD1D  A9 FF 85 DF AA 9A ...
```

The maintained negative playtest expects its warning:

```text
PLEASE START WITH
PART 1
```

That is why normal continuation must begin from completed Zenpen state and then
request **Kouhen Side B** through `E0 C7`. Booting Kouhen Side A directly
takes the guard path instead.

## Machine-readable contract

`work/time_twist/part2_startup.py` owns:

- SAVE address mapping for persisted zero page;
- `$CE -> $03D9`;
- the persisted `$03DD=$55` title marker;
- title menu-3 record IDs;
- `E0 C7`;
- row-7 file IDs;
- the verified Part 2 availability truth rule.

`work/tools/audit_part2_startup_handoff.py` verifies against the original
Japanese disks:

- the ending `0F 05` path and resident sequence-5 entry;
- SAVE build/restore/checksum byte sequences;
- startup SAVE validation;
- the persisted-marker callback;
- NOV4 header/menu/filter bytes;
- the explicit `$C059: E0 C7` transition;
- physical location of row-7 files on Kouhen Side B;
- TT4's scene-index initialization;
- the Kouhen Side-A `SON-KOUH` negative path.

## Remaining runtime certification

The low-level transition contract is statically closed. Runtime certification
is still useful for the full user-visible sequence:

```text
TO BE CONTINUED...
power-cycle
Part 2 becomes selectable
Part 2 / Side B prompt
wrong-side/wrong-disk recovery
TT4 first scene
```

That replay would validate emulator/FDS write persistence and visible timing. It
is no longer required to discover the title-to-row-7 control-flow edge.
