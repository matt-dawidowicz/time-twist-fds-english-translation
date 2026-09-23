# Part 1 to Part 2 handoff

This note documents the retail Zenpen-to-Kouhen continuation path that occurs
outside the ordinary gameplay `E0` scene-transition chain.

## Status

The low-level handoff is **VERIFIED** from the original Japanese Zenpen/Kouhen
disks, NOV2/NOV4 native code, the composed TT3A+TT3B ending overlay, and the
title-menu predicate tables.

The important architectural fact is that Zenpen does **not** execute a gameplay
`E0` transition directly into Kouhen. Instead, Part 1 exits into NOV2's resident
save/disk system. On a later title startup, NOV4 derives whether the Part 2 menu
choice should be visible from persistent SAVE metadata. Selecting Part 2 then
performs the first Kouhen `E0` transition.

## 1. Zenpen ending exits through system sequence 5

The final composed Zenpen gameplay scene is row 6, `TT3A + TT3B`. The active
TT3B ending tail is:

~~~text
$A60C  B2
$A60D  10 39
$A60F  A1 78
$A611  10 3A
$A613  0F 05
~~~

`0F 05` is the only instruction-aligned use of system sequence 5 in the 13
retail gameplay scenes.

NOV2's class-0 handler at `$7D9D` stores operand `$05` in `$A1`, enters
engine state `$22`, and state-`$22` handler `$7DED` dispatches the
`$A1=05` case through `$7E89`. That installs the resident system-script
pointer `$7EB4`.

Thus the ending leaves TT3B's story bytecode and enters NOV2's resident
save/disk workflow. It does not directly load Kouhen.

## 2. Persistent SAVE layout and validity

Zenpen's FDS file `SAVE` is an 80-byte block loaded at
`$0390-$03DF`.

NOV2 `$9CBA` serializes:

- persistent flags `$0480-$049F` -> `$0390-$03AF`;
- exploration/checkpoint state -> `$03B0...`;
- zero-page runtime state `$C5-$D4` -> `$03D0-$03DF`;
- checksum/validity metadata through `$9D76`.

The checksum-validity byte at `$03CF` is `$A5`; checksum words live at
`$03CD/$03CE`.

A successful FDS SAVE-write callback reaches NOV2 `$7B25`. That path validates
or restores the write buffer, then stamps:

~~~text
$03DD = $55
~~~

before recomputing the SAVE checksum.

The same callback has a separate conditional secondary marker:

~~~text
if $CE == $0B:
    $03DE = $AA
~~~

The `$AA` marker is **not** the Part 1-completion gate and should not be named
as such. It belongs to a later progression condition.

## 3. Startup restores the disk-write marker

During title/startup state, NOV2 `$6990-$69C2` validates the persistent SAVE.

If validation fails:

- native flag `$E3` is set;
- `$D2=$00`;
- `$D3=$00`.

If validation succeeds:

~~~text
$03DD -> $D2
$03DE -> $D3
~~~

NOV2 then enters resident route `51 01`, which selects route 1 of the currently
loaded title overlay. On Zenpen Side A, that overlay is NOV4 and route 1 is
`$BFE2`.

## 4. NOV4 derives the Part 2 menu flag

NOV4 route 1 contains this sequence:

~~~text
$BFEB  0C D2 00 00 07
$BFF0  61 E4
$BFF2  61 EA
$BFF4  29 03 01
$BFF7  30 FE BF 51 C0 59 C0
~~~

The engine-only `0C` form compares `$D2` with zero. Its fifth byte is a
relative conditional selector. When `$D2 == 0`, the native conditional path
jumps seven bytes from `$BFEB` to `$BFF2`, skipping `61 E4`.

When `$D2 != 0`, execution advances normally through:

~~~text
61 E4
~~~

which sets persistent flag `$E4`.

Therefore the exact title-side derivation is:

~~~text
E4 = (D2 != 0)
~~~

Because a valid disk-written SAVE restores `$03DD=$55` into `$D2`, the
normal retail continuation arrives with `E4=true`.

## 5. The title menu filters Start / Load / Part 2

NOV4 primary menu descriptor #3 is the three-choice list:

~~~text
Start
Load
Part 2
~~~

Route `$BFE2` opens that descriptor with `29 03 01`.

Its secondary predicate record at `$A27C` is:

~~~text
09 00 91 E3 92 01 E3 E4 00
~~~

Decoded choice predicates are:

| Choice | Predicate |
| --- | --- |
| Start | unconditional |
| Load | `NOT E3` |
| Part 2 | `NOT E3 AND E4` |

So the exact title behavior is:

~~~text
Load visible   = SAVE checksum is valid
Part 2 visible = SAVE checksum is valid AND D2 != 0
~~~

The code does **not** directly test a story flag named "Part 1 complete." It
tests persistent SAVE validity plus the disk-write marker restored through
`$D2`.

This distinction matters: the handoff should be documented in terms of the
actual storage contract rather than assigning narrative meaning to a byte the
native code does not give it.

## 6. Selecting Part 2 enters Kouhen Side B, row 7

The absolute target table following the three-choice menu is:

~~~text
Start  -> $BFFE
Load   -> $C051
Part 2 -> $C059
~~~

At `$C059`:

~~~text
E0 C7
~~~

The verified packed `E0` target `$C7` means:

- bit 7 = 1 -> Kouhen / Part 2;
- bit 6 = 1 -> Side B;
- low six bits = 7 -> scene-load row 7.

Row 7 loads:

~~~text
47 57 FF FF
~~~

which is `TT4 + BG4/OBJ4`, the first Kouhen gameplay composition.

Thus the normal continuation is:

~~~text
Zenpen ending
  -> NOV2 system sequence 5
  -> resident save/disk workflow
  -> persistent disk-written SAVE
  -> restart/title flow on Zenpen Side A
  -> validate SAVE
  -> $03DD -> $D2
  -> NOV4 derives E4 from D2 != 0
  -> Start / Load / Part 2 menu
  -> choose Part 2
  -> E0 C7
  -> Kouhen Side B
  -> scene row 7
  -> TT4
~~~

## 7. Kouhen Side A remains a negative/direct-boot path

Kouhen Side A contains the 739-byte `SON-KOUH` startup guard.

It is not the normal continuation entry and does not replace the live resident
Zenpen engine/title state. Directly booting Kouhen Side A displays the warning
that Part 1 must be started first.

The normal Part 2 continuation therefore specifically requests **Kouhen Side B**.

## 8. Runtime evidence note

Two historical Mesen states named
`Time-Twist-continuation-four-side-playtest-2026-08-12_1.mss` and
`_2.mss` were decoded directly using MesenCE's serialized-state format.

Both snapshots are early title/start states with:

- a zeroed `$0390-$03DF` SAVE block;
- flag `$E4` clear;
- `$D2=$00`.

They therefore provide a useful negative baseline but do not contain the
post-Zenpen completed SAVE state.

The static retail-byte path above is sufficient to recover the handoff
contract; clean replay remains appropriate for final behavioral certification.

## 9. Source guards

`work/tools/audit_retail_vm_semantics.py` now guards:

- TT3B's unique `0F 05` ending tail at `$A60C`;
- NOV2 SAVE validation and `$03DD/$03DE -> $D2/$D3` at `$6990`;
- the successful FDS-write marker stamping at `$7B25`;
- NOV4 route-1 `$D2` compare and `61 E4` derivation at `$BFEB`;
- the exact Start / Load / Part 2 descriptor and predicate record;
- the final `E0 C7` target at `$C059`.

`work/time_twist/part_handoff.py` owns the machine-readable title-gate contract.
