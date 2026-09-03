# TT5 voice and prose pilot

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

This pass continues the source-first voice/prose revision through the September 1864 Atlanta chapter: George and Belle's plantation life, emancipation, racist violence, farm-work puzzles, Tom and the livestock trader, and the occult sequence leading into T25.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep the protagonist's internal voice direct and contemporary while he occupies George.
- Keep Belle colloquial and maternal while preserving her deferential register toward Meyer; do not impose an exaggerated racial or minstrel dialect.
- Give Tom clear rural/working-class flavor from his source speech without assigning him a specific real-world accent or phonetic caricature.
- Give the livestock trader an older, folksier voice matching his `-ja`, `-kanou`, and `shitchoru` forms without overplaying it.
- Keep Meyer practical and paternalistic on the surface while preserving his controlling assumptions and the chapter's later evidence of his opportunism.
- Preserve source-explicit racism, slavery, violence, dated terminology, and coercion without sanitizing it and without inventing stronger slurs, insults, or threats.
- Treat all work-order, livestock, quiz, and measuring-puzzle quantities as gameplay-critical information.
- Do not borrow wording from the removed external translation.

## Source-grounded restorations and corrections

- `TT5/g0/r6`: restores the attacker's contemptuous complaint that the freed people are acting big/high and mighty and his intent to make an example of them with the whip; the old `You won't lord over us` shifted the relationship implied by `dekai tsura`.
- `TT5/g0/r7`: restores the threat that, whatever Lincoln says, the attackers will not allow George and the others freedom while men like them remain. The old `While we live, you obey` was a stronger/different formulation than the Japanese.
- `TT5/g0/r16`: keeps the discovered money as a single 100-dollar bill in the man's reaction and preserves Belle's `oni / akuma` outburst as `Demon! Devil!` rather than flattening both words together.
- `TT5/g0/r18`: preserves the order not to leave the South and the demand that they devote their lives to the attackers' interests.
- `TT5/g0/r30` and `TT5/g0/r31`: makes Belle's late-night reaction and her motherly scolding more colloquial while preserving the protagonist's stammer and the attacker's `cold reality` threat.
- `TT5/g1/r0`: restores that only Belle, George, and old Tom remain after the other workers leave one by one.
- `TT5/g1/r1`: restores Belle's confidence that Meyer, unusually reasonable for a Southerner in her view, will actually give them permission to leave rather than merely `understand` them.
- `TT5/g1/r4` and `TT5/g1/r5`: preserves that Belle accumulated the money little by little over decades and that the drawer contains several 100-dollar bills.
- `TT5/g1/r13`: keeps George's source-explicit religious framing that Lincoln is a child of God.
- `TT5/g1/r16`: restores Meyer's explicit reason for the ordered work sequence: efficiency across several tasks.
- `TT5/g1/r18`: restores the missing deadline that failure to keep pace means the work will not be finished **today**.
- `TT5/g1/r19`: preserves every work-order quantity and corrects the water-fetch instruction to **three round trips** (`3 oufuku`) with two buckets, rather than the ambiguous old `three trips`.
- `TT5/g2/r7`: restores Tom's statement that Meyer gave him the bills **this morning**.
- `TT5/g2/r8`: corrects the addressee logic: Tom is speaking to Belle and says that **thanks to George** they can buy livestock; the old `With your help` incorrectly credited Belle.
- `TT5/g2/r10`: restores Tom's worsening eyesight and request to have the money counted while giving his strongly colloquial Japanese a restrained folksy English voice.
- `TT5/g2/r12`: preserves the source's dated/racist framing of the quiz question about troops fighting Indigenous people to protect white settlers. The wording is not modernized into a different historical claim.
- `TT5/g2/r18`: restores `hatsudenki` as `generator` in the Edison-inventions question rather than the looser `dynamo`.
- `TT5/g2/r19`: restores the trader's explicit praise that **all** the questions were answered correctly before he begins the transaction.
- `TT5/g2/r22` through `TT5/g2/r26`: strengthens Tom's rural/folksy voice while preserving the exact livestock arithmetic: $1,000 total, 50 animals, cows at $120, sheep at $30, and pigs at $5.
- `TT5/g2/r28` and `TT5/g2/r29`: preserves the measuring puzzle exactly: an empty 1-liter bottle, full 500 ml and 300 ml bottles, and a target of 700 ml in the 1-liter bottle with no measurement marks.
- `TT5/g3/r12`: preserves Belle's relief that the work is finally done and that they can leave the South.
- `TT5/g3/r13`: restores that Meyer's proposed solution is for Belle to keep working there until she can save the money **again**, sharpening the source's paternalistic complacency after the robbery.
- `TT5/g3/r19`: restores that light is leaking out from a cave on the far bank rather than merely describing the cave as generally lit.
- `TT5/g3/r23`: keeps the sculpture/object as a hand-shaped form reaching to grasp something and the protagonist's sense of having seen it before.
- `TT5/g3/r25`: preserves the cultist's explicit **soul pact** and claim that they will create the dark history the Devil desires, without escalating that into an invented statement that they literally sold their souls.

## Character/register decisions

### George / protagonist

George's spoken dialogue is earnest and straightforward. The protagonist's internal observations remain contemporary and compact. Source stutters, exertion cries, uncertainty, and physical distress remain performance information rather than being normalized away.

### Belle

Belle is warm, practical, and colloquial with George, while speaking much more deferentially to Meyer when asking permission to leave. Her Japanese has marked flavor, but the English avoids racial eye-dialect or a fabricated Southern caricature.

### Tom

Tom's forms such as `wakaranee`, sentence-final `da`, and `manzu` give him an unmistakably rustic/working-class texture. The English reflects that through contractions, blunt syntax, and informal phrasing rather than misspelling words to imitate a specific accent.

### Livestock trader

The trader's `-ja`, `-kanou`, and `shitchoru` mark him as older and folksy. His English is terse, slightly old-fashioned in rhythm, and sharper during the quiz, including the source-explicit `aho` as `Idiot.`

### Meyer

Meyer speaks with the authority of an employer/master and frames the chapter's labor as orderly practical management. The pass does not make him more openly vicious than the Japanese, but it preserves the controlling assumptions in his instructions and his complacent response when Belle's savings are stolen.

### Night attackers

Their racism, whipping, theft, and threats are intentionally direct because the Japanese is direct. The pass neither sanitizes those scenes nor imports historically plausible slurs or additional cruelty that the source itself does not contain.

## Gameplay-critical puzzle language

TT5 contains several information-dense puzzles. The revised text preserves:

- 28 cotton baskets at 5 kg each;
- 120 pieces of firewood at 70 cm each;
- a 10-minute rest;
- two water buckets carried for three round trips;
- one hour of weeding;
- a 15-minute rest;
- four roof repairs;
- the livestock problem's $1,000 / 50-animal total and all three prices;
- the 1 L / 500 ml / 300 ml milk-bottle capacities and 700 ml target;
- the source's historical quiz framing, including dated material where explicitly present.

## Display-safety revision

Runtime/visual review in the preceding chapters established a practical target of no more than 23 visible characters between control events because exact-24-cell segments can appear clipped or lose right-edge punctuation even when they satisfy the repository's nominal 24-tile validator.

The pre-pass TT5 translation contained 45 records with at least one exact-24-cell segment. Every one of those boundary records was revised.

## Validation

The final TT5 candidate contains 123 scenario records and changes 58 of them.

Structural/editorial validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters anywhere in TT5;
- maximum final segment width: 23 characters;
- all 45 prior exact-24 boundary records revised;
- no new character repertoire introduced relative to the prior TT5 English text;
- revised TT5 visible text is 126 characters shorter overall than the prior branch version.

These checks validate text structure, source fidelity, and the stricter display-width policy only. Raw-character savings are useful headroom but are **not** proof of dictionary-compressed packed fit. The canonical compression/release build remains the required fit gate before release approval.
