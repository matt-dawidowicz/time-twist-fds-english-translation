# Time Twist translation progress

- Total records: **2,058**
- Completed records: **2,058**
- Remaining records: **0**
- Completed banks/components: **TT1A, TT1B, TT2, T22, TT3A, TT3B, TT4, TT5, T25, TT6A, TT6B, TT6C, TT6D, NOV2, NOV4, TITLE, SON-KOUH**
- Current phase: **Final cross-bank editorial freeze complete; post-freeze compression/build validation pending**
- Glossary entries: **67**
- Records requiring gameplay/visual context: **6**
- Source records requiring technical expansion: **0**

## Source fingerprints

- `Time Twist Japanese-English script comparison.json` — SHA-256 `825E5FCF3506E6AE673D36535C19FDBD17251EAB33FFECD9B275EF506B2568D9`
- Diagnostic review: not supplied (neutral diagnostics used)

## Bank coverage

- TT1A: 54 records complete
- TT1B: 190 records complete
- TT2: 239 records complete
- T22: 91 records complete
- TT3A: 247 records complete
- TT3B: 79 records complete
- TT4: 280 records complete
- TT5: 236 records complete
- T25: 118 records complete
- TT6A: 141 records complete
- TT6B: 156 records complete
- TT6C: 200 records complete
- TT6D: 8 records complete
- NOV2: 15 records complete
- NOV4: 1 record complete
- TITLE: 2 records complete
- SON-KOUH: 1 record complete

## Final editorial freeze

The voice/prose pass now covers every scenario bank from TT1A through TT6D. A final cross-bank consistency pass then reconciled recurring terminology and callbacks and retrofitted the early banks to the same practical display policy established by runtime review in later chapters.

Final editorial policy:

- preserve exact control-event order;
- target no more than **23 visible characters per control-delimited segment** for scenario text;
- preserve source-explicit register, stutters, profanity, brutality, dated language, and historical ugliness without sanitizing or escalating it;
- use **God's child** consistently for recurring `かみのこ` where the same story concept is intended;
- use **Demon-Sealing Jar** consistently for `まふうじのつぼ`;
- preserve genuine source variants of `Maradul Barao Garadura / Galdura` rather than normalizing them;
- preserve deliberate callback wording when the Japanese itself repeats a line.

The final freeze specifically brought TT1A, TT1B, TT2, T22, and TT3A from the older nominal 24-column editorial ceiling to the stricter 23-cell practical target. TT3B and all later scenario-bank voice/prose passes were already authored under that stricter policy.

## Compression status after the final freeze

The optimized dictionary-compression figures previously recorded in this file were produced **before** the completed voice/prose/final-consistency branch and therefore do **not** prove that the current branch fits. They are intentionally no longer presented as current validation results.

All scenario maps changed during the editorial pass. Post-freeze fit must therefore be re-established with the repository's canonical compression/release workflow before release approval. Visible-character savings and the 23-cell display checks are useful editorial evidence, but they are not packed-fit proof.

Required next gates include the public/static checks, private integration checks where the legal fixture overlay is available, and a fresh candidate build from the locked Japanese inputs. The reviewed candidate must then pass the runtime playtest matrix before promotion.

## Records requiring gameplay screenshots or visual verification

These remain deliberately unresolved by the editorial freeze because their uncertainty depends on staging, rendering, or spatial presentation rather than Japanese prose alone:

- `TT1B/g0/r28` — punctuation alone permits statement/question readings, but the reply いえ strongly favors a question.
- `TT3A/g2/r7` — the off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` — spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` — the line may be Hitler himself or the Devil speaking through him; visual staging determines the displayed identity.
- `TT4/g4/r14` — the command `Wait` is unlabeled; a gameplay shot is needed to identify the warning voice.
- `NOV2/wait` — source control preservation conflicts with the existing one-line English display fix.

## Major terminology decisions

- `レベッカ / Rebecca`: treated as the resistance network's name; the spatial clue still needs visual confirmation.
- `マラドゥル・バラオ・ガラドゥーラ / ガルドゥーラ`: source variants are preserved rather than silently regularized.
- `マイヤー`: retained as **Meyer** for consistency with the current script; **Mayer** remains a possible romanization.
- `カシム`: retained as **Kashim**; **Kasim/Qasim** are possible transliterations.
- `黄泉の国`: localized as **the underworld** in the Greek chapter; **Yomi** is retained as an analysis alternative.
- `魔封じの壺`: **Demon-Sealing Jar**.
- `かみのこ`: **God's child** where it denotes the recurring theological/story concept used by the finale.

## Remaining genuinely uncertain lines

- `TT1B/g0/r28` (Medium) — punctuation alone permits statement/question readings, but the reply いえ strongly favors a question.
- `TT3A/g2/r7` (Requires gameplay context) — the off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` (Requires ROM or visual verification) — spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` (Requires gameplay context) — the line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` (Requires gameplay context) — the command `Wait` is unlabeled; a gameplay shot is needed to identify the warning voice.
- `NOV2/wait` (Requires ROM or visual verification) — source control preservation conflicts with the existing one-line English display fix.
