# TT2 voice and prose pilot

> **Editorial-compression supersession — 2026-09-03.** The exact-Japanese,
> semantic, speaker, register, dialect, sentiment, characterization, and voice
> findings in this pilot remain review evidence. Any statement below that uses
> visible-character reduction as a reason to shorten otherwise better English,
> or treats source-exact controls as an absolute prohibition on an explicitly
> audited English-only `CTRL:0` presentation break, reflects the earlier fit
> strategy and is superseded by `docs/ENGLISH_LAYOUT.md`,
> `docs/COMPRESSION_OPTIMIZER.md`, and `docs/NATIVE_ACCELERATOR.md`. Natural
> source-faithful English is now chosen first; layout and verified compression
> are used to fit it into the unchanged ROM footprint.

This pass extends the source-first voice/prose pilot into TT2: October 1428 France, the possessed Pierre, the town craftsmen, Lugot and Jeanne d'Arc, the witch-hunt decrees, the jail, and the Bishop confrontation.

## Editorial rules

- Exact Japanese meaning remains authoritative.
- External fan-translation wording is never copied; it may only trigger a source re-check.
- Source control-code order is preserved exactly.
- Every control-delimited English segment remains at or below 24 visible columns.
- Color comes from source-supported register, roughness, hesitation, profanity, humor, social hierarchy, and rhythm rather than invented period flavor.
- Ordinary medieval characters do not receive faux-Shakespearean English merely because the scene is historical.
- Neutral observation text remains comparatively neutral so the marked speakers retain contrast.

## Character voices active in TT2

### Protagonist

- The protagonist remains the same contemporary 1995 viewpoint even while inhabiting Pierre.
- English target: quick contractions, fragments, panic, disbelief, and casual internal observation.
- He should not suddenly narrate like a medieval Frenchman simply because his body has changed.

### Pierre

- Japanese: rough masculine speech with forms such as `shikanee`, `temee`, emphatic exclamations, insults, hiccups, and drunken outbursts.
- English: earthy working-class commoner; blunt, emotional, profane when the source supports it, and increasingly sloppy when drunk.
- He pushes forward and explodes rather than hesitating.
- `akuma no danna` in the opening is allowed a comic familiar turn (`Mister Devil`) rather than being flattened to a generic `a devil`.

### Chino

- Japanese: rough commoner speech, but with conspicuous nervous starts and stutters under pressure.
- English: coarse enough to belong with Pierre and Gordo, but much less confident. Preserve stutters, balking, and defensive reactions.
- Examples include `D-don't be nuts!`, `I can't do that!`, and the source-supported curses around Jeanne and the Bishop.

### Gordo

- Japanese: broad rough speech (`omee`, `ze`, `kurenee ka`, `shouganee`) delivered with more confidence than Chino.
- English: blunt gossiping buddy voice, short contractions, casual profanity, and confident teasing.
- Avoid making him merely another nervous commoner.

### Older quizmaster / shopkeeper

- Japanese: marked old-man/folksy language including `shitchoru`, proverb recitation, praise, scolding, and reward banter.
- English: dry, playful, lightly old-fashioned/folksy quizmaster cadence.
- Avoid exaggerated rural phonetics.

### Lugot

- Japanese: elderly `washi/ja` role-language plus unusually open grief and pleading for his granddaughter.
- English: old working-class grandfather with restrained old-fashioned cadence and strong emotional vulnerability.
- He should not sound like a wizard or court noble.

### Official / guard

- Japanese: code-switches between terse commands, polite institutional speech, nervous stutters, and private drunken gossip.
- English: on duty he is a low-level bureaucratic guard; privately he becomes ordinary, nervous, and indiscreet.
- The pass deliberately preserves his formal lines rather than making every appearance rougher.

### Jailer

- Japanese: consistently deferential and polite, including honorific treatment of the Bishop.
- English: controlled institutional functionary. Full sentences and respectful restraint are characterization.
- His formal dialogue is intentionally not given the commoners' slang.

### Bishop

- Japanese: old-authority role-language, commanding diction, ceremonial self-importance, and private smugness.
- English: oily ecclesiastical authority with some elevated cadence, but no faux Shakespeare.
- His speech should contrast with the ordinary prisoners and craftsmen.

### Jeanne

- Jeanne is sixteen in this chapter.
- Her ordinary Japanese is straightforward and frightened rather than grandly archaic.
- English: exhausted, sincere teenage girl. Keep requests and escape dialogue immediate and human.
- Elevated prophetic language belongs only where the Japanese itself later becomes prophetic.

### Imprisoned women and townspeople

- English remains plain and immediate: frightened parents, workers, and bystanders rather than a generic historical dialect.
- Their desperation is carried by content and rhythm, not antique vocabulary.

## Source-grounded semantic restorations

- `TT2/g0/r25`: restores `tadachi ni` (report scarred women **at once/immediately**) and `genbatsu ni shosu` (concealers face **severe punishment**) while retaining the source date, **October 1428**. The previous `Hiding one is a crime` lost the first two details.
- `TT2/g3/r23`: restores Pierre's opening `bakayarou` insult in his drunken retort after Chino asks why Pierre will not rescue Jeanne himself.
- Rough forms and stutters are retained rather than normalized away, especially Chino's `ba, baka...` restart and Pierre's repeated drunken insults/hiccups.
- Formal official/jailer speech is retained as formal where the Japanese switches into `desu/masu` and honorific register.

## Prose-direction examples

- `Pierre: War looks grim.` -> `Pierre: War's going bad.`
- `so I prayed to God... / but a devil came...` -> `I had to pray to God... / then Mister Devil came.`
- `Chino: Witch hunts... / what an awful age.` -> `Chino: Witch hunts... / What a rotten age.`
- `Gordo: Pierre, listen!` -> `Gordo: Pierre, get this!`
- `He is extremely drunk.` -> `He's plastered.`
- `Guard: Keep this secret.` -> `Guard: Tell no one.` in his private drinking/gossip scene, while his on-duty institutional lines remain formal.
- `She's still just a child` -> `She's only a kid...` in the protagonist's contemporary internal voice.

## Validation

The final TT2 candidate contains 169 scenario records and changes 85 of them.

Local structural validation found:

- exact source control-event sequence preserved for every changed record;
- no changed control-delimited English segment longer than 24 visible characters;
- maximum changed-segment width: 24 characters;
- no unsupported English-font characters;
- revised TT2 visible text is 85 characters shorter overall than the prior branch version.

The raw-character reduction is useful headroom but is not proof of packed fit. TT2 uses dictionary compression and the canonical compression/release-build fit gate remains required before release approval.
