# TT1A voice and prose pilot

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

This pilot applies the expanded character-voice policy only to TT1A: the September 1995 prologue, newscast, fortune/personality service, and the protagonist's first internal reactions.

## Editorial rules

- Exact Japanese meaning remains authoritative.
- External fan-translation wording is not copied.
- Source control-code order is preserved exactly.
- Control-delimited text segments remain at or below 24 visible columns.
- More colorful English is used where the Japanese supports personality, register, irony, or dramatic cadence; neutral source text is not embellished merely to sound literary.
- Japanese geographic dialect is localized by social effect, not mapped mechanically to a specific English-speaking region.

## Voices active in TT1A

### Newscaster

- Japanese register: formal broadcast narration; polished institutional phrasing.
- English target: concise 1990s television-news cadence, detached and professional.
- Avoid: conversational filler, tabloid hype, or turning the newscaster into generic narration.

### Dr. Simon

- Japanese register: educated `watashi`, formal explanatory prose, deliberate hesitation (`ee...`).
- English target: precise, humane academic speech with occasional halting delivery.
- Avoid: mad-scientist theatrics, excessive technobabble, or making him unnaturally eloquent under pressure.
- Pilot decision: the existing TT1A research line is already strong enough and remains unchanged.

### Protagonist / internal voice

- Japanese register: modern, casual masculine voice; skeptical, quick, emotionally transparent.
- English target: natural contemporary speech with contractions, fragments, dry disbelief, and abrupt pivots.
- Avoid: macho action-hero banter, constant jokes, or polished literary narration.
- Pilot examples: `All talk so far. / No one's pulled it off.` and `That's weird... / Some kind of charm? / Whatever... Let's go!`

### Fortune Service / interface voice

- Japanese register: polite commercial-service language mixed with deliberately cheesy fortune-telling copy.
- English target: earnest late-20th-century computerized fortune service: courteous, slightly canned, and charmingly corny when the prediction calls for it.
- Avoid: sterile technical UI language for the fortune itself.
- The personality questionnaire should be fast, punchy, and immediately answerable as yes/no prompts.

### Prologue narrator

- Japanese register: broad social commentary with a mildly sardonic final observation that fortune-telling strangely works.
- English target: compact late-20th-century documentary/game-prologue narration. Serious about social anxiety, but allowed a dry final turn.
- Avoid: apocalyptic purple prose beyond the Japanese.

## Prose-direction examples

- `Do you prefer consommé to miso soup?` -> `Consommé over miso soup?`
- `Do you want to hit 3 or more people?` -> `Want to punch 3+ people?`
- `Do you want a brief, full life?` -> `Live fast, die young?`
- `Calm thought and resolve shall bring good luck.` -> `Keep a cool head and / hold firm. Luck follows.`
- `Use this perfect line:` -> `Seal it with this line:`
- `Strangely, it works.` -> `Oddly enough, it works.`

## Capacity notes

The pilot preserves every TT1A source control-code sequence and does not introduce any control-delimited segment over 24 visible characters. Across the 35 TT1A scenario records, the revised English is also shorter overall than the previous text, so the richer voice does not depend on consuming additional raw prose space.

## Scope

This is intentionally a pilot rather than the full-game rewrite. If the direction is approved, the same source-first process should continue section by section, with each historical cast receiving its own voice treatment rather than a single global "colorful prose" pass.
