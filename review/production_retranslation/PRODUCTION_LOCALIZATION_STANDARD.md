# Time Twist — production English localization standard

**Scope:** Editorial review only. Files in this directory are not build inputs.

The goal is an English script that could plausibly have been professionally localized for release while remaining uncensored and faithful to the Japanese ROM. The Japanese source and the project's completed authenticity audit outrank the old patch-safe English whenever they conflict.

## Core rule

Write the English we actually want first. Do not shorten, fragment, euphemize, or distort a line merely because the existing compressor, renderer, control layout, or byte budget makes the natural version inconvenient. Technical adaptation happens after editorial approval.

## Accuracy

1. Preserve concrete facts, relationships, chronology, objects, historical references, and speaker identity from the Japanese.
2. Preserve meaningful stutters, hesitations, repetitions, abrupt interruptions, and comic timing.
3. Localize Japanese formulas by communicative function when literal English would misrepresent the social act (for example `おじゃましました` / `おかまいもしませんで`).
4. Preserve culture-specific references when they are part of characterization or humor (Yomiuri Giants, miso soup versus consommé, etc.).
5. Do not infer a stronger claim than the Japanese makes. Conversely, do not flatten explicit detail into vague English.

## Uncensored policy

- Do not sanitize profanity, sexual jokes, racial prejudice, slavery, torture, religious language, demonic material, Nazi material, killing, or sacrificial imagery that is present in the source.
- Do not add profanity, sexual content, slurs, or cruelty just to make the translation feel "mature."
- When an old Japanese term maps poorly to a modern English ethnonym, preserve the referent without introducing an unnecessary English slur; explanatory documentation can retain the source wording.

## Character voices

### Protagonist
Quick, contemporary, wry, emotionally transparent. His panic, flirting, disbelief, and occasional crude joke should sound spontaneous. Do not turn him into a macho action hero or a constant profanity machine.

### Girl
Warm, poised, friendly, capable of teasing. Feminine-coded Japanese informs softness and social tone; it does not justify baby talk, exaggerated coyness, or eye dialect.

### Devil
Grandiose, sardonic, entitled, theatrical. Selectively old-fashioned syntax is welcome when it adds authority, but he should not sound Shakespearean. His `わし / じゃ` role-language is not a rural dialect.

### Dr. Simon
Educated, precise, formal, humane, sometimes halting under stress. Scientific exposition should read clearly rather than as clipped notes.

### Nagoya/Owari-coded businessman
Loud, brash, boastful, money-obsessed. Convey marked regional energy through rhythm, emphasis, contractions, and attitude. Never map him onto a specific American region.

### Pierre / Chino / Gordo and medieval commoners
Earthy, rough, readable adventure dialogue with gallows humor. No faux-Shakespearean `thee/thou` treatment.

### Bishop
Self-important ecclesiastical authority shading into theatrical menace. Religious language should sound institutional, not comic unless the source makes it comic.

### Schmidt
Clipped, disciplined, restrained. He softens only after his allegiance is revealed.

### Belle / George
Plain rural and working-class English with dignity. No minstrel spelling, phonetic caricature, or invented racialized dialect.

### Joseph
Earnest, worried, fundamentally kind. His comic self-pity should remain human rather than buffoonish.

### Mary
Quiet, clear, compassionate, resolute when necessary.

### Village Elder / Magi
Measured and dignified, lightly elevated where appropriate. Avoid pseudo-biblical archaism.

### Animals
Only lightly rustic/comic where the Japanese itself marks their speech. Do not make every animal speak in a novelty dialect.

## Punctuation and typography — review copy

- Prefer ordinary American-English punctuation: periods, commas, colons, question marks, exclamation marks, and true ellipses.
- Use the ellipsis character `…` for a true spoken or narrative ellipsis.
- An em dash is **exceptional**, not house style. Use one only for a genuine interruption or abrupt broken turn that ordinary punctuation cannot represent faithfully.
- Do **not** use em dashes for apposition, ordinary contrast, parenthetical explanation, labels, exhibit names, dates, headings, signatures, report text, or generic rhetorical emphasis. Rewrite those with commas, periods, colons, or the source-supported display/control boundary.
- Japanese `／` is an emphatic display/beat mark, not an em dash. Translate its communicative function with normal English punctuation or timing rather than mapping the glyph mechanically.
- A future production em dash requires a record-specific source justification and an explicit regression-test exception. The current production corpus intentionally requires none.
- Use curly apostrophes and quotation marks in human-facing review copy.
- Use sentence-final punctuation unless the lack of it is an intentional interruption or trailing thought.
- Preserve multiple exclamation marks only where the performance is intentionally extreme.
- Use commas around direct address where natural in English.
- Use a colon to introduce formal labels, exhibit descriptions, dates, and report text when punctuation is useful; otherwise let the existing display/control boundary carry the separation.
- Do not use repeated ASCII periods as editorial prose. A game-safe export may later map `…` to supported glyphs or timing controls.

## Names and terminology

- **Devil Museum**
- **Time Belt**
- **Demon-Sealing Jar**
- **Sabbath Box**
- **Warding Bell**
- **Devil's Hand**
- **Jeanne d'Arc** (Jeanne in direct address)
- **Lugot**, **Chino**, **Gordo**, **Cougar**, **Schmidt**, **Nicras**, **Kashim**, **Caspar**, **Melchior**, **Balthazar**
- Preserve the incantation's source variants where the plot uses them.
- Preserve the intentional false infant name **Demon** and the later **Jesus Christ** reveal/wordplay.

## Historical/religious register

The game is a time-travel adventure written in modern Japanese, not a period-language simulation. Historical scenes should be clear contemporary English colored by social role. Biblical and liturgical material may be slightly elevated, but no King James imitation is introduced unless a direct scriptural quotation specifically benefits from a familiar established English phrasing.

## Editing test

A proposed line should pass all five questions:

1. **Meaning:** Does it preserve what the Japanese actually says?
2. **Voice:** Could this speaker plausibly say it in this game's established English voice?
3. **Context:** Does it make sense as a menu action, observation, conversation, placard, article, sermon, joke, or narration in the actual scene?
4. **English:** Would a native editor accept it without knowing it was translated?
5. **Restraint:** Did we avoid both censorship and gratuitous embellishment?

Only after all five pass should engineering decide how to encode, wrap, compress, or relocate it.
