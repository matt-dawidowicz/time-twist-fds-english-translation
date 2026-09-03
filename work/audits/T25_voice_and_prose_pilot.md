# T25 voice and prose pilot

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

This pass continues the source-first voice/prose revision through the Civil War continuation involving Meyer, Lincoln, Belle, George, the plantation mansion, and the flooded-island escape.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep the protagonist's internal observations direct and contemporary.
- Keep George young, earnest, easily excited, and visibly nervous where the Japanese marks stutters or hesitation.
- Keep Lincoln measured and polite without pseudo-historical or presidential grandiloquence.
- Keep Meyer's public politeness distinct from his private contempt, opportunism, coercion, and rough commands.
- Preserve the soldiers' sarcasm about Meyer's political opportunism.
- Preserve source-explicit slavery/racism and dehumanizing language without sanitizing it, while not inventing stronger insults or threats absent from the Japanese.
- Preserve the coyote-crossing puzzle information exactly enough for the gameplay logic to remain recoverable.

## Source-grounded restorations and corrections

- `T25/g0/r2`: restores that Meyer blames the men from **last night** for Lincoln's disappearance; the old English dropped the time reference.
- `T25/g0/r3`: restores Meyer's surprised `oo` reaction as `Oh!` before his relief that Lincoln is safe.
- `T25/g0/r4`: preserves Meyer's stammer and Lincoln's polite `This time, I will take you` formulation without making Lincoln unnaturally stiff.
- `T25/g0/r5`: keeps the protagonist's defiant promise to follow the Devil to the ends of Hell while fitting the observed display-safe width.
- `T25/g0/r11`: strengthens the soldiers' source-explicit sarcasm: once the South began losing, Meyer defected and supplied intelligence; the final line admires his skill at getting by rather than treating it as neutral survival exposition.
- `T25/g0/r12`: restores Lincoln's counterfactual meaning: with men like Meyer, the war would not have happened. The old English `no war would start` flattened the tense and implication.
- `T25/g0/r18`: restores Lincoln's promise that America **will be reborn**, followed by a time when Belle and George can fully use their abilities.
- `T25/g0/r22`: corrects the interaction from `Coffee fills both cups` to the protagonist pouring coffee into a cup; the Japanese does not state that both cups are filled.
- `T25/g0/r28` and `T25/g0/r29`: give George a more natural youthful sense of wonder while preserving his excitement at the guest bed and speaking with the President.
- `T25/g1/r0`: restores Meyer's `omoshiroi tokoro` as taking Belle and George somewhere interesting/fun rather than the unrelated `a fine treat`.
- `T25/g1/r5` and `T25/g1/r6`: restore that the cloth hood/bag has openings for the eyes and nose; `slit cloth hood` was too vague.
- `T25/g1/r17`: restores Meyer's sharper `What is it / need something?` challenge and the protagonist's casual `No, nothing...` rather than formal `It is nothing`.
- `T25/g1/r19`: preserves Meyer's ingratiating request for appointment as Lincoln's special adviser and his claim that a Southerner would provide political balance.
- `T25/g1/r20`: removes the invented `That is, if appointed...`. The Japanese says Meyer could suppress the attackers' movements, but does not make that phrase an explicit condition.
- `T25/g1/r21`: keeps Lincoln's dismissal as a waste of time and retains the sudden whistle beat.
- `T25/g1/r22`: preserves Lincoln's startled stammer about the guards and Meyer's reveal that the coffee contained a sleeping drug.
- `T25/g1/r23`: corrects `baka o iu na` from the stronger personal insult `You fool!` to `Nonsense!` / `Don't be absurd` territory.
- `T25/g1/r24`: preserves Meyer's source-explicit description of the island as the graveyard of disobedient slaves and the one-hour flooding threat without euphemism or added brutality.
- `T25/g1/r30`: restores Meyer's rough `omae wa damattero` as `You shut up!`, distinguishing his private register from his public politeness.
- `T25/g2/r4`: preserves the puzzle rule: coyotes remain calm against groups equal to or larger than themselves and attack smaller groups. Meyer's contemptuous `Forget those slaves` and instruction for Lincoln to take the boat alone are retained as source-explicit dialogue.
- `T25/g2/r6` through `T25/g2/r11`: makes George's escape/puzzle reactions more natural while preserving the underlying state information and urgency.

## Character/register decisions

### Meyer

Meyer uses politeness strategically around Lincoln, but his speech becomes rough and controlling toward Belle and George. The English keeps that split. His opportunism is also explicit in the soldiers' conversation: he changed sides when the Confederacy began losing and supplied intelligence to the Union.

### Lincoln

Lincoln remains composed, polite, and concise. The translation avoids both modern slang and invented nineteenth-century rhetoric. When he becomes alarmed, the Japanese itself supplies the stammer; when he rejects Meyer, the English stays firm without escalating `baka o iu na` into a stronger personal insult.

### George

George is earnest, excitable, and frightened. His source stutters are preserved, while awkward literal constructions are replaced with short youthful reactions such as `Wow...` where the Japanese conveys excitement or emotional impact rather than formal awe.

### Protagonist / Belle

The protagonist's internal voice remains contemporary despite occupying Belle. Short interactions therefore favor contractions and direct phrasing where the Japanese is casual.

### Soldiers

The soldiers' exchange about Meyer is deliberately sarcastic. `yowatari no umasa` is not neutral praise for survival skill; it is admiration for how deftly Meyer navigates changing circumstances to his own advantage.

## Display-safety revision

Runtime/visual review from the preceding chapters established a practical target of no more than 23 visible characters between control events, because exact-24-cell segments can appear clipped or lose right-edge punctuation even when they pass the repository's nominal 24-tile validation.

The pre-pass T25 translation contained 24 records with at least one exact-24-cell segment. Every one of those boundary records was revised.

## Validation

The final T25 candidate contains 76 scenario records and changes 51 of them.

Structural/editorial validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters anywhere in T25;
- maximum final segment width: 23 characters;
- all 24 prior exact-24 boundary records revised;
- no new character repertoire introduced relative to the prior T25 English text;
- revised T25 visible text is 63 characters shorter overall than the prior branch version.

These checks validate text structure and display-width policy only. The raw-character reduction provides useful headroom but is **not** proof of dictionary-compressed packed fit. The canonical compression/release build remains the required fit gate before release approval.
