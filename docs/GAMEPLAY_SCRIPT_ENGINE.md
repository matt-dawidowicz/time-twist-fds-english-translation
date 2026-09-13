# Gameplay script and event VM

This document is the maintained model of the gameplay-script architecture in NOV2
and the `$A200` scenario overlays. It complements
[Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md): the graphics reference
covers scene assets and loaders, while this document covers the bytecode that selects,
mutates, and transitions that state.

The important structural result is that Time Twist has a small bytecode interpreter,
not a collection of unrelated event tables. The interpreter owns a script program
counter, a software call stack, a label table, a predicate evaluator, a persistent
256-bit event-flag bank, and high-nibble opcode families.

Evidence labels follow the repository convention:

- **VERIFIED** - proven from exact source bytes and native control flow;
- **DERIVED** - follows mechanically from verified behavior;
- **INFERRED** - a higher-level name that is useful but not yet safe as a binary rule;
- **UNKNOWN** - deliberately unresolved.

Historical audit snapshots and superseded labels belong under `docs/history/`; this
file should describe the current recovered model only.

## 1. Interpreter dispatch

NOV2 `$69E5` fetches the byte at the script PC in `$C5/$C6`, shifts out its high
nibble, and maps it to a NOV2 engine state. High nibble zero is remapped to state
`$20`; nibbles `$1-$F` become states `$11-$1F`. The normal next-command path at
`$69FF` restores state `$10`, whose handler is the fetch/decode routine itself.

The scheduler at `$68C5` uses major state `$26` and substate `$27` to dispatch through
the word table at `$690B`. The recovered handler map is:

| Script high nibble | NOV2 state | Handler | Current classification |
| ---: | ---: | ---: | --- |
| `$1x` | `$11` | `$6A04` | text/scenario-record dispatch; `18/19` terminate through current route |
| `$2x` | `$12` | `$6A82` | menu/selection dispatch; direct/resumable and optional secondary selector forms |
| `$3x` | `$13` | `$6BFD` | selection-result branch/dispatch |
| `$4x` | `$14` | `$6C5E` | predicate/conditional branch |
| `$5x` | `$15` | `$6DA9` | control flow: jump/call/return/label dispatch |
| `$6x` | `$16` | `$6F2C` | persistent event-flag mutation |
| `$7x` | `$17` | `$6F49` | scene/presentation component configuration |
| `$8x` | `$18` | `$717E` | audio command-latch write with `$D1` mirror |
| `$9x` | `$19` | `$7192` | audio command-latch write |
| `$Ax` | `$1A` | `$71A4` | delay/input gate |
| `$Bx` | `$1B` | `$71F5` | exploration/movement/hotspot state machine |
| `$Cx` | `$1C` | `$7870` | persistent presentation/input state; no source-reachable retail form |
| `$Dx` | `$1D` | `$78BA` | runtime background-CHR clone/transform; retail uses `D2` |
| `$Ex` | `$1E` | `$79A7` | FDS/scene/file transition state machine |
| `$Fx` | `$1F` | `$7C0E` | shared VM memory/ALU handler; no source-reachable retail form |
| `$0x` | `$20` | `$7C0E` | source-used VM memory/ALU operations |

Engine capability and retail source language are distinct. The interpreter implements
all sixteen high-nibble families, but shipped source usage is narrower. In particular,
retail uses only `70`, `83`, `A1`, `D2`, and `E0` from classes 7, 8, A, D, and E
respectively, and has no source-reachable class C or class F command.

## 2. Script program counter, entry point, and label table

The active script PC is `$C5/$C6`.

NOV2 `$695D` initializes it directly from scenario-header word `$A222/$A223`.
Across every recovered real scene composition, `$A222` points to `$A232`, and word
zero of the table selected by `$A220/$A221` is the same `$A232` entry point.

The resulting model is:

- `$A222` - initial script entry pointer;
- `$A220` - pointer to the script label/subroutine pointer table;
- `$A232..($A220-1)` - script bytecode region in current source overlays;
- `$A220[0]` - label zero, equal to `$A222` in all recovered scenes.

The label table can be bounded source-side by reading consecutive words from the
`$A220` target while they continue to point back into the script bytecode region.
Recovered source scenes contain between 2 and 15 label entries.

Same-address overlays change the script program while intentionally inheriting other
high tables. Examples include TT1A over TT1B, T22 over TT2, and TT3B over TT3A.
The script engine therefore must be analyzed against the **composed runtime image**,
not an isolated small overlay.

### Source-reachability baseline

The current source graph composes all 13 real `$A200` gameplay scenes and explores
both fresh-start execution and every valid `$A220` route/label entry.

- total gameplay script region: **24,229 bytes**;
- fresh start: **6,917 command starts**, **22,705 covered bytes**;
- all valid route entries seeded: **7,283 command starts**, **23,902 covered bytes**;
- route-seeded coverage: **98.6504%**;
- all valid labels reached in the route-seeded model;
- decode errors: **0**;
- overlapping decoded command ranges: **0**;
- reachable indexed `$A20E` predicate forms: **0**.

The remaining **327 bytes** are non-reached source islands, not evidence of a second
bytecode format. Do not inflate coverage by connecting them without a proven incoming
VM state.

Fresh-start execution leaves valid route/resume entries cold at T22 labels 4, 8, 11,
12, and 13, and TT5 label 6. Those labels become reachable when valid route entry is
modeled.

## 3. Software call stack

The `$5x` family proves that the VM has subroutines rather than only branches.
NOV2 `$6EE6` pushes the current script PC to the software stack addressed by
`$9D/$9E`; `$6F09` restores it. Script initialization sets the stack pointer into
page `$01`.

Verified `$5x` forms include:

| Form | Behavior |
| --- | --- |
| low nibble `$0` | absolute jump to 16-bit pointer in following bytes |
| low nibble `$3` | return from script subroutine |
| low nibble `$4` | absolute call; push return PC then jump |
| low nibble `$5-$7` | indexed call through the `$A220` label table |
| low nibble `$8-$F` | compact signed relative branch/jump using byte 1 |
| low nibble `$2` | jump through `$A220` using the current route/selection index |
| low nibble `$1` | state-dependent route dispatch through `$A220`; exact narrative-level name incomplete |

This is sufficient to describe `$A220` as a **script label/subroutine table**, rather
than a generic event-pointer table.

## 4. `$1x` text control flow

Retail uses `10`, `11`, `18`, and `19`.

- the following byte selects the text/scenario record;
- bit 0 selects the alternate interaction/wait path;
- `10/11` return to the next sequential script command;
- bit 3 (`18/19`) is **route-terminating**, not fallthrough: native completion takes
  the equivalent of opcode `52`, jumping through the current route entry in `$A220`.

Treating `18/19` as fallthrough was an earlier reachability error. The 98.6504%
baseline above uses the corrected terminating behavior.

## 5. `$2x` menu modifiers and `$3x` selection results

Retail uses only `20`, `21`, `28`, and `29`. Two bits are independent modifiers:

- bit 0 (`21/29`) adds a third-byte selector into the `$A212` secondary menu/prompt
  table;
- bit 3 (`28/29`) snapshots current script PC and software-stack context into
  `$9B/$9C/$9F/$A0` before entering the menu state machine, enabling later resume;
- the byte after the opcode selects the primary `$A210` menu record;
- that primary record's choice count determines the following `$30/$31`
  selection-result target-table size.

Thus `20/21` are direct menu forms and `28/29` are resumable forms; `21/29`
additionally select the secondary prompt/table entry.

## 6. Predicate engine and `$4x` conditional branches

The predicate evaluator lives around `$96D6-$9BAF`. Its source pointer is `$94/$95`.
It tests the persistent event-flag bank and combines terms with negation and logical
composition. Static tracing proves support for NOT-like inversion plus AND/OR chaining;
the final result/route mask is returned through `$A9` and consumed by the `$4x`
branch handler.

The engine supports several predicate sources:

1. an inline predicate expression immediately following the opcode;
2. a compact one-flag predicate synthesized by NOV2 from the command byte;
3. an indexed predicate expression from the table base stored at `$A20E`;
4. a spatial predicate comparing two actor positions against a command-supplied
   distance threshold.

The branch result can select either signed relative targets or absolute 16-bit targets,
depending on command flags.

### `$A20E` is an unused retail capability

`$A20E/$A20F` is structurally an optional predicate-expression table base. The native
engine can dereference it, but the composed header value is `$0000` in every recovered
gameplay scene, and the four command forms that would use it (`42`, `46`, `4A`,
`4E`) have **zero reachable occurrences** in both fresh-start and all-route source
graphs.

Therefore ordinary retail gameplay does not use an `$A20E` predicate table. Do not
invent one merely because the interpreter supports the feature.

## 7. Persistent story/event flags

The `$6x` command family operates on a 256-bit flag bank at CPU `$0480-$049F`.
NOV2 provides common helpers for testing, setting, and clearing one flag:

- `$9BB0` - test flag;
- `$9BCE` - set flag;
- `$9BE0` - clear flag;
- `$9BF4` - map the 8-bit flag ID to byte index and bit mask.

Two packed `$6x` layouts are verified.

### Extended count form

When the opcode low nibble is zero, byte 1 contains two counts:

```text
low nibble  = number of following flag IDs to set
high nibble = number of following flag IDs to clear
```

The set-ID sequence comes first, followed by the clear-ID sequence. Command length is
`2 + set_count + clear_count`.

### Compact count form

When the low nibble is nonzero, the opcode itself carries small set/clear counts:

```text
bits 0-1 = set_count
bits 2-3 = clear_count
```

Following bytes are again the flag IDs. Command length is
`1 + set_count + clear_count`.

These flags are also consumed by the predicate engine, so they form the VM's persistent
story/event state rather than merely local renderer flags.

## 8. `$7x` scene/presentation configuration

The `$7x` family controls the scene components whose binary formats are documented in
the graphics-engine reference. Its setup logic clears or populates selectors including
`$83-$89`; the activation path at `$70CE` then invokes the corresponding native
loaders.

Verified links include:

- selector `$85` -> static metasprite placement loader `$8AFC`;
- selectors `$86/$87` -> palette loader `$89EB`;
- selector `$88` -> actor spawn loader `$8C88`;
- selector `$89` -> palette-animation initializer `$90E8`.

Retail source uses only opcode `70` from this family. The broad role is verified; do
not assign narrative names to unused low-nibble forms without evidence.

## 9. `$8x/$9x` audio command-latch writes

NOV2 handler `$717E` (`8x`) and `$7192` (`9x`) write the four-byte command-latch
block at `$07E0-$07E3`:

- `8x`: write `$07E0 + low_nibble` and mirror the written value to zero-page `$D1`;
- `9x`: write `$07E0 + low_nibble` without the `$D1` mirror.

Retail uses only `83` and `90-93`.

NOV3 is the resident audio driver. It writes NES APU registers `$4000-$4017` and FDS
audio registers `$4040-$4089` and consumes these latches. Static source references
establish the broad roles:

- `$07E0`: resident APU/noise-SFX command latch;
- `$07E1`: scene-overlay audio/SFX command latch;
- `$07E2`: resident pulse-channel SFX command latch;
- `$07E3`: resident music/FDS-audio command latch.

`83` therefore writes the music/FDS-audio latch and also mirrors its value into `$D1`.
NOV2 preserves/restores `$D1` across scene-loading paths, consistent with audio-state
continuity.

Observed retail values are:

- `83`: `80`, `01`, `02`, `08`, `04`;
- `90`: `02`, `80`;
- `91`: `01`, `80`, `02`, `04`, `10`, `08`, `20`, `40`, `03`;
- `92`: `01`, `04`, `02`, `08`, `80`;
- `93`: `10`, `40`, `20`, `80`, `04`, `01`, `02`.

These values are not yet assigned specific song/SFX names without an audio-table
correlation.

## 10. Palette-animation table at `$A21C`

`$A21C/$A21D` is the palette-animation table base.

NOV2 `$90E8` loads this pointer and expands the record selected by `$89` into runtime
state. `$91AD` advances the resulting sequences every frame and calls `$89EB`, the
verified `$A208` palette loader, with background and sprite palette record selectors.

The source format is:

```text
record:
    sequence_count
    repeat sequence_count times:
        frame_count
        repeat_or_control
        repeat frame_count times:
            duration_or_control
            background_palette_record
            sprite_palette_record
```

Normal frame durations use the low seven bits. The sequence wraps to frame zero after
its final frame. `$7F` in the sequence repeat/control byte means indefinite cycling.
`$7E` and high-bit duration forms retain input/state-sensitive behavior that is not yet
fully named.

## 11. Actor selector and animation/motion tables

The three header words beginning at `$A22C` are structurally separated:

- `$A22C` - two packed animation/motion selectors per actor type;
- `$A22E` - pointer table for metasprite-animation streams;
- `$A230` - pointer table for motion/velocity streams.

NOV2 `$8E08` reads the first `$A22C` selector. Its high nibble selects an `$A22E`
stream bank and its low nibble selects a sequence within that bank. Normal animation
steps provide a duration and metasprite index, stored into actor fields `+7` and `+8`.

NOV2 `$8E7F` does the same for the second selector and `$A230`. Normal motion steps
provide a duration plus X/Y deltas, stored into actor fields `+10`, `+0B`, and `+0C`.
The per-frame mover at `$8F28` applies those deltas to actor coordinates.

Both channels recognize control values:

- `$7F` - loop/restart the current sequence;
- `$FF` - terminate/deactivate the actor;
- other `$80+N` values - transition/reinitialize the actor as type/state `N`.

## 12. `$Bx` exploration primitives and hotspot sentinels

The source-used exploration family is no longer treated as one opaque movement state
machine. The strongest verified forms are:

- `B5` - fixed-point move-to-target setup. Four payload bytes populate
  `$07AD-$07B0`; native code selects coordinate pair `$57/$58` or `$18/$19`, converts
  to 1/16 fixed point in `$07B1/$07B2`, and the per-frame mover at `$777F` approaches
  the target by scripted step `$07AE`, stopping exactly on the target;
- `B7` - configure active hotspot/exploration boundary selection. Operand 1 becomes
  `$07AC`; operand 2 becomes `$07AA`, with `$07AB = operand2 + 1`;
- `B9` - save script/stack continuation context into `$9B/$9C/$9F/$A0`;
- `BA` - restore/move actor coordinate slots using IDs stored in the `$07B3` record
  area;
- `BB` - clear one saved-coordinate slot ID from the `$07B3` table;
- `BC` - shares the `$72C6` exploration reset/continuation path; its higher-level
  narrative name remains deliberately conservative.

`B0/B2/B3/B6` have recovered setup routines but are not assigned narrative names until
their state correlations are complete.

Hotspot rectangles are selected through `$A20C`. NOV2 `$768F` recognizes `$FD` and
`$FE` as successful terminal hotspot results instead of Y bounds. The exploration
state at `$750B` treats them oppositely:

- direction/state `$1D=1` rejects `$FE` but permits `$FD`;
- direction/state `$1D=2` rejects `$FD` but permits `$FE`;
- permitted paths use opposite boundary selectors at `$07AA/$07AB`.

The verified binary meaning is **opposite directional/one-way boundary sentinels**.
Human-facing world-direction names remain unassigned pending controller/world-axis
correlation.

## 13. `D2` runtime background-CHR clone and flip

`D2` is the only source-reachable class-D opcode. Its payload is:

```text
D2 count
repeat count times:
    source_tile
    destination_tile
    transform_flags
```

The native path is verified from NOV2 `$78F6`, `$7972`, `$95F2`, and `$9671`:

1. the byte after `D2` becomes record count `$078C`;
2. each record stages source tile `$0789`, destination tile `$078A`, and flags
   `$078B`;
3. `$95F2` reads the source background-pattern tile from PPU pattern table 1 into
   scratch tile `$06F0-$06FF`;
4. `$9671` clones it into `$0700-$070F` and applies requested transformations;
5. `$95F2` writes the resulting 16-byte tile to the destination tile in pattern
   table 1.

Transform flags are geometric:

- `$40` - reverse bits in every CHR row byte: **horizontal flip**;
- `$80` - reverse the eight rows independently in both bitplanes: **vertical flip**;
- `$C0` - apply both flips;
- neither bit - unflipped runtime tile clone.

This allows scripts to synthesize mirrored background tiles without storing duplicate
CHR data.

## 14. FDS/scene transition bytecode

The `$Ex` family at `$79A7` is a multi-phase FDS/scene transition state machine.
Retail uses `E0`. Its path reads a scene index, selects the four-byte NOV2 scene-load
record at `$7BA5`, copies those file IDs to `$60DF-$60E2`, and enters the FDS BIOS
loading wrapper.

This statically connects script bytecode to the recovered scene-load table: script
events request new program/CHR overlay compositions.

The interpreter contains other `$Ex` low-nibble handling for disk/side transition and
retry behavior, but unused forms should not be promoted to retail language without
source evidence.

## 15. Source-used `$0x` VM memory/ALU forms

Opcode families `$Fx` and `$0x` share handler `$7C0E`, but the recovered retail source
contains no source-reachable `$Fx` command.

Source-used `$0x` forms are:

- `00` - store immediate byte;
- `01` - add immediate and store;
- `02` - subtract immediate and store;
- `04` - compare/subtract for condition flags without storing the result;
- `06` - copy byte;
- `09` - counted block write;
- `0E` - counted `(address, value)` multi-store;
- `0F 05` - invoke built-in/system sequence 5, entering engine state `$22`.

The helper at `$7DD8` projects CPU arithmetic results into story flags `$FA/$FB`, so
carry and zero conditions become queryable through the same persistent flag mechanism
used by predicates.

## 16. Remaining reverse-engineering frontier

The retail gameplay VM is structurally recovered. Remaining work is value-level and
semantic refinement, not discovery of the interpreter skeleton:

1. correlate individual `$07E0-$07E3` values with exact music/SFX identities;
2. finish stable low-level names for remaining source-used `Bx` forms;
3. identify real runtime conditions, if any, that enter the **327 non-reached source
   bytes** without connecting them speculatively;
4. assign human-facing world directions to verified opposing `$FD/$FE` sentinels;
5. finish the remaining high-bit palette-animation control semantics.

Do not inflate source coverage by decoding arbitrary source islands without a proven
incoming VM state. Engine capability is not evidence of retail source usage, and a
plausible opcode decode is not an incoming control-flow edge.
