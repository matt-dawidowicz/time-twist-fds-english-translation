# Final Materialized Text-Flow Audit — 2026-09-15

## Scope

This pass audits the **materialized production text**, not only the certified base
translation maps. It specifically looks for defects that can survive earlier
record-level semantic review because later production overrides, compression, or
reflow can accidentally reintroduce ambiguity or remove a source distinction.

The pass covers scene-to-scene flow, obscure/negative responses, English-only
comprehension, previously approved semantic corrections, historical-source
fidelity, and the known runtime-dependent ambiguity inventory. The Japanese
source records remain the authority. A wording change is classified as definite
only when the source or a previous source-backed audit settles it without
gameplay guesswork.

## Definite fixes

### TT1B/g2/r16 — preserve epistemic uncertainty

Japanese `めが わるいようだ` is an inference. Final production had regressed to
`His eyesight's poor.`, which states the condition categorically. Production now
uses **`His eyesight seems poor.`**

### TT3A/g4/r6 — repair quiz grammar

The materialized quiz prompt read `Which big-nosed actor star of Pepe le Moko?`.
The reviewed source-backed wording is restored as **`Which big-nosed actor starred
in "Pépé le Moko"?`**

### TT3B/g1/r8 — repair narration flow

`The rust falls away. and the words appear!` contained a sentence-boundary error.
Production now uses the reviewed natural rendering **`The rust flakes away,
revealing the words beneath!`**

### TT3B/g1/r22 — restore the observed event

Schmidt's `しかし おそろしいものをみた` says that the group **saw something
terrible**. Compression had reduced this to `What a horror.`, weakening the
concrete observation. Production again states **`But we saw something terrible.`**

### T22/g0/r4 — restore the jailer's aside

`いえ… ひとりごとです` means that the jailer was talking to himself / thinking
aloud. The materialized `proof... just to myself` was neither idiomatic nor a
complete equivalent. Production now uses **`Just thinking aloud.`**

### T25/g1/r20 — preserve the attackers' referent

The source explicitly identifies the threat as **the men who attacked George and
Belle the previous night**. The compressed `Last night's men` weakened that
connection. Production now restores the explicit referent.

### TT6A/g0/r18 — preserve recognition of the descending figure

The source uses `あいつ`, recognizing the figure rather than introducing an
unknown `someone`. A later override had regressed to `Someone came from above`.
Production now keeps that recognized referent with the control-safe wording
**`He came down from above.`** The original speaker/control topology is preserved.

### TT6A/g2/r26 — restore the omitted object

`だれかを まっているようだ` explicitly says **waiting for someone**. The
materialized line had been shortened to `Seems he's waiting.`, dropping the
object. Production now restores it.

### TT6B/g1/r27 — repair Demon-Sealing Jar sentence grammar

The materialized line lacked a finite verb: `a Demon-Sealing Jar said to trap
devils.` The source says that far to the east there is said to be a vessel called
the Demon-Sealing Jar that can imprison devils. Production now uses the reviewed
complete sentence while retaining the frozen **Demon-Sealing Jar** terminology.

### TT6C/g3/r8 — restore the Yes / Jesus payoff

The source deliberately repeats `いえす` before resolving it as
`いえす・きりすと`. The final consistency policy explicitly preserves this
Yes/Jesus wordplay. A later production override changed the payoff to
`Right. Jesus Christ.`, breaking the callback. Production again ends
**`Yes… Jesus Christ!`** after the preceding `Yes` responses. The true ellipsis
preserves the beat while complying with the production typography rule that
scenario prose contains no em or en dashes.

## Historical atrocity fidelity — Nazi Germany and slavery

This pass also rechecked the 1944 Germany and 1864 Atlanta chapters directly
against the Japanese source. The translation policy here is deliberately
non-sanitizing: preserve the source's coercion, racism, violence, and historical
terminology when the Japanese states them, but do not invent stronger claims or
collapse distinct historical institutions.

### Nazi Germany

The materialized chapter correctly preserves the source's explicit content:

- `TT3A/g1/r25` states that Hitler's regime is rounding up spies and rebels and
  sending them to **gas chambers**; this is not softened to generic imprisonment
  or disappearance.
- `TT3A/g3/r4` preserves `かんきんして` and `きょうせいしました`: Simon says the
  **Nazis imprisoned him and forced him to develop a secret weapon**, and that he
  will not help them murder anyone again.
- Gestapo identifications remain explicit in `TT3A/g3/r27`, `TT3A/g4/r21`, and
  surrounding resistance dialogue.
- `TT3A/g0/r14` remains a **POW camp in southern Germany** because the source says
  `ほりょしゅうようじょ`; the translation does not inaccurately upgrade it to a
  concentration or extermination camp.
- `TT3B/g0/r23` explicitly keeps Rebecca's agents **inside the Nazi ranks**.

No additional Nazi-scene euphemism requiring a production rewrite was found in
this pass.

### Slavery and post-emancipation racial violence

Several polished English lines were gentler or more interpretive than the
Japanese and were corrected:

- `TT5/g0/r6`: `きさまらなどに でかいつらされてたまるか` is contemptuous and
  hierarchical. Production now uses **`We won't let the likes of you lord it over
  us!`**, followed by the explicit threat **`I'll make an example of you. Taste my
  whip!`** rather than the softer `Don't start getting ideas around here!`.
- `TT5/g0/r7`: the beating remains explicit, Belle says **`At this rate, my son
  will die!`**, and the attacker states **`You people were born slaves.`** The
  anti-emancipation threat is not reframed as merely a labor dispute.
- `TT5/g0/r18`: `なんぶから でていこうなどとおもうな` and
  `いっしょうを おれたちのためにささげるんだ` are restored as **`Don't even
  think about leaving the South. Devote your whole lives to us.`**
- `T25/g1/r24`: `いうことをきかないどれいどもの はかば` is rendered as **`the
  graveyard of slaves who refused to obey`**. The previous polished wording added
  `me`; that ownership pronoun is contextually plausible but not present in the
  Japanese, so it has been removed.
- `T25/g2/r4` continues to state explicitly **`Leave the slaves behind`** rather
  than replacing `どれいたち` with workers, servants, or another euphemism.

The goal is fidelity rather than amplification: historically ugly dialogue
remains ugly because the source is ugly, while translator-added slurs or stronger
claims are not introduced.

## Suspicious but not changed statically

### T25/g1/r15 — pronoun clarity

`He keeps talking to him` is weak English-only comprehension because both
pronouns depend on the visible scene. The Japanese likewise omits explicit names
(`しきりに なにごとかはなしかけている`). Without proving which sprite/object the
inspection is attached to at runtime, replacing the pronouns with names would be
an unsupported clarification. **Runtime/staging check recommended; no static
change.**

### TT3A/g2/r29 — elliptical request

`A child gave it to me. A stranger asked him to.` is understandable but leaves
its final infinitive implicit in English. The object/action relationship depends
on the surrounding interaction state. **Check during the WWII scene playtest;
no static rewrite without source/staging confirmation.**

### TT3B/g1/r21 — unlabeled disembodied speech

The lines `The Devil did this.` / `The Devil stole my body.` are followed by
Simon's `Someone spoke?!`, which strongly suggests that their lack of an ordinary
speaker label is intentional dramatic information. Adding a label would risk
spoiling or misassigning the scene. **Leave unchanged unless runtime evidence
contradicts this reading.**

## Runtime evidence still required

The existing four staging-dependent questions remain unresolved and should not be
settled from text alone:

1. `TT3A/g2/r7` — identity of the off-screen `Wait, Cougar…` voice.
2. `TT3A/g2/r30` — spatial ordering/reconstruction of the torn note.
3. `TT3B/g0/r24` — Hitler speaking versus the Devil speaking through Hitler.
4. `TT4/g4/r14` — identity of the unlabeled `Wait` warning.

For each, capture the surrounding screen state, sprites/portraits, preceding and
following actions, and (for the torn note) the actual nametable/visual layout.
Do not infer a speaker merely because one English label would read more smoothly.

## Control-flow / dramatic timing result

The prior pagination audit already established that the surviving `CTRL:1` and
`CTRL:2` boundaries are linguistically defensible. This pass found no new static
reason to generalize or remove those controls. Remaining concerns are subjective
runtime timing: pause duration, reveal cadence, blank-looking boxes, stale tiles,
and typewriter/audio behavior. Those stay in the runtime playtest matrix rather
than becoming speculative text edits.

## Obscure-branch result

Wrong-answer, repeated-action, refusal, already-completed-action, and inspection
responses were reviewed with an English-only comprehension lens. The pass found
no new source-backed puzzle-logic correction beyond the grammar/referent fixes
listed above. The release candidate still needs `BRANCH-01` runtime coverage to
prove that every response is reached in the state assumed by its pronouns and
speaker identity.

## Regression policy

The accompanying unit regression materializes the authoritative production layer
and locks the semantic distinctions above after reflow, including explicit
historical-atrocity checks for the Nazi and slavery chapters. This is intentional:
a future base edit, override, or compression pass must not silently turn a
previously fixed source distinction back into an ambiguity or euphemism.
