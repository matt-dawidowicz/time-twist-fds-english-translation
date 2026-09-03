# TT6D voice and prose pilot

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

This pass completes the source-first voice/prose revision of the short 1995 epilogue: the protagonist and the girl wake after the restored timeline, he recognizes her while she does not remember him, the recurring incantation returns during another earthquake, her morning fortune closes the romantic loop, and the final unexplained growl keeps the supernatural threat alive.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep the protagonist casual, awkward, and contemporary rather than turning the reunion into sentimental or elevated prose.
- Keep the girl's voice warm, polite-to-friendly, and increasingly confident without exaggerating Japanese feminine sentence endings into an English caricature.
- Preserve the fact that the protagonist remembers their shared history while the girl apparently does not.
- Preserve the established incantation spelling `Maradul Barao Garadura` exactly; do not normalize it to another source variant.
- Preserve the morning-fortune callback as an actual prediction of meeting a desirable man rather than inventing a different romantic proposition.
- Keep the final growl deliberately unidentified.
- Do not borrow wording from the removed external translation.

## Source-grounded restorations and corrections

- `TT6D/g0/r1`: keeps the girl's relief that she thought **she herself was dead**. The protagonist immediately recognizes her and reacts as though it has been a long time, while her polite `dokoka de oaishimashita` makes clear that she can only wonder whether they have met somewhere before. The revised English uses the control break to preserve `somewhere / have we met before...?` instead of flattening that beat. `okashina hito` remains an amused `What a funny guy.` rather than a stronger insult.
- `TT6D/g0/r4`: preserves the protagonist's startled `Y-yes!` and `!!` reactions when the girl unexpectedly knows the incantation. The old English split the **first** `Maradul Barao Garadura...` across the existing `{CTRL:0}`, placing `Garadura... Me: !!` after the control even though the Japanese completes the incantation before that event. The revision keeps the complete incantation before `{CTRL:0}` while preserving the same control-code sequence.
- `TT6D/g0/r4`: the exact incantation spelling remains `Maradul Barao Garadura`, consistent with this source occurrence. To keep the full phrase within the stricter display limit, the tentative first use ends with a single period, the next repetition is unpunctuated, and the final repetition receives `!`; this retains an escalation across the three uses without creating a 24-cell segment.
- `TT6D/g0/r5`: retains the explicit **this-morning** framing through `Morning fortune` and corrects the prediction itself toward `suteki na dansei to no deai ari`: an encounter/meeting with a desirable man. The prior `"A fine man awaits you."` was natural but changed the proposition from **meeting** a man to a man already waiting for her. `"You meet a great man."` keeps the fortune-like prediction and the source's encounter meaning within 23 cells.
- `TT6D/g0/r6` and `TT6D/g0/r7`: leave the final ominous growl and the protagonist's `Ack!` reaction unexplained, as in the source. The epilogue does not identify the growling voice.

## Character/register decisions

### Protagonist

The protagonist has just experienced the entire historical journey and recognizes the girl immediately, but his English remains casual and awkward: `Ah... been a while`, followed by embarrassed laughter when he realizes she does not remember him. The script does not explain the mismatch for the player or make him suddenly solemn.

### Girl

The girl begins relieved and slightly formal when asking whether they have met, then becomes amused and confident. Her later `Leave it to me!` during the earthquake is deliberately decisive. Japanese feminine-coded endings are conveyed through tone rather than a fabricated accent or excessively delicate diction.

### Incantation and fortune callbacks

Both callbacks are treated as continuity-critical text. The incantation retains the established source spelling for this occurrence. The fortune retains the morning timing and the romantic `meeting a wonderful/great man` proposition rather than being rewritten into a different prophecy for elegance.

## Display-safety revision

Runtime/visual review in preceding chapters established a practical target of no more than 23 visible characters between control events because exact-24-cell segments can appear clipped or lose right-edge punctuation even when they satisfy the nominal 24-tile validator.

The pre-pass TT6D translation contained three scenario records with at least one exact-24-cell segment: `TT6D/g0/r1`, `TT6D/g0/r4`, and `TT6D/g0/r5`. All three were revised.

The incantation required special handling because `Maradul Barao Garadura` is already 22 visible characters before punctuation. The revision does **not** abbreviate or respell the phrase; instead it adjusts speaker labeling/punctuation around the existing controls so the source wording remains intact and the full incantation is no longer split across the first control event.

## Validation

The final TT6D candidate contains 8 scenario records and changes 3 of them.

Structural/editorial validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters anywhere in TT6D;
- maximum final segment width: 23 characters;
- all 3 prior exact-24 boundary records revised;
- no new character repertoire introduced relative to the prior TT6D English text;
- revised TT6D visible text is 12 characters shorter overall than the prior branch version.

These checks validate source fidelity, epilogue continuity, text structure, voice/register decisions, and the stricter display-width policy only. Raw-character savings provide useful headroom but are **not** proof of dictionary-compressed packed fit. The canonical compression/release build remains the required fit gate before release approval.
