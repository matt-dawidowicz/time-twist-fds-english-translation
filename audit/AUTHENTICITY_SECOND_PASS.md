# Dialogue Authenticity Second Pass

Status: **in progress** on `menu-dialogue-authenticity-audit-20260826`

This pass re-reviews every playable scenario record against the exact Japanese source. It is deliberately stricter than the first workbook pass: a line is not considered finished merely because its basic meaning is understandable.

## Review contract

Every scenario record is checked for:

- semantic accuracy and omitted concrete detail;
- natural American English;
- speaker identity and consistency;
- age, social role, politeness, class, and emotional register;
- regional or stylized Japanese dialect where actually marked;
- recurring verbal tics, stutters, hesitation, insults, and comic timing;
- preservation and ordering of native `{CTRL:n}` events;
- 24-column renderer safety;
- successful bank recompression within the bank's fixed footprint.

The target is the closest American-English **effect**, not a one-to-one substitution of Japanese dialect geography. Mild Japanese regional flavor should remain mild in English; archaizing role-language is not automatically a country accent; deliberate class or regional characterization must not be flattened into neutral prose.

## Current voice decisions

- **Protagonist:** quick contemporary American English; wry, panicky, emotionally transparent. Preserve the softer effect when the source switches from `ore` to `boku`.
- **Girl:** warm, poised, capable of teasing. Feminine-coded Japanese endings are represented through tone rather than exaggerated gendered speech.
- **Devil:** grandiose, sardonic, pompous and selectively old-fashioned. His `washi` / `ja` role-language is not a rural accent.
- **Dr. Simon:** educated, precise, formal, humane, occasionally halting.
- **Nagoya/Owari-coded businessman:** brash regional-businessman cadence. Preserve conspicuous regional flavor without assigning him a literal U.S. hometown.
- **Pierre / Chino / Gordo:** rough, earthy commoner speech and gallows humor; readable adventure dialogue, not faux-Shakespearean English.
- **Lugot / conventional elders:** measured older speech where source role-language supports it; do not make every `washi` speaker rustic.
- **Schmidt:** terse and disciplined, softening after his allegiance is revealed.
- **Belle / George:** plain rural / working-class American speech with dignity. Do not use minstrel-style eye dialect.
- **Joseph:** earnest, worried and fundamentally kind.
- **Mary:** quiet, clear and compassionate.
- **Magi:** dignified ceremonial diction.
- **Camel in TT6B:** Ibaraki / northeastern-Kanto-flavored rural speech, marked by forms including `-dappe`, `ora`, and related colloquial phrasing. American-English target: a **light country twang**, mainly through rhythm and vocabulary, without heavy eye dialect or caricature.

## Technical constraints

The dialogue renderer still has a 24-tile row. A more complete translation may therefore need a compact natural equivalent or a verified control/layout change; "more room" does not mean unlimited line width.

The old public footprint report predates the extended-dictionary TT1A release path and the relocated full-word TT1B architecture. It must not be treated as the current used-byte authority. The physical capacities remain hard invariants; current use is recomputed from the playable translation and current compressor.

Latest independently reproduced measurements before enabling the final 68-entry optimizer pass are:

| Bank / architecture | Used | Capacity | Headroom | Status |
| --- | ---: | ---: | ---: | --- |
| TT1A, fuller authenticity wording + extended dictionary | about 1660 | 1669 | about 9 | Fits; compressor selected 36 useful entries in the independent fit pass |
| TT1B, authenticity rewrite + relocated full-word menus | 3930 | 4026 | 96 | Fits; this predates enabling dictionary-order optimization for 68-entry relocated banks, so the final optimized size may be smaller |

For the remaining banks, the last published optimized figures are still useful as conservative review baselines until each bank is re-reviewed and recompressed:

| Bank | Published used | Capacity | Published headroom |
| --- | ---: | ---: | ---: |
| TT2 | 3834 | 3847 | 13 |
| T22 | 1801 | 1812 | 11 |
| TT3A | 3733 | 3741 | 8 |
| TT3B | 1837 | 1840 | 3 |
| TT4 | 4738 | 4741 | 3 |
| TT5 | 3693 | 3702 | 9 |
| T25 | 2363 | 2374 | 11 |
| TT6A | 2823 | 2833 | 10 |
| TT6B | 2298 | 2336 | 38 |
| TT6C | 3520 | 3536 | 16 |
| TT6D | 323 | 332 | 9 |

The live-fit test now recompresses every bank and enforces **capacity**, rather than requiring equality with stale historical used-byte evidence. TT1A may use the patched English dictionary range through entry 68. Relocated full-word banks likewise use the 68-entry-capable compressor and now opt into the same stronger optimization passes instead of deliberately using greedy-only compression.

A proposed rewrite is not promoted to playable authority until it passes both display-width validation and optimized bank recompression.

## Font / symbol audit

The existing English map supports letters, digits, space, comma, period, hyphen, slash, exclamation point, quotation mark, apostrophe, colon, question mark, and `e` acute. The packed prefix tree itself has no unused branch. Extended values 0-36 are already used for dictionary entries 32-68.

Two extended values are currently unused by the English text map, but they are **not automatically safe glyph slots** because their Japanese/runtime tile identities still matter. In particular, code 63 points at the Japanese literal-space tile, so that tile must remain blank unless the lookup is explicitly remapped.

The symbol set will be demand-driven by the revised script. Likely useful candidates include `$`, `%`, `&`, `+`, `=`, `#`, `@`, parentheses, and semicolon. If only one or two are genuinely needed, use the smallest source-guarded mapping. If many are needed, investigate a secondary symbol escape/table rather than sacrificing the 68-entry dialogue dictionary.

## Bank review status

| Bank | Scenario records | Semantic/voice re-review | Proposed edits | Width checked | Recompressed | Runtime checked |
| --- | ---: | --- | --- | --- | --- | --- |
| TT1A | 35 | **35/35 complete** | **staged** | **checked for changed records** | **fits with extended dictionary** | pending fresh candidate |
| TT1B | 137 | **137/137 complete** | **29 dialogue edits staged** | **checked for changed records** | **fits with relocated full-word architecture** | pending fresh candidate |
| TT2 | 169 | **in progress (~85/169 directly rechecked)** | pending completion | pending | pending | pending |
| T22 | 58 | pending | pending | pending | pending | pending |
| TT3A | 152 | pending | pending | pending | pending | pending |
| TT3B | 58 | pending | pending | pending | pending | pending |
| TT4 | 183 | pending | pending | pending | pending | pending |
| TT5 | 123 | pending | pending | pending | pending | pending |
| T25 | 76 | pending | pending | pending | pending | pending |
| TT6A | 100 | pending | pending | pending | pending | pending |
| TT6B | 94 | pending | pending | pending | pending | pending |
| TT6C | 106 | pending | pending | pending | pending | pending |
| TT6D | 8 | pending | pending | pending | pending | pending |

The scenario counts above sum to **1,299** and are tracked separately from fixed-address menu records. Menu semantic corrections are handled in the parallel menu audit rather than being silently mixed into dialogue changes.

## Confirmed early findings

- `TT1A/g0/r7`: `50 meetoru ijou` includes **"50 meters or more / at least 50 meters"**. Current `Can you swim 50 meters?` loses `ijou`. The playable audit branch now uses `Swim 50 meters or more?`.
- `TT1A/g0/r14`: the source asks whether work cutting into leisure/free time is unwelcome. The earlier storage-tight `Won't trade leisure for work?` was retired once extended-dictionary compression removed the need for that compromise.
- `TT1A/g0/r24-r26`: the fuller personality profiles restore source traits that storage-tight wording had flattened, including principled/hardworking/stubborn characterization, loss of motivation when uninterested, sharp insight, weakness with money, and romantic temperament.
- Several TT1A personality-test records contain spaces chosen to make automatic 24-column wrapping safe. Those spaces must not simply be stripped until an equivalent safe layout is proved.
- `TT1B`: museum exhibit prose, the Elder / Dr. Simon material, church dialogue, and the sermon contain several places where concrete detail or register was compressed away; the current branch stages the reviewed authenticity rewrite.
- `TT2/T22`: Pierre, Chino, Gordo, Lugot, Jeanne, the Bishop, and formal proclamations need a stronger voice/register pass even where the first workbook marked basic meaning as accurate.
- `TT3A/TT3B`: resistance and military dialogue often reads like telegram prose; the source supports more natural speech while retaining terse military characterization where appropriate.
- `TT4`: formal and ceremonial speech must not be flattened into casual English (for example, a respectful `sensei` should not become `Doc!`).
- `TT5/T25`: emancipation and plantation dialogue needs restored emotional/politeness detail while preserving rural/working-class characterization with dignity.
- `TT6B`: the camel's marked rural Japanese voice was flattened to neutral textbook English and needs a consistent light-country localization.
- `TT6C`: the Magi / Devil confrontation lost some explicit time-travel and ceremonial detail.

## Extended-dictionary safety

The English codec maps dictionary references 32-68 onto the otherwise-unused extended-glyph range without changing token width. The release path and optimizer now carry the selected maximum dictionary size through compression and rebuild.

Regression coverage includes both dictionary-order optimization above 31 entries and a synthetic TT1A-style rebuild that deliberately references dictionary entry 33. That test preserves the original fixed-tail offset, reparses the rebuilt bank in extended-dictionary mode, and verifies the high dictionary reference expands correctly. This protects against the two failures that matter most here: silently falling back to a 31-entry assumption or gaining text space by overwriting/moving fixed-address data.

This document is an audit ledger, not itself the playable script. `work/translations/*.json` remains the playable scenario authority.
