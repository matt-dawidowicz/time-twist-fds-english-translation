# ROM modification inventory

This document records the **user-visible and engine-level modifications made to the
English Time Twist ROM**, including changes that go beyond replacing Japanese text.
It is intended to answer a practical question that the lower-level engine references
do not: **what does the English patch actually change in the game, and why?**

The native-engine documents remain authoritative for how the original retail game
works. This file describes the localization layer built on top of that model.

> **Canonical release baseline**
>
> The completed, end-to-end playtested **v50** image remains the behavioral
> baseline, SHA-256
> `820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43`.
> The public release adds the reviewed TT1A fortune-menu handoff correction and
> the Dr. Simon dialogue-scroll fix, and is SHA-256
> `39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5`,
> still a 262,000-byte four-side FDS image.
>
> Older v25/v38 artifacts are retained as historical build inputs and regression
> evidence. They do **not** define target behavior. Exact release reproduction now
> rebuilds frozen v38 from the v25 seed and then follows the validated, hash-guarded
> v38 -> late-v41 -> v50 checkpoint lineage, followed by the guarded TT1A
> correction and the final Dr. Simon dialogue-fix delta. The final release is never regressed
> to match an older recovery state.

## 1. Scope

The English patch is not a text-only hack. It modifies several independent parts of
the game:

- scenario dialogue and narration;
- compressed fixed-menu labels;
- menu-page addressing and runtime menu geometry;
- selection brackets and cursor placement;
- text pagination and speaker-heading presentation;
- title-screen graphics and title transition behavior;
- system/disk-change messages;
- quiz wording and selected answer-routing fixes;
- contextual object/action descriptions;
- CHR graphics used by localized UI;
- ending/staff-roll sprite graphics and packed metasprite definitions;
- selected runtime guards needed to keep the expanded English UI stable.

The design principle throughout the later project has been:

1. recover the original machine behavior first;
2. distinguish a translation problem from a routing/layout/runtime problem;
3. prefer size-neutral or address-preserving edits when possible;
4. when relocation is necessary, regenerate every affected pointer/table contract;
5. validate in Mesen/MesenCE with real scene transitions rather than relying only on
   static decode tests.

## 2. Scenario-text localization

All 13 gameplay scenario banks have been translated. The canonical scenario-English
maps cover **1,299 records**.

The translation was repeatedly revised against the original Japanese FDS images rather
than treated as a one-pass literal conversion. Later playtesting corrected contextual
misreadings, overly terse English, historical terminology, speaker identity, and
question/answer wording.

Presentation policy changed as the translation matured:

- recognized speaker headings begin on a fresh physical row;
- ordinary dialogue fills the available 24-column rows naturally;
- line breaks are selected for readable English rather than copied from Japanese;
- headings, quiz cards, menus, and other structural UI records can retain deliberate
  non-greedy geometry;
- American punctuation is used;
- em dashes are avoided except where an actual interruption requires them;
- English is not shortened merely to satisfy an obsolete implementation limit.

Examples of late contextual corrections include:

- the T25 sky inspection was corrected from **“He's lost in thought.”** to
  **“The sky darkens.”** after confirming that the menu routing was already correct
  and the Japanese `たそがれている` was being interpreted in the wrong sense;
- the Edison quiz prompt was revised to reflect `3大発明` as **“three great
  inventions”**, not an ordinal “third invention”;
- the Edison answer remains **Projector**; the English patch does not reroute that
  question to Camera;
- the disk-change message was polished to **“Try another side.”**;
- several historical/item terms were normalized after context checks rather than
  dictionary-only translation.

## 3. Packed text and English compression

English expansion required more than replacing one Japanese record with one
same-length English record.

The release architecture uses entropy-compressed text and per-bank dictionaries.
The runtime decoder accepts the production token classes while preserving the native
scenario-control semantics.

Important implementation effects:

- scenario records are bit-contiguous within independently addressed streams;
- fixed menu pages are independently addressed so page starts remain byte-addressable;
- dictionary entries are bounded and acyclic;
- build-time round trips verify that every configured English record decodes back to
  the intended text and controls;
- fixed-layout and production-typography tests prevent accidental regressions.

A major lesson from late playtesting was that **repacking an active scene bank can be
unsafe for an emulator save state captured inside that scene**. A save state can hold
live pointers/cursors into the old packed layout. For late candidate testing, several
repairs were therefore made as exact-footprint, in-place substitutions rather than
full bank repacks.

## 4. Full-word menu conversion

The original English work initially inherited Japanese-size menu slots, forcing
abbreviations and uneven choices. The current architecture replaces those fixed-width
assumptions with full English labels.

The patch changes the runtime behavior of the menu system in several ways.

### 4.1 Page-aware menu relocation

The fixed menu table is split into 32-record pages. When English labels change the
size of a page, the builder regenerates:

- record-32/64/96 page pointers;
- the `$A210` and `$A212` secondary-table bases;
- scenario group-zero placement;
- scenario-group pointers;
- fixed tails and NOV3 boundary checks.

This allows labels within a page to vary in encoded length without corrupting later
records.

### 4.2 Runtime width metadata

The patched renderer records decoded menu-label width in Work RAM at
`$042D + visual_index`.

That metadata is then used to derive:

- the amount of menu text to draw;
- the start of a second column;
- selector/bracket positions;
- dynamic trailing-cursor placement.

This replaced the earlier hard-coded six/eight-glyph span.

### 4.3 Wider labels

The recovered staging renderer supports substantially longer labels than the legacy
English implementation assumed. The production validator uses:

- an **18-visible-glyph** conservative per-label ceiling;
- geometry checks for two-column rows;
- actual calculated cursor/column positions rather than one fixed template.

This is what allowed labels such as **Magnifying glass** and other formerly abbreviated
choices to appear naturally.

### 4.4 Two-column alignment

Two-column choices were changed from hand-positioned/fixed coordinates to a coherent
layout rule: the second column is positioned from the first-column content plus a
controlled gap.

This work went through multiple regressions during development. The final direction is
to calculate layout from actual visible widths rather than maintain independent
per-menu X-coordinate hacks.

### 4.5 Back/Cancel behavior

The expanded menu work exposed edge cases in Back/Cancel behavior, especially at root
menus and after redraws. Runtime guards were added so Back does not incorrectly enter
an invalid parent/menu state, and later testing concentrated on stale rows, cursor
state, and redraw behavior after backing out.

See [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md) for the
maintained architecture.

## 5. Text renderer and presentation changes

The English patch also changes how some text is presented, not just what bytes are
stored.

### 5.1 Speaker-heading geometry

English speaker headings can be much longer than Japanese labels. The canonical
layout policy now treats a heading as an indivisible unit and starts a recognized
speaker on a fresh physical row.

### 5.2 Line-break and window balancing

During the final playthrough, line breaks were repeatedly adjusted to avoid:

- orphaned final words;
- large accidental blank regions;
- headings sharing inappropriate rows;
- overly sparse English caused by literal Japanese segmentation;
- text that technically fit but looked visibly unbalanced.

### 5.3 Typewriter/audio edge cases

The project traced the game's typewriter-sound path and leading presentation controls.
Most behavior remains native. Scene-specific exceptions were treated narrowly rather
than applying global timing changes that could destabilize the rest of the game.

## 6. Title-screen and opening graphics

The English title is not a simple text record.

The title work reconstructs and patches NOV4's title presentation, including:

- the English **Time Twist** title artwork;
- the subtitle **“On the Outskirts of History...”**;
- upper and lower CHR pattern assignment;
- the moving monochrome title-swipe phase;
- the final colored title phase;
- the Nintendo-logo phase;
- the clock-sprite source tiles;
- the raster split between upper and lower pattern tables;
- transition/restore behavior when leaving the title screen.

The maintained title implementation explicitly preserves the clock-owned CHR tail and
reuses pattern-table slots across non-overlapping title phases to fit the English art
within the NES/FDS limits.

The title transition also includes a blanking/restore guard so the lower title-machine
tile IDs are not briefly rendered through the wrong upper pattern table when START
leaves the title.

The result is a translated title sequence that keeps the original animation/timing
concept instead of replacing it with a static screen.

## 7. Gameplay graphics reverse engineering used by the patch

A large part of the project became graphics-engine reverse engineering because
localization defects could not safely be fixed by guessing at tile bytes.

The project recovered that:

- `OB*` / `OBJ*` files are raw sprite CHR loaded into pattern table 0;
- `BG*` files are raw background CHR loaded into pattern table 1;
- several graphics files are deliberate partial overlays that inherit previous CHR;
- `$A204` points to packed metasprite definitions;
- `$A200` points to static metasprite placements;
- `$A202` points to actor spawn/layout records;
- `$A208` selects palettes;
- `$A21E` selects gameplay nametable-patch descriptors;
- animation and motion streams are separately addressed.

That recovered model made later graphics edits addressable and testable. In particular,
it enabled the ending-credit translation described below without rewriting the ending
engine.

See [Gameplay graphics and scene engine](GAMEPLAY_GRAPHICS_ENGINE.md).

## 8. Ending/staff-roll translation

The ending credits were one of the last major non-text subsystems translated.

They are **not ordinary TT6D dialogue records**. The staff roll is rendered as packed
metasprites backed by `OBJ6D` CHR.

The English patch translates:

- **SCRIPT** — Keiji Terui
- **DESIGN** — Eiko Takahashi, Katsutomo Maeiwa, Takahiro Umehara
- **PROGRAMMING** — Tomoshige Hashishita, Taisuke Araki, Motoo Yasuma
- **MUSIC** — Hajime Hirasawa
- **PRODUCTION** — Tatsuya Hishida
- **DIRECTOR** — Keiji Terui
- **PRODUCED AND / COPYRIGHT BY / NINTENDO**

### 8.1 Preserve the ending engine

The credit renderer, timing, movement, and scroll choreography remain native.
Localization changes are confined to:

- selected packed metasprite definitions in TT6D;
- the corresponding `OBJ6D` CHR patterns.

No replacement staff-roll engine is introduced.

### 8.2 Japanese spacing versus English spacing

The Japanese credit cards contain transparent 8-pixel cells that visually separate
kanji. A direct English substitution initially produced headings and names with large
internal gaps.

The final layout moves transparent cells to the outer margins where possible and packs
English text contiguously through the center. This preserves:

- record count;
- metasprite indexing;
- visible-sprite count where possible;
- original timing and movement;
- native OAM emission.

### 8.3 Role-heading typography

The role cards received a dedicated typography pass after the first English prototype
proved too visually compressed.

`SCRIPT`, `DESIGN`, `PROGRAMMING`, `MUSIC`, and `DIRECTOR` were redrawn with
more deliberate tracking and a narrower `I` glyph while keeping the same runtime
metasprite structure.

### 8.4 v50 Production-card structural adjustment

`PRODUCTION` was the one heading that still looked squeezed after the general
typography pass because its native allocation provided only a 32-pixel text span.

v50 fixes that structurally rather than by making the letters unnaturally narrow:

- `PRODUCTION` is expanded from **32 pixels to 48 pixels**;
- it uses the same standard heading style and approximately 2-pixel tracking as the
  roomier role cards;
- the adjacent **KEIJI / TERUI** credit is reduced from four 16-pixel text cells to
  three, where the name still fits comfortably;
- the saved bytes/CHR allocation are reused for the wider Production heading;
- total TT6D credit-table size remains unchanged;
- later records resynchronize to their previous addresses;
- no ending-code rewrite is required.

This is an example of the project's late-stage rule: preserve the engine contract and
move capacity within the existing format instead of “solving” a visual problem with a
new renderer.

## 9. Quiz and choice corrections

The final playthrough exposed several cases where a plausible English question was not
enough: the answer-routing table also had to be checked against the original game.

The debugging rule became:

```text
Japanese prompt
    -> Japanese choices
    -> original branch/routing table
    -> surrounding scene context
    -> English wording
```

Confirmed late examples include:

- the TT4 crop-question routing correction, where **Fig** is the intended accepted
  answer;
- TT6C **Ash** was verified as already encoded correctly, so no unnecessary routing
  patch was applied;
- the Edison invention question was checked against the original choice set and
  walkthrough behavior; **Projector** remains the correct routed answer.

Where the routing was correct but the English was misleading, only the wording was
changed.

## 10. Disk/system-message localization

System-level text was also localized and polished. Because some of these messages are
stored in packed resident streams rather than ordinary scenario records, late edits
were handled cautiously.

One final example is:

```text
Wrong disk!
Try another side.
```

The added period was retained while avoiding a scene-bank repack that could invalidate
a live checkpoint.

## 11. FDS scene and overlay behavior preserved

The patch relies on the original scene-loading model rather than flattening it.

Important preserved behaviors include:

- four FDS sides in the combined development image;
- program overlays loaded into the same `$A200` CPU range;
- small overlays intentionally inheriting high tables from earlier larger overlays;
- partial sprite/background CHR overlays;
- native disk/side switching;
- the native Part 1 -> Part 2 handoff and persistent save/title state.

This matters because apparently “unused” RAM/CHR from the previous overlay can be
intentional input to the next overlay. Rebuilding every file as a standalone full
image would break the game.

## 12. Save-state compatibility lessons

Mesen/MesenCE save states contain more than story flags. A mid-scene state can contain:

- the active program overlay;
- resident CHR;
- decoded/repacked menu/text data;
- live pointers into those data;
- CPU/PPU state that assumes exact addresses.

During the late TT5 work, replacing the entire resident bank while keeping old live
pointers caused post-quiz graphics corruption and eventually an invalid-opcode crash.

The stable procedure became:

1. identify whether the checkpoint is inside the bank being changed;
2. prefer an exact-footprint in-place patch;
3. if CHR or overlay bytes are resident, patch only the corresponding bytes;
4. preserve unrelated CPU/PPU/story state;
5. assert the expected old bytes before mutation;
6. load the migrated state under the matching ROM and run through the next transition.

This procedure was used for the final credit/graphics testing as well.

Save states are test artifacts only and are not release inputs or repository content.

## 13. Candidate-lineage summary

The final manual playtest lineage included a sequence of narrow candidate builds rather
than repeated whole-ROM redesigns. Important late milestones were:

| Candidate | Purpose |
| --- | --- |
| v41 | Practical local baseline before the final quiz/system-message corrections |
| v42/v43 | Consolidated TT4 crop-answer routing correction and checkpoint cleanup |
| v44 | Edison wording + disk-message punctuation experiment; exposed unsafe active-bank repacking |
| v45 | Restored TT5 layout compatibility while retaining safe system-message correction |
| v46 | Exact-footprint Edison wording patch |
| v47 | T25 sky contextual translation fix; full game subsequently completed |
| v48 | English ending/staff-roll graphics and metasprite translation |
| v49 | Credit-role typography/tracking polish |
| v50 | Wider, unsqueezed `PRODUCTION` role card using a size-neutral TT6D/OBJ6D reallocation |

The candidate numbers are development provenance only. **v50 is the canonical final
behavioral baseline.** The public release should be built from maintained source that
reproduces v50 and versioned independently as the English patch release (for example,
v1.0).

## 14. Runtime verification performed

The final playtesting process covered much more than static text decode:

- complete progression through the game;
- both halves of the FDS title;
- menu selection and Back/Cancel behavior across many scenes;
- quiz correct/wrong-answer behavior;
- visual line wrapping;
- scene transitions;
- contextual object inspections;
- late TT6D ending sequence;
- translated credit cards in the native scrolling renderer;
- targeted credit-card captures for Script, Design, Programming, Music, Production,
  Director, staff names, and the final Nintendo card.

The complete gameplay route was finished on the v47 lineage. v48-v50 then changed
only the ending-credit presentation layer and related CHR/table geometry described
above. The final credit presentation was subsequently accepted, so v50 is now the
release behavior to preserve.

## 15. Reproducible v1.0 checkpoint lineage

The late playtest sequence included exact-footprint edits and binary-layout changes
that the frozen recovered v38 packer cannot honestly regenerate from the final maps.
The maintained release path therefore reproduces the validated binary lineage
explicitly rather than claiming capabilities the recovered compiler does not have:

1. the private v25 safe-encoding seed and frozen recovered compiler reproduce exact
   v38, SHA-256
   `62C5DBC2DE33C484DE9F8C1318FC903642EB08E2B4D5FA8E28384DC699C4C400`;
2. a compact source-copy checkpoint delta promotes exact v38 to the validated
   late-v41 image, SHA-256
   `13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1`;
3. a second guarded checkpoint delta reproduces the reviewed v42-v50 changes and
   requires the corrected four-side SHA-256
   `39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5`.

The checkpoint payloads contain only copy/literal deltas, not a complete original or
translated FDS image. Their SHA-256 values, source identities, target identities,
and byte counts are locked in `work/release_sources.json`.

The 13 canonical translation maps remain the editorial source of truth for all 1,299
scenario records. Future edits must establish a new reviewed lineage and final hash
rather than silently changing these immutable checkpoints.

## Related references

- [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)
- [Gameplay graphics and scene engine](GAMEPLAY_GRAPHICS_ENGINE.md)
- [Gameplay script and event VM](GAMEPLAY_SCRIPT_ENGINE.md)
- [Text layout engine reference](TEXT_LAYOUT_ENGINE_REFERENCE.md)
- [English pagination policy](ENGLISH_PAGINATION_POLICY.md)
- [FDS scene-transition map](FDS_SCENE_TRANSITIONS.md)
- [Part 1 to Part 2 handoff](PART1_PART2_HANDOFF.md)
- [Reverse-engineering status](REVERSE_ENGINEERING_STATUS.md)
- [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)