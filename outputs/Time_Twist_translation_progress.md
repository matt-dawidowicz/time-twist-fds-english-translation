# Time Twist translation progress

- Total records: **2,058**
- Completed records: **2,058**
- Remaining records: **0**
- Completed banks/components: **TT1A, TT1B, TT2, T22, TT3A, TT3B, TT4, TT5, T25, TT6A, TT6B, TT6C, TT6D, NOV2, NOV4, TITLE, SON-KOUH**
- Current bank: **Complete — cross-bank consistency and QC finished**
- Glossary entries: **67**
- Records requiring gameplay/visual context: **5**
- Records requiring technical expansion/recompression review: **0**

## Source fingerprints

- `Time Twist Japanese-English script comparison.json` — SHA-256 `F23E7118B35C28579FBC67356E9DDB209ACE3C9614115DAD5DBA0E4AB27A0103`
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

## Native compression validation

Every patch-safe scenario line passed the ROM character encoder and 24-column display validator. All 13 complete public scenario maps also passed exact optimized dictionary recompression against their recorded fixed-tail capacities. A private ROM-backed candidate build and playtest remain separate gates:

- TT1A: 1656/1669 bytes used; 13 bytes remain.
- TT1B: 4022/4026 bytes used; 4 bytes remain.
- TT2: 3834/3847 bytes used; 13 bytes remain.
- T22: 1801/1812 bytes used; 11 bytes remain.
- TT3A: 3733/3741 bytes used; 8 bytes remain.
- TT3B: 1837/1840 bytes used; 3 bytes remain.
- TT4: 4738/4741 bytes used; 3 bytes remain.
- TT5: 3693/3702 bytes used; 9 bytes remain.
- T25: 2363/2374 bytes used; 11 bytes remain.
- TT6A: 2823/2833 bytes used; 10 bytes remain.
- TT6B: 2298/2336 bytes used; 38 bytes remain.
- TT6C: 3520/3536 bytes used; 16 bytes remain.
- TT6D: 323/332 bytes used; 9 bytes remain.

## Records requiring gameplay screenshots or visual verification

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

- `TT3A/g2/r7` (Requires gameplay context) — The off-screen voice is probably an ally, but the exact speaker needs the surrounding gameplay shot.
- `TT3A/g2/r30` (Requires ROM or visual verification) — Spatial order of the torn-note characters needs a gameplay screenshot or nametable capture.
- `TT3B/g0/r24` (Requires gameplay context) — The line may be Hitler himself or the Devil speaking through him; the visual staging determines the displayed identity.
- `TT4/g4/r14` (Requires gameplay context) — The command “Wait” is unlabeled; a gameplay shot is needed to identify the warning voice.
- `NOV2/wait` (Requires ROM or visual verification) — Source control preservation conflicts with the existing one-line English display fix.
