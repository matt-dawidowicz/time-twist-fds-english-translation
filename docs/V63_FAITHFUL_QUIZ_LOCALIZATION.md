# v63 faithful quiz localization

v63 builds on the v61 TT3A control-free dictionary repair and adopts a clear
localization rule: **preserve original game content, including questionable
trivia, unless English localization or a technical defect obscures the game's
intended behavior.**

## Retained localization fixes

- TT2: `Citizens` -> `Commoners` for the Third Estate concept.
- TT3A: clarifies the Normandy question as the **Supreme Allied Commander** so
  the intended answer, Eisenhower, is unambiguous in English.
- TT4: makes the `Polis` question singular to match the singular answer.
- TT4: retains the established Parthenon result-routing repair.
- TT3A: retains the v61 control-free dictionary structural repair.

## Restored original-game content

- TT4: restores the translated original olives/grapes/**Fig** crop question.
- TT5: restores the translated original Edison “three great inventions” question
  with **Projector** as the intended answer.
- TT6B: restores the retail result routing where **Fruit of wisdom** is accepted
  and **Fruit of knowledge** is rejected.
- TT6B: **Jehovah** remains unchanged.

These restorations are deliberate. They preserve what the Japanese game says
rather than silently turning the fan translation into a fact-corrected rewrite.

## Binary verification

Candidate:

`Time-Twist-v63-faithful-quiz-localization-candidate.fds`

SHA-256:

`A222078D97EB5B5CB9DC43B59AECC2E5D2B74D1C169E5E107CDF294C28EC464E`

The image remains exactly 262,000 bytes. Relative to v61, only TT2, TT3A, and
TT4 change. TT5 and TT6B are byte-identical to v61.

A static audit covers all **39 scored quiz result tables** (25 regular questions
plus the 14-question TT6C retrospective finale). All 39 route the intended
visible answer to a unique success path under the v63 policy.
