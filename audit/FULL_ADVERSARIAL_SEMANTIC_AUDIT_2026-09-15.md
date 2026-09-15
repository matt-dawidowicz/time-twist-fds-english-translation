# Full Adversarial Semantic Audit — 2026-09-15

## Scope

This pass re-audits all **1,299 playable scenario records** plus the maintained
fixed-address menu vocabulary. It is deliberately narrower than a prose-polish
pass: the goal is to find English that sounds natural but changes Japanese
meaning, logic, referents, epistemic status, or established character voice.

The audit uses the ROM-derived Japanese source as authority and treats the
existing voice policy in `audit/AUTHENTICITY_SECOND_PASS.md` as a hard
constraint. It does not rewrite lines merely to make them more literal.

Each record was evaluated for:

- uncertainty, hearsay, inference, and probability;
- negation, exclusivity, conditions, quantities, and puzzle logic;
- omitted subjects and subject/object attribution;
- tense/aspect and already/still/yet distinctions;
- referent and pronoun resolution across neighboring records;
- fixed-menu command + target semantics;
- repeated-source consistency and terminology continuity;
- unsupported additions or dropped information;
- character voice/register drift; and
- gameplay consequences and cross-record scene coherence.

## Classification

- **PASS** — semantics and voice are acceptable in context.
- **CHANGE — high confidence** — the maintained English changes or drops a
  source distinction that can be corrected without runtime guesswork.
- **RUNTIME EVIDENCE REQUIRED** — text alone cannot safely settle the reading.

The audit does **not** convert natural English back into word-for-word Japanese.
Idiomatic equivalents such as `おじゃましました` -> `Thanks for having me`
remain acceptable when they preserve the scene's social function and voice.

## High-confidence corrections

The broader audit confirms the corrections already made on PR #70 and adds the
following findings.

### TT1B/g2/r16

Japanese `めが わるいようだ` is an observation/inference, not a categorical
medical fact. Use **`His eyesight seems poor.`**

### TT3B/g1/r22

Schmidt says `しかし おそろしいものをみた` — the group **saw something
terrible**. The prior review wording `After an ordeal like that…` generalized
away the concrete observation. Schmidt's established terse, disciplined voice
supports **`But we saw something terrible.`**

### TT5/g0/r7

Belle's `このままでは むすこが しんでしまいます` means **`At this rate,
my son will die!`**; it does not directly accuse the attacker of killing him.
The attacker's `おれたちがいるかぎり` means **`as long as we're around`**,
not `as long as you're here`. Both subject relations are restored while keeping
his threatening register and Belle's dignified pleading voice.

### T25/g1/r20

Meyer explicitly identifies the threat as **the men who attacked George and
Belle the previous night**. That connection is retained rather than compressed
to the vaguer `men from last night`.

### TT6A/g0/r18

The narration uses `あいつ`, recognizing the descending figure as **that guy /
he**, rather than an unknown `someone`. The correction keeps the protagonist's
quick contemporary internal voice: **`that guy came down from the sky…`**

### TT6A/g2/r26

`だれかを まっているようだ` means **waiting for someone**. The maintained
English `waiting for something` was a direct object-category error.

### TT6C/g2/r12

`たにんのようなきが せん` expresses the Devil's felt kinship with the
protagonist: he does not feel like a stranger. **`I feel a certain kinship with
you.`** preserves that meaning and the Devil's grandiose register more exactly
than generic `You and I are not so different.`

## Fixed-menu audit

Every repeated fixed-address Japanese label was compared across banks and
against gameplay targets. Two systematic problems are corrected on PR #70:

- `きく` -> **Listen** where it is the fixed command label;
- `へやのなか` -> **Room** in the verified room-interior target slots.

The remaining repeated-label variation is contextual and intentional:

- `しょうにん` -> Merchant / Merchants / Trader;
- `ふく` -> Robe / Clothes;
- `けいむしょ` -> Jail / Prison.

No additional fixed-menu semantic correction was justified.

## Puzzle / logic audit

The larger pass found no new high-confidence error in negation, conditionals,
counts, directions, exclusivity, or puzzle rules. In particular, the previously
corrected coyote-count rule, livestock totals, work-order quantities, quiz
prompts, and conditional access rules remain semantically intact.

## Existing runtime-evidence boundary

Four records remain deliberately unresolved because text alone cannot identify
visual staging or speaker identity safely:

- `TT3A/g2/r7` — identity of the off-screen `Wait, Cougar…` voice;
- `TT3A/g2/r30` — exact spatial reconstruction of the torn note;
- `TT3B/g0/r24` — Hitler speaking versus the Devil speaking through Hitler;
- `TT4/g4/r14` — identity of the unlabeled `Wait` voice.

These remain **RUNTIME EVIDENCE REQUIRED**, not translation guesses.

## Result

The full semantic audit did **not** justify another wholesale rewrite. The
translation is generally stable. The remaining actionable findings are a small
set of source-meaning corrections concentrated in epistemic nuance,
subject/object attribution, and referent preservation. Character voice is
preserved under the established project style guide rather than normalized into
uniform literal English.
