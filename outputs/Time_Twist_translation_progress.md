# Time Twist translation progress

- Total records: **2,058**
- Completed records: **2,058**
- Remaining records: **0**
- Completed banks/components: **TT1A, TT1B, TT2, T22, TT3A, TT3B, TT4, TT5, T25, TT6A, TT6B, TT6C, TT6D, NOV2, NOV4, TITLE, SON-KOUH**
- Current bank: **Complete — cross-bank consistency and QC finished**
- Glossary entries: **67**
- Records requiring gameplay/visual context: **4**
- Records requiring technical expansion/recompression review: **0**

## Source fingerprints

- `Time Twist Japanese-English script comparison.json` — LF-normalized SHA-256 `CEBABD9C9603E8A7AFAED11C36BC4B63533D6BF72E7C95C43BDB67CBEF82986C`
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
- NOV4: 1 records complete
- TITLE: 2 records complete
- SON-KOUH: 1 records complete

## Current conservative fit checks

Recomputed from the current playable scenario maps and configured full-word menus using the 68-entry greedy baseline. Measurements include structural pointers and the recovered movable menu reservation where applicable. All 13 banks fit this public model:

- TT1A: 1664/1669 bytes used; 5 bytes remain.
- TT1B: 3911/4234 bytes used; 323 bytes remain.
- TT2: 4044/4141 bytes used; 97 bytes remain.
- T22: 1896/1939 bytes used; 43 bytes remain.
- TT3A: 4120/4169 bytes used; 49 bytes remain.
- TT3B: 1875/1927 bytes used; 52 bytes remain.
- TT4: 5140/5187 bytes used; 47 bytes remain.
- TT5: 4121/4201 bytes used; 80 bytes remain.
- T25: 2422/2561 bytes used; 139 bytes remain.
- TT6A: 2779/3000 bytes used; 221 bytes remain.
- TT6B: 2485/2601 bytes used; 116 bytes remain.
- TT6C: 3839/3947 bytes used; 108 bytes remain.
- TT6D: 317/332 bytes used; 15 bytes remain.

Actual release usage, including any optimizer fallback, must come from a fresh ROM-backed candidate manifest. These conservative measurements do not certify a built image or runtime behavior.

## Records requiring gameplay screenshots or visual verification

- `TT3A/g2/r7` — The off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` — Spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` — The line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` — The command “Wait” is unlabeled; a gameplay shot is needed to identify the warning voice.

## Records requiring technical expansion or recompression review

- None.

## Major unresolved terminology decisions

- `レベッカ / Rebecca`: treated as the resistance network's name; the spatial clue still needs visual confirmation.
- `マラドゥル・バラオ・ガラドゥーラ / ガルドゥーラ`: source variants are preserved rather than silently regularized.
- `マイヤー`: retained as **Meyer** for consistency with the current script; **Mayer** remains a possible romanization.
- `カシム`: retained as **Kashim**; **Kasim/Qasim** are possible transliterations.
- `黄泉の国`: localized as **the underworld** in the Greek chapter; **Yomi** is retained as an analysis alternative.

## Remaining genuinely uncertain lines

- `TT3A/g2/r7` (Requires gameplay context) — The off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` (Requires ROM or visual verification) — Spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` (Requires gameplay context) — The line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` (Requires gameplay context) — The command “Wait” is unlabeled; a gameplay shot is needed to identify the warning voice.
