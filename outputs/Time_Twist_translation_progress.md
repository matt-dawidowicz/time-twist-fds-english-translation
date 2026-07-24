# Time Twist translation progress

- Total records: **2,052**
- Completed records: **2,052**
- Remaining records: **0**
- Completed banks/components: **TT1A, TT1B, TT2, T22, TT3A, TT3B, TT4, TT5, T25, TT6A, TT6B, TT6C, TT6D, NOV2, NOV4, TITLE, SON-KOUH**
- Current bank: **Complete — cross-bank consistency and QC finished**
- Glossary entries: **67**
- Records requiring gameplay/visual context: **6**
- Records requiring technical expansion/recompression review: **0**

## Source fingerprints

- `Time Twist Japanese-English script comparison.json` — SHA-256 `945B7347A8D5ADE4035F6A9E679449015A9AF7C44C29A4D5BDD904E983975ABB`
- `Time_Twist_full_Japanese_English_translation_review_revised.html` — SHA-256 `E46AA7F982698A59DA7534D9C3C03D7D90DD0BCDA8C01501674B48F925CF8A6D`

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
- NOV2: 9 records complete
- NOV4: 1 records complete
- TITLE: 2 records complete
- SON-KOUH: 1 records complete

## Native compression validation for revised banks

Every patch-safe scenario line passed the ROM character encoder and 24-column display validator. The four materially revised banks also passed native dictionary recompression:

- TT1A: 1618/1669 bytes used; 51 bytes remain.
- TT1B: 4021/4026 bytes used; 5 bytes remain.
- TT3A: 3740/3741 bytes used; 1 byte remain.
- TT6A: 2696/2833 bytes used; 137 bytes remain.

## Records requiring gameplay screenshots or visual verification

- `TT1B/g0/r28` — Punctuation alone permits statement/question readings, but the reply いえ strongly favors a question.
- `TT3A/g2/r7` — The off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` — Spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` — The line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` — The command “Wait” is unlabeled; a gameplay shot is needed to identify the warning voice.
- `NOV2/wait` — Source control preservation conflicts with the existing one-line English display fix.

## Records requiring technical expansion or recompression review

- None.

## Major unresolved terminology decisions

- `レベッカ / Rebecca`: treated as the resistance network's name; the spatial clue still needs visual confirmation.
- `マラドゥル・バラオ・ガラドゥーラ / ガルドゥーラ`: source variants are preserved rather than silently regularized.
- `マイヤー`: retained as **Meyer** for consistency with the current script; **Mayer** remains a possible romanization.
- `カシム`: retained as **Kashim**; **Kasim/Qasim** are possible transliterations.
- `黄泉の国`: localized as **the underworld** in the Greek chapter; **Yomi** is retained as an analysis alternative.

## Remaining genuinely uncertain lines

- `TT1B/g0/r28` (Medium) — Punctuation alone permits statement/question readings, but the reply いえ strongly favors a question.
- `TT3A/g2/r7` (Requires gameplay context) — The off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` (Requires ROM or visual verification) — Spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` (Requires gameplay context) — The line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` (Requires gameplay context) — The command “Wait” is unlabeled; a gameplay shot is needed to identify the warning voice.
- `NOV2/wait` (Requires ROM or visual verification) — Source control preservation conflicts with the existing one-line English display fix.
