# Full Dramatic Pagination Audit — 2026-09-15

## Scope

This pass audits the production-English pagination and timing boundaries across all
**1,299 playable scenario records**. It is separate from the semantic translation
audit: the question here is whether a player is ever forced to advance the dialogue
in the middle of an English sentence, phrase, name, date, or dramatic unit merely
because the Japanese source used a different presentation break.

The audit examines the fully materialized production text, not only the certified
base templates. Every surviving `CTRL:1` input wait and `CTRL:2` page boundary was
reviewed in its English context, with speaker turns and neighboring text considered.
`CTRL:3` and `CTRL:6` were also screened for obvious presentation-only interruptions;
the existing record-scoped rewrites remain authoritative for those controls.

## Result

Before this pass, production contained **147 surviving `CTRL:1` input waits**.
The project already demoted 12 known presentation-only waits discovered during prior
playtesting. This audit identifies **54 additional records** where the inherited
`CTRL:1` is presentation-only in English.

The production policy therefore now contains **66 exact, source-locked `CTRL:1`
demotions** in total.

After those demotions, **93 `CTRL:1` waits remain**. Every remaining wait was reviewed
and falls at a defensible boundary: a completed sentence or proposition, a speaker
change, a reaction/reveal, or an intentional dramatic pause. No remaining high-
confidence case splits an English noun phrase, verb phrase, date, quotation, or other
continuous syntactic unit.

Production also contains **98 surviving `CTRL:2` page boundaries**. All 98 were
reviewed. No additional high-confidence demotion is justified: the surviving
boundaries are attached to speaker changes, completed thoughts, headings/reveals, or
other natural page transitions.

No new static `CTRL:3`/`CTRL:6` rewrite was justified beyond the four previously
approved record-scoped semantic-control rewrites. Runtime playtesting remains the
authority for subjective timing that cannot be inferred from text alone.

## Failure mode found

The larger audit confirmed that inherited Japanese input waits could survive in
places that are plainly wrong for the rewritten English. Representative pre-fix
boundaries included patterns equivalent to:

- `You're earnest and [A] passionate`
- `You've got beautiful [A] eyes`
- `The pact is [A] sealed`
- `Read the [A] inscription!`
- `September 25, [A] 1995`

These are presentation artifacts, not meaningful dramatic beats. They are now
handled through the same fail-closed policy as the earlier playtest discoveries:
each exception is keyed by stable record ID and locked to its exact certified base
template. The certified translation maps are not edited to erase source topology.

## Duplicate-template case

`T22/g0/r10` and `T22/g1/r1` share the same exact certified base template. One copy
made the problem especially visible because the wait could land inside the English
sentence; the other placed it after the `PACT` heading. Because the heading break is
not semantically required and both records share identical source topology, both are
covered by the same source-locked demotion policy. This keeps the compatibility
validator deterministic without broadening the exception beyond those two records.

## Validation contract

Regression coverage now proves that:

- the complete audited exception set contains exactly **66 records**;
- all 66 production records remove the inherited `CTRL:1` wait;
- the corresponding certified base templates retain their original `CTRL:1`;
- changing an audited base template fails closed and requires a new audit;
- representative intentional `CTRL:1` waits remain present;
- production materialization still covers all 1,299 scenario records; and
- renderer-buffer validation remains mandatory after reflow.

## Runtime boundary

This audit can establish that the surviving waits are linguistically and narratively
reasonable. It cannot prove the subjective duration or feel of every native timing
effect without playing the resulting ROM. The final candidate should therefore still
receive a normal runtime playthrough, with any newly suspicious pause recorded by
stable record ID before changing control policy.

The intended release rule is now: **no known forced A-button advance interrupts a
continuous English sentence or phrase.**
