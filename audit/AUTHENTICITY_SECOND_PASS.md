# Dialogue Authenticity Second Pass

Status: **semantic/voice review complete; CI and fresh runtime validation pending** on `menu-dialogue-authenticity-audit-20260826`

This pass re-reviewed all **1,299 playable scenario records** against the exact Japanese source. It is deliberately stricter than the first workbook pass: a line is not considered finished merely because its basic meaning is understandable.

The completed pass stages **129 scenario-record edits** across all 13 playable scenario banks, plus the parallel fixed-menu correction `Call` -> `Intercom` in TT1B. The edits restore omitted concrete detail, relationship/status information, puzzle rules, stutters and hesitations, rough or ceremonial register, plot logic, and several outright referent/pronoun errors. They are not a blanket prose rewrite.

## Review contract

Every scenario record was checked for semantic accuracy, natural American English, speaker identity, social/emotional register, actually marked dialect, verbal tics and hesitation, native control-event preservation, the 24-column renderer contract, and bank-fit constraints.

The target is the closest American-English **effect**, not a one-to-one substitution of Japanese dialect geography. Mild Japanese regional flavor should remain mild in English; archaizing role-language is not automatically a country accent; deliberate class or regional characterization must not be flattened into neutral prose.

## Voice decisions

- **Protagonist:** quick contemporary American English; wry, panicky, emotionally transparent.
- **Girl:** warm, poised, capable of teasing; feminine endings are represented through tone, not caricature.
- **Devil:** grandiose, sardonic, pompous and selectively old-fashioned; `washi` / `ja` are not a rural accent.
- **Dr. Simon:** educated, precise, formal, humane, occasionally halting.
- **Nagoya/Owari businessman:** brash regional-businessman cadence without a fake U.S. hometown.
- **Pierre / Chino / Gordo:** rough, earthy commoner speech and gallows humor, not faux Shakespeare.
- **Lugot / conventional elders:** measured older speech only where source role-language supports it.
- **Schmidt:** terse and disciplined, softening after his allegiance is revealed.
- **Belle / George:** plain rural / working-class American speech with dignity; no minstrel-style eye dialect.
- **Joseph:** earnest, worried and fundamentally kind.
- **Mary:** quiet, clear and compassionate.
- **Magi:** dignified ceremonial diction.
- **Camel / cow in TT6B:** light rustic rhythm/vocabulary where the Japanese is explicitly marked, without heavy eye dialect or a named American regional caricature.

## Capacity architecture

The dialogue renderer remains a 24-tile row. More dictionary space does not mean unlimited line width.

The English NOV2 decoder maps otherwise-unused extended-glyph values to dictionary references 32-68. The canonical release path now passes the **68-entry maximum to every playable scenario bank**. Native Japanese parsing remains 31-entry-aware because that describes the untouched source encoding, not an English release limit.

For the 11 relocated full-word-menu banks, playable capacity is the historical scenario reservation plus the source-verified movable menu prefix:

| Bank | Scenario capacity | Reclaimed prefix | Combined capacity |
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

Independent conservative fit evidence already established TT2 at **<=4092/4141** and T22 at **<=1913/1939** before optimizer improvements. TT1A's fuller script independently fit its non-relocated capacity with the extended dictionary. The final whole-game script still requires current GitHub Actions recompression confirmation; CI was still queued when this ledger was frozen.

## Completed bank status

| Bank | Records reviewed | Scenario edits |
| --- | ---: | ---: |
| TT1A | 35/35 | 6 |
| TT1B | 137/137 | 29 |
| TT2 | 169/169 | 25 |
| T22 | 58/58 | 8 |
| TT3A | 152/152 | 12 |
| TT3B | 58/58 | 4 |
| TT4 | 183/183 | 7 |
| TT5 | 123/123 | 9 |
| T25 | 76/76 | 4 |
| TT6A | 100/100 | 2 |
| TT6B | 94/94 | 7 |
| TT6C | 106/106 | 13 |
| TT6D | 8/8 | 3 |

Total: **1,299/1,299 scenario records reviewed; 129 scenario records changed.** Fixed-menu `Call` -> `Intercom` is tracked separately.

## Confirmed findings

### TT1A

- `50 meetoru ijou` means **50 meters or more / at least 50 meters**.
- The work/leisure proposition specifically means not wanting work to cut into leisure time.
- `-tai` expresses **wanting** to help society, not predicting that the player will.
- Personality results restore explicit traits including principled/hardworking/stubborn character, sudden loss of motivation, sharp insight, weakness with money, and dreams of dramatic romance.

### TT1B

- Exhibit prose restores omitted period/place, secret-society, sacrificial-victim, and engraved-spell details.
- The Devil's long captivity, body-theft force, protagonist stutters, and `fukumimi` **earlobes** are more fully represented.
- The Nagoya/Owari businessman keeps deliberate regional force without invented American geography.
- Dr. Simon/Elder material restores completed-machine, self-warp, late-life eyesight and accidental-oversharing details.
- Church material restores collection effort, sins in the prayer, hymn/sermon distinctions, the gentle smile, courage against the Devil, and missing stutters.
- Fixed menu `Call` is corrected to **`Intercom`**.

### TT2

- Restores Chino's stutters, Pierre's drunken hiccups/exclamations, **tears and snot**, Jeanne as Lugot's **granddaughter**, jail access as **come and go freely**, Jeanne having **just turned sixteen**, concern for **France**, the jailer's explicit empathy, the **leg** scar, **thick rope**, the fact she is still a child, Jeanne's command to **flee**, and the Bishop's fuller motive/explanation.

### T22

- Restores the Baron's affectionate gaze, explicit confinement order, **Devil's baptism** accusation, slow drawn-out torment, crying-swollen eyes, the Bishop's panic/stutter and `let go`, Jeanne explicitly hearing **God's message**, and the closing praise of Jeanne as France's fair savior.

### TT3A

- The hidden contact explicitly says the resistance will make the escape arrangements.
- Nick explicitly mentions the **assassination plot against Hitler**.
- `Rebecca` is an **escape/resistance organization code**, not a woman.
- `kutabare Hitler` is restored consistently as **`Drop dead, Hitler!`**.
- Simon's note came via a child sent by an unknown man.
- The watermill trap explicitly reveals **`I'm Gestapo!`**.

### TT3B

- Keeps the same harsh password, restores missing Simon/Cougar stutters, and restores the Devil's contract logic: Hitler must keep doing evil **until the pact expires**, and must remember that he dies **April 30, 1945**.

### TT4

- Fixes a major referent error: Athena's `ano ko` is the **child Alexander**, not an unidentified girl.
- Restores marked stutters, a missing speaker label, and grammatical Aristotle self-identification without rewriting the source's Greek/underworld riddles.

### TT5

- Corrects `tomorrow`, the attacker's actual threat rather than unsupported `ours for life`, Belle calling him **monster and devil**, explicit old Tom, the bundle of hundred-dollar bills, the **50 animals total** livestock constraint, Meyer's instruction to work and save again, `don't make any mistakes`, and the cultists' explicit **soul pacts** / dark-history goal.
- No exaggerated racialized eye dialect was invented.

### T25

- Restores the joke that Meyer switched from the **Confederacy to the Union when the South began losing** and supplied intelligence.
- Restores Lincoln's stutter and the correct gameplay rule: coyotes stay calm when the opposing group is **equal to or larger than** them, and attack smaller groups.

### TT6A

- Joseph explicitly says his **fiancee Mary seems to be pregnant** while insisting he has not even held her hand and that she has no explanation.
- Mary's line is an expectation that Joseph **would trust/believe her**, not the false completed event `He believed me!`.

### TT6B

- Restores the camel/cow's intentionally rustic flavor, `Honesty's my gift`, Kashim as **trusty/reliable**, and the protagonist's stutter.
- Fixes two quiz prompts so the intended answers are unambiguous: Moses led the Israelites **out of which country?** and **what word** for Savior means `anointed one`?

### TT6C

- Restores the Devil explicitly going **back** for revenge, Joseph's stutters, the `not in the jar` clue, the museum as the time-belt destination, the Devil explicitly **trying to tempt Jesus**, grammatical `serve God alone`, the Devil's sealing panic/stutter, both **real me** challenges, the Devil himself feeling kinship with the protagonist, the protagonist's three `damare` beats, and `Grr...! Why...?` rather than the invented `Why resist me?`.

### TT6D

- Corrects a workbook-level pronoun error: the girl thought **she herself had died**, not that the protagonist was dead.
- `okashina hito` describes him as a funny/strange guy.
- Restores his startled reaction during the incantation and the fact that her fortune was heard **that morning**.
- The final ominous growl remains deliberately unexplained.

## Extended-dictionary safety

The patched English decoder's 32-68 references are global. The release and live-fit paths now use the 68-entry limit for **all 13 banks**, with a dedicated TT6D regression proving a non-relocated bank may exceed 31 entries. Additional regressions protect high dictionary references and the fixed-address tail. Native Japanese source parsing intentionally retains the native 31-entry fact.

## Continuation commit ledger

- TT3A: `636946b117ff6127cc4886ab1f38e412251e83e1`
- TT3B: `76f58c808abd229a73141b17ece645b0f3542cd8`
- TT4: `7681c7ab289a408d0c02671b90ea4168050f1a8e`
- TT5: `59daa3bdf0b34786cf2a402b57d465cf496aa935`
- T25: `2b37dea803e429d37fd49bd6a6e9b49979a57eb7`
- TT6A initial pass: `a5fe53c65e7a5674ebfc564181407fc46feb0636`
- TT6B: `41d37772ee97dc401ee4cd438d10613bd3b0a43e`
- TT6C pass: `563c1f61c856d22cc6ff6ac0f59129b0374cc5ec`; width correction: `a6606c3701c7e2294562de90502dec10cc7efe63`
- TT6D: `06dce720aa93f2f2985ff2ae2eee369b27170b89`
- TT6A pregnancy clarification: `cd28b36a4ff0795592729c27f402eacc934ce68c`

Earlier completed France revisions remain TT2 `f3f4879d1dccbded7c141e364e94f2b36c6e3e54` and T22 `68a6c18a074fa687bbee6b4bea296ab2a2aefc80`.

This ledger is not the playable authority; `work/translations/*.json` is. **Do not merge or promote a release solely because semantic review is complete.** Current CI/recompression and a fresh emulator/playtest candidate are still required.
