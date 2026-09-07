# Dialogue Authenticity Second Pass

This completed review records the Japanese-source reasoning behind an earlier
editorial pass. Current wording comes from `work/translations/*.json`; the
[cross-bank decisions](../work/audits/final_cross_bank_consistency.md) and
[playtest matrix](../docs/PLAYTEST_MATRIX.md) track the maintained editorial
policy and remaining scene checks.

This pass re-reviewed all **1,299 playable scenario records** against the exact Japanese source. It is deliberately stricter than the first workbook pass: a line is not considered finished merely because its basic meaning is understandable.

The pass produced **129 scenario-record edits** across all 13 playable scenario banks, plus the parallel fixed-menu correction `Call` -> `Intercom` in TT1B. The findings below explain the source readings; quoted English records that pass's wording and may have been refined by subsequent reviews.

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

Current capacity rules are documented in the
[full-word menu implementation](../docs/FULL_WORD_MENU_IMPLEMENTATION.md).
The [generated progress report](../outputs/Time_Twist_translation_progress.md)
provides measurements recomputed from the current script.

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
- Restores his startled reaction during the incantation and the fact that her fortune was heard **that morning**; the final wording is `Girl: Morning fortune:` followed by `"A fine man awaits you."` so both control-delimited segments remain natural and width-safe.
- The final ominous growl remains deliberately unexplained.

## Manual evidence / canonical terminology

The original Zenpen instruction manual is treated here as **secondary canonical evidence**. The ROM-derived Japanese scenario and fixed-address text remain the translation authority; manual prose is not inserted into playable dialogue unless it resolves an actual contradiction in the ROM text. The manual is nevertheless valuable for authorial framing, historical terminology, and terse FDS-system wording.

### Reconstructed booklet order

The supplied scans are printer-imposed spreads rather than reading-order page pairs. The numbered manual reads normally from printed page 1 through 12. The scanned spreads reconstruct as:

| Supplied scan | Left printed page | Right printed page |
| --- | ---: | ---: |
| Manual Page 12 | 12 | 1 |
| Manual Page 2 | 2 | 11 |
| Manual Page 10 | 10 | 3 |
| Manual Page 4 | 4 | 9 |
| Manual Page 8 | 8 | 5 |
| Manual Page 6 | 6 | 7 |

The cover/back-cover and greeting/contents spread sit outside that numbered sequence.

### Opening premise and protagonist

Printed page 2 states that on **September 25, 1995**, the protagonist is a `shounen` (**boy / young male**) casually watching television when `aru jaaku na terepashii` (**a certain evil telepathy**) changes his ordinary life and draws him into an extraordinary space-time distortion.

This is useful story framing but is not silently injected into TT1A dialogue. It supports the audit's youthful, contemporary treatment of the protagonist's voice and records that the manual explicitly presents a **malevolent psychic influence** as part of the inciting event.

### Alexander / Alexandria

Printed page 8's historical-primer entry `Arekisandoria (Arekusandoria)` explains that **Alexander (Alexandros) the Great** gave his name to cities he founded or conquered, producing the name Alexandria. This independently corroborates the TT4 correction that Athena's `ano ko` refers to the **boy Alexander**, not an unidentified girl.

### Magi / astrologers

The same page labels the Nativity tradition `San'ou raichou (Sanhakase no sanpai / Magi no reihai)` and explicitly glosses the Three Kings as `sannin no senseijutsushi` — **three astrologers** guided by a star from the East.

This strongly supports keeping **`astrologers`** in the Magi's playable self-introduction while using **Magi** or **Wise Men** where broader English documentation needs a collective traditional label. `Astrologers` is not an accidental over-literalism; it is terminology Nintendo itself foregrounds in the manual.

### Historical-primer framing

Printed page 9 supplies short player-facing explanations for several subjects that recur in the script:

- **Witch hunts / witch trials:** Church persecution of people regarded as heretics, with social disorder and disease attributed to devils or witches and accused people subjected to irrational interrogation and execution.
- **American Civil War:** a conflict with multiple causes in which the slavery issue had a major influence; the manual describes the anti-slavery North as victorious.
- **Gestapo:** the common name for Nazi Germany's state secret police, described as repeatedly using brutal repression against Jews and political opponents.

These entries do not add scenario dialogue, but they support the audit policy of translating the game's historically harsh material directly rather than softening it merely because the wording is severe.

### Intended tone

Printed page 1 describes the game as `choppiri karakuchi no geemu`, roughly a **slightly sharp / biting game**. Combined with the manual's blunt historical primer, this is useful evidence that the game's insults, black humor, racism, witch-persecution material, Nazi material, and demonic threats are not automatically localization artifacts to be toned down.

The same introductory text also states that the game has **no Game Over**, encouraging the player to act boldly without fear of failure. This is useful playtest context for puzzle and wrong-answer behavior.

### FDS system prompts

The manual also provides external confirmation for several terse fixed-address interface translations:

- Printed page 5 tells the player to choose `saisho kara` to begin from the start, supporting the functional fixed-slot localization **`Start`**.
- Printed page 7 explains that after saving with `seebu`, play is resumed from the title screen by choosing `seebu kara` (**from the save**), supporting the title-menu localization **`Load`**.
- Printed page 12 gives the FDS wrong-disk sentence `chigatta disuku ga setto sareteimasu` — **the wrong disk is inserted/set**. NOV2 stores the same sentence across the separate records `chigatta disuku ga` and `setto sareteimasu`, independently confirming the existing **`WRONG DISK!`** interpretation.

The manual's disk-error table also distinguishes wrong side/order/version conditions. Those descriptions are useful semantic evidence for NOV2 recovery paths, but the exact English fixed-slot wording remains governed by ROM layout and runtime readability.

### Translation consequence

The manual review produced **no reason to revert any of the 129 scenario-record changes**. Its strongest effects are corroborative: it reinforces the Alexander correction, the Magi-as-astrologers wording, the direct treatment of historical violence/oppression, and the meanings of several terse system prompts. The only materially new story framing is the manual's explicit **evil-telepathy** description of the opening, which is documented here rather than inserted into dialogue that does not say it.

For candidate construction, validation, and promotion, follow the
[maintainer release process](../docs/MAINTAINER_RELEASE_PROCESS.md). Semantic
review alone does not establish runtime readiness.
