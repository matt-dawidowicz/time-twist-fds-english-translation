# Gameplay VM completion pass (2026-09-12)

This note records the second-pass source-reachability and semantic audit of Time Twist's gameplay VM. It supplements `GAMEPLAY_SCRIPT_ENGINE.md` and **supersedes that note's provisional labels where this document is more specific**.

Evidence labels follow the repository convention: **VERIFIED** is direct native-code/source-byte behavior; **DERIVED** follows mechanically; **INFERRED** remains a higher-level label.

## Corrected reachability baseline

The audit composes the 13 real `$A200` gameplay scenes exactly as NOV2 loads them and explores both fresh-start execution and every valid `$A220` route/label entry.

- total gameplay script region: **24,229 bytes**;
- fresh start: **6,917 command starts**, **22,705 covered bytes**;
- all valid route entries seeded: **7,283 command starts**, **23,902 covered bytes**;
- route-seeded coverage: **98.6504%**;
- all valid labels are reached in the route-seeded model;
- decode errors: **0**;
- overlapping decoded command ranges: **0**;
- reachable indexed `$A20E` predicate forms: **0**.

The remaining **327 bytes** are best described as **non-reached source islands**, not an unknown bytecode format. Several islands contain byte patterns that decode plausibly as ordinary VM commands, but the recovered abstract machine has no proven incoming state for them. They are therefore deliberately excluded from executable coverage rather than connected speculatively.

Fresh-start execution leaves a small number of route labels cold that are valid under route-resume entry:

- T22 scene: labels 4, 8, 11, 12, 13;
- TT5 scene: label 6.

This is evidence for additional runtime route/resume entry, not evidence that those labels are dead.

## Corrected `$1x` text control flow

Retail uses `10`, `11`, `18`, and `19`.

- following byte: text/scenario record selector;
- bit 0 selects the alternate interaction/wait path;
- `10/11` return to the next sequential script command;
- bit 3 (`18/19`) is **route-terminating**, not fallthrough: native completion executes the equivalent of opcode `52`, jumping through the current route entry in `$A220`.

The earlier reachability model treated `18/19` as fallthrough and overstated coverage by two bytes. The corrected totals above replace the older 7,284-command / 23,904-byte figure.

## `$2x` menu modifiers

Retail uses only `20`, `21`, `28`, and `29`. Two opcode bits are independent modifiers:

- bit 0 (`21/29`) adds a third-byte selector into the `$A212` secondary menu/prompt table;
- bit 3 (`28/29`) snapshots current script PC and software-stack context into `$9B/$9C/$9F/$A0` before entering the menu state machine, enabling later continuation/resume;
- the byte after the opcode selects the primary `$A210` menu record;
- that record's choice count determines the size of the subsequent `$30/$31` selection-result target table.

Thus `20/21` are direct menu forms and `28/29` are resumable menu forms; `21/29` additionally select the secondary prompt/table entry.

## `$A20E` is source-unused engine capability

The indexed predicate base `$A20E/$A20F` is `$0000` in every composed gameplay scene. More strongly, the four predicate forms that would dereference it (`42`, `46`, `4A`, `4E`) have **zero reachable occurrences** in both fresh-start and all-route source graphs.

The ordinary retail gameplay scripts therefore do not use an `$A20E` predicate table. The native engine supports the feature, but the recovered source programs do not exercise it.

## `$8x/$9x` are audio command-latch writes

The previous generic "engine parameter write" label is obsolete.

NOV2 handler `$717E` (`8x`) and `$7192` (`9x`) write a four-byte command-latch block at `$07E0-$07E3`:

- `8x`: write `$07E0 + low_nibble` and mirror the written value to zero-page `$D1`;
- `9x`: write `$07E0 + low_nibble` without the `$D1` mirror.

Retail uses only `83` and `90-93`.

NOV3 is the resident audio driver: it writes the NES APU register range `$4000-$4017` and FDS audio registers `$4040-$4089`, and consumes these latches. Static source references establish the broad roles:

- `$07E0`: resident APU/noise-SFX command latch;
- `$07E1`: scene-overlay audio/SFX command latch;
- `$07E2`: resident pulse-channel SFX command latch;
- `$07E3`: resident music/FDS-audio command latch.

`83` therefore writes the music/FDS-audio latch and also mirrors its value into `$D1`. NOV2 preserves/restores `$D1` across scene-loading paths, consistent with audio-state continuity.

Observed retail command values are:

- `83`: `80`, `01`, `02`, `08`, `04`;
- `90`: `02`, `80`;
- `91`: `01`, `80`, `02`, `04`, `10`, `08`, `20`, `40`, `03`;
- `92`: `01`, `04`, `02`, `08`, `80`;
- `93`: `10`, `40`, `20`, `80`, `04`, `01`, `02`.

These values should not yet be called specific song or SFX IDs without an audio-table correlation pass.

## `$Bx` exploration primitives

The exploration family is no longer a single opaque movement state machine. The strongest source-backed forms are:

- `B5`: fixed-point move-to-target setup. Four payload bytes populate `$07AD-$07B0`; native code selects coordinate pair `$57/$58` or `$18/$19`, converts to 1/16 fixed point in `$07B1/$07B2`, and the per-frame mover at `$777F` approaches the target by scripted step `$07AE`, stopping exactly on the target.
- `B7`: configure active hotspot/exploration boundary selection. Operand 1 becomes `$07AC`; operand 2 becomes `$07AA`, with `$07AB = operand2 + 1`.
- `B9`: save script/stack continuation context into `$9B/$9C/$9F/$A0`.
- `BA`: restore/move actor coordinate slots using IDs stored in the `$07B3` record area.
- `BB`: clear one saved-coordinate slot ID from the `$07B3` table.
- `BC`: shares the `$72C6` exploration reset/continuation path; its higher-level name remains deliberately conservative.

`B0/B2/B3/B6` have recovered setup routines but are not assigned narrative names until their state correlations are complete.

## Source-used `$0x` ALU forms

The retail scripts use the following forms from the shared `$0x/$Fx` VM memory/ALU handler:

- `00`: store immediate byte;
- `01`: add immediate and store;
- `02`: subtract immediate and store;
- `04`: compare/subtract for condition flags without storing the result;
- `06`: copy byte;
- `09`: counted block write;
- `0E`: counted `(address, value)` multi-store;
- `0F 05`: invoke built-in/system sequence 5, entering engine state `$22`.

No source-reachable `$Fx` command occurs in the recovered gameplay programs.

## `D2` dynamically clones and flips background CHR tiles

`D2` is the only source-reachable class-D opcode. Its payload is a count followed by three-byte records:

```text
D2 count
repeat count times:
    source_tile
    destination_tile
    transform_flags
```

The native path is **VERIFIED** from NOV2 `$78F6`, `$7972`, `$95F2`, and `$9671`:

1. the byte after `D2` becomes the record count at `$078C`;
2. each record is staged as source tile `$0789`, destination tile `$078A`, and flags `$078B`;
3. `$95F2` reads the source background-pattern tile from PPU pattern table 1 into a 16-byte scratch tile at `$06F0-$06FF`;
4. `$9671` clones that tile into `$0700-$070F` and applies the requested transformations;
5. `$95F2` writes the resulting 16-byte tile to the destination tile in pattern table 1.

The transformation bits have exact geometric meanings:

- `$40` reverses the bits in every CHR row byte, producing a **horizontal flip**;
- `$80` reverses the eight row bytes independently in both bitplanes, producing a **vertical flip**;
- `$C0` applies both transformations;
- with neither bit set, the record is an unflipped runtime tile clone.

This command therefore avoids storing redundant mirrored background tiles in CHR data and permits scripts to synthesize transformed copies directly in background pattern memory.

## Retail VM is narrower than the interpreter

The native interpreter implements sixteen high-nibble classes, but shipped source usage is much narrower. In particular:

- class 7 uses only `70`;
- class 8 uses only `83`;
- class A uses only `A1`;
- class D uses only `D2`;
- class E uses only `E0`;
- no source-reachable class C or class F command is present.

This distinction matters: engine capability and retail source language are not identical.

## Remaining reverse-engineering frontier

The gameplay VM is structurally recovered. The remaining work is refinement rather than discovery:

1. correlate individual `$07E0-$07E3` values with exact music/SFX identities;
2. finish stable low-level names for the remaining source-used `Bx` forms;
3. identify the real runtime conditions that enter the 327 bytes of non-reached source islands, if any;
4. assign human-facing world directions to the already-verified opposing `$FD/$FE` hotspot sentinels;
5. finish the few high-bit palette-animation control semantics.

Do not inflate source coverage by decoding arbitrary orphaned bytes without a proven incoming VM state. The current **98.6504%** figure is intentionally conservative.
