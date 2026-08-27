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

The old public footprint report records the native **scenario-region** reservation. It predates the current relocated full-word-bank architecture and must not be treated as the complete capacity for a bank whose menu table is repacked together with dialogue. The physical boundaries remain hard invariants; current use is recomputed from the playable translation and current compressor.

The English NOV2 decoder reclaims 37 otherwise-unused extended-glyph values as dictionary references 32-68. The canonical release path now passes that **68-entry maximum to every playable scenario bank**, including the non-relocated path. The Japanese-source parser remains natively 31-entry-aware because that describes the untouched source format, not an English release limit.

### Relocated full-word capacity

For the 11 page-indexed menu banks, the canonical release owns two verified movable regions inside the same overlay:

1. the normal scenario/group/dictionary reservation; and
2. the prefix from the original fixed-menu base through the first following pointer-addressed structure.

`fixed_record_table_combined_capacity()` proves those boundaries against the locked source at release-build time. ROM-free CI mirrors them with source-derived reclaimed-prefix constants in `time_twist.capacity`.

| Bank | Historical scenario capacity | Reclaimed menu-prefix bytes | Canonical combined capacity |
| --- | ---: | ---: | ---: |
| TT1B | 4026 | 208 | **4234** |
| TT2 | 3847 | 294 | **4141** |
| T22 | 1812 | 127 | **1939** |
| TT3A | 3741 | 428 | **4169** |
| TT3B | 1840 | 87 | **1927** |
| TT4 | 4741 | 446 | **5187** |
| TT5 | 3702 | 499 | **4201** |
| T25 | 2374 | 187 | **2561** |
| TT6A | 2833 | 167 | **3000** |
| TT6B | 2336 | 265 | **2601** |
| TT6C | 3536 | 411 | **3947** |

The combined figures intentionally use the conservative historical scenario capacities already tracked by the public footprint report, plus only the source-verified movable prefix. Some original banks contain a few additional trailing source dictionary bytes that are not counted here; the audit does not need them to make the revised English fit.

### Current independent fit evidence

An independent mirror of the repository's current English encoder, byte-aligned record packing, top-200 greedy dictionary selection, 68-entry reference encoding, full-word menu records, and structural pointer costs gives the following conservative baselines for the newly revised France banks:

| Bank | Current fuller script + menu | Canonical capacity | Minimum proven headroom | Status |
| --- | ---: | ---: | ---: | --- |
| TT2 | **4092** | **4141** | **49 bytes** | Fits before beam/order optimization |
| T22 | **1913** | **1939** | **26 bytes** | Fits before beam/order optimization |

These are deliberately conservative rather than claimed final optimizer outputs. `compress_english_groups(optimize=True)` always includes the greedy result among its candidates and chooses the smallest valid exact result, so the final optimized footprint cannot be larger than these baselines. GitHub Actions remains the authoritative repository-level confirmation and will print the exact selected sizes once the queued run executes.

For non-relocated banks, the historical scenario capacity remains the hard capacity. TT1A's fuller authenticity wording independently fits inside 1669 bytes with the extended dictionary. TT6D now receives the same 68-entry English maximum as every other playable bank.

A proposed rewrite is not promoted to playable authority until it passes display-width validation and bank-fit validation; runtime promotion remains a separate gate.

## Font / symbol audit

The existing English map supports letters, digits, space, comma, period, hyphen, slash, exclamation point, quotation mark, apostrophe, colon, question mark, and `e` acute. The packed prefix tree itself has no unused branch. Extended values 0-36 are used by the patched English decoder for dictionary entries 32-68.

Two extended values remain unused by the visible English character map, but they are **not automatically safe glyph slots** because their Japanese/runtime tile identities still matter. In particular, code 63 points at the Japanese literal-space tile, so that tile must remain blank unless the lookup is explicitly remapped.

The symbol set will be demand-driven by the revised script. Likely useful candidates include `$`, `%`, `&`, `+`, `=`, `#`, `@`, parentheses, and semicolon. If only one or two are genuinely needed, use the smallest source-guarded mapping. If many are needed, investigate a secondary symbol escape/table rather than sacrificing dialogue dictionary space.

## Bank review status

| Bank | Scenario records | Semantic/voice re-review | Proposed edits | Width checked | Recompressed | Runtime checked |
| --- | ---: | --- | --- | --- | --- | --- |
| TT1A | 35 | **35/35 complete** | **staged** | **checked for changed records** | **fits with extended dictionary** | pending fresh candidate |
| TT1B | 137 | **137/137 complete** | **29 dialogue edits staged** | **checked for changed records** | **fits with relocated full-word architecture** | pending fresh candidate |
| TT2 | 169 | **169/169 complete** | **25 dialogue edits staged** | **169/169 width-safe** | **independent greedy fit: <=4092/4141** | pending fresh candidate |
| T22 | 58 | **58/58 complete** | **8 dialogue edits staged** | **58/58 width-safe** | **independent greedy fit: <=1913/1939** | pending fresh candidate |
| TT3A | 152 | in progress | pending completion | pending | pending | pending |
| TT3B | 58 | pending | pending | pending | pending | pending |
| TT4 | 183 | pending | pending | pending | pending | pending |
| TT5 | 123 | pending | pending | pending | pending | pending |
| T25 | 76 | pending | pending | pending | pending | pending |
| TT6A | 100 | pending | pending | pending | pending | pending |
| TT6B | 94 | pending | pending | pending | pending | pending |
| TT6C | 106 | pending | pending | pending | pending | pending |
| TT6D | 8 | pending | pending | pending | pending | pending |

The scenario counts above sum to **1,299** and are tracked separately from fixed-address menu records. Menu semantic corrections are handled in the parallel menu audit rather than being silently mixed into dialogue changes.

## Confirmed findings

- `TT1A/g0/r7`: `50 meetoru ijou` includes **"50 meters or more / at least 50 meters"**. The playable audit branch uses `Swim 50 meters or more?`.
- `TT1A/g0/r14`: the source asks whether work cutting into leisure/free time is unwelcome. The earlier storage-tight wording was retired once extended-dictionary compression removed the need for that compromise.
- `TT1A/g0/r24-r26`: the fuller personality profiles restore source traits that storage-tight wording had flattened, including principled/hardworking/stubborn characterization, loss of motivation when uninterested, sharp insight, weakness with money, and romantic temperament.
- Several TT1A personality-test records contain spaces chosen to make automatic 24-column wrapping safe. Those spaces must not simply be stripped until an equivalent safe layout is proved.
- `TT1B`: museum exhibit prose, the Elder / Dr. Simon material, church dialogue, and the sermon contain several places where concrete detail or register was compressed away; the current branch stages the reviewed authenticity rewrite.
- `TT2/g2/r28`: Chino's source stutter and Pierre's drunken hiccup were absent from the first English pass; both are restored.
- `TT2/g2/r30`: the source explicitly describes **tears and snot**, not tears alone.
- `TT2/g3/r10`: Lugot explicitly calls Jeanne **his granddaughter**.
- `TT2/g3/r14`: church personnel may **come and go freely** at the jail, and Pierre directs Chino to Gordo for the monk's robe; the earlier wording flattened both details.
- `TT2/g3/r26`: Lugot says Jeanne has **just turned sixteen**, not merely that she is sixteen.
- `TT2/g4/r2`: the townsman worries about what will happen to **the country**, not merely "us"; the branch localizes the referent naturally as France.
- `TT2/g4/r14`: the jailer explicitly says he understands **how the protagonist feels** before asking him to return.
- `TT2/g4/r20`: the imprisoned woman's scar is specifically on her **leg** and came from a fall.
- `TT2/g4/r27`: Jeanne is suspended by a **thick rope**; the adjective was omitted previously.
- `TT2/g5/r2`: Jeanne says to **flee/escape**, not merely "go."
- `TT2/g5/r3`: the Bishop says the order came from **someone he reveres**, explains that Jeanne would become troublesome if left alive, and says he continued the witch hunts expecting eventually to encounter her; the earlier compressed English reduced this to generic "my lord" and "I hunted witches to find you."
- `T22/g0/r3`: the Baron looks at his wife **affectionately/fondly**, not merely neutrally.
- `T22/g0/r14`: the jailer's source explicitly says the prisoner is **not to be let outside** on the Bishop's orders.
- `T22/g1/r7`: the formal accusation says Jeanne received the **Devil's baptism** and became captive to vile desire before the Church condemns her; the earlier English flattened this into the awkward `Devil's slave to desire`.
- `T22/g1/r14`: `じわじわと` adds the idea of **slow, drawn-out torment**, which the earlier generic `They will torture her` omitted.
- `T22/g1/r15`: as in TT2, `目を真っ赤に泣き腫らしている` describes eyes red/swollen from crying, not merely red.
- `T22/g1/r18`: the Bishop's panicked **stutter** and command to **let go of him** were omitted from the first English pass.
- `T22/g1/r20`: Jeanne explicitly says that while on the cross she heard **God's message/revelation**; the prior `upon that cross, I heard` left the object unstated.
- `T22/g1/r21`: the closing reflection calls Jeanne a **beautiful maiden** as well as France's savior; the branch restores that praise compactly as `France's fair savior...`.
- `TT3A/TT3B`: resistance and military dialogue often reads like telegram prose; the source supports more natural speech while retaining terse military characterization where appropriate.
- `TT4`: formal and ceremonial speech must not be flattened into casual English (for example, a respectful `sensei` should not become `Doc!`).
- `TT5/T25`: emancipation and plantation dialogue needs restored emotional/politeness detail while preserving rural/working-class characterization with dignity.
- `TT6B`: the camel's marked rural Japanese voice was flattened to neutral textbook English and needs a consistent light-country localization.
- `TT6C`: the Magi / Devil confrontation lost some explicit time-travel and ceremonial detail.

The TT2 playable-script revisions were committed as `f3f4879d1dccbded7c141e364e94f2b36c6e3e54`; the T22 revisions were committed as `68a6c18a074fa687bbee6b4bea296ab2a2aefc80`. Every record in both current maps has been rechecked for the 24-column control-delimited display contract: TT2 is 169/169 safe and T22 is 58/58 safe.

## Extended-dictionary safety

The English codec maps dictionary references 32-68 onto otherwise-unused extended-glyph values without changing token width. `patched_nov2_ui()` installs that decoder change globally, so every scenario overlay loaded by the English game may use the extended references.

The canonical release path now passes `EXTENDED_DICTIONARY_ENTRY_COUNT` for **all 13 playable scenario banks**, not only TT1A or the relocated-menu banks. The live-fit model does the same. A dedicated TT6D release-policy regression deliberately supplies a 32-entry dictionary on the non-relocated path and checks that both compression and rebuild receive the 68-entry maximum.

Regression coverage also includes dictionary-order optimization above 31 entries and a synthetic rebuild that deliberately references dictionary entry 33 while proving the fixed-address tail remains byte-for-byte unmoved. These tests protect against silently reintroducing the old English ceiling or gaining text space by overwriting/moving fixed-address data.

Native source parsing intentionally remains native: an untouched Japanese bank still describes the original 31-entry encoding. Removing that source-format fact would weaken validation rather than increase playable English capacity.

This document is an audit ledger, not itself the playable script. `work/translations/*.json` remains the playable scenario authority.
