# Translation-layer retirement — 2026-09-19

## Status

The project retired its former multi-layer English translation system on
2026-09-19.

The sole current scenario-English authority is now:

```text
work/translations/BANK.json
```

Those 13 bank files contain the complete materialized v17 wording and approved
control layout for all 1,299 scenario records. The canonical release builder
consumes those files directly and does not merge any secondary English source.

## Why the old system was retired

Historically, scenario English could be assembled from several layers: a base
map, a later editorial/retranslation layer, and explicit production overrides.
That architecture made it possible for an older compact override to silently
supersede a newer reviewed translation. The September 2026 playtest exposed
this failure when a stale compact TT1B line survived even though a newer,
source-faithful translation had already been reviewed.

The v17 audit resolved the active corpus and materialized the accepted result
into a single source per bank. The old layering mechanism was then removed so
the same precedence failure cannot recur.

## Historical access only

The retired review, override, workbook-checkpoint, and generated comparison
artifacts remain recoverable from Git history before this retirement. They are
historical evidence only.

**Do not restore, copy, merge, or import English wording from those historical
layers into a release build.** If an old decision needs to be studied, use Git
history for context and make any accepted change directly to the canonical
`work/translations/BANK.json` record.

## Current editing rule

For scenario text:

1. edit the canonical record in `work/translations/BANK.json`;
2. preserve source meaning and verified speaker identity;
3. keep every new speaker heading on a fresh row;
4. fill each ordinary 24-column row greedily within that speaker turn;
5. preserve audited semantic controls and structural quiz/info-card geometry;
6. validate the full bank and rebuild before playtesting.

There is no fallback English layer.
