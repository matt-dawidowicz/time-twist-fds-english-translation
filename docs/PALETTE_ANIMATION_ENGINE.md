# Gameplay palette-animation engine

This note closes the remaining value-level ambiguity around the gameplay
palette-animation table selected through scenario header word `$A21C`.

## Status

The runtime behavior is **VERIFIED** from the original NOV2 code and the unique
retail animation tables.

NOV2:

- initializes the selected record at `$90E8`;
- advances active sequences at `$91AD`;
- applies background/sprite palette records through the existing `$89EB` palette
  loader;
- uses `$1F & $80` as the fresh-A-button edge test.

The source record shape is:

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

The current retail data contains one sequence per record, but the initializer
supports multiple sequences.

## Runtime state

For the current sequence, NOV2 expands:

```text
$92BA = frame_count
$92BB = repeat/control
$92BC... = repeated duration, background selector, sprite selector triples

$078F = current frame index
$0790 = current frame tick counter
```

`$92DA` holds the active sequence count plus per-sequence runtime copies.

## Repeat/control semantics

### `$00`: inactive/stopped

At `$9209-$9213`, a zero control exits immediately. No frame advances and no
new palette selector is applied.

### `$01-$7D`: finite cycle counter

After the final frame of a cycle, NOV2 decrements the control byte. When the
decrement reaches zero, later ticks hit the zero-control exit and the sequence
is stopped.

Thus an ordinary value `n` is a finite cycle count under the native initialized
state.

### `$7E`: loop until fresh A on a cycle boundary

At the end of every completed frame-list cycle:

- if there is no fresh A edge, `$7E` is preserved and another cycle may run;
- if `$1F & $80` is set on that cycle boundary, NOV2 stores zero in the control
  byte, stopping the sequence on later ticks.

This is not a generic duration marker. It is a sequence-level
**cycle-until-fresh-A-at-boundary** control.

### `$7F`: permanent cycle

At a completed cycle, `$7F` is preserved unconditionally. A input does not
change it.

### `$80-$FF`: fresh-A pre-start gate

Before processing the current frame, any control with bit 7 set checks
`$1F & $80`:

- without a fresh A edge, the sequence does not advance;
- with a fresh A edge, NOV2 clears bit 7 and continues on that same tick.

Examples:

- `$85` waits for fresh A, then becomes ordinary finite control `$05`;
- `$FE` waits for fresh A, then becomes `$7E`;
- `$FF` waits for fresh A, then becomes permanent-loop `$7F`.

The source-unused `$80` case is mechanically unusual: after A clears it to zero,
NOV2 does **not** re-run the earlier zero-control test on that same tick. The
runtime therefore continues into frame processing once before later state
transitions take effect. This is documented as raw engine behavior, not assigned
a narrative name.

## Frame-duration semantics

At `$9249` NOV2 loads the current duration byte and immediately executes
`AND #$7F`. No other NOV2 path reads that frame-duration byte.

Therefore:

```text
effective_duration = duration_raw & $7F
```

Bit 7 of a duration byte is ignored/reserved by this path. It is **not** the
A-button gate.

After incrementing `$0790` once per tick:

- ordinary effective durations advance when the counter equals the duration;
- effective duration `$7F` bypasses the equality/advance path and holds the
  current frame indefinitely;
- effective duration `$00` advances only when the 8-bit tick counter wraps back
  to zero, i.e. after 256 increments.

## Retail source inventory

Seven unique owning tables parse exactly:

| Owner | Range | Bytes | Records |
| --- | --- | ---: | ---: |
| `TT1B` | `$CE0B-$CE2C` | 33 | 3 |
| `TT2` | `$CF67-$CFCA` | 99 | 8 |
| `TT3A` | `$CEDD-$CF3A` | 93 | 10 |
| `TT4` | `$D147-$D192` | 75 | 5 |
| `TT5` | `$CAF2-$CB1F` | 45 | 5 |
| `T25` | `$C056-$C08C` | 54 | 3 |
| `TT6C` | `$CC5C-$CD0D` | 177 | 16 |

Total: **50 records**.

Retail repeat/control bytes:

| Value | Count |
| ---: | ---: |
| `$03` | 1 |
| `$04` | 1 |
| `$14` | 1 |
| `$1E` | 3 |
| `$7F` | 44 |

Retail duration bytes:

`$01, $02, $03, $04, $08, $10, $12, $1E, $30, $3C, $40, $5A, $60` only.

Critically, retail source uses:

- **zero `$7E` sequence controls**;
- **zero `$80+` sequence controls**;
- **zero high-bit duration bytes**;
- **zero `$7E/$7F` effective duration holds**.

So the formerly unresolved forms are native engine capability, not hidden
shipped-script behavior.

## Source guards and tests

`work/tools/audit_recovered_engine_surfaces.py` guards:

- the zero/high-bit A-gate code at `$9209-$9225`;
- duration masking and cycle-control code at `$9249-$929B`;
- all seven table extents;
- the 50-record count;
- exact retail control and duration inventories;
- absence of `$7E`, `$80+`, and high-bit-duration use in retail data.

`work/time_twist/palette_animation.py` contains the public parser and pure control
helpers. `work/tests/test_palette_animation.py` protects the synthetic edge cases,
including `$7E`, `$7F`, `$80`, `$FF`, and high-bit duration aliases.

## Remaining boundary

This pass recovers the low-level palette-animation control language. It does not
assign story-facing names such as “lightning flash” or “fire flicker” to
individual animation records. Those names should be attached only when a clean
playthrough or scene-specific call site proves the visual context.
