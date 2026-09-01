# TT1B voice and prose pilot

This pass extends the source-first voice/prose pilot into TT1B: the Devil Museum, the protagonist's first meeting with the girl and Devil, the Nagoya/Owari-coded businessman, Kuga's house, Dr. Simon, and the church sequence before the first time warp.

## Editorial rules

- Exact Japanese meaning remains authoritative.
- External fan-translation wording is never copied; it may only trigger a source re-check.
- Source control-code order is preserved exactly.
- Every control-delimited English segment remains at or below 24 visible columns.
- Color comes from source-supported register, rhythm, vivid verbs, hesitation, humor, and character behavior rather than added facts.
- Marked Japanese dialect is localized by social effect, not mapped mechanically to a named English-speaking region.
- Neutral lines are left neutral when extra color would distort characterization.

## Character voices active in TT1B

### Protagonist

- Japanese: modern casual masculine speech, normally `ore`; situationally softens toward `boku` and polite forms.
- English: quick, contemporary, skeptical, flustered, and openly reactive. Contractions and fragments are welcome.
- Romantic comedy: awkward rather than suave. Compliments such as `You have nice eyes` should feel like a young man trying to keep a conversation going, while intentionally silly lines remain silly.
- Panic: preserve stutters and abrupt reactions instead of smoothing them into composed narration.

### Girl

- Japanese: standard young feminine speech, warm and relatively poised, with teasing laughter and embarrassed reactions.
- English: gentle, concise, and amused when the source is amused. Avoid exaggerated feminine diction.
- The contrast with the protagonist matters: she is often calmer than he is.

### Devil

- Japanese: authority-coded `washi` and archaizing role-language, inflated self-importance, mockery, and theatrical certainty.
- English: grandiose and sardonic, but economical enough for the bank. Slightly elevated turns such as `Farewell, then` and `I must oblige` are appropriate.
- Avoid rural old-man dialect and faux Shakespeare.
- His dry understatement can be part of the joke: `Call me a devil` contrasts with the protagonist's panic.

### Dr. Simon

- Japanese: educated, formal, explanatory speech; precise even when injured, with meaningful stutters under shock.
- English: controlled academic/scientific diction with urgency only where the scene demands it.
- `M-monster!` preserves his startled restart.
- The Time Belt explanation restores the source point that he had only just completed the machine.

### Nagoya/Owari-coded businessman

- Japanese: conspicuously marked forms including `nanbo`, `kuryaate`, `urusha`, `gaya`, and `doeryaa`; loud, panicked, boastful, and money-obsessed.
- English: brash regional-businessman flavor through contractions, `ya`, blunt commands, rural-versus-boom vocabulary, and oversized claims.
- Do not assign him a specific American regional identity or overuse phonetic spelling.

### Kuga / the older man

- Japanese: fundamentally courteous standard elderly speech. His first `nani ka goyou desu ka` is polite, not hostile. He becomes defensive because he mistakes the protagonist for a land speculator, then immediately apologizes.
- English: courteous older gentleman, slightly rambling and self-conscious. His poor eyesight is reflected in recognizing the protagonist by voice.
- Avoid generic gruff-old-man treatment.

### Priest and congregants

- Japanese: modern polite clerical speech and ordinary anxious congregants. The sermon becomes more formally rhetorical than conversation.
- English: the priest is calm and courteous in conversation, then measured and elevated while preaching. Congregants remain ordinary contemporary people.
- Avoid medieval/church caricature in the modern 1995 scene.

## Source-grounded semantic restorations

- `TT1B/g0/r0`: restores the protagonist's arrival beat, `Made it...`.
- `TT1B/g0/r14`: repairs the Sabbath Box description: it was used at witches' gatherings/rites in medieval Europe.
- `TT1B/g0/r15`: restores `several thousand years ago` as `Millennia ago` and keeps the fierce battle.
- `TT1B/g2/r12`: restores `last night` to the Dr. Simon newspaper report while keeping concise newspaper prose.
- `TT1B/g3/r6`: restores Simon's source stutter: `M-monster!`.
- `TT1B/g3/r8`: restores that the belt-shaped time machine had only just been completed.
- `TT1B/g3/r9`: restores Simon's explicit urgency.
- `TT1B/g3/r13`: restores the protagonist's stammer when churchgoers mistake him for the Devil.
- `TT1B/g3/r29`: retains that the youth smiled gently before speaking.
- `TT1B/g3/r30`: restores the sermon's `steadfast/unwavering justice` concept.

## Deliberate non-change

`TT1B/g1/r6` remains **Maradul Barao Galdura**, not Garadura. The Japanese at this specific record deliberately/actually differs from the normal incantation, so the localized wrong variant must not be normalized away.

## Prose examples

- `Blue sky... when was it?` -> `Blue sky... how long ago`
- `My body's falling apart!` -> `My body's crumbling!`
- `Her ponytail is so cute.` -> `That ponytail's so cute.`
- `She is unconscious.` -> `She's out cold.`
- `Devil: You might say so.` -> `Devil: Call me a devil.`
- `...: What do you want?` -> `...: Can I help you?` (a semantic/register correction, not merely style)
- `A church, way out / in the country? Strange.` -> `A church this far out? / Strange.`
- `Honestly, it looks lame.` -> `Honestly... pretty lame.`

## Capacity discipline

TT1B is an unusually tight bank. The pass therefore favors sharper wording over expansion. Relative to the current branch text before this pass, the revised 137-record TT1B map is 28 visible characters shorter overall.

A local structural validation of all 87 changed records found:

- exact Japanese/source control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 24 visible characters;
- maximum changed-segment width: 24 characters.

This does not substitute for the repository's actual compression/release-build fit gate. Packed dictionary cost is not proportional to visible character count, so a canonical build/test remains required before release approval.
