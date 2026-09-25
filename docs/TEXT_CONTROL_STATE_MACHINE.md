# Native text-control state machine

This document records the recovered runtime meaning of Time Twist scenario text
controls `0-7`. It separates **native engine behavior** from localization
policy. The native behavior is deterministic; editorial decisions about whether
a Japanese pause still belongs in English are separate.

## Evidence and ownership

The controls are decoded by the resident NOV2 text engine. Relevant CPU
addresses use NOV2's `$6000` load base.

| Surface | CPU address | Recovered role |
| --- | ---: | --- |
| controller poll | `$67E4-$6850` | builds current/new-press button masks |
| dialogue scheduler | `$7F0F-$7F3F` | dispatches renderer state in `$69` |
| renderer state table | `$7F42` | 27 little-endian state-handler pointers |
| text decoder | `$815E` | decodes the next packed text token |
| control dispatcher | `$8242` | maps control value to row geometry or semantic state |
| semantic-state setter | `$831D` | stores next renderer state in `$69` |
| dirty-row selector | `$837E` | selects staging source and PPU destination |
| staged-cell uploader | `$83D9` | walks staged glyph cells toward PPU writes |
| software row shift | `$844F` | shifts rows 2-4 upward and clears row 4 |
| scroll NMI worker | `$84AE` | performs the 15-step row-scroll nametable rewrite |
| typewriter SFX | `$85C5` | writes command `$04` to `$07E0` |

The staging buffer begins at `$8747` and contains four `$30`-byte rows.
Each displayed glyph consumes two staged bytes, so one text row holds 24
characters.

## Control dispatcher

At `$8242`, the native engine explicitly tests values `1,2,4,3,5,6`.
Values `0` and `7` fall through to the same ordinary row-advance path.

The semantic-control stubs are:

| Control | Initial state written to `$69` |
| ---: | ---: |
| `1` | `$13` |
| `2` | `$0F` |
| `3` | `$06` |
| `4` | `$09` |
| `6` | `$17` |

Control `5` is the packed-record/dictionary terminator and does not enter this
presentation state machine.

## All semantic controls are A-button waits

Controls `1`, `2`, `3`, and `6` share the same high-level shape:

1. flush the currently dirty staged text to the nametable;
2. enter a dedicated wait state;
3. test for a **new A-button press**;
4. resume with control-specific row/scroll behavior.

The wait states are `$15`, `$11`, `$08`, and `$19` respectively. They
are among the scheduler's odd-frame exceptions, so the wait/input path is
serviced every frame rather than only on the renderer's ordinary even-frame
cadence.

The input check is `LDA $1F / AND #$80`. The controller poll at `$67F2`
reads `$4016` eight times and rotates those bits into `$1D`; the first NES
controller bit (A) ends in bit 7. `$6831-$6835` derives `$1F` as a
new-press edge mask. The repeat path masks with `#$3F`, so A and B are not
auto-repeated. A semantic text wait therefore requires a fresh A press rather
than merely holding A.

While waiting, the common path at `$7FD2` submits one OAM sprite using tile
`$A4` at X=`$7C`, Y=`$CA`, attribute `$01`. That is the native
continuation-prompt sprite path; the exact artwork is CHR-dependent, but the
state-machine role is source-verified.

## Exact semantics

### `CTRL:1` — wait, then resume on row 2

State sequence:

```text
$13 -> $14 -> $15 [wait for fresh A] -> $16
```

On A, state `$16`:

- stores `$80` in `$6E`;
- resumes decoding at X=`$30`.

That is the start of physical text row 2. There is **no scroll**.

Therefore `CTRL:1` means:

> Commit the current presentation, wait for A, then reveal/continue beginning
> on row 2 while preserving row 1.

The preceding segment must not already extend past X=`$30`, or continuation
would overwrite staged text.

### `CTRL:2` — wait, then resume on row 3

State sequence:

```text
$0F -> $10 -> $11 [wait for fresh A] -> $12
```

On A, state `$12`:

- stores `$FF` in `$6E`;
- resumes decoding at X=`$60`.

That is physical text row 3. There is **no scroll**.

Therefore `CTRL:2` means:

> Commit the current presentation, wait for A, then reveal/continue beginning
> on row 3 while preserving rows 1-2.

The preceding segment must not already extend past X=`$60`.

The native opcode itself is not “mixed.” It always performs this wait/re-entry
behavior. The localization policy may remove a *source* `CTRL:2` when review
shows that the Japanese author used that wait only as pagination and continuous
English reads better without it.

### `CTRL:6` — wait, then resume on row 4 without scrolling

State sequence:

```text
$17 -> $18 -> $19 [wait for fresh A] -> $1A
```

On A, state `$1A`:

- stores `$40` in `$6E`;
- resumes decoding at X=`$90`.

That is physical text row 4. There is **no row shift or scroll sequence**.

Therefore `CTRL:6` means:

> Commit the current presentation, wait for A, then reveal/continue on row 4
> while preserving rows 1-3.

The preceding segment must not already extend past X=`$90`.

### `CTRL:3` — wait, scroll one text row, then resume on row 4

State sequence before A:

```text
$06 -> $07 -> $08 [wait for fresh A]
```

A press sends the renderer to state `$0C`. That begins the same scroll chain
used by `CTRL:4`:

1. `$0C` loads `$6D = $0F`;
2. state `$0D` waits while the NMI worker at `$84AE` consumes the
   15-step countdown;
3. when the countdown reaches zero, NMI changes the state to `$0E`;
4. state `$0E` stores `$40` in `$6E`;
5. `$844F` shifts software rows 2-4 into rows 1-3 and clears the new row 4
   to tile `$AC`;
6. decoding resumes at X=`$90`.

Therefore `CTRL:3` means:

> Commit the current presentation, wait for A, scroll the dialogue area upward
> by one text row, then continue on the newly cleared bottom row.

This is why `CTRL:3` is not interchangeable with `CTRL:6`, even though
both eventually continue at X=`$90`.

## Layout controls for comparison

### `CTRL:0` — ordinary next-row advance

`CTRL:0` does not enter a wait state. The fallthrough path advances X to the
next `$30`-byte row start while the cursor is above row 4. It also updates
row-selection bookkeeping in `$72/$73`.

### `CTRL:4` — immediate scroll, then row-4 continuation

`CTRL:4` enters state `$09`, flushes staged text, and reaches the same
`$0C-$0E` scroll chain as `CTRL:3` **without waiting for A**.

So the exact relationship is:

```text
CTRL:3 = A wait + CTRL:4-style scroll/continuation
CTRL:6 = A wait + row-4 continuation, no scroll
```

### `CTRL:5` — record/dictionary terminator

At `$8304`, control 5 either:

- restores the previous packed-text pointer when returning from a nested
  dictionary entry; or
- at dictionary depth zero, switches to the normal end-of-record flush state.

It is structural encoding, not editable dialogue markup.

### `CTRL:7` — unused alias of the control-0 fallthrough

The decoder can represent value 7, but the retail-source audit finds no
`CTRL:7` tokens. Because the dispatcher has no explicit value-7 branch, it
falls through the same row-advance code as value 0.

Production must not generate `CTRL:7`; use the intentional control whose
semantics are actually required.

## Dirty-row bookkeeping

`$837E` decides where a flush begins.

After semantic continuation, `$6E` records the first dirty row:

| `$6E` | Flush begins at | PPU text origin |
| ---: | --- | ---: |
| other/default | row 1 | `$2244` |
| `$80` | row 2 | `$2284` |
| `$FF` | row 3 | `$22C4` |
| `$40` | row 4 | `$2304` |

`$73` is separate leading-row bookkeeping used when controls position a
record before its first visible glyph. It selects row 2, 3, or 4 as the
initial flush origin and is then cleared.

This explains the overwrite constraints enforced by production validation:
`CTRL:1`, `CTRL:2`, and `CTRL:6` directly re-enter earlier fixed rows,
whereas `CTRL:3` scrolls before re-entering row 4.

## Scenario usage census

A repository-wide count of the 13 decoded Japanese scenario banks versus the
13 current canonical English maps gives:

| Control | Japanese source | Current English | Difference |
| ---: | ---: | ---: | ---: |
| `0` | 744 | 1,353 | +609 |
| `1` | 160 | 90 | -70 |
| `2` | 151 | 89 | -62 |
| `3` | 192 | 178 | -14 |
| `4` | 202 | 640 | +438 |
| `6` | 98 | 70 | -28 |
| `7` | 0 | 0 | 0 |

Control 5 is the record separator and is not represented as an ordinary
`{CTRL:5}` tag in these JSON maps.

The large increases in controls 0 and 4 are expected: English layout
regenerates row advances and scrolling for longer English prose. The smaller
counts for controls 1, 2, 3, and 6 show that historical localization work
already removed some Japanese A-wait boundaries before the current canonical
policy was frozen.

That census is **not** evidence that the native controls have variable
semantics. Their machine behavior is fixed as documented above. It is also not
a blanket endorsement of every historical removal. The current English map is
reviewed state; any future change to a semantic wait should remain
record-scoped, source-aware, and runtime-tested.

## Canonical names

For engineering discussion, these names describe the recovered operations more
accurately than “pause/page/reveal”:

| Control | Canonical runtime name |
| ---: | --- |
| `0` | `ROW_NEXT` |
| `1` | `WAIT_ROW2` |
| `2` | `WAIT_ROW3` |
| `3` | `WAIT_SCROLL_ROW4` |
| `4` | `SCROLL_ROW4` |
| `5` | `END_RECORD_OR_DICTIONARY` |
| `6` | `WAIT_ROW4` |
| `7` | `ROW_NEXT_UNUSED_ALIAS` |

Narrative effects such as a speaker change or dramatic reveal are consequences
of where the script places these operations. They are not separate opcode
meanings.

## Typewriter SFX after a leading presentation control

Issue #74 is a renderer-state edge case, not a TT3A scene-SFX timing defect.

A record can begin with a semantic/presentation control before it has decoded a
single new glyph. In that case the control's initial flush walks staging cells
that still contain the preceding presentation. Rewriting those cells leaves the
screen visually unchanged, but the shared uploader can still request the native
typewriter sound.

### Recovered path

For the motivating record:

```text
TT3A/g0/r26 = {CTRL:4}In fact, he's an{CTRL:4}intelligence agent.
```

the first control follows:

```text
state $09 -> $7FC0 -> $837E row selector
state $0A -> $7FC4 -> $83D9 staged-cell uploader
state $0B -> $0C/$0D/$0E scroll chain
resume -> JSR $815E text decoder
```

The state-`$0A` upload therefore happens **before** the visible scroll and
before `In fact...` has been decoded. Its cells are stale row-4 content from
the previous presentation.

The NMI cell-write path remains:

```asm
$8479  LDA $65
$847B  STA $2007
$847E  JSR $988D
```

and native `$85C5` writes command `$04` to resident SFX latch `$07E0`.
TT3A's `91 10` and `91 20` use the separate scene-overlay latch
`$07E1`; neither command is removed or retimed by this fix.

### Runtime evidence from v17-v19

The successive checkpoint tests localized the defect:

- **v17:** eight pre-scroll typewriter-like bursts while the old text remains
  visually static;
- **v18:** filtering common-space `$C0` reduced that train from eight bursts
  to seven, but the stale-flush symptom remained;
- **v19:** keeping the marker active across the complete control flush removed
  the early train, proving that the native typewriter path was the producer,
  but marker clearing at renderer state `$04` was too late.

The v19 AVI makes the latter failure measurable: the first visible `I`
appears at frame 661, while the strong typewriter train does not resume until
about frame 718, roughly 57 frames / 0.95 seconds later.

The reason is structural. State `$04` is an end-of-record flush, not the
generic boundary for newly decoded text. The first clause
`In fact, he's an` is later flushed by the record's second `CTRL:4`
through state `$0A`. Leaving the marker set until state `$04` therefore
silences that entire clause.

### Correct marker lifetime

The marker must cover exactly this interval:

```text
leading control detected
        |
        v
initial stale control flush  <-- typewriter suppressed for every cell
        |
        v
control-specific scroll/wait/re-entry
        |
        v
resume text decoding         <-- clear marker here
        |
        v
new translated text          <-- native typewriter behavior restored
```

The recovered semantic-control resume sites all tail back into the same text
decoder:

| Continuation | Resume call |
| --- | ---: |
| `CTRL:3` / `CTRL:4` scroll-row4 | `$7FFD: JSR $815E` |
| `CTRL:2` row3 | `$8016: JSR $815E` |
| `CTRL:1` row2 | `$802F: JSR $815E` |
| `CTRL:6` row4 | `$8048: JSR $815E` |

Production redirects only those four calls to the five-byte NOP-owned frontend
tail at `$819E`:

```asm
$819E  LSR $73
$81A0  JMP $815E
```

Because the original sites use `JSR`, the wrapper may tail-jump to the native
decoder; the decoder's eventual `RTS` returns to the original continuation
caller.

The typewriter helper itself no longer consumes the marker on the first stale
cell:

```asm
$988D  LDA $73
$988F  BNE $98AD       ; marker active: stale control-flush cell stays silent
$9891  JMP $85C5       ; marker clear: native typewriter SFX
```

The existing leading-row selector still reduces the leading-control marker to
one after using its row geometry. The marker consequently remains nonzero for
the whole initial stale flush, then is cleared immediately before decoding the
first real text after the control.

This design requires no delay, no scheduler change, no NMI cadence change, no
scratch RAM, no `$C0` special case, and no changes to `$91 10` /
`$91 20`. It generalizes across the recovered `CTRL:1/2/3/4/6`
continuation architecture instead of special-casing TT3A.

The v20 checkpoint candidate implements this resume-boundary design and remains
runtime-pending.

