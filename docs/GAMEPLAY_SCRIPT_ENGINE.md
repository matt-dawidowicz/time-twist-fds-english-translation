# Gameplay script and event VM

This note records the recovered gameplay-script architecture in NOV2 and the `$A200`
scenario overlays. It complements [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md):
the graphics note describes the scene data rendered by NOV2, while this note describes
the bytecode that selects, mutates, and transitions that scene state.

The important structural result is that Time Twist has a small bytecode interpreter,
not a collection of unrelated event tables. The interpreter owns a script program
counter, a software call stack, a label table, a predicate evaluator, a persistent
256-bit event-flag bank, and high-nibble opcode families.

Evidence labels follow the repository convention:

- **VERIFIED** - proven from exact source bytes and control flow;
- **DERIVED** - follows mechanically from verified behavior;
- **INFERRED** - a higher-level name that is useful but not yet safe as a binary rule;
- **UNKNOWN** - deliberately unresolved.

## 1. Interpreter dispatch

NOV2 `$69E5` fetches the byte at the script PC in `$C5/$C6`, shifts out its high
nibble, and maps it to a NOV2 engine state. High nibble zero is remapped to state
`$20`; nibbles `$1-$F` become states `$11-$1F`. The normal next-command path at
`$69FF` restores state `$10`, whose handler is the fetch/decode routine itself.

The scheduler at `$68C5` uses major state `$26` and substate `$27` to dispatch through
the word table at `$690B`. For the script states, the recovered handler map is:

| Script high nibble | NOV2 state | Handler | Current classification |
| ---: | ---: | ---: | --- |
| `$1x` | `$11` | `$6A04` | multi-phase UI/text state machine; partially named |
| `$2x` | `$12` | `$6A82` | multi-phase menu/selection state machine; partially named |
| `$3x` | `$13` | `$6BFD` | selection-result branch/dispatch |
| `$4x` | `$14` | `$6C5E` | predicate/conditional branch |
| `$5x` | `$15` | `$6DA9` | control flow: jump/call/return/label dispatch |
| `$6x` | `$16` | `$6F2C` | persistent event-flag mutation |
| `$7x` | `$17` | `$6F49` | scene/presentation component configuration |
| `$8x` | `$18` | `$717E` | engine parameter write; exact field semantics incomplete |
| `$9x` | `$19` | `$7192` | engine parameter write; exact field semantics incomplete |
| `$Ax` | `$1A` | `$71A4` | delay/input gate |
| `$Bx` | `$1B` | `$71F5` | exploration/movement/camera interaction state machine |
| `$Cx` | `$1C` | `$7870` | persistent presentation/input state; exact semantic name incomplete |
| `$Dx` | `$1D` | `$78BA` | display/scroll/presentation parameters; partially named |
| `$Ex` | `$1E` | `$79A7` | FDS/scene/file transition state machine |
| `$Fx` | `$1F` | `$7C0E` | VM memory/ALU operations and waits |
| `$0x` | `$20` | `$7C0E` | same VM memory/ALU handler as `$Fx` |

Do not treat this table as a claim that every low-nibble subcommand is fully named.
The handler addresses and broad structural roles are verified; several user-facing
meanings remain deliberately conservative.

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
The script engine therefore has to be analyzed against the **composed runtime image**,
not an isolated small overlay.

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
than the previous generic “event pointer” label.

## 4. Predicate engine and `$4x` conditional branches

The predicate evaluator lives around `$96D6-$9BAF`. Its source pointer is `$94/$95`.
It tests the persistent event-flag bank and combines terms with negation and logical
composition. Static tracing proves support for NOT-like inversion plus AND/OR chaining;
the final result/route mask is returned through `$A9` and consumed by the `$4x`
branch handler.

The `$4x` family supports several predicate sources:

1. an inline predicate expression immediately following the opcode;
2. a compact one-flag predicate synthesized by NOV2 from the command byte;
3. an indexed predicate expression from the table base stored at `$A20E`;
4. a spatial predicate comparing two actor positions against a command-supplied
   distance threshold.

The branch result can select either signed relative targets or absolute 16-bit targets,
depending on command flags.

### `$A20E` is optional and unused in the recovered scene data

`$A20E/$A20F` is read by the indexed-predicate form of the `$4x` handler, so its
**structural role is an optional predicate-expression table base**.

However, the composed header value is `$0000` in all 13 recovered gameplay scenes.
There is therefore no source-backed non-null `$A20E` table to decode in Time Twist's
ordinary scene overlays. The old description of `$A20E` as a populated generic
“script/predicate/action table” was too broad.

The remaining question is narrower: whether the indexed-predicate opcode form is
unused in source scripts, or whether some exceptional runtime context installs a
nonzero base before executing it.

## 5. Persistent story/event flags

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

## 6. `$7x` scene/presentation configuration

The `$7x` family controls the scene components whose binary formats are documented in
the graphics-engine note. Its setup logic clears or populates selectors including
`$83-$89`; the activation path at `$70CE` then invokes the corresponding native
loaders.

Verified links include:

- selector `$85` -> static metasprite placement loader `$8AFC`;
- selectors `$86/$87` -> palette loader `$89EB`;
- selector `$88` -> actor spawn loader `$8C88`;
- selector `$89` -> palette-animation initializer `$90E8`.

This command family is therefore the bridge from event bytecode to room presentation.
Individual low-nibble forms are still being named.

## 7. `$A21C` is the palette-animation table

`$A21C/$A21D` is no longer an unknown room/presentation-state pointer.

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
`$7E` and high-bit duration forms have input/state-sensitive behavior that remains to
be named more specifically.

This table should now be called the **palette-animation table** or **palette-cycle
table**.

## 8. Actor selector and animation/motion tables

The three header words beginning at `$A22C` are now structurally separated:

- `$A22C` - two packed animation/motion selectors per actor type;
- `$A22E` - pointer table for metasprite-animation streams;
- `$A230` - pointer table for motion/velocity streams.

NOV2 `$8E08` reads the first `$A22C` selector. Its high nibble selects an `$A22E`
stream bank and its low nibble selects a sequence within that bank. Normal animation
steps provide a duration and metasprite index, stored into actor fields `+7` and `+8`.

NOV2 `$8E7F` does the same for the second selector and `$A230`. Normal motion steps
provide a duration plus X/Y deltas, stored into actor fields `+10`, `+0B`, and `+0C`.
The per-frame mover at `$8F28` applies those deltas to the actor coordinates.

Both channels recognize control values:

- `$7F` - loop/restart the current sequence;
- `$FF` - terminate/deactivate the actor;
- other `$80+N` values - transition/reinitialize the actor as type/state `N`.

This replaces the previous generic description of `$A22E/$A230` as unidentified
animation/motion lookup tables.

## 9. Directional hotspot sentinels `$FD` and `$FE`

Hotspot rectangles are selected through `$A20C`; their geometric format remains as
documented in the graphics-engine note. The two non-geometric bottom values are now
more specific.

NOV2 `$768F` recognizes `$FD` and `$FE` as successful terminal hotspot results instead
of Y bounds. The exploration/movement state at `$750B` then treats them oppositely:

- movement direction/state `$1D=1` rejects `$FE` but permits the `$FD` path;
- movement direction/state `$1D=2` rejects `$FD` but permits the `$FE` path;
- the permitted paths use the opposite boundary selectors at `$07AA` and `$07AB`.

The verified binary meaning is therefore **opposite directional/one-way boundary
sentinels**. The human-facing names of direction 1 versus direction 2 are not assigned
here until their controller/world-axis mapping is traced explicitly.

## 10. FDS/scene transition bytecode

The `$Ex` family at `$79A7` is a multi-phase FDS/scene transition state machine.
Its low-nibble dispatcher includes the path that reads a scene index, selects the
four-byte NOV2 scene-load record at `$7BA5`, copies those file IDs to `$60DF-$60E2`,
and enters the FDS BIOS loading wrapper.

This statically connects script bytecode to the already recovered scene load table:
script events are what request new program/CHR overlay compositions.

Other `$Ex` low-nibble forms participate in disk/side transition and retry handling.
They remain grouped under the broad verified FDS/scene-transition role until every
form has a stable semantic name.

## 11. VM memory/ALU operations

Opcode families `$Fx` and `$0x` share handler `$7C0E`. Their low three bits select
operations that read embedded 16-bit addresses, manipulate byte values, and record
arithmetic status.

The helper at `$7DD8` projects CPU arithmetic results into story flags `$FA` and `$FB`:
carry and zero conditions therefore become queryable through the same persistent flag
mechanism used by predicates. Other forms implement waits or transfer control into
engine states.

The broad role is verified as a **VM memory/ALU family**. The exact mnemonic for each
low-nibble form is intentionally deferred until source command usage is exhaustively
parsed.

## 12. Remaining work

The event engine is structurally recovered enough to stop using generic names such as
“unknown event pointers,” but several tasks remain before calling the VM complete:

1. enumerate every source-reachable command and low-nibble form from all label entry
   points;
2. finish stable names and operand layouts for `$1x-$3x`, `$8x/$9x`, `$Bx-$Dx`, and
   every `$Ex` and `$Fx/$0x` subcommand;
3. prove whether the `$A20E` indexed-predicate form is source-unreachable;
4. assign human-facing direction names to hotspot sentinels `$FD/$FE`;
5. decode the remaining `$7E`/high-bit palette-animation control behavior;
6. produce a source-backed control-flow graph for each composed gameplay overlay;
7. add pure parsers/tests only after the binary contracts above are stable enough not
   to encode provisional names as APIs.

Until those tasks are complete, patches should continue to modify only already-
recovered formats. This document is a reverse-engineering model, not permission to
rewrite gameplay scripts generically.
