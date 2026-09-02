# TT4 voice and prose pilot

This pass continues the source-first voice/prose revision through the Ancient Athens and Greek-underworld chapter.

## Editorial direction

- Preserve exact Japanese meaning and control-code order.
- Keep the protagonist's internal observations contemporary even while he occupies the physician Nicras.
- Keep Dario respectful and competent rather than generic exposition.
- Keep the priest educated and slightly fussy, the merchant brisk and rougher under pressure, and Aristotle articulate without pseudo-classical English.
- Differentiate the gods: Athena is serene and compassionate; Hermes brusque and practical; Artemis casual; Hades dry and bureaucratic; Poseidon an older-authority gag.
- Preserve Cerberus's deliberate contrast between a casual `osu` greeting and the pompous `wagahai` riddle-master persona.
- Give the fisherman dry older/folksy flavor without a pirate accent or phonetic caricature.
- Keep the Devil theatrical and cruel, including source-explicit profanity and threats, without inventing harsher material.

## Source-grounded restorations and corrections

- `TT4/g0/r0`: restores the Devil's physical disgust in `hedo ga deru`; the statue is so ugly he says he could puke.
- `TT4/g0/r9`: makes the priest's reaction to the beheaded goddess statue more natural while preserving his suspicion of local thugs and his sacrilege judgment.
- `TT4/g0/r12`: restores Athena's direction to seek the gods' aid/counsel before entering the underworld rather than reducing it to a generic `Ask the gods.`
- `TT4/g1/r14`: preserves the merchant's rough, frightened register while keeping the explicit fact that the boy was already dead when he found him.
- `TT4/g2/r14`: corrects the protagonist's `saa...` from a definite `No...` to the source's uncertainty (`Not sure...`) and restores the boy's refined appearance without prematurely identifying him as nobility.
- `TT4/g2/r15`: restores the source's order of description: a winding road with shabby houses lining it.
- `TT4/g3/r9`: restores Artemis's casual `watashi ja wakannai` as `I dunno.` rather than formal `I do not know.`
- `TT4/g3/r23`: corrects Hades's `yoku wakatta na` from `You know me` to `You got it.`
- `TT4/g4/r8`: fixes puzzle logic. Pythagoras is a mathematician who does not sit next to a philosopher; he does not generally `shun philosophers.`
- `TT4/g4/r9`: fixes puzzle logic by restoring that the speaker tells the player to ask the neighboring historian, not merely any historian.
- `TT4/g4/r15`: restores source-explicit `kuso gaki` as `Little shit...` rather than sanitizing it to `Brat...`.
- `TT4/g4/r20`: restores the Devil's repeated threat in `nando demo`: he will keep killing the protagonist, not merely kill him `again` once.
- `TT4/g5/r0`: keeps the medical observation blunt and clinical: stopped pulse/heart and dilated pupils establish that Alexander is already beyond ordinary treatment.
- `TT4/g5/r1`: preserves the divine voice's claim that the child has been chosen by God for a special mission.
- `TT4/g5/r8` through `TT4/g5/r18`: strengthens the fisherman's old, dry, sharp voice while preserving the herb and quiz content.

## Character/register decisions

### Nicras / protagonist

Nicras's social role is that of a physician, but the internal voice belongs to the 1995 protagonist. Internal observations therefore use contractions and direct modern phrasing instead of pretending that possession changes his native register.

### Dario

Dario remains deferential to Dr. Nicras. His English is concise, competent, and polite rather than stiff.

### Aristotle

Aristotle remains articulate and status-conscious, but the translation avoids fake classical diction. His search for the missing boy preserves his politeness, escalating anxiety, and the boy's refined appearance.

### Gods

The gods deliberately do not share one generic divine register. Athena is composed and compassionate; Hermes is brusque; Artemis is conversational; Hades behaves like a dry gatekeeper; Poseidon's short refusal lands as a bureaucratic joke.

### Cerberus

The source first gives Cerberus the casual greeting `osu`, then has him refer to himself with pompous `wagahai`. The English therefore keeps `Yo.` before shifting into a cocky underworld-bouncer/riddle-master performance.

### Fisherman

His `ja` and `shitchoru` mark him as an old, folksy speaker. The English uses dry older phrasing and blunt reactions such as `Idiot.` without assigning him a specific real-world accent.

## Display-safety revision

Runtime/visual review of TT3B showed that technically legal 24-cell segments can look clipped or force punctuation loss at the right edge. TT4 therefore uses the stricter practical target of no more than 23 visible characters between control events.

The pre-pass TT4 workbook contained 49 records with at least one exact-24-cell segment. Every one of those boundary records was revised. This is intentionally stricter than the repository's general 24-tile validator and is based on observed runtime/visual behavior rather than a claim that the engine itself has only 23 physical columns.

Puzzle clues were shortened only when their deduction logic could be preserved. In two cases (`TT4/g4/r8` and `TT4/g4/r9`), source review showed that the old English had already lost adjacency information, so the pass corrects the logic rather than merely compressing wording.

## Validation

The final TT4 candidate contains 183 scenario records and changes 80 of them.

Structural validation found:

- exact control-event sequence preserved for every changed record;
- no control-delimited English segment longer than 23 visible characters anywhere in TT4;
- maximum final segment width: 23 characters;
- all 49 prior exact-24 boundary records revised;
- no unsupported English-font characters introduced;
- revised TT4 visible text is 186 characters shorter overall than the prior branch version.

The raw-character reduction provides useful headroom but is not proof of packed fit. TT4 has historically been a very tight dictionary-compressed bank (roughly 3 bytes spare), so the canonical compression/release-build fit gate remains mandatory before release approval.
