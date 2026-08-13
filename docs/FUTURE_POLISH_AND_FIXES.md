# Deferred polish and fixes

This is a deliberately deferred backlog, not a promise that any item will be
included in the current playtest candidate. The immediate priority is a stable
full English playthrough. Keep the existing candidate, its hashes, and the
post-START transition fix separate from any work listed here.

## When to resume this work

Resume an item only after the relevant scene has been manually played and its
current behavior is captured. Rebuild from the locked Japanese source inputs,
preserve packed-record sizes and bank footprints, run the applicable static
checks, and validate a fresh candidate in Mesen. Do not modify the current
four-side playtest image in place.

## Presentation polish

### Dialogue indentation and line presentation

Review screenshots and save points for awkward first-line indentation,
unbalanced wrapped lines, or visually unclear paragraph breaks. Fix only
demonstrated presentation defects. Preserve the translated wording, control
codes, fixed record boundaries, and the native 24-column layout unless a
separate renderer change is explicitly justified and proven.

### More readable menu choices

The August 12 full-label audit is now the current baseline. See
[`MENU_LABEL_AUDIT.md`](MENU_LABEL_AUDIT.md) for the applied changes,
remaining constrained labels, and command-abbreviation meanings.

The footprint-neutral pass expands every high-confidence fixed menu label that
fits its exact packed record slot. Examples include `HIT` -> `Hit`,
`STOVE` -> `Stove`, `GUN` -> `Gun`, `SCHED` -> `Schedule`,
`DK` -> `Desk`, `NIK` -> `Nick`, and `E` -> `East` where a four-byte slot
permits it. Context-specific labels are documented, including the TT6A
`BK` record that represents a roof tile rather than the colour black.

The remaining compact command labels are intentional capacity fallbacks, not
unknown translations: `SE` means `Look`, `GT` means `Take`, `AS` means
`Ask`/listen by context, `SM` means `Smell`, `DR` means `Drink`, and
`WR` means `Wear`. The clothing commands `On` and `Of` represent
wear/put-on and remove/take-off respectively. Do not change these to other
English guesses such as `See`, `Get`, or `Talk`; they are confirmed against
the source glossary and workbook pipeline.

A dictionary-forced expansion pass was attempted across the fixed-UI banks.
It was rejected by the existing footprint checks: the relevant banks either
overran their preserved scenario/dictionary region or failed the
full-dictionary requirement needed by fixed UI tables. Leave constrained
labels such as `N`, `W`, `S`, `BOD`, `BCK`, `YS`, `HITLR`, `JORDN`,
`ROOSVLT`, and `CHRCHL` compact unless a separate capacity project proves a
safe bank-level change and then replays the affected menus in Mesen.

The fixed FDS prompt is a separate, solved footprint case: two unused
extended-font tiles now render compact ` 2` and ` A` suffixes, so its direct
five-/six-byte slots visibly read `Part 2` and `Side A` without relocating
NOV2 code. This does not expand the scenario dictionary or make the same
technique appropriate for regular menu labels.

### English logo and native slide

The current logo is deliberately frozen for this playtest. A future artwork
pass may change only the pink/purple interior colour assignments: retain the
continuous white outer letter contour, pink faces, purple inner bevels, the
pink outer and white inner clock rings, the unchanged subtitle and TM, and the
native animated blue clock hand. Do not change the wordmark geometry or use
clock-reserved tiles.

Both the settled and sliding presentations must continue to be generated from
the same English wordmark. They are adjacent native nametables used by the
horizontal-scroll sequence, not two alternative logo designs. A future pass
must retain the 236 safe upper-title tile budget and prove matching final and
slide wordmark pixels before emulator review.

The one-frame Nintendo-to-title remap artifact has a stricter size-neutral
candidate correction. Save-state analysis showed that restoring `$2001` inside
the helper could reveal the old Nintendo nametable with the restored English
title CHR before the next NMI installed the new scroll origin. The helper now
clears the `$1C` PPUMASK mirror, blanks rendering, disables NMI, restores the
CHR and `$01F0` origin while blank, restores PPUCTRL/NMI and the `$1C` mirror,
but leaves `$2001` blank for the next NMI to restore after applying scroll. Any
later title work must retain the 12,214-byte NOV4 footprint and recheck a cold
boot plus the full title sequence in Mesen.

## Bugs found during playtesting

Treat every new report as evidence to investigate, not an automatic patch.
Record the candidate hash, disk/side, scene, inputs, expected result, actual
result, and a screenshot/video or save point. Then compare the same path with
the Japanese original when possible and classify the result as one of:

- a translation regression;
- a presentation or clearing defect;
- a proven original-engine defect; or
- intended native behavior.

Change original behavior only after that comparison, source-byte guards,
focused regression tests, and runtime proof. Recheck disk switching, saves,
text wrapping/clearing, and title-to-START behavior after every approved fix.

## Current playtest gate

The post-START title-transition repair has static coverage but still requires
the user's manual visual confirmation. Keep overscan correction disabled while
testing: the apparent random bold glyphs came from rescaling after left
overscan cropping, and the eight-pixel left-edge black strip is original
NES/FDS clipping. Neither is a safe ROM-polish target without a separate
scrolling proof.

The save-present branch needs the same discipline. The reported old glyph
patterns were traced to NOV2's separate four-byte `Save` record at `$8648` and
NOV4's separate six-byte saved-game title choice at `$A29B`, rather than only
the short NOV2 `Load` record at `$8657`. The current candidate guards and
replaces all three; NOV4 displays `Load` with two invisible trailing spaces to
preserve its exact footprint.
Manual visual confirmation from a clean save-present boot is still required
before declaring SAVE-01 fixed.
