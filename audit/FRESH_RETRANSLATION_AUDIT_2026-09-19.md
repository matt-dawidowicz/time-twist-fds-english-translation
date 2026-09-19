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
- TT1B/g2/r10 — RETRANSLATE: same omission as g2/r6; おや！そのこえはさっきのひとですね means "Ah! That voice—you’re the person from before," not merely "Ah! That voice."
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
- TT2/g1/r12 — LOCALIZATION CONFIRMED: fixed answer choices are Damascus /
  Jerusalem / Crimea, so the intended answer is Jerusalem. Rewrite the prompt to ask
  which place/city the Crusaders sought to recapture rather than vague "what land."
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

- TT3A/g4/r4 — LOCALIZATION: current "What was the French Resistance called?" is nearly tautological because the answer is Résistance. Source asks what the resistance movement in German-occupied France was called.

- TT3A/g0/r28 — REVIEW: occult oath "human fat and sharpened stakes" is source-faithful
  but okite may read more naturally as "rites/precepts" than "law."
- TT3A/g2/r29 — OPTIONAL: nigirishimeru -> "clutching a scrap of paper."
- TT3A/g2/r7 — RUNTIME REVIEW: identity of the off-screen "Wait, Cougar…" voice
  cannot be settled from text alone.
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

- TT4/g0/r3 — KEEP v17: current ROM already reads naturally as "Athena, goddess of wisdom and guardian of Athens."

- TT4/g3/r23 — RETRANSLATE Hades: "Well done. I am Hades, guardian of the
  underworld. Very well—I'll make an exception and let you pass."
- TT4/g4/r4 — RETRANSLATE Cerberus exchange in natural conversational English;
  preserve casual "Yo", gateway-to-afterlife explanation, and explicit promise to
  return the child if answers are correct.
- TT4/g4/r5 — RETRANSLATE: "Talk to all five of them, then tell me who each one is."
- TT4/g4/r6 — RETRANSLATE: "Now tell each man his name to his face."
- TT4/g4/r7 — OPTIONAL: "Too bad. Start over."
- TT4/g4/r9 — RETRANSLATE: "Ask the historian sitting next to me."
- TT4/g4/r11 — LOCALIZATION BUG CONFIRMED: Japanese says the end man's name has four
  kana. In Japanese the short-name ambiguity is Homer/Plato; in English both Homer and
  Plato are five letters while Socrates, Herodotus, and Pythagoras are longer.
  Therefore "the man at the end has a five-letter name" preserves the intended clue
  class and puzzle logic.
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
- TT5/g2/r12 — LOCALIZATION CONFIRMED: the fixed answer table contains Marine Corps /
  Cavalry, and Cavalry is the intended answer. Rewrite the prompt naturally around the
  western-frontier historical claim without changing the answer.
- TT5/g2/r15 — LOCALIZATION CONFIRMED: the fixed answer choices are Red ship / White
  ship / Black ship; the intended answer is Black ship(s). Ask what Commodore Perry's
  ships were called rather than generic "what fleet".
- TT5/g2/r16 — RETRANSLATE with attribution: "the novel said to have helped spark
  the Civil War."
- TT5/g2/r18 — LOCALIZATION CONFIRMED: the fixed answer table includes Projector,
  Cotton gin, Plow, Camera, Airplane, and VCR. The intended answer is Projector.
  Rewrite the question as the third of the game's stated Edison trio alongside the
  phonograph and generator.
- T25/g1/r17 — RETRANSLATE omission: Meyer explicitly says "What’s wrong, Belle… need something?" Current shortened line drops Belle’s name and the concerned opening.
- T25/g2/r7 — RETRANSLATE definite omission: source explicitly says "Let's save all
  the coyotes too!"
- T25/g0/r11 — KEEP later "lands on his feet" localization for sarcastic yo-watari
  nuance.
- T25/g1/r22 — TECHNICAL: natural "Mr. President" currently exceeds the native
  pre-CTRL:1 row budget; must be solved by layout/engine work or remain documented.

## TT6A / TT6B / TT6C / TT6D



- TT6A/g1/r4 — RETRANSLATE omission: source explicitly says the sweet smell of hay tickles the protagonist's nose; current wording drops hay entirely.
- TT6A/g2/r8 — OPTIONAL refinement: v17 already improved this to "Some tools really haven't changed much." Source more explicitly frames the comparison across time; consider making that temporal joke clearer, but it is no longer a mistranslation.
- TT6A/g2/r7 — RETRANSLATE nuance: yakekuso -> planing wood in frustration/desperation.
- TT6B/g2/r2 — RETRANSLATE omitted modifier: source asks which Jewish king built the magnificent/splendid Temple in Jerusalem.
- TT6B/g0/r20 — OPTIONAL/context: v17 already says "There's none left. Hang in there." If the immediately preceding interaction makes water explicit on screen, this is acceptable; otherwise prefer "There's no water left."
- TT6B/g1/r9 — RETRANSLATE natural dialogue: "Joseph: Kashim really is dependable… / Mary: He is." Current "Trusty Kashim. Truly." is translationese.
- TT6B/g1/r13 — TECHNICAL: natural "Sleep by the road" was shortened to "Sleep out"
  for native control staging; retest under current layout engine.
- TT6B/g2/r18 — RETRANSLATE mare joke: "No nibbling—eat it in one big bite!"
- TT6C/g1/r8 — RETRANSLATE ceremonial register: "This is our humble offering. Please accept it…" better preserves the marked polite/honorific Japanese.
- TT6C/g1/r9 — RETRANSLATE Devil voice: "Ominous? On the contrary—it's the perfect
  name."
- TT6C/g1/r15 — RETRANSLATE for clarity: explicitly return to the museum "before the
  Devil appeared", not ambiguous "before he arrived."
- TT6C/g2/r6 — RETRANSLATE vivid source metaphor; nuclear bombs are thrown back and
  forth like catch rather than merely "weapons were exchanged."
- TT6C/g3/r8 — MAJOR MISTRANSLATION: いえす is Iesu = Jesus, not English "yes".
  Correct sequence: "Me: Jesus. / Mary and Joseph: Jesus… / Me: Right. Jesus Christ."
- TT6D/g0/r3 — RETRANSLATE omission: source is identical to TT1B/g1/r13 and includes the girl's startled cry before "An earthquake!"; current layer reduced it to an empty "Girl: !".
- TT6D/g0/r5 — current natural "You'll meet a wonderful man" is source-faithful.

## Next

1. Complete source-side pass over records not highlighted by previous review metadata.
2. Verify quiz answers and spatial puzzles against fixed UI/runtime evidence.
3. Materialize proposed canonical English independently of legacy translation layers.
4. Run layout/control/bank-capacity checks; document every natural line that cannot fit.
5. Build v18 only after the audit corpus is stable.


## Audit-of-audit corrections

A second review of this audit confirmed the following:

- The TT4 four-kana -> five-letter clue adaptation preserves the same Homer/Plato
  short-name ambiguity rather than inventing a new solution.
- TT2/g1/r12's answer is confirmed as Jerusalem from the fixed answer table.
- TT5/g2/r12, g2/r15, and g2/r18 have confirmed answer targets of Cavalry,
  Black ship(s), and Projector respectively.
- TT3A/g2/r7 must remain in the runtime-evidence set; it was accidentally omitted
  from the first draft.
- This document currently audits the 1,299 scenario records. Fixed-address menus,
  answer labels, command labels, graphics text, and other non-scenario English still
  require a separate source-first audit before claiming full-game retranslation.


## Fixed-address / menu / answer text audit

This section is source-first and does not trust the workbook's generated
`final_natural_english_translation` field blindly. Several generated glosses are
themselves wrong in context.

### Confirmed fixes

- `TT3A/fixed/r75` — RETRANSLATE distractor: `じーぼーと` is "G-boat",
  not "Gunboat." It sits beside Nazi boat / U-boat / Banana boat as a deliberately
  patterned submarine-quiz distractor.
- `TT5/fixed/r29` — RETRANSLATE action: `みずくみ` is "Fetch water."
  Current "Water" turns a fetching task into an ambiguous noun/verb.
- `TT6B/fixed/r55` — RETRANSLATE action: `のみをとる` is "Pick off fleas"
  (or a similarly compact verb phrase), not the noun "Fleas."
- `TT6C/fixed/r46` — RETRANSLATE answer label: `さかや` is "Tavern keeper"
  in the occupation-answer set Glazier / Blacksmith / Tavern keeper / Tailor.
  "Tavern" is the wrong semantic category.

### Technical expansion candidates

- `TT3A/fixed/r84` — current "Mont" represents Montgomery. The full-word menu is
  repacked, so test whether "Montgomery" now fits safely.
- `TT3A/fixed/r89` — current "MacA." represents MacArthur. Test full "MacArthur"
  under the current repacked table rather than preserving an obsolete abbreviation
  automatically.

### Runtime/context review

- `TT4/fixed/r9` — `くび` is literally neck, but can cover head/neck depending on
  the medical-selection context. Current "Head" should not be changed without
  confirming the actual target graphic/menu behavior.

### Do-not-regress source corrections

- `TT2/fixed/r26` — KEEP "Damascus." In this Crusades quiz-answer table,
  hiragana `だますかす` represents Damascus. The generated workbook gloss
  "Deceive and coax" is a false context-free parse.
- `TT4/fixed/r78` — KEEP "Alice." Japanese `ありす` is the deliberately odd
  answer distractor Alice; do not replace it with workbook gloss "Aris."


## Actual-v17 verification pass

The fresh audit was cross-checked against the decoded v17 ROM rather than only
workbook/current-analysis fields.

Already fixed in v17 and therefore removed from the actionable list:

- TT1B/g2/r16 — already "His eyesight seems poor."
- TT1B/g3/r25 — already "We're in the middle of the sermon."
- TT6A/g2/r26 — already "waiting for someone."
- TT6C/g2/r12 — already preserves "I feel a certain kinship with you."
- TT4/g0/r3 — current inscription is already natural and source-faithful enough.

Confirmed still actionable in v17:

- TT1B/g2/r10 — still ends at "Ah! That voice…" and drops "you're the person from before."
- TT3A/g4/r4 — still reads awkwardly as "France's resistance movement was called?"
- T25/g1/r17 — still drops "Belle" and the opening "What's wrong?"
- TT6A/g1/r4 — still omits hay from the sweet-smell observation.
- TT6B/g1/r9 — still has stiff "Good old Kashim. / Mary: Truly."
- TT6B/g2/r2 — still omits the source adjective describing Jerusalem's magnificent Temple.
- TT6C/g1/r8 — still flattens Caspar's ceremonial register.
- TT6D/g0/r3 — still contains an empty "Girl: !" where the source has a startled cry.
