# Text layout engine reference

This is the maintainer-facing synthesis of Time Twist's dialogue geometry. It
does not replace [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md)
or [English pagination policy](ENGLISH_PAGINATION_POLICY.md); those remain
authoritative for instruction-level behavior and editorial policy.

## Physical model

**VERIFIED.** NOV2 stages dialogue in four physical rows beginning at CPU
`$8747`. Each row is `$30` bytes and each visible glyph consumes two staged
bytes, giving **24 visible columns per row** and a 192-byte four-row staging
surface.

Row starts in staging coordinates are therefore:

| Physical row | Staging cursor |
| ---: | ---: |
| 1 | `$00` |
| 2 | `$30` |
| 3 | `$60` |
| 4 | `$90` |

A record must not implicitly cross a 24-column boundary. Row movement is an
explicit renderer operation.

## Control-to-geometry contract

| Control | Canonical name | A wait | Scroll | Resume cursor |
| ---: | --- | :---: | :---: | ---: |
| 0 | `ROW_NEXT` | no | no | next row start |
| 1 | `WAIT_ROW2` | yes | no | `$30` |
| 2 | `WAIT_ROW3` | yes | no | `$60` |
| 3 | `WAIT_SCROLL_ROW4` | yes | yes, one row | `$90` |
| 4 | `SCROLL_ROW4` | no | yes, one row | `$90` |
| 5 | `END_RECORD_OR_DICTIONARY` | n/a | n/a | structural |
| 6 | `WAIT_ROW4` | yes | no | `$90` |
| 7 | `ROW_NEXT_UNUSED_ALIAS` | no | no | control-0 path |

Controls 1, 2, 3, and 6 require a **fresh A-button edge**. They are not
intrinsically speaker-change, reveal, or dramatic-pause opcodes. Those are
narrative uses of fixed renderer operations.

Control 7 is representable but absent from the recovered retail scenario
corpus. Production must not invent it.

## Preservation and overwrite behavior

Controls 1, 2, and 6 re-enter a fixed physical row without scrolling. Existing
staged rows remain present. Consequently:

- control 1 must be reached before preceding text occupies row 2;
- control 2 must be reached before preceding text occupies row 3;
- control 6 must be reached before preceding text occupies row 4.

Control 3 is different: after the A press it executes the native one-row scroll,
shifts software rows 2-4 into rows 1-3, clears the new row 4, and resumes there.
Control 4 uses the same scroll chain without the A wait.

Cross-record continuation has the same ownership problem. A following record
that begins with a presentation control can re-enter a retained row. Translation
growth in the preceding record must not overwrite the row that the next record
expects to own. `work/time_twist/dialogue_flow.py` models this staging-buffer
ownership for regression checks.

## Dirty-row origins

**VERIFIED.** NOV2's dirty-row selector at `$837E` uses `$6E` to select the
first staged row that needs uploading:

| `$6E` | First dirty row | PPU text origin |
| ---: | ---: | ---: |
| default | row 1 | `$2244` |
| `$80` | row 2 | `$2284` |
| `$FF` | row 3 | `$22C4` |
| `$40` | row 4 | `$2304` |

`$73` separately tracks a leading presentation transition before the first
visible glyph.

## English layout policy

Ordinary English uses greedy 24-column wrapping:

1. fill a row with complete words while they fit;
2. use control 0 for an ordinary row advance;
3. use control 4 when continuation requires the native row-four scroll;
4. start every recognized speaker heading on a fresh physical row;
5. do not move semantic A-wait controls merely to gain horizontal space.

The canonical translation contains explicitly protected structural layouts:
scenario quiz prompts, identity/info cards, presentation records, and
hash-locked reviewed exceptions. These are interface geometry rather than
ordinary prose and must not be normalized by generic wrapping.

Scenario quiz prompts are additionally constrained because the prompt shares
the renderer with native answer-selection UI. The generic tested segment ceiling
is 23 columns unless an exact reviewed checkpoint layout is hash-locked.

## Typewriter sound edge case

**VERIFIED.** A leading presentation-only control can cause a renderer
transition before the first printable glyph. Production preserves `$73=1`
long enough to act as a one-shot marker and routes the glyph uploader through
the helper at `$988D`. Exactly the first post-control click is suppressed;
the renderer cadence and native typewriter SFX at `$85C5` are otherwise
unchanged.

The motivating retail case is `TT3A/g0/r26`, which begins with control 4.
This is an edge-case SFX gate, **not a global text-delay mechanism**.

## Debugging order

For a cutoff, overwrite, premature disappearance, or apparently wrong line:

1. identify the current record and its control sequence;
2. map each segment onto the four physical row starts;
3. check fixed-row re-entry after controls 1/2/6;
4. check scroll ownership after controls 3/4;
5. inspect the following record for leading continuation controls;
6. only then investigate encoding or compression.

For a click that precedes visible text, inspect leading-control state and the
one-shot `$73` marker before changing renderer timing.

## Evidence boundary

The geometry and control behavior above are **VERIFIED** from NOV2 code and
maintained tests. Editorial judgments about whether a particular source pause
should remain in English are separate and remain record-scoped.
