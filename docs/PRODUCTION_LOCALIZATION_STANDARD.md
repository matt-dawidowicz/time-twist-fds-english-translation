# Production localization standard

This document defines the English target for the production retranslation.

## Goal

The finished game should read like an officially released English localization rather than a technically successful fan patch. English quality is an engineering requirement, not a luxury to be discarded when the original Japanese layout is inconvenient.

The target is idiomatic American English with disciplined character voice, clear UI terminology, strong dramatic pacing, and source-faithful historical/religious content.

## Uncensored means faithful

The translation does **not** sanitize material that exists in the Japanese source. Historical violence, religious material, racism, sexual jokes, insults, profanity, demonic threats, witch-persecution material, Nazi material, slavery, and other uncomfortable content should be translated directly when the source contains it.

Do not intensify or invent material merely to make the patch more provocative. The standard is fidelity, not edginess.

The ROM-derived Japanese remains authoritative. The original manual is secondary canonical evidence for terminology, framing, and terse system text.

## Character and register contract

These decisions are inherited from `audit/AUTHENTICITY_SECOND_PASS.md` and are release requirements:

- **Protagonist:** quick contemporary American English; wry, panicky, emotionally transparent. Avoid telegram-like fragments unless the Japanese is genuinely fragmentary.
- **Girl:** warm, poised, capable of teasing. Feminine Japanese endings affect tone, not caricature.
- **Devil:** grandiose, sardonic, pompous, selectively old-fashioned. `washi` / `ja` are not a rural accent.
- **Dr. Simon:** educated, precise, formal, humane, occasionally halting.
- **Nagoya/Owari businessman:** brash regional-businessman cadence. Preserve the comic regional force without pretending Nagoya maps literally to a named U.S. city or dialect.
- **Pierre / Chino / Gordo:** rough, earthy commoner speech and gallows humor; never faux-Shakespeare.
- **Conventional elders / Lugot:** measured older speech only where Japanese role-language supports it.
- **Schmidt:** terse and disciplined, softening after his allegiance is revealed.
- **Belle / George / Tom:** readable rural or working-class American speech with dignity; no minstrel-style eye dialect.
- **Joseph:** earnest, worried, fundamentally kind.
- **Mary:** quiet, clear, compassionate.
- **Magi:** dignified ceremonial diction.
- **Camel / cow:** light rustic rhythm and vocabulary where the Japanese explicitly marks it; avoid heavy phonetic spelling.

## Translation hierarchy

For every scenario record:

1. Recover the exact Japanese meaning and referents.
2. Identify speaker, relationship, social register, dialect marking, and dramatic function.
3. Write the best natural English line without considering the old byte budget.
4. Preserve source controls and timing semantics unless a deliberate renderer change proves a better layout safe.
5. Engineer compression, relocation, or renderer support around that English.
6. Shorten wording only when the shorter version is also what an editor would voluntarily choose.

A line is not acceptable merely because it is semantically correct. Translationese, omitted subjects that sound unnatural in English, forced noun phrases, and word order chosen only to fit a byte slot are defects.

## UI standard

Menu labels must be the natural English concept a commercial localization would use. They may not be abbreviated merely because the original Japanese record was short.

The UI must adapt to the English label rather than clipping the label. `Intercom` is the reference regression: returning to `Call`, `Interc`, or another truncation is not an acceptable workaround.

All fixed menus must be tested in their real runtime geometry, including 1-10 choice definitions, left/right columns, arrows, page boundaries, cursor motion, selection, and Back/Cancel behavior.

## Compression policy

Compression is subordinate to localization quality.

The production build may use:

- larger deterministic dictionary searches;
- bank-specific phrase selection;
- local-search / beam / replacement optimization;
- safe text relocation into recovered free space;
- additional pointer indirection;
- a purpose-built English decoder when source-verified and easier to audit than continued format contortions.

Every change must remain deterministic, source-guarded, round-trip tested, and bounded by explicit runtime evidence.

## Historical and terminology invariants

Do not regress established source corrections, including:

- Athena's `ano ko` referring to the child Alexander;
- `Rebecca` as an escape/resistance organization code;
- Jeanne's relationships, age, and France-specific concerns;
- the Hitler pact/expiration logic and April 30, 1945 date;
- the Civil War / slavery and Meyer details;
- Mary/Joseph pregnancy and trust characterization;
- Magi as astrologers where the source/manual explicitly supports it;
- the recovered Devil Museum exhibit details;
- fixed-menu `Intercom`.

## Release bar

No release promotion until a final candidate completes:

- cold-boot Zenpen -> Kouhen continuity;
- all four FDS sides and both required disk changes;
- wrong-side / wrong-disk recovery;
- game-native Save -> power cycle -> Load;
- every menu family and page boundary;
- all retranslated high-risk scenes in context;
- ending and credits;
- a final prose review of screenshots/video, not only JSON text.

The final release should have no known clipped English, no known garbage glyph paths, and no line retained solely because an older technical constraint made better English inconvenient.
