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

The native behavior of these controls is now recovered exactly:

| Control | Native operation after the preceding text is committed |
| ---: | --- |
| `CTRL:1` | wait for a fresh A press, then continue at row 2 |
| `CTRL:2` | wait for a fresh A press, then continue at row 3 |
| `CTRL:3` | wait for a fresh A press, scroll up one text row, then continue at row 4 |
| `CTRL:6` | wait for a fresh A press, then continue at row 4 without scrolling |

See [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md) for the
instruction-level trace.

Thus all four are mechanically A-button waits. “Speaker change,” “reveal,” and
“dramatic beat” describe how a scene uses the wait/re-entry operation; they are
not separate meanings encoded by the control value.

Their placement in the canonical map is reviewed state. Do not move one merely
to gain room for a longer sentence.

Important constraints include:

- `CTRL:1` must occur before staged text passes row-2 start;
- `CTRL:2` must occur before staged text passes row-3 start;
- `CTRL:6` must occur before staged text passes row-4 start;
- `CTRL:3` intentionally scrolls before row-4 continuation;
- a semantic control may not split a speaker heading;
- a speaker-changing boundary must remain attached to the intended turn;
- cross-record entry geometry must not overwrite text still visible from the
  preceding record.

Localization policy still permits a source `CTRL:2` to be removed when
record-scoped review establishes that the Japanese A wait was pagination-only
and continuous English should not pause there. That is an editorial demotion of
a source wait, not a different native meaning for control 2.

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
