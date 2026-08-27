# Dialogue Authenticity Second Pass

Status: **semantic/voice review complete; CI and fresh runtime validation pending** on `menu-dialogue-authenticity-audit-20260826`

This pass re-reviewed all **1,299 playable scenario records** against the exact Japanese source. It is deliberately stricter than the first workbook pass: a line is not considered finished merely because its basic meaning is understandable.

The completed pass stages **129 scenario-record edits** across all 13 playable scenario banks, plus the parallel fixed-menu correction `Call` -> `Intercom` in TT1B. The edits restore omitted concrete detail, relationship/status information, puzzle rules, stutters and hesitations, rough or ceremonial register, plot logic, and several outright referent/pronoun errors. They are not a blanket prose rewrite.

## Review contract

Every scenario record was checked for:

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
- **Cow in TT6B:** intentionally rustic and rambling. Preserve that comic contrast without turning it into a named American regional caricature.

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

The combined figures intentionally use the conservative historical scenario capacities already tracked by the public footprint report, plus only the source-verified movable prefix. Some original banks contain a few additional trailing source dictionary bytes that are not counted here; the audit does not rely on them.

### Current independent fit evidence

An independent mirror of the repository's English encoder, byte-aligned record packing, top-200 greedy dictionary selection, 68-entry reference encoding, full-word menu records, and structural pointer costs produced these conservative baselines for the revised France banks:

| Bank | Fuller script + menu | Canonical capacity | Minimum proven headroom | Status |
| --- | ---: | ---: | ---: | --- |
| TT2 | **4092** | **4141** | **49 bytes** | Fits before beam/order optimization |
| T22 | **1913** | **1939** | **26 bytes** | Fits before beam/order optimization |

These are deliberately conservative rather than claimed final optimizer outputs. `compress_english_groups(optimize=True)` includes the greedy result among its candidates and chooses the smallest valid exact result, so the final optimized footprint cannot be larger than those baselines.

For non-relocated banks, the historical scenario capacity remains the hard capacity. TT1A's fuller authenticity wording independently fit inside 1669 bytes with the extended dictionary. TT6D now receives the same 68-entry English maximum as every other playable bank.

The final full-game script has **not yet been promoted on fit evidence**. GitHub Actions run #281 for the current semantic-review head was queued when this ledger was updated. CI remains the authoritative repository-level control/width/encoding/recompression check, and a fresh emulator candidate remains a separate runtime gate.

## Font / symbol audit

The existing English map supports letters, digits, space, comma, period, hyphen, slash, exclamation point, quotation mark, apostrophe, colon, question mark, and `e` acute. The packed prefix tree itself has no unused branch. Extended values 0-36 are used by the patched English decoder for dictionary entries 32-68.

Two extended values remain unused by the visible English character map, but they are **not automatically safe glyph slots** because their Japanese/runtime tile identities still matter. In particular, code 63 points at the Japanese literal-space tile, so that tile must remain blank unless the lookup is explicitly remapped.

The completed second-pass script did not require inventing a new visible symbol mapping. For example, TT5 describes a bundle of hundred-dollar bills as `A bundle of 100s.` rather than adding an unnecessary `$` glyph solely for that line.

## Bank review status

| Bank | Scenario records | Semantic/voice re-review | Staged scenario edits | Width/control status | Recompression | Runtime |
| --- | ---: | --- | ---: | --- | --- | --- |
| TT1A | 35 | **35/35 complete** | **6** | changed records constrained to display contract | independent fit with extended dictionary | pending fresh candidate |
| TT1B | 137 | **137/137 complete** | **29** | changed records constrained to display contract | existing relocated-full-word fit evidence; final CI pending | pending fresh candidate |
| TT2 | 169 | **169/169 complete** | **25** | **169/169 previously width-safe** | **independent greedy <=4092/4141** | pending fresh candidate |
| T22 | 58 | **58/58 complete** | **8** | **58/58 previously width-safe** | **independent greedy <=1913/1939** | pending fresh candidate |
| TT3A | 152 | **152/152 complete** | **12** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT3B | 58 | **58/58 complete** | **4** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT4 | 183 | **183/183 complete** | **7** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT5 | 123 | **123/123 complete** | **9** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| T25 | 76 | **76/76 complete** | **4** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT6A | 100 | **100/100 complete** | **2** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT6B | 94 | **94/94 complete** | **7** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT6C | 106 | **106/106 complete** | **13** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |
| TT6D | 8 | **8/8 complete** | **3** | changed records constrained to display contract | **final CI pending** | pending fresh candidate |

The scenario counts sum to **1,299** and are tracked separately from fixed-address menu records. The 13 staged edit counts sum to **129 scenario records**. Menu semantic corrections are handled in the parallel menu audit rather than silently mixed into dialogue counts.

## Confirmed findings by bank

### TT1A - personality test / 1995 prologue

Edited records: `g0/r7`, `g0/r14`, `g0/r18`, `g0/r24`, `g0/r25`, `g0/r26`.

- `50 meetoru ijou` explicitly includes **50 meters or more / at least 50 meters**.
- The work/leisure proposition means not wanting work to cut into leisure time, rather than the broader `put play first`.
- `-tai` in the social-help proposition expresses **wanting** to help society, not a prediction that the player eventually will.
- The personality profiles restore source traits compressed away in the first pass: principled/hardworking/stubborn characterization, sudden loss of motivation when not in the mood, sharp insight/inspiration, weakness with money, and dreams of **dramatic** romance.

### TT1B - Devil Museum / possession / Dr. Simon

29 scenario edits plus fixed-menu `Call` -> `Intercom`.

- Exhibit descriptions restore omitted Europe/period, secret-society, sacrificial-victim, and engraved-spell detail.
- The Devil's long captivity, forceful body theft, and protagonist stutters are preserved more fully.
- `fukumimi` is specifically lucky/fortunate **earlobes**, not generic `ears`.
- The heavily Nagoya/Owari-coded businessman retains rough regional-businessman force without being assigned a fake U.S. hometown; `do-inaka` is stronger than neutral `rural` and `leisure center` is the explicit source noun.
- The Elder's Dr. Simon material restores the completed machine / self-warp rumor, late-life loss of sight, and accidental oversharing cadence.
- Church material restores the father's effort collecting exhibits, explicit sins in the prayer, hymn/sermon distinctions, gentle smile, courage against the Devil, and the protagonist's missing stutter.
- `Intercom` is the actual object; the earlier `Call` label was an abbreviation that is no longer required by the full-word menu architecture.

### TT2 - 1428 France / Jeanne d'Arc

25 scenario edits.

- Chino's source stutters and Pierre's drunken hiccups/exclamations are restored.
- The source explicitly describes **tears and snot**.
- Lugot explicitly calls Jeanne **his granddaughter**.
- Church personnel may **come and go freely** at the jail, and Pierre directs Chino to Gordo for the monk's robe.
- Jeanne has **just turned sixteen**, not merely `is sixteen`.
- The town conversation worries about **France/the country**, not generic `us`.
- The jailer explicitly understands **how the protagonist feels**.
- The prisoner's scar is specifically on her **leg** and came from a fall.
- Jeanne is held by **thick rope** and is described emotionally as still just a child.
- Jeanne says to **flee/escape**, not merely `go`.
- The Bishop's explanation restores the revered source of his order, the concern that Jeanne will cause future trouble, and his expectation that the witch hunts would eventually uncover her.

### T22 - France continuation

8 scenario edits.

- The Baron looks at his wife **fondly/affectionately**.
- The Bishop's order explicitly prevents the prisoner from being let outside.
- Jeanne's formal accusation explicitly invokes **the Devil's baptism** and depravity/vile desire.
- `jiwajiwa` adds **slow, drawn-out torment**.
- Red eyes are swollen/puffy from crying, not merely red.
- The Bishop's panic includes a stutter and an explicit demand to **let go**.
- Jeanne says she heard **God's message/revelation** while on the cross.
- The closing narration praises Jeanne as a fair/beautiful savior of France.

### TT3A - POW camp / resistance escape

Edited records: `g0/r19`, `g1/r17`, `g1/r19`, `g1/r21`, `g1/r22`, `g2/r29`, `g3/r2`, `g3/r3`, `g3/r7`, `g3/r26`, `g3/r27`, `g4/r20`.

- The hidden contact explicitly says the resistance will **make the escape arrangements**.
- The star medal's text is unreadable because of rust.
- Nick explicitly describes an **assassination plot against Hitler**.
- `Rebecca` is an **escape/resistance organization code**, not a woman. Lines that treated Rebecca as a person were corrected.
- The password `kutabare Hitler` is intentionally harsh and is restored as **`Drop dead, Hitler!`** throughout the sequence.
- Simon says a **child** delivered the note and that an unknown man sent it.
- The watermill trap character explicitly reveals **`I'm Gestapo!`** rather than the flatter `I am Gestapo`.

### TT3B - Germany continuation / border

Edited records: `g0/r22`, `g1/r15`, `g1/r17`, `g1/r23`.

- The resistance password remains **`Drop dead, Hitler!`** for continuity with TT3A.
- Simon's and Cougar's source stutters are restored.
- The Devil explicitly orders Hitler to continue doing evil **until the pact expires**.
- The Devil tells Hitler to remember his exact death date: **April 30, 1945**.

### TT4 - Ancient Athens / Greek underworld

Edited records: `g0/r12`, `g0/r13`, `g1/r14`, `g1/r15`, `g2/r14`, `g3/r24`, `g4/r19`.

- A major referent error was corrected: Athena's `ano ko` is the **child Alexander**, not an unidentified girl. The playable English now uses **him/he**.
- Merchant, soldier, Nicras/protagonist hesitation and stutters are restored where explicitly marked.
- Aristotle's self-introduction is made grammatical while preserving his formal identity.
- A missing `Man:` speaker label is restored.
- Greek/underworld terminology and deliberately odd source riddles were otherwise left alone rather than normalized into a different mythological system.

### TT5 - 1864 Atlanta / emancipation / plantation

Edited records: `g0/r3`, `g0/r7`, `g0/r16`, `g1/r0`, `g2/r10`, `g2/r23`, `g3/r13`, `g3/r16`, `g3/r25`.

- Meyer says they may leave **tomorrow**, not specifically tomorrow morning.
- The racist attacker's threat is restored closer to the source: while men like him remain, George will not be allowed to live as he pleases. The unsupported `ours for life` wording was removed.
- Belle explicitly calls the attacker both a **monster and a devil**.
- `old Tom` is explicit.
- The money is a **bundle of hundred-dollar bills**.
- The livestock puzzle explicitly requires **50 animals total** while spending exactly 1,000.
- Meyer tells them to **work there and save up again** after the robbery.
- `Don't make any mistakes` replaces an unsupported `embarrass me`.
- The cultists explicitly say they have made **soul pacts** and will create the dark history the Devil desires.
- No exaggerated minstrel-style English dialect was invented for Black characters.

### T25 - Atlanta continuation / Lincoln river puzzle

Edited records: `g0/r11`, `g0/r12`, `g1/r22`, `g2/r4`.

- The soldiers explicitly joke that Meyer switched from the **Confederacy to the Union when the South began losing** and supplied intelligence; the first English pass dropped the defection.
- Lincoln's response is a counterfactual about men like Meyer preventing war from starting, not merely perhaps stopping an existing war.
- Lincoln's stutter on calling for the guards is restored.
- The coyote rule is gameplay-significant: coyotes remain calm when the opposing group is **equal to or larger than** the coyotes; they attack smaller groups. The earlier `equal-size groups` wording was incomplete.

### TT6A - Nazareth / Joseph and Mary

Edited records: `g0/r13`, `g1/r28`.

- Joseph's confession explicitly establishes that his **fiancee Mary seems to be pregnant**, while he swears he has not even held her hand and says she herself has no explanation. A temporary second-pass wording that accidentally left `Mary seems...` without its complement was corrected before completion.
- Mary's source line is an expectation that Joseph **would believe/trust her**, not a completed event `He believed me!`.

### TT6B - road to Bethlehem / animal riddles

Edited records: `g0/r29`, `g0/r30`, `g1/r9`, `g2/r1`, `g2/r3`, `g2/r6`, `g2/r8`.

- The camel's marked rustic speech is lightly localized without caricature.
- `Honesty's my gift` reflects `shoujiki dake ga torie`, rather than the different claim `honest to a fault`.
- `tayori ni naru` describes Kashim as **reliable/trusty**, not merely `sound`.
- Two quiz questions were clarified to protect answer logic: Moses led the Israelites **out of which country?**, and **what word** for Savior means `anointed one`? The intended answers are Egypt and Messiah.
- The cow's deliberately rustic/rambling voice and the protagonist's `wh-what a tedious guy` stutter are restored.

### TT6C - Nativity climax / Devil confrontation

Edited records: `g0/r2`, `g0/r13`, `g0/r16`, `g0/r23`, `g1/r15`, `g1/r16`, `g1/r19`, `g1/r20`, `g2/r10`, `g2/r12`, `g2/r13`, `g2/r14`, `g2/r31`.

- The Devil explicitly says he was reborn and **went back** for revenge, preserving the time-travel direction.
- Joseph's source stutters are restored after the jar incident and when meeting the Magi.
- The protagonist explicitly explains that the Devil is **neither him nor in the jar** and has possessed the infant; the `not in the jar` clue had been omitted.
- The time-belt destination again identifies the **museum before the Devil's appearance**, rather than only `back before he appeared`.
- The Devil explicitly says he appeared during Jesus's training and **tried to tempt him**.
- `Scripture says serve God alone` fixes the grammatical `Scripture says us to serve...` without changing the theology.
- The Devil's `y-yamero` panic/stutter is restored during sealing.
- `hontou no washi` is restored as the **real me**, not merely `who I am`, in both challenge lines.
- The Devil says **he** feels a kinship/similarity with the protagonist; the earlier English incorrectly made the protagonist the experiencer (`You feel like one of us`).
- The protagonist's source has **three** shouted `damare`; the branch preserves the triple beat compactly as `Shut up! Shut! Shut!`.
- `Ununu... doushite...` is restored as the Devil's frustrated **`Grr...! Why...?`**, rather than the added interpretation `Why resist me?`.

### TT6D - 1995 epilogue

Edited records: `g0/r1`, `g0/r4`, `g0/r5`.

- The first workbook gloss itself contained a pronoun error: `watashi shinderu no ka to` means the girl thought **she herself had died**, not that she thought the protagonist was dead. The playable line now says `I thought I had died.`
- The girl's `okashina hito` describes the protagonist as a **funny/strange guy**, rather than the abstract situation being `strange`.
- The protagonist's startled reaction between the girl's first incantation and `Leave it to me!` is restored instead of silently consuming that control-delimited segment as word-wrap space.
- The girl says she heard the fortune **that morning**; that timing is restored.
- The final ominous growl remains deliberately unexplained.

## Extended-dictionary safety

The English codec maps dictionary references 32-68 onto otherwise-unused extended-glyph values without changing token width. `patched_nov2_ui()` installs that decoder change globally, so every scenario overlay loaded by the English game may use the extended references.

The canonical release path now passes `EXTENDED_DICTIONARY_ENTRY_COUNT` for **all 13 playable scenario banks**, not only TT1A or the relocated-menu banks. The live-fit model does the same. A dedicated TT6D release-policy regression deliberately supplies a 32-entry dictionary on the non-relocated path and checks that both compression and rebuild receive the 68-entry maximum.

Regression coverage also includes dictionary-order optimization above 31 entries and a synthetic rebuild that deliberately references dictionary entry 33 while proving the fixed-address tail remains byte-for-byte unmoved. These tests protect against silently reintroducing the old English ceiling or gaining text space by overwriting/moving fixed-address data.

Native source parsing intentionally remains native: an untouched Japanese bank still describes the original 31-entry encoding. Removing that source-format fact would weaken validation rather than increase playable English capacity.

## Commit ledger for the completed second-pass continuation

- TT3A: `636946b117ff6127cc4886ab1f38e412251e83e1`
- TT3B: `76f58c808abd229a73141b17ece645b0f3542cd8`
- TT4: `7681c7ab289a408d0c02671b90ea4168050f1a8e`
- TT5: `59daa3bdf0b34786cf2a402b57d465cf496aa935`
- T25: `2b37dea803e429d37fd49bd6a6e9b49979a57eb7`
- TT6A initial semantic pass: `a5fe53c65e7a5674ebfc564181407fc46feb0636`
- TT6B: `41d37772ee97dc401ee4cd438d10613bd3b0a43e`
- TT6C semantic pass: `563c1f61c856d22cc6ff6ac0f59129b0374cc5ec`
- TT6C width correction: `a6606c3701c7e2294562de90502dec10cc7efe63`
- TT6D: `06dce720aa93f2f2985ff2ae2eee369b27170b89`
- TT6A pregnancy clarification: `cd28b36a4ff0795592729c27f402eacc934ce68c`

Earlier completed France-bank playable revisions remain recorded as TT2 `f3f4879d1dccbded7c141e364e94f2b36c6e3e54` and T22 `68a6c18a074fa687bbee6b4bea296ab2a2aefc80`.

This document is an audit ledger, not itself the playable script. `work/translations/*.json` remains the playable scenario authority. **Do not merge or promote a release solely because semantic review is complete:** final CI/recompression and fresh runtime/playtest validation are still required.
