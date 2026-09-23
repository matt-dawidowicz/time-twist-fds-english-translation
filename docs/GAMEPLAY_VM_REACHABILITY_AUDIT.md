# Gameplay VM reachability-island audit

This note closes the address-level follow-up to the historical
`23,902 / 24,229 = 98.6504%` gameplay-script reachability result.

## Final structural result

The old **327-byte** remainder was not one class of unknown code. It combined
three modeling omissions:

1. exploration result state was not propagated through
   `B9 -> $BA -> $A20C hotspot group -> $91/$A7 -> 30/31`;
2. the native **no-result** path of `30/31` was not represented;
3. the extended inline-predicate span was decoded one byte short.

With all three native behaviors modeled, the 24,229-byte gameplay-script region
has the following structural classification:

```text
structural may-reach bytes          24,199
unused but valid helper bytecode        20
unreferenced valid text bytecode         2
skipped data / padding                   8
                                    ------
total script-region bytes            24,229
```

Structural may-reach coverage is therefore **24,199 / 24,229 = 99.8762%**.

The remaining **30 bytes are fully classified**. They are not an unresolved
incoming-control-flow frontier.

This is still a static **may-reach** result, not a claim that a clean playthrough
has executed all 24,199 potentially live bytes.

## 1. Exploration supplies selection-result state

The first missing edge was recovered in the previous pass:

1. `B9` saves VM continuation state and copies its operand into `$BA`;
2. NOV2 `$768F` uses `$BA` as a one-based hotspot-group selector into
   `$A20C`;
3. the group rectangle count is copied to `$91`;
4. the selected rectangle index is maintained in `$A7`;
5. `30/31` at `$6BFD` consumes `$91/$A7`.

Therefore `$91/$A7` are shared result-dispatch state, not menu-only state.

## 2. `30/31` has a native no-result fallthrough

The second omission was more important than the earlier classification implied.

At `$6BFD`, both selection-result forms explicitly test `$A4 == $FF`.

### Relative form `31`

If a result exists, `$A7` indexes one signed relative target.

If `$A4 == $FF`, NOV2 executes:

```text
LDA $91
CLC
ADC #$01
JMP $69FC
```

That advances the PC across the opcode and its `$91` relative target bytes,
landing on the next sequential command.

### Absolute form `30`

NOV2 first advances one byte to the absolute-target table. If `$A4 == $FF`, it
then advances by `2 * $91`, again landing immediately after the target table.

`$A4=$FF` is a real native state, not a hypothetical decoder invention:

- the hotspot scanner writes it when no rectangle matches;
- the menu path writes it when filtering leaves no selectable result;
- menu initialization and timeout/cancel-related paths also initialize or return
  the same sentinel.

A sound structural may-reach graph must therefore include the no-result
fallthrough edge unless a particular call site proves the sentinel impossible.

Adding this edge explains **125 bytes** that the previous pass still left outside
the graph. In particular, the TT5 `$A7EB-$A80D` block and nearby short branches
are normal no-result continuations, not orphan helper code.

## 3. Extended inline predicates were one byte longer than modeled

The third issue was an exact decoder bug.

NOV2 `$977D-$97AF` advances the predicate source pointer to the result-target
table.

For a compact predicate whose low nibble is `n != $0F`:

```text
span = n + floor((n + 2) / 2)
```

For the extended form, where the low nibble is `$0F` and the following byte is
the full term count `n`:

```text
span = n + floor((n + 6) / 2)
```

The earlier scratch model used `n + floor((n + 4) / 2)` for the extended form,
which is one byte short for the retail extended predicates.

The concrete T25 predicate beginning at `$A8C9` has count `$10` and occupies
**27 bytes**, not 26. Correcting that span removes the false
`$A8E7-$A8EB` island and restores the subsequent control-flow targets,
including `$A8FF-$A902`.

The canonical helper `inline_predicate_span()` and a native guard on `$977D`
now lock this formula.

## 4. Final 30 non-live bytes

### Skipped data / padding - 8 bytes

| Scene | Program | Range | Bytes | Evidence |
| ---: | --- | --- | ---: | --- |
| 1 | TT1B + TT1A | `$A2FE-$A304` | 7 | skipped by absolute `50 $A305`; no label/call/branch target enters the range |
| 13 | TT6C | `$A978` | 1 | single byte after `53` return and immediately before route label `$A979` |

These bytes have no proven VM entry and are structurally outside executable
source flow.

### Unused audio-helper library variants - 20 bytes

TT3A contains a compact library of tiny audio/delay/return subroutines. Several
siblings are called throughout the scene, while three variants have no call,
jump, route-label, resume, or native-PC entry.

| Scene | Range | Bytes | Contents |
| ---: | --- | ---: | --- |
| 5 | `$A2DB-$A2E4` | 10 | `92 04; A1 3C; 53` and `92 08; A1 3C; 53` |
| 5 | `$A2EA-$A2EE` | 5 | `93 20; A1 78; 53` |
| 6 | `$A2F7-$A2FB` | 5 | `92 02; A1 78; 53` |

The classification is strengthened by adjacent used siblings. In TT3A, reachable
calls target helpers such as `$A2D3`, `$A2D6`, `$A2E5`, `$A2EF`,
`$A2F4`, and `$A2FB`; no source reference targets the three ranges above.

These are best described as **shipped but unused helper variants**, not unknown
gameplay paths.

### Unreferenced valid text bytecode - 2 bytes

| Scene | Range | Bytes | Evidence |
| ---: | --- | ---: | --- |
| 7 | `$AE00-$AE01` | 2 | `18 A2`, immediately after route-terminating `18 A4`; no route label, branch, call, or resume target enters `$AE00` |

This is valid bytecode but has no incoming retail control-flow edge. It is most
likely an abandoned alternate text action retained in the shipped overlay.

## 5. Script-PC incoming-edge audit

The active gameplay PC is `$C5/$C6`. Native inspection accounts for its writers
through:

- scene initialization from `$A222`;
- selection and predicate result dispatch;
- absolute/relative jumps, calls, returns, and `$A220` routes;
- FDS/scene-transition state;
- restoration of saved continuation from `$9B/$9C`;
- normal PC-advance helpers such as `$95E5`.

Exploration does not install an arbitrary hidden PC. It supplies result state and
returns through the ordinary dispatcher.

No native writer, route label, branch, call, or saved-continuation edge enters
the final 30 bytes.

## 6. Status of the historical 98.6504% figure

The **98.6504%** number should now be treated as a historical conservative
baseline, not the current structural result. Its address-level implementation
was not committed, and later reconstruction exposed the missing state edges and
the extended-predicate off-by-one described above.

The maintained figures are now:

```text
total gameplay script region            24,229
structural may-reach bytes               24,199
classified non-live bytes                    30
structural may-reach percentage         99.8762%
classified region                       100.0000%
```

"Classified region" means every byte in the bounded script region has a
source-backed role: potentially executable retail VM, unused valid helper/text
bytecode, or skipped/padding bytes. It does **not** mean 100% runtime execution
coverage.

## 7. What remains

The **327-byte reachability-island investigation is closed at the static
reverse-engineering level**.

Future clean replay tracing is still useful for runtime certification and for
story-facing labels, but it is no longer needed to determine whether the 327
bytes conceal an unknown interpreter path.

The major low-level VM/graphics-control unknowns listed by the original audit are now
closed: `$FD/$FE` are verified left/right boundaries and the `$A21C`
palette-animation control language is fully recovered. Remaining work is contextual:

1. correlate individual palette/audio call sites with story-facing visual/Foley/music
   names when clean replay proves them;
2. correlate FDS transition selectors with exact scene/file outcomes.
