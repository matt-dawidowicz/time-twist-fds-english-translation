# English dialogue pagination policy

Production English uses the recovered four-row NOV2 dialogue buffer efficiently
instead of preserving Japanese presentation breaks mechanically. The renderer has 24
visible columns, two staging bytes per glyph, and four `$30`-byte rows. English layout
regenerates ordinary row advances and row-four scrolling while preserving controls
that still carry timing, section, or speaker semantics.

For the complete runtime model, see the
[text and graphics reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md#9-dialogue-renderer-geometry).

## Regenerated presentation geometry

Interior `CTRL:0` and `CTRL:4` values are Japanese presentation geometry. Production
layout discards those source row choices and greedily reflows the reviewed English.
It inserts `CTRL:0` while advancing through the first four physical rows and uses
`CTRL:4` when another visible row requires the native scroll behavior. Leading and
trailing layout controls are retained when they affect record entry or exit.

## Scenario quiz questions: native geometry is authoritative

Scenario quiz prompts are a special case and are **not** ordinary reflowable
dialogue. The question shares the four-row text buffer with a native answer-selection
UI that opens immediately afterward. Expanding a one- or two-row Japanese question
into additional English rows can therefore corrupt the answer menu even when the
generic dialogue renderer considers the record valid.

Production registers all 25 scenario quiz-question records across TT2, TT3A, TT4,
TT5, and TT6B. For those records:

- most quiz prompts preserve the exact source control sequence;
- empty leading row geometry is preserved;
- every occupied English segment is limited to 23 visible columns;
- each production question must be an explicit control-bearing override rather than
  generic prose reflow;
- the five Athens fisherman questions are a playtested exception: they retain the
  two leading row advances but may use one additional `CTRL:0` so natural English
  can occupy two visible rows without invoking scroll behavior.

The TT6C retrospective quiz is a different storage class: its prompts/answers live in
a fixed-address table and remain protected by the fixed-table build and regression
tests instead.

This rule was added after runtime playtesting showed the same failure class in
multiple chapter quizzes, culminating in the Athens fisherman quiz corrupting the
screen when its first question had been expanded into ordinary multi-row prose.

## `CTRL:2`: mixed semantic/page behavior

`CTRL:2` can represent an ordinary page transition or a meaningful speaker/timing
boundary. Production layout may omit a source `CTRL:2` only when the English layout
proves that it interrupts continuous prose. It must not demote a speaker-changing
`CTRL:2`, invent a new `CTRL:2`, or reorder surviving semantic controls.

Strong sentence/section boundaries and source speaker transitions remain preserved.
If a speaker-changing boundary cannot fit within the native two-row re-entry limit,
the build fails closed so the wording can be shortened explicitly instead of moving
the control into the wrong turn.

The full dramatic-pagination audit reviewed all **98 surviving production `CTRL:2`
boundaries** and found no additional high-confidence demotion. The surviving page
boundaries occur at speaker changes, completed thoughts, headings/reveals, or other
natural English transitions.

## `CTRL:1`: mandatory by default, 66 exact audited exceptions

`CTRL:1` normally remains a mandatory semantic/input wait. Playtesting exposed one
narrow failure mode: Japanese records can use `CTRL:1` for presentation pacing even
when the corresponding English is one continuous thought. Preserving such a wait can
force an A-button press inside an English phrase, sentence, name, or date.

The first playtest pass identified 12 source-locked exceptions. The full dramatic-
pagination audit then reviewed all **147 surviving production `CTRL:1` waits** and
identified **54 additional records** where the inherited wait is presentation-only in
English. Production therefore has **66 exact record-scoped demotions** in total.

The original 12 are:

- `TT1A/g0/r5`
- `TT1A/g0/r30`
- `TT1B/g0/r0`
- `TT1B/g0/r6`
- `TT1B/g2/r11`
- `TT1B/g2/r29`
- `T25/g0/r24`
- `T25/g1/r12`
- `TT3A/g0/r1`
- `TT4/g0/r30`
- `TT6B/g0/r6`
- `TT6C/g2/r5`

The additional 54 exact base templates live in
`work/time_twist/pagination_ctrl1_policy.py`; the audit rationale is recorded in
`audit/FULL_DRAMATIC_PAGINATION_AUDIT_2026-09-15.md`.

After all 66 demotions, **93 `CTRL:1` waits remain in production**. Every remaining
wait was reviewed and falls at a defensible boundary: a completed sentence or
proposition, a speaker change, a reaction/reveal, or an intentional dramatic pause.
No remaining high-confidence case splits a continuous English syntactic unit.

`TT1A/g0/r30` was promoted into the original set during final playtesting after the
inherited wait after `Time travel, huh...` proved to interrupt one continuous internal
thought. The later inherited `CTRL:6` in that same thought was subsequently observed
to create the same false interruption and is also presentation-only in the approved
build. `TT1B/g0/r0` likewise treats the arrival-line `CTRL:1` as presentation geometry
so the museum introduction reads continuously.

These exceptions do **not** modify the certified base translation maps. Every record
is registered together with its exact certified base template. During production
layout that record's audited `CTRL:1` is treated as regenerable row geometry. If the
stable ID's base template changes, contains a different control topology, or otherwise
drifts from the audited source, the build fails and requires a fresh audit.

Some source records can share the same exact certified template. Where every record
sharing that template has the same audited demotion, the legacy template-only
validator may use either record as the representative because the effective control
sequence is identical. The T22 `PACT` duplicate is explicitly covered this way.

All non-audited `CTRL:1` values remain mandatory. This record-scoped, source-locked
pattern is the required model for any future control exception; do not generalize an
exception from one record to every occurrence of the same control number.

## `CTRL:7`: runtime alias recovered, but absent from source text

The native NOV2 control dispatcher at CPU `$8242` explicitly branches on values
`1, 2, 4, 3, 5, 6`. Values `0` and `7` both fall through to the same row-advance
routine at `$826E`. At the decoder/runtime level, `CTRL:7` is therefore a verified
operational alias of `CTRL:0` for this text path.

A complete audit of the 13 recovered scenario banks, their reachable source
dictionaries, and the 11 large fixed-menu tables finds **zero source `CTRL:7`
occurrences**. There is therefore no evidence that the game script assigns a distinct
narrative or timing meaning to control 7.

Production policy intentionally remains stricter than the low-level decoder: it does
not invent or normalize text to `CTRL:7`. If a newly recovered fixed stream contains a
7, treat its runtime geometry as known but its authorial intent as a fresh call-site
audit.

The repeatable binary/source check lives in
`work/tools/audit_recovered_engine_surfaces.py`.

## Other semantic controls

`CTRL:3` and `CTRL:6` remain mandatory by default and preserve source order. Final
playtesting established four exact record-scoped exceptions where a native semantic
control acts only as Japanese presentation timing in the reviewed English:

- `TT1A/g0/r24`: the scholar-profile `CTRL:3` is regenerated as ordinary scroll
  geometry so one continuous result is not split artificially;
- `TT1A/g0/r30`: the later `CTRL:6` is presentation-only, in addition to the audited
  `CTRL:1` demotion above;
- `TT1A/g0/r31`: the `CTRL:3` before `Whatever…` is presentation-only and the
  approved build uses normal row-four scrolling there;
- `TT1A/g1/r1`: the opening `CTRL:1` and the early `CTRL:6` are presentation-only;
  the later `CTRL:3` boundaries remain semantic.

The full dramatic-pagination audit screened the remaining `CTRL:3`/`CTRL:6`
boundaries for obvious continuous-English interruptions and found no new static
rewrite that could be justified without runtime timing evidence.

These rewrites are locked to the exact certified base templates and native control
sequences. The materializer fails if the English base template drifts; ROM-backed
validation independently fails if the Japanese source control topology drifts. This
keeps the exceptions narrow without requiring Japanese visible text to equal the
English template.

`CTRL:5` is the record separator in the packed stream and is never an ordinary
translated control.

## Regression intent

Coverage protects both sides of the policy:

- all 66 audited presentation-only `CTRL:1` waits disappear only in production;
- the certified base maps retain their original source control topology;
- the four final-playtest semantic-control rewrites reproduce the approved control
  geometry without broadening the policy to unrelated records;
- unrelated dramatic, speaker-change, and timing `CTRL:1` waits remain intact;
- a source-template change invalidates the corresponding exception;
- source speaker-changing `CTRL:2` boundaries remain attached to the correct turn;
- `CTRL:7` remains absent from the recovered scenario/menu corpus and is not invented
  by production layout;
- the Maradul Barao Garadura chant retains its intentional strong pause;
- all 25 scenario quiz questions retain their native control/row geometry and 23-column segment limit;
- every production record is checked against the four-row renderer staging model.

Manual playtesting remains necessary because static layout checks cannot determine the
subjective feel of every native timing effect. When a suspicious pause is found,
record the stable ID and source topology first, then decide whether it is semantic or
presentation-only from runtime context.
