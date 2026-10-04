# v62 quiz correction pass

> **Superseded by v63.** v62 experimentally corrected several original-game trivia items. v63 restores those source-faithful premises/answers and adopts the preservation-oriented localization policy documented in the README.

v62 builds on the v61 TT3A control-free dictionary candidate and corrects the
remaining reviewed quiz wording/content issues without changing the requested
TT6B label **Jehovah**.

## Changes

- TT2: `Citizens` -> `Commoners` for the Third Estate answer.
- TT3A: makes Eisenhower unambiguous by asking for the Supreme Allied Commander
  for the Normandy invasion.
- TT4: changes the `Polis` prompt to singular and replaces the dubious
  "third major crop" premise with a question about prized/dried Athenian figs.
  The already-fixed Parthenon routing remains intact.
- TT5: replaces the dubious "three great Edison inventions" premise with a
  Vitascope/projector question while retaining `Projector` as the answer.
- TT6B: preserves both translated choices `Fruit of wisdom` and
  `Fruit of knowledge`, but swaps the result table so **Fruit of knowledge**
  reaches success. `Jehovah` is unchanged.

## Binary verification

Candidate:

`Time-Twist-v62-quiz-corrections-candidate.fds`

SHA-256:

`6A3058F1D159AB7B401FC1489D1D047793C9F757C2DBF3E7782C6E4258379D46`

The image remains exactly 262,000 bytes. Only TT2, TT3A, TT4, TT5, and TT6B
payloads differ from v61.

An exhaustive static result-table audit checks all **39 scored quiz questions**:
25 regular historical questions plus the 14-question TT6C retrospective finale.
Every one routes its intended visible answer to the unique success path.

The v61 TT3A control-free dictionary remains intact.
