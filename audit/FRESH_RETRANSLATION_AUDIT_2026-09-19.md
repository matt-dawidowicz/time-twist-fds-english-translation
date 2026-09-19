# Fresh Japanese retranslation audit — 2026-09-19

This audit treats exact Japanese source as authoritative and v17 only as the current
playable baseline. It intentionally ignores legacy-English precedence.

## Classification

- RETRANSLATE: source meaning, speaker identity, or natural English should change.
- LOCALIZATION: source is understood, but English puzzle/cultural logic must adapt.
- TECHNICAL: natural English is known, but renderer/control constraints may block it.
- RUNTIME REVIEW: source text alone cannot settle the correct presentation.
- OPTIONAL: editorial improvement, not a correctness failure.

## TT1A

Provisional result: translation-complete, with two optional personality-test edits.

- TT1A/g0/r14 — OPTIONAL: current yes/no wording is serviceable; source is closer to
  "Do you hate working when it cuts into your free time?"
- TT1A/g0/r17 — OPTIONAL: source nuance is "in the end, the only one who can protect
  you is yourself"; consider "Do you believe that, in the end, you can only rely on
  yourself?"

## TT1B

- TT1B/g2/r6 — RETRANSLATE: Japanese explicitly says "That voice—you're the person
  from before." Current shortened English drops the second clause.
- TT1B/g0/r16 — RETRANSLATE: source says a pharaoh used the bell, not necessarily
  pharaohs collectively. Prefer "A legendary bell said to have been used by a
  pharaoh in ancient Egypt to ward off evil."
- TT1B/g3/r23 — RETRANSLATE: "Lord, forgive our sins and the sins of our forefathers!"
- TT1B/g4/r4 — OPTIONAL: preserve emphasis in "Take good care of my body."
- TT1B/g1/r12 — OPTIONAL: "You've got lucky earlobes."
- TT1B/g2/r5 — RETRANSLATE: contextualize jiageya naturally as "I'm not here to force
  you out."
- TT1B/g4/r7 — OPTIONAL: sore ga dou shita -> "So what?"
- TT1B/g0/r5 — OPTIONAL: source locates the sign at the entrance.
- TT1B businessman voice — LOCALIZATION: preserve marked Nagoya/Owari comic
  characterization through consistent diction/syntax, not an invented U.S. accent.

## TT2 / T22

- TT2/g0/r7 — OPTIONAL/RUNTIME REVIEW: koshi o nukasu is physical collapse from fright;
  "He's collapsed in fright" may fit better than generic "terrified."
- TT2/g0/r15 — RUNTIME REVIEW: nani o! is context-sensitive ("What the—?!", "Hey!",
  "What are you doing?!").
- TT2/g0/r22 — RETRANSLATE: formal church decree should preserve tavernkeeper Lugot
  relationship and "in the name of the Church."
- TT2/g1/r12 — LOCALIZATION: Crusades quiz should ask which holy city/holy land was
  sought; verify answer choices before final English.
- TT2/g1/r21 — RETRANSLATE after source-byte verification; likely "You're giving it
  to me? Heh-heh!"
- TT2/g1/r26 — OPTIONAL: "Oh, you want some wine? Here—it's your reward."
- TT2/g3/r26 — RETRANSLATE: "Wait until her trial is over."
- TT2/g3/r31 — RETRANSLATE: formal reported church edict, not clipped exposition.
- TT2/g4/r12 — RETRANSLATE: tsurete kaeru -> "Shall we take him home?"
- TT2/g4/r27 — RETRANSLATE: Jeanne is suspended/hoisted by a thick rope.
- T22/g0/r4 — RETRANSLATE: "No… just talking to myself."
- T22/g0/r6 — RETRANSLATE: "I won't speak to churchmen."
- T22/g0/r10 / g1/r1 — RETRANSLATE: pact uses "ruler of darkness", not "lord of
  night"; restore solemn legal/ritual register.
- T22/g0/r11 — RETRANSLATE: "It's definitely the bishop's handwriting!"
- T22/g1/r6 — RETRANSLATE: restore bishop's sadistic "more interesting if a bigger
  crowd gathers" nuance.
- T22/g1/r11 — RETRANSLATE: hanaseba wakaru -> "We can talk this out!"
- T22/g1/r20 — RETRANSLATE: major Jeanne revelation should use natural prophetic
  register: "Don pure white armor and fight for your homeland. In your wake, a new
  path will surely open…"

## TT3A / TT3B

- TT3A/g0/r28 — REVIEW: occult oath "human fat and sharpened stakes" is source-faithful
  but okite may read more naturally as "rites/precepts" than "law."
- TT3A/g2/r29 — OPTIONAL: nigirishimeru -> "clutching a scrap of paper."
- TT3A/g2/r30 — RUNTIME REVIEW: torn-note spatial order requires screenshot/nametable
  evidence; blue ink is source-verified.
- TT3A/g3/r3 — RETRANSLATE: tsute o tadotte + boumei -> "Through my contacts, I asked
  Rebecca for asylum/help defect"; current wording changes agency and weakens boumei.
- TT3A/g3/r9 / g3/r29 — CONSISTENCY: identical coded gesture should use identical
  English wording.
- TT3B/g0/r24 — RUNTIME REVIEW: unseen speaker can be Hitler or Devil; do not infer
  label from text alone.
- TT3B/g1/r21 — KEEP UNLABELED unless runtime evidence says otherwise; the missing
  ordinary label is dramatic information.
- TT3B/g1/r23 — RETRANSLATE: restore Hitler's contractual duty/obligation to continue
  evil until the pact expires.
- TT3B/g1/r24 — OPTIONAL: explicitly preserve possession mechanism ("Whose body am I
  going to end up possessing next…?").

## TT4

Major retranslation/localization bank.

- TT4/g3/r23 — RETRANSLATE Hades: "Well done. I am Hades, guardian of the
  underworld. Very well—I'll make an exception and let you pass."
- TT4/g4/r4 — RETRANSLATE Cerberus exchange in natural conversational English;
  preserve casual "Yo", gateway-to-afterlife explanation, and explicit promise to
  return the child if answers are correct.
- TT4/g4/r5 — RETRANSLATE: "Talk to all five of them, then tell me who each one is."
- TT4/g4/r6 — RETRANSLATE: "Now tell each man his name to his face."
- TT4/g4/r7 — OPTIONAL: "Too bad. Start over."
- TT4/g4/r9 — RETRANSLATE: "Ask the historian sitting next to me."
- TT4/g4/r11 — LOCALIZATION BUG: Japanese four-character-name clue must become
  five-letter-name in English. Homer and Plato are both 5 letters; all other candidate
  names are longer, preserving puzzle logic.
- TT4/g4/r13 — RETRANSLATE Cerberus success line with natural voice and promise.
- TT4/g4/r14 — RUNTIME REVIEW: anonymous "Wait." immediately before Devil entrance;
  determine whether to label Devil, Voice, or leave anonymous.
- TT4/g5/r7 — RETRANSLATE quiz: "What were the independent city-states of ancient
  Greece called?"
- TT4/g5/r12 — RETRANSLATE quiz: "What was the temple dedicated to Athena called?"
- TT4/g5/r15 — RETRANSLATE proverb: "No tears dry faster than those shed for
  another's misfortune."

## TT5 / T25

- TT5/g0/r6 — RETRANSLATE racist attacker without sanitizing source contempt:
  emancipation does not mean the freedmen may "act high and mighty" around him.
- TT5/g0/r30 — RETRANSLATE idiomatically: "cold, hard reality."
- TT5/g0/r31 — RETRANSLATE: tachi ga warui gives a mean/cruel-joke nuance, stronger
  than simply "Don't tease your mother."
- TT5/g2/r12 — LOCALIZATION: verify answer; likely ask which U.S. military force
  fought Native Americans to protect white settlers in the West.
- TT5/g2/r15 — LOCALIZATION: if answer is Black Ships, ask what Commodore Perry's
  ships were called, not generic "what American fleet".
- TT5/g2/r16 — RETRANSLATE with attribution: "the novel said to have helped spark
  the Civil War."
- TT5/g2/r18 — RETRANSLATE question structure: identify the third of Edison's stated
  "three great inventions" alongside phonograph and generator.
- T25/g2/r7 — RETRANSLATE definite omission: source explicitly says "Let's save all
  the coyotes too!"
- T25/g0/r11 — KEEP later "lands on his feet" localization for sarcastic yo-watari
  nuance.
- T25/g1/r22 — TECHNICAL: natural "Mr. President" currently exceeds the native
  pre-CTRL:1 row budget; must be solved by layout/engine work or remain documented.

## TT6A / TT6B / TT6C / TT6D

- TT6A/g2/r7 — RETRANSLATE nuance: yakekuso -> planing wood in frustration/desperation.
- TT6B/g1/r13 — TECHNICAL: natural "Sleep by the road" was shortened to "Sleep out"
  for native control staging; retest under current layout engine.
- TT6B/g2/r18 — RETRANSLATE mare joke: "No nibbling—eat it in one big bite!"
- TT6C/g1/r9 — RETRANSLATE Devil voice: "Ominous? On the contrary—it's the perfect
  name."
- TT6C/g1/r15 — RETRANSLATE for clarity: explicitly return to the museum "before the
  Devil appeared", not ambiguous "before he arrived."
- TT6C/g2/r6 — RETRANSLATE vivid source metaphor; nuclear bombs are thrown back and
  forth like catch rather than merely "weapons were exchanged."
- TT6C/g3/r8 — MAJOR MISTRANSLATION: いえす is Iesu = Jesus, not English "yes".
  Correct sequence: "Me: Jesus. / Mary and Joseph: Jesus… / Me: Right. Jesus Christ."
- TT6D/g0/r5 — current natural "You'll meet a wonderful man" is source-faithful.

## Next

1. Complete source-side pass over records not highlighted by previous review metadata.
2. Verify quiz answers and spatial puzzles against fixed UI/runtime evidence.
3. Materialize proposed canonical English independently of legacy translation layers.
4. Run layout/control/bank-capacity checks; document every natural line that cannot fit.
5. Build v18 only after the audit corpus is stable.
