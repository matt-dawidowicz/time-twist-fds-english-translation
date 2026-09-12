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

## `CTRL:2`: mixed semantic/page behavior

`CTRL:2` can represent an ordinary page transition or a meaningful speaker/timing
boundary. Production layout may omit a source `CTRL:2` only when the English layout
proves that it interrupts continuous prose. It must not demote a speaker-changing
`CTRL:2`, invent a new `CTRL:2`, or reorder surviving semantic controls.

Strong sentence/section boundaries and source speaker transitions remain preserved.
If a speaker-changing boundary cannot fit within the native two-row re-entry limit,
the build fails closed so the wording can be shortened explicitly instead of moving
the control into the wrong turn.

## `CTRL:1`: mandatory by default, ten exact audited exceptions

`CTRL:1` normally remains a mandatory semantic/input wait. Playtesting exposed one
narrow failure mode, however: several Japanese records used `CTRL:1` as a short
presentation pause even though the corresponding English is one continuous thought
and the four-row box still has unused space.

The production layer therefore demotes `CTRL:1` **only** for these ten audited stable
record IDs:

- `TT1A/g0/r5`
- `TT1B/g0/r6`
- `TT1B/g2/r11`
- `TT1B/g2/r29`
- `T25/g0/r24`
- `T25/g1/r12`
- `TT3A/g0/r1`
- `TT4/g0/r30`
- `TT6B/g0/r6`
- `TT6C/g2/r5`

This exception does **not** modify the certified base translation maps. Each record is
registered in `production_translation.py` together with its exact certified base
template. During production layout that one `CTRL:1` is treated as regenerable row
geometry. If the stable ID's base template changes, contains a different number of
`CTRL:1` values, or otherwise drifts from the audited source, the build fails and
requires a fresh audit.

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

`CTRL:3` and `CTRL:6` remain mandatory and preserve source order. `CTRL:5` is the
record separator in the packed stream and is never an ordinary translated control.

## Regression intent

Coverage protects both sides of the policy:

- the ten audited presentation-only `CTRL:1` waits disappear only in production;
- unrelated dramatic, speaker-change, and timing `CTRL:1` waits remain intact;
- a source-template change invalidates the corresponding exception;
- source speaker-changing `CTRL:2` boundaries remain attached to the correct turn;
- `CTRL:7` remains absent from the recovered scenario/menu corpus and is not invented
  by production layout;
- the Maradul Barao Garadura chant retains its intentional strong pause;
- every production record is checked against the four-row renderer staging model.

Manual playtesting remains necessary because static layout checks cannot determine the
narrative intent of a newly encountered wait. When a suspicious pause is found,
record the stable ID and source topology first, then decide whether it is semantic or
presentation-only from runtime context.
