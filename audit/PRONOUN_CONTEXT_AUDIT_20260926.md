# Pronoun and omitted-subject audit — 2026-09-26

## Trigger

Runtime playtesting of TT3A showed the narration `He takes off in a flash.`
while the visible NPC was a woman.

The Japanese source for `TT3A/g3/r23` is:

```text
あっというまに はしりさっていった
```

The sentence has no explicit subject. Static translation had supplied a male
pronoun from one neighboring branch.

## Branch finding

TT3A contains parallel male and female park-contact paths:

- `TT3A/g3/r19-r22` explicitly uses `おとこ` (man).
- `TT3A/g4/r16-r23` explicitly uses `おんな` (woman).
- The runtime female route can reuse `TT3A/g3/r23` for the departure narration.

Therefore changing the line from `He` to `She` would merely invert the bug.
The record must remain valid for either actor.

## Fix

```text
He takes off in a flash.
    ->
They dash off at once.
```

The revised line:

- preserves the source action `走り去る` (run/dash off);
- preserves the immediacy of `あっというまに`;
- introduces no unsupported gender;
- stays below the project's practical 23-column segment ceiling;
- remains valid when the shared record is reached from either contact branch.

A regression test now locks the line as gender-neutral.

## Whole-ROM audit

A source/English scan was repeated across all 1,299 canonical scenario records
for English gendered pronouns whose Japanese sentence omits an explicit gendered
subject.

This produces many expected candidates because Japanese routinely omits subjects.
The candidates were reviewed as context-sensitive rather than mechanically
rewritten.

No second cross-gender reuse was established by the available source/runtime
evidence in this pass. Typical retained cases have a stable referent supplied by
the scene itself, for example Frankie, Simon, Joseph, Mary, Belle, Joan, a
specific soldier, or another uniquely selected visible actor.

The important distinction is:

- **omitted Japanese subject + stable scene referent**: an English pronoun can be
  correct;
- **omitted Japanese subject + record reused across different actor contexts**:
  do not hard-code gender.

Future runtime evidence takes precedence over a static assumption about which
actor owns an otherwise subjectless narration record.
