# TT6A voice and prose pilot

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

This pass continues the source-first voice/prose revision through the circa-4-BC Nazareth chapter: the protagonist as Kashim the donkey, Joseph and Mary's estrangement and reconciliation, the Devil's false-angel intervention, the village elder's history/prophecy speech, and the Roman census order that sends Joseph toward Bethlehem.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep Kashim/the protagonist's internal voice contemporary and comic; the comedy comes from being trapped in a donkey body, not from giving ancient characters invented parody accents.
- Keep Joseph emotional, colloquial, insecure, and occasionally melodramatic. His Japanese uses plain masculine speech rather than Biblical grandeur.
- Keep Mary gentle, hurt, hopeful, and conversational. Preserve the distinction between what she believes and what Joseph believes.
- Give the village elder restrained older-role flavor from `washi`, `-ja`, and `-nou` without rewriting him in faux-King-James English.
- Keep the Roman soldier blunt and authoritarian.
- Let the Devil become deliberately mock-formal while posing as an angel; this register contrast is source-supported and central to the gag.
- Preserve source-explicit religious claims, irreverence, bodily comedy, profanity, and the Devil's attempt to have the child named `Demon` without sanitizing or amplifying them.
- Do not borrow wording from the removed external translation.

## Source-grounded restorations and corrections

- `TT6A/g0/r12`: the Japanese is specifically Joseph realizing Kashim does not want to **listen** (`kikitakunai ka`); the old `So you refuse...` broadened the meaning.
- `TT6A/g0/r13`: fixes a material speaker-attribution problem. After Kashim's bray, `mou nani mo shinjirarenai / konyaku nante kaishou da` is still **Joseph** speaking: he says he can believe nothing and breaks off the engagement. The old English visually made those lines read as if the donkey/protagonist said them.
- `TT6A/g0/r13`: keeps Joseph's oath that he has never even held Mary's hand and his disbelief at Mary's claim that she has no explanation for the pregnancy.
- `TT6A/g0/r17`: restores Joseph's omitted `usotsuku na` (`Don't lie`) when he insists the bracelet came from Mary.
- `TT6A/g0/r18`: keeps Joseph's continued refusal to believe the angel-message story and removes the unsupported narrator label `fiend`; the Japanese simply says that **that guy** suddenly came down from the sky.
- `TT6A/g0/r19`: renders `shinpai shinaide Maria to kekkon suru ga yoi` directly as reassurance followed by an order to marry Mary, rather than the slightly shifted `Wed her without fear.` The Devil's formal angel-pose is otherwise preserved.
- `TT6A/g1/r8`: preserves the interrupted comic thought that there is no way the protagonist can eat the hay, followed by the realization that it somehow tastes good.
- `TT6A/g1/r14`: `chikara naku` describes Mary working without energy/listlessly; the old `turns a mill weakly` could read as a statement about physical strength rather than mood.
- `TT6A/g1/r17`: clarifies the inspected object as a hand-cranked wheat mill, matching the source explanation that turning the handle grinds wheat.
- `TT6A/g1/r23`: restores the omitted **last night** (`yuube`) in Mary's account of receiving the angel's message and keeps her complaint that Joseph will not believe/credit her.
- `TT6A/g1/r25` and `TT6A/g2/r2`: correct `furimuite kureru made`. Mary is waiting until Joseph **turns toward her again emotionally**, not simply until he physically `returns`.
- `TT6A/g1/r27`: restores Mary's immediate denial/confirmation beat when she concludes the necklace came from Joseph.
- `TT6A/g1/r28`: restores `omotteta` as what Mary **thought** Joseph would do, rather than the stronger old `I knew` formulation.
- `TT6A/g1/r31`: restores the concrete warning `ha ga oreru wa yo`: Kashim will **break a tooth / his teeth**. `Mind your teeth` softened the consequence.
- `TT6A/g2/r3`: clarifies `motte itte kureru` as Kashim **carrying/taking the bracelet for Mary**, rather than merely taking possession of it.
- `TT6A/g2/r7`: restores `yakekuso no you ni`: Joseph is planing in a frustrated/desperate fury, not merely `grimly`.
- `TT6A/g2/r13`: keeps Joseph's accusation that Mary invented the story because she had tired of him and that the pregnancy story itself must be a lie.
- `TT6A/g2/r20`: restores the wedding-gift context of Joseph's necklace and retains both source curse beats instead of reducing the outburst to a single `Damn!`.
- `TT6A/g2/r21`: restores the physical action `kuwaeta`: Kashim takes/holds the necklace in his mouth.
- `TT6A/g2/r26`: restores the uncertainty in `...you da`; the elder **seems** to be waiting rather than the narration asserting it as a fact.
- `TT6A/g2/r31`: keeps the elder's source sequence of wandering, wars, oppression, successive foreign masters, continued hardship, and promised savior while making the English less telegraphic.
- `TT6A/g3/r0`: corrects the prophecy location from `Judah` to **Judea** (`yudaya no chi`) and keeps the prophecy that a savior will arise from Bethlehem.
- `TT6A/g3/r3`: keeps the soldier's Roman census order blunt and direct, including Joseph's Bethlehem birthplace and instruction to go there and register immediately.

## Character/register decisions

### Kashim / protagonist

The protagonist is still a contemporary person internally even while occupying a donkey. Contractions, short reactions, disbelief, eating noises, brays, and physical interaction text therefore remain quick and modern. The donkey sounds are performance information and are preserved rather than normalized into ordinary speech.

### Joseph

Joseph is emotionally volatile but not written as a Biblical patriarch. His source uses ordinary plain masculine Japanese (`ore`) and he swings from despair, suspicion, and profanity to credulous relief when the Devil poses as an angel. The English keeps that comic emotional range without adding archaic scripture diction.

### Mary

Mary is softer and more hopeful than Joseph but not ceremonially formal. Her central emotional point is that she expects Joseph eventually to believe her and turn back toward her; the revised wording keeps that distinction clear.

### Village elder

The elder's `washi`, `-ja`, and related forms identify an elderly storyteller/authority register. The English gives him steady, slightly measured phrasing but avoids `thee`, `thou`, `verily`, or other invented Biblical English.

### Roman soldier

The soldier addresses Joseph bluntly and delivers Augustus's order as an instruction, not a polite request. The English is terse and institutional rather than theatrically Roman.

### Devil posing as an angel

The Devil deliberately adopts formal, authoritative language while claiming to carry God's voice. That elevated pose is retained because the contrast with Joseph's credulous responses and the proposed name `Demon` is the joke; the translation does not make all ancient dialogue equally grandiose.

## Display-safety revision

Runtime/visual review in preceding chapters established a practical target of no more than 23 visible characters between control events because exact-24-cell segments can appear clipped or lose right-edge punctuation even when they satisfy the repository's nominal 24-tile validator.

The pre-pass TT6A translation contained 26 scenario records with at least one exact-24-cell segment. Every one of those boundary records was revised.

## Validation

The final TT6A candidate contains 100 scenario records and changes 46 of them.

Structural/editorial validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters anywhere in TT6A;
- maximum final segment width: 23 characters;
- all 26 prior exact-24 boundary records revised;
- no new character repertoire introduced relative to the prior TT6A English text;
- revised TT6A visible text is 86 characters shorter overall than the prior branch version.

These checks validate source fidelity, text structure, voice/register decisions, and the stricter display-width policy only. Raw-character savings provide useful headroom but are **not** proof of dictionary-compressed packed fit. The canonical compression/release build remains the required fit gate before release approval.
