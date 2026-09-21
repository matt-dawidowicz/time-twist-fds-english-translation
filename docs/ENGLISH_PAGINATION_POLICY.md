# English dialogue pagination policy

The canonical scenario maps already contain the approved English wording and
control placement. Release construction validates that layout; it does not
derive a different translation from another source.

## Frozen v38 exception

The current release preserves the exact checkpoint controls. Nineteen
record-hash-scoped exceptions retain twelve non-greedy wraps and seven quiz
records with 24-column segments. Generic edits retain the stricter rules below.
These exceptions do not waive four-row buffer safety or establish complete
in-game quiz coverage. The compact France and Nazareth identity-card layouts
also remain exactly v38; runtime review is still required.

## Renderer geometry

NOV2 stages dialogue in four physical rows:

- 24 visible columns per row;
- two staging bytes per glyph;
- four `$30`-byte rows.

Ordinary English must fit this geometry without implicit row crossing.

## Speaker turns

A recognized character heading such as `Mary:`, `Soldier 2:`, or
`Old Man:` begins a new speaker turn.

**Every new speaker heading starts on a fresh physical row.**

Within that speaker's turn:

- fill the current row with as many complete words as fit;
- break only when the next word would exceed 24 columns;
- never split the speaker heading;
- do not create deliberately short aesthetic rows merely to balance later text.

A speaker heading must not be orphaned from all of its following dialogue when
the record contains spoken text after the label.

## Soft row and scroll controls

`CTRL:0` is used for ordinary row advance while the text is still moving
through the four physical rows.

`CTRL:4` is used when continuation requires the native row-four scroll
behavior.

For ordinary prose, a soft break is invalid when the first complete word after
the break would still fit on the preceding 24-column row.

Leading or trailing controls can affect entry/exit state and are not treated as
ordinary interior word wrapping.

## Semantic controls

`CTRL:1`, `CTRL:2`, `CTRL:3`, and `CTRL:6` can carry timing, page,
re-entry, reveal, or speaker-transition meaning.

Their placement in the canonical map is reviewed state. Do not move one merely
to gain room for a longer sentence.

Important constraints include:

- a semantic control may not split a speaker heading;
- a speaker-changing boundary must remain attached to the intended turn;
- re-entry controls must not overwrite text staged earlier in the same record;
- cross-record entry geometry must not overwrite text still visible from the
  preceding record.

When a preferred translation cannot fit without moving a meaningful control,
the problem is an engine/layout constraint. Shorten only with an explicit,
source-faithful editorial decision or change the engine with corresponding
runtime evidence.

## Structural exceptions

### Scenario quiz prompts

Twenty-five scenario quiz prompts share the text buffer with native
answer-selection UI. Their row geometry is structural interface state.

For these records:

- preserve the audited control/row geometry;
- keep each occupied prompt segment within the tested width limit;
- do not apply ordinary prose reflow across the answer-menu reservation.

The TT6C retrospective quiz is a separate fixed-address text class and is
protected by fixed-table tests.

### Identity/info cards

Chapter identity cards use rows as fields such as `TIME`, `PLACE`,
`NAME`, `RANK`, and `OCCUPATION`.

Those field boundaries are structural and may intentionally leave otherwise
usable horizontal space.

## CTRL:7

The recovered NOV2 dispatcher treats control value 7 as the same low-level row
advance path as control 0 for this renderer. The recovered scenario corpus does
not use `CTRL:7`, and canonical English does not invent it.

## Required validation

Every canonical scenario record is checked for:

- four-row renderer safety;
- no implicit row crossing;
- speaker headings beginning at row starts;
- no controls splitting a speaker heading;
- maximal ordinary soft wrapping;
- protected quiz geometry;
- protected info-card structure.

Static validation cannot determine whether every dramatic pause feels correct.
Playtest any changed semantic boundary in its actual scene.
