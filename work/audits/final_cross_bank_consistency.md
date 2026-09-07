# Cross-bank editorial decisions

These maintained decisions cover the source-first voice/prose review across TT1A through TT6D. Playable wording comes from `work/translations/*.json`; the generated workbook and voice guide describe the current script. Superseded per-bank pilot reports remain in Git history. Runtime evidence is still required for the six staging-dependent questions below.

## Scope

The pass reviewed recurring terminology, character voice, source-explicit register, repeated story callbacks, puzzle/quiz terminology, and display safety across:

- TT1A
- TT1B
- TT2
- T22
- TT3A
- TT3B
- TT4
- TT5
- T25
- TT6A
- TT6B
- TT6C
- TT6D

Non-scenario components remain translated and complete, but this freeze did not editorially guess at the unresolved `NOV2/wait` rendering/control conflict.

## Final editorial rules

The completed script uses these rules consistently:

- Japanese source meaning is authoritative; natural English is preferred only when it preserves the proposition, force, referents, causality, implication, and source register.
- Exact control-event order is preserved.
- Scenario text uses a practical maximum of **23 visible characters per control-delimited segment**. The engine's nominal validator may allow 24, but runtime/visual evidence showed that exact-width lines can look clipped or lose right-edge punctuation.
- Source-explicit stutters, pauses, profanity, threats, brutality, racist/dated language, religious claims, and other ugly material are preserved without sanitization.
- The translation does not invent stronger material that is absent from the Japanese.
- Stylized Japanese dialect or role-language is represented through English register, rhythm, contractions, and diction rather than fabricated geographic eye-dialect unless the fiction itself requires one.
- Recurring characters maintain recognizable voices across chapters rather than being re-invented scene by scene.
- Gameplay-critical quantities, directions, truth/lie roles, puzzle relations, and recap-question facts are treated as requirements-sensitive text.
- Wording is never borrowed from the removed external translation.

## Cross-bank terminology decisions

### God's child

Recurring `かみのこ` is now consistently **God's child** where it denotes the theological/story concept that culminates in the TT6C finale.

This specifically corrects two early TT1B references that had used `God's son`:

- `TT1B/g0/r15`, the Demon-Sealing Jar plaque;
- `TT1B/g3/r29`, the priest's story of the youth who died protecting God's child.

The choice also aligns with T22's Jeanne narration and the repeated `God's child` language that drives TT6C's final realization/exorcism.

This is a story-term consistency decision, not a rule that every English occurrence of `son`, `child`, or religious kinship vocabulary must be mechanically normalized regardless of Japanese context.

### Demon-Sealing Jar

`まふうじのつぼ / 魔封じの壺` is consistently **Demon-Sealing Jar**, matching the project glossary and its first museum occurrence.

The final sweep corrected `TT6B/g1/r27` from `Magic-Sealing Jar` to `Demon-Sealing Jar`. TT1B and TT6C already used the canonical term.

### Time Belt

The named device remains **Time Belt** with capitalization when it is the specific invention/item. Generic explanatory references to a time machine remain context-sensitive rather than being forcibly capitalized.

### Underworld

`黄泉の国` remains localized as **the underworld** in the Greek chapter. The TT6C recap quiz was already corrected during its bank pass to ask for the **underworld guard**, avoiding the misleading `Who guarded Hades?` person/place ambiguity.

### Meyer / Kashim

Existing project spellings **Meyer** and **Kashim** remain frozen for consistency. Possible transliteration alternatives such as Mayer and Kasim/Qasim remain analysis notes, not script variants.

## Intentional variants that remain variants

The final consistency pass deliberately does **not** normalize source variants of the incantation.

The Japanese itself contains Garadura/Galdura-type variation. The English therefore preserves the corresponding established forms rather than treating every difference as a typo. This includes TT1A, TT1B, and TT6D occurrences.

Display-safety edits may remove surrounding quotation marks or final punctuation where required, but they do not silently change the incantation spelling.

## Repeated-line and callback consistency

### `It's all over... / all is as before...`

TT1B's priest recounts a brave youth's final words using the same underlying Japanese line later spoken directly in the Nativity climax:

`すべてがおわった…… / これでなにもかも もとのままだ……`

The freeze aligns the TT1B quotation to the TT6C payoff:

`It's all over...` / `all is as before...`

This makes the repeated source line function as an intentional callback in English instead of two unrelated paraphrases.

### `Drop dead, Hitler!`

The resistance passphrase remains stable across the WWII chapter. Where a speaker label would consume the practical display margin, the passphrase itself takes priority; the established wording is not rewritten merely to retain a redundant label.

### Final name reveal

TT6C retains the source's intentional `Iesu` / English `yes` / Jesus transition as far as English can support it. The final consistency pass does not regularize that beat into a plainer but less faithful name assignment.

## Character-voice continuity

The cross-bank read found no reason to replace the voice framework established by the individual audits. The final frozen direction remains:

- **Protagonist:** quick, contemporary, wry, emotionally transparent; internal narration avoids parser-like stiffness.
- **Girl:** warm, poised, increasingly confident; Japanese feminine-coded endings are represented through tone rather than caricature.
- **Devil:** grandiose, sardonic, domineering, selectively old-fashioned; never generic rural dialect.
- **Dr. Simon:** precise, educated, humane, controlled, with source-explicit hesitation preserved.
- **Pierre/Chino/Gordo and medieval commoners:** earthy and rough without faux-Shakespearean speech.
- **Bishop:** theatrical institutional/religious authority, increasingly menacing under demonic influence.
- **Schmidt:** terse and disciplined, softening only after the resistance reveal.
- **Belle/George/Tom:** rural/working-class distinctions with dignity; no invented racial eye-dialect or minstrel caricature.
- **Lincoln:** measured and polite rather than inflated presidential pastiche.
- **Joseph:** earnest, worried, colloquial, fundamentally kind.
- **Mary:** quiet, clear, compassionate, and firm when the source makes her decisive.
- **Magi:** dignified/ceremonial without King-James imitation.
- **TT6B animals:** camel/cow rustic through syntax and diction, mare status-conscious, sheep mildly elderly; no fabricated American regional accent.

## Gameplay and quiz integrity

The final consistency sweep preserved the already-audited gameplay-critical information in the individual chapters. In particular:

- TT4 underworld adjacency clues remain exact;
- TT5 farm workload, livestock arithmetic, and milk-measuring quantities remain exact;
- T25 coyote puzzle relations remain exact;
- TT6B truth/lie roles remain **honest / liar / unreliable**, with the same unique westward solution;
- TT6B religious quiz answer-bearing propositions remain intact;
- TT6C recap questions retain the facts needed to recover answers from earlier chapters.

No prose consistency edit was allowed to override puzzle semantics.

## Remaining evidence-dependent records

Six items remain deliberately unresolved because text-only editorial work cannot settle them reliably:

- `TT1B/g0/r28` — punctuation permits more than one reading, though the reply strongly favors a question;
- `TT3A/g2/r7` — off-screen speaker identity needs gameplay staging;
- `TT3A/g2/r30` — torn-note spatial ordering needs a gameplay screenshot/nametable capture;
- `TT3B/g0/r24` — Hitler versus Devil-through-Hitler speaker identity depends on staging;
- `TT4/g4/r14` — unlabeled `Wait` warning needs gameplay context;
- `NOV2/wait` — source control preservation conflicts with the existing one-line English display treatment.

The freeze intentionally leaves these as runtime/visual verification tasks rather than manufacturing certainty.

## Validation and runtime evidence

The [generated progress report](../../outputs/Time_Twist_translation_progress.md)
contains fresh public fit measurements. A built candidate still needs the
[maintainer release checks](../../docs/MAINTAINER_RELEASE_PROCESS.md) and
[runtime playtest matrix](../../docs/PLAYTEST_MATRIX.md), including the six
records above. Editorial review and public compression checks do not certify
gameplay, disk recovery, or save/load behavior.
