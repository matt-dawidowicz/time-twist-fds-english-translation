# Quiz engine reverse engineering

This document records the complete static model used to audit the scored quiz
system in the English Time Twist candidate.

The maintained scope is **39 scored questions**:

- 5 in TT2;
- 5 in TT3A;
- 5 in TT4;
- 5 in TT5;
- 5 in TT6B;
- 14 in the TT6C retrospective finale.

The audit follows the actual compiled path from question text through answer
selection, result dispatch, continuation, and completion state. It does not
treat the English question/answer list as sufficient evidence by itself.

## 1. Runtime state

NOV2 owns the common menu and script machinery.

The quiz-relevant state is:

| State | Meaning |
| --- | --- |
| `$C5/$C6` | active gameplay-script PC |
| `$91` | current primary-menu choice count |
| `$A4` | selected fixed-text record; `$FF` means no result |
| `$A7` | logical compacted answer index |
| `$A8` | visual cursor index |
| `$9B/$9C` | saved parent script PC |
| `$9F/$A0` | saved parent software-stack continuation |

For the scored quizzes there is no predicate compaction, so `$A7 == $A8`
throughout answer selection.

## 2. Primary-menu descriptors

Overlay header words `$A210/$A212` delimit the primary-menu descriptor
table. Each descriptor contains:

```text
choice_count
one-based fixed-label record
one-based fixed-label record
...
```

The script operand used by menu opcodes is itself a **one-based descriptor
selector**. Thus `28 0E` selects descriptor 13.

Large fixed-text tables are paged in 32-record chunks. Page zero begins at
`$A214`; later page starts are reached through the page-pointer table at
`$A21A`. The quiz audit explicitly crosses all relevant 32-record boundaries,
including TT2 32/33, TT4 96/97, TT5 64/65, and TT6C's page-2 return to the
page-0 `Joseph` record.

## 3. Menu opcodes used by quizzes

The gameplay VM exposes four primary menu forms:

| Opcode | Behavior |
| ---: | --- |
| `20` | direct primary menu |
| `21` | direct primary menu plus secondary/predicate path |
| `28` | resumable primary menu |
| `29` | resumable primary menu plus secondary/predicate path |

Every scored quiz uses only `20` or `28`.

- TT3A's five Old Man questions use `20`.
- The other 34 scored questions use `28`.
- No scored quiz uses `21` or `29`.

This matters because NOV2 sends `20/28` directly through the all-choice mask
path. The predicate-filter state used by `21/29` is skipped completely.
Consequently no quiz answer can disappear because of a story-flag predicate.

The same setup gives `20/21/28/29` a zero timeout unless the explicit timed
forms are selected. The scored quizzes therefore have no timer-generated
selection result.

## 4. Direct versus resumable menus

Descriptor bit 3 snapshots the current script PC and software-stack
continuation into `$9B/$9C/$9F/$A0`.

A direct menu does **not** mean "no parent." It preserves an inherited parent.
This is why TT3A can use direct `20` menus inside the Old Man interaction.

The repaired Back/Cancel dispatcher behaves as follows:

- no parent: reject B and redraw the same menu;
- saved parent equals current PC: reject B and redraw;
- valid ancestor: return to that ancestor.

Back therefore never manufactures a quiz answer and never sends `$A4=$FF`
through the result table.

## 5. Cursor/navigation state machine

The native menu input path was reconstructed for Up, Down, Left, Right, A, and
B.

The scored quizzes use 2-, 3-, 4-, 5-, and 6-choice menus. Exhaustive simulation
from every selectable slot proves:

- Up/Down wrap only within the active choice count;
- Left/Right cross the 0/4, 1/5, 2/6, 3/7 column pairs only when the partner
  exists;
- no direction can create a logical or visual index outside the menu;
- with no predicate filtering, logical index `$A7` always equals visual index
  `$A8`.

A confirms the current visual slot, resolves its fixed-text record into
`$A4`, and advances the gameplay PC to the result opcode.

## 6. Result dispatch

Every scored quiz immediately follows its menu opcode with VM opcode `31`,
the relative selection-result dispatcher.

For a real selection, opcode `31` uses `$A7` to select a signed byte from the
target table. The branch base is the address of the `31` opcode itself.

The native dispatcher also supports `$A4=$FF`, in which case it falls through
past the target table. That state is real elsewhere in Time Twist, but it is
not reachable through a scored quiz:

1. quiz menus use `20/28`, so filtering cannot remove all choices;
2. quiz menus have no timeout;
3. rejected B redraws or backs to a real ancestor and does not return a result;
4. A writes a real selected fixed-text record to `$A4`.

This closes the apparent "no selection could accidentally count as correct"
edge case.

## 7. Correct and wrong continuations

Each of the five-question historical sets has one common wrong-answer handler.
All non-correct targets for every question converge on that handler.

The correct branch advances to the next question. The fifth correct branch
sets the chapter completion state:

| Bank | Completion |
| --- | --- |
| TT2 | set flag `$26` |
| TT3A | set flag `$42` |
| TT4 | set flag `$4E` |
| TT5 | set flag `$25` |
| TT6B | set flag `$1D` |

TT6C intentionally differs. Every wrong answer reaches `$A797`, whose script
sequence is:

```text
10 4C    show "Devil: Fool!"
10 51    show question 1
28 14    reopen question-1 answer menu
```

Thus a wrong answer restarts the 14-question retrospective from question 1.
The fourteenth correct answer switches to route 6.

## 8. Answer-menu geometry

The English variable-width renderer records the actual width of each visible
label and derives second-column and cursor positions from that width.

All 39 answer sets pass the recovered geometry limits:

- maximum single label: 18 glyphs;
- maximum paired total: 20 glyphs;
- right trailing cursor must remain at or before x=`$F8`.

In v63 the longest individual quiz label is `Fruit of knowledge` at 18
glyphs. The widest two-column pair is `Montgomery` / `Churchill` at 19
combined glyphs.

## 9. Question-card geometry

The 25 scenario quiz prompts share the four-row text staging area with the
native answer-selection UI. They are therefore structural layouts, not ordinary
prose records.

Every compiled v63 prompt:

- semantically round-trips to the canonical translation record;
- stays within the four-row buffer;
- has no visible segment wider than 24 columns.

Only six currently active quiz layouts still require a hash-locked 24-column
checkpoint exception:

- `TT4/g5/r11`;
- `TT5/g2/r16`;
- `TT6B/g1/r30`;
- `TT6B/g2/r1`;
- `TT6B/g2/r2`;
- `TT6B/g2/r3`.

The v63 Normandy and Polis edits fit the stricter rule, so their obsolete
historical exceptions were removed.

TT6C questions are ordinary scenario records while their answer labels live in
the fixed menu table; their compiled text and answer tables are audited in the
same binary pass.

## 10. Entropy/dictionary safety

The old TT3A corruption was not an answer-routing bug. Presentation controls
were hidden inside dictionary expansions. A control could suspend the decoder
while it was inside a nested dictionary expansion, after which restoration of
nested bitstream state could resume incorrectly and emit unrelated text.

v63 was audited recursively, not merely at the dictionary-definition surface.

| Bank | Dictionary entries | Expanded entries containing controls |
| --- | ---: | ---: |
| TT2 | 115 | 0 |
| TT3A | 102 | 0 |
| TT4 | 129 | 0 |
| TT5 | 120 | 0 |
| TT6B | 68 | 0 |
| TT6C | 108 | 0 |

Every quiz-bearing bank is therefore free of the control-inside-dictionary
failure class.

The audit also decodes and re-encodes every scenario group byte-exactly,
including the TT2 and TT3A split-stream layouts.

## 11. Verified answer routing

The v63 candidate has one unique success route for every intended visible
answer and one common wrong route per quiz set.

Important retained cases include:

- TT4 accepts `Parthenon`, not the formerly misrouted choice;
- TT4 accepts `Fig`;
- TT5 accepts `Projector`;
- TT6B accepts `Fruit of wisdom`, preserving the Japanese game's trivia;
- TT6B preserves `Jehovah`.

The canonical answer manifest contains all 39 scored questions and is enforced
by source-level regression tests.

## 12. Save-state boundary

A Mesen save state can retain:

- resident scenario/NOV2 bytes;
- decoded menu-width metadata;
- script PC and parent continuation state;
- live packed-text cursors;
- CPU/PPU state from the candidate that created it.

A state captured inside an older TT5 or TT3A bank can therefore produce apparent
quiz corruption when loaded with a newer repacked ROM. That is not a valid
candidate-level regression test.

Use a cold boot or a checkpoint created under the exact candidate being tested.
For a state crossing a runtime ABI change, recreate it whenever possible.

## 13. Maintainer audit

Run the candidate-level checker against a four-side image:

```powershell
python work/tools/audit_quiz_engine.py <candidate.fds>
```

The checker verifies the 39 scored paths, compiled fixed labels, descriptor/page
resolution, variable-width geometry, navigation bounds, relative result tables,
wrong-answer convergence, next-question continuations, final completion state,
prompt semantic identity, full-bank entropy decoding, and recursive dictionary
control safety.

## 14. Evidence boundary

At the static/binary level, the scored quiz subsystem is fully accounted for:
there is no unclassified quiz opcode path, unresolved answer-table branch, or
known data-layout corruption path left in v63.

Static reverse engineering cannot prove analog/runtime observations such as an
emulator-specific PPU timing artifact, a stale external save sidecar, or a
transient display defect that depends on exact frame timing. Final release
certification should still cold-run the quiz sequences in Mesen, including
wrong answers and the TT6C restart behavior.
