# TT1A Fortune Teller logic

This document records the recovered mechanics of the Fortune-Telling Service
Center sequence in TT1A. It separates what the player is asked from what the
game actually stores and uses.

## Summary

The sequence looks like a personality test, but it is not scored from the
answers.

- **Blood type determines the displayed personality result.**
- **Birth month is not stored for later use.**
- **Yes/No answers only choose which statement appears next.**
- **The final Yes/No press on the terminal statements is accepted by the UI but
  does not alter the result.**
- **No Fortune Teller state survives into the next gameplay scene.**

The questionnaire is therefore a branching presentation layer around a
blood-type-based result selector.

## Inputs and result selection

The blood-type selector is the only input that seeds the temporary event-flag
state used by the final personality selector.

| Blood type | Temporary flag pattern | Result record | Result theme |
| --- | --- | --- | --- |
| A | flags 2, 3, 4 | `TT1A/g0/r24` | cautious/methodical scholar |
| B | flags 3, 4 | `TT1A/g0/r25` | upbeat/curious journalist |
| O | flag 4 | `TT1A/g0/r26` | earnest/passionate politician |
| AB | no flags | `TT1A/g0/r23` | cool-headed/intellectual |

**VERIFIED.** The native blood menu opens at CPU `$A2EA`; the relative
four-way dispatch begins at `$A2EC`. The branch entries at
`$A2F1/$A2F3/$A2F5/$A2F7` deliberately fall through one another, producing
the cumulative flag encoding above. The final result predicate begins at
`$A372`.

## Birth month

The first month menu presents January through June plus a `Jul-Dec` entry.
Choosing `Jul-Dec` opens a second menu for July through December.

**VERIFIED.** All month choices converge at `$A305`, the personality-test
introduction. The month selector does not set a result flag, store a month
value for the personality selector, or choose a different first statement.

All 48 blood-type/month combinations therefore enter the same statement graph.
Month has no effect on the displayed profile.

## Statement-routing graph

The current English records are declarative statements. The Yes/No choice after
each statement controls only the next statement.

| ID | Record | YES -> | NO -> |
| --- | --- | --- | --- |
| S1 | r6 | S4 | S2 |
| S2 | r7 | S5 | S3 |
| S3 | r8 | S6 | S5 |
| S4 | r9 | S7 | S3 |
| S5 | r10 | S8 | S9 |
| S6 | r11 | S5 | S9 |
| S7 | r12 | S6 | S11 |
| S8 | r13 | S12 | S9 |
| S9 | r14 | S13 | S10 |
| S10 | r15 | S14 | S15 |
| S11 | r16 | S15 | S3 |
| S12 | r17 | Finish | Finish |
| S13 | r18 | Finish | Finish |
| S14 | r19 | Finish | Finish |
| S15 | r20 | Finish | Finish |

Every route begins at S1.

Graph properties:

- 69 distinct statement sequences reach a terminal statement;
- 138 complete answer sequences exist when the terminal Yes/No press is counted;
- shortest route: 5 statements;
- longest route: 11 statements.

Examples:

```text
Always Yes:
S1 -> S4 -> S7 -> S6 -> S5 -> S8 -> S12 -> RESULT

Always No:
S1 -> S2 -> S3 -> S5 -> S9 -> S10 -> S15 -> RESULT

One shortest route:
S1(Y) -> S4(Y) -> S7(N) -> S11(Y) -> S15 -> RESULT

One longest route:
S1(Y) -> S4(Y) -> S7(N) -> S11(N) -> S3(Y) -> S6(Y)
-> S5(Y) -> S8(N) -> S9(N) -> S10(Y) -> S14 -> RESULT
```

## Why the answers do not affect the profile

The answer-routing bytecode performs menu selection and relative dispatch but
does not mutate the temporary personality-result flag pattern. The personality
selector later tests only the blood-type-seeded flags.

The terminal statements make this especially clear: the game still opens the
Yes/No UI, but both choices converge immediately on the same result-selection
path.

Thus the answer tree changes the player's *experience of the questionnaire*,
not the profile computation.

## Downstream lifetime

The personality flags are scene-local.

- TT1A transitions onward at `$A44F` with `E0 $42`.
- NOV2 fresh-scene initialization at `$6957` calls the event-flag clear at
  `$9C0B`.
- `$9C0B` zeroes the complete `$0480-$049F` event-flag bank before the new
  scene script begins.
- Month was never stored and answer choices never created a persistent
  personality variable.

Therefore the Fortune Teller does **not** affect later dialogue, puzzles,
inventory, routes, Part 2, or the ending.

## Practical consequence for playtesting

A tester using **A + May** will always receive the A profile
(`TT1A/g0/r24`) regardless of the Yes/No route. May itself has no mechanical
effect.

When testing this sequence, treat failures as one of four separate surfaces:

1. blood-type result mapping;
2. month-menu presentation;
3. statement-routing correctness;
4. text/layout/menu presentation.

Do not infer a hidden personality-scoring bug merely because different answer
routes still produce the same profile; that is the recovered native behavior.

## Evidence boundary

The control flow, cumulative blood-type flags, month convergence, result
selector, and fresh-scene flag clear are **VERIFIED** from the recovered
Zenpen/NOV2 program logic. The description of the questionnaire as presentation
or misdirection is a design interpretation, not an additional engine fact.
