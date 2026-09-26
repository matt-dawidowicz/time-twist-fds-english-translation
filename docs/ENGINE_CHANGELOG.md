# Engine changes and bug-fix history

This document is the maintained ledger of the significant **runtime, renderer,
format, and build-system fixes** made during the English translation project.

It is not a release changelog for wording edits. It records changes where the
project had to recover or alter game-engine behavior, repair a runtime defect,
retire an incorrect assumption, or add a structural guard after a playtest
failure.

For the current architecture, read
[Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md). For the current
solved/unsolved ledger, read
[Reverse-engineering status](REVERSE_ENGINEERING_STATUS.md).

## Why this ledger exists

Many of the project's hardest failures looked like ordinary translation
problems but were actually engine problems: a line could fit in source JSON and
still overwrite a retained staging row; a menu label could decode correctly and
still use the wrong cursor geometry; an apparently harmless text upload could
trigger typewriter audio while no new text was visible.

The durable rule is therefore:

> Preserve the runtime invariant, not the historical workaround.

The entries below record the invariants that were established by static reverse
engineering, deterministic builds, and Mesen/MesenCE runtime testing.

---

## Text codec and scenario-bank engine

### Native text grammar was separated from production entropy packing

The Japanese source grammar and the production English representation now share
one semantic token model: common glyphs, extended glyphs, dictionary references,
controls, and record separators.

The production runtime uses a frozen entropy grammar, but it dispatches decoded
tokens into the recovered native semantic handlers. This avoided replacing the
entire text engine and made source semantics independently testable.

Key consequences:

- native and entropy record framing are no longer conflated;
- separator 5 remains the semantic record terminator;
- entropy records remain bit-contiguous inside independently addressed streams;
- byte alignment occurs only at a genuinely new byte-addressed stream;
- the scanner carries bit state across record boundaries and frame-budget returns.

See [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md#4-production-entropy-grammar).

### Dictionary expansion became bounded and source-verified

The production dictionary may use backward references to earlier entries.
Runtime depth tracking and a build-time nesting cap make expansion acyclic and
bounded. The project explicitly rejected borrowing unrelated zero-page state
for decoder temporaries after tracing showed that apparently free bytes were
live native-engine state.

### Scenario text may spill, but fixed tails may not move

Scenario-bank rebuilding was changed from a simple in-place text replacement to
an ownership-aware allocator.

The current model:

- preserves source-owned fixed code/data tails at their exact loaded addresses;
- allows complete scenario groups to spill after the original bank when safe;
- keeps every loaded overlay below the exclusive NOV3 boundary at `$D7B5`;
- regenerates group pointers after relocation;
- verifies rebuilt streams by decoding them again.

This removed the false assumption that the original text reservation was the
only safe capacity.

### Incremental playtest builds reuse the approved dictionary

For late playtesting, the incremental builder can decode the currently compiled
bank, reuse its existing entropy dictionary unchanged, rebuild only the
scenario text that differs from canonical source, and verify every rebuilt
record. This is the path used for narrow wording candidates such as the v21
Rebecca-line revision.

---

## Dialogue renderer and control-flow fixes

### Four-row staging-buffer ownership was recovered

The dialogue renderer uses four physical rows of 24 visible columns, with two
staging bytes per glyph. The translation validator now models row ownership
rather than merely counting characters.

This fixed and prevents defects where:

- a line silently crossed a physical row;
- a following control reused a row containing wrapped text;
- a later line overwrote the bottom row instead of scrolling;
- a cross-record continuation re-entered a row still owned by the preceding
  presentation.

The whole canonical corpus is regression-checked through this model.

See [Text layout engine reference](TEXT_LAYOUT_ENGINE_REFERENCE.md).

### Text controls 0-7 were mapped as machine operations

Controls are no longer treated as approximate "line break" markup. Their native
wait, row-selection, and scroll behavior was recovered through NOV2's control
dispatcher and renderer-state table.

In particular:

- controls 1, 2, 3, and 6 are fresh-A-button waits with different continuation
  geometry;
- control 3 waits and then scrolls to row 4;
- control 4 scrolls to row 4 without an A wait;
- control 5 is the record/dictionary terminator;
- control 7 falls through the same low-level row path as control 0.

This made pagination an explicit runtime contract instead of an editorial guess.

See [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md).

### TT3A two-sheet overlay must preserve cell identity

The Rebecca paper puzzle uses a renderer behavior that is distinct from ordinary
dialogue replacement. The red and blue sheets are sparse spatial records, and
the completed message is drawn over the currently visible sheet without first
clearing the dialogue cells.

The Japanese data encodes the two sheet records as disjoint character-cell
subsets whose overlay reconstructs the completed message exactly. An English
revision briefly replaced those sparse layouts with prose headings such as
`Red writing:` and `Blue writing:`. The text was semantically correct but
violated the renderer contract: stale heading glyphs remained visible while the
completed message typed over them.

The maintained invariant is now:

- every non-space cell in either sheet must already equal the character in the
  completed message at that exact row/column;
- the two sheets must not contain conflicting non-space cells;
- cell-wise overlay of the two sheets must reproduce `TT3A/g3/r13` exactly;
- no descriptive heading may be embedded in the sheet payload itself; the menu
  label supplies the color context.

A whole-source scan of all 1,299 Japanese scenario records found exactly one
native composite-presentation triple of this kind:
`TT3A/g2/r30 + TT3A/g2/r31 -> TT3A/g3/r13`. No later chapter uses the same
overlay mechanism.

A regression test now reconstructs the completed English message from the two
sheet layouts cell by cell.

### Joan bottom-row overwrite became a whole-ROM geometry regression

A runtime playtest exposed a continuation that overwrote the bottom row instead
of scrolling. The immediate line was repaired, but the important project change
was broader: all 1,299 scenario records are now checked against the recovered
four-row ownership model so equivalent geometry failures are rejected
automatically.

### Issue #74: leading-control typewriter noise

`TT3A/g0/r26` begins with `CTRL:4` before any new glyph:

```text
{CTRL:4}In fact, he's an{CTRL:4}intelligence agent.
```

The leading control caused state `$0A` to re-upload stale bottom-row cells from
the previous presentation. Those cells produced no visible change, but the
uploader still reached the native typewriter call at `$85C5`, producing an
audible burst before the scroll.

The final fix uses a suppression marker with this lifetime:

```text
leading presentation control detected
        |
        v
stale control flush            marker remains set
        |
        v
scroll / control continuation  marker remains set
        |
        v
resume text decoder            clear marker
        |
        v
first genuinely new glyph      native typewriter SFX restored
```

The marker is cleared at the recovered control-specific decoder-resume sites,
not at a generic uploader state. The v20 Mesen replay confirmed that:

- the stale pre-scroll burst is gone;
- the first post-scroll text regains normal typing audio;
- later glyph cadence remains normal;
- TT3A scene-overlay SFX on `$07E1` remain separate and intact.

Two failed experiments are intentionally documented because they define what
**not** to reintroduce:

1. filtering common-space `$C0` uploads reduced the burst but did not remove
   the stale flush;
2. keeping the marker until renderer state `$04` removed the early burst but
   suppressed the entire first new clause, restoring audio roughly one second
   late.

See
[Typewriter SFX after a leading presentation control](TEXT_CONTROL_STATE_MACHINE.md#typewriter-sfx-after-a-leading-presentation-control).

---

## Menu engine fixes

### Fixed six/eight-character assumptions were retired

The native menu renderer used six-glyph geometry. An early English patch merely
raised two loop counts to eight, which was later mistaken for an engine limit.

Reverse engineering and live MesenCE testing showed that the renderer could be
made genuinely variable-width. The production implementation now:

- records each decoded label's pixel width in Work RAM;
- draws the first row from that measured width;
- reuses the measured width for paired rows;
- positions the second column from the first-column label width;
- places trailing selection cursors from the same metadata;
- clears enough staging space for labels up to the proven production limit.

The project also learned that `$9390-$93AF` is live palette state. An earlier
variable-width experiment used that area and caused graphics corruption even
though the menu algorithm itself was sound. Current code keeps menu scratch
state away from that palette region.

See [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md).

### Large menu tables were recovered as 32-record pages

Large scenario menu/object/quiz tables are byte-addressed in 32-record pages,
not as one continuous table with one pointer per record.

The builder now regenerates page pointers and preserves the two relocated
secondary tables identified by header pointers `$A210/$A212`.

A runtime failure in TT2 exposed a truncation of the relocated secondary-prefix
block. The relocation path now rejects any build that changes, truncates, or
mispoints that entire block. This became a structural regression guard rather
than a one-off TT2 repair.

### Back/Cancel parent handling was repaired

The inherited menu runtime could mishandle Back/Cancel when no valid parent
menu existed. The release pipeline now applies a guarded NOV2 patch that:

- preserves valid submenu parents;
- rejects missing or self-referencing parents;
- routes a rejected Back press through the normal redraw path;
- keeps the patch size-neutral by reusing equivalent native state-handler space.

See `work/time_twist/menu_cancel.py` and the Back/Cancel tests.

---

## Font, title, and graphics-safety fixes

### Font storage is treated as shared runtime-owned data

The project stopped treating apparently unused CHR bytes as automatically safe
font space. Reverse engineering showed that some regions are consumed by other
title or gameplay graphics phases.

The current font patch therefore uses source-verified slots and guards known
shared regions. Unsupported glyphs fail validation instead of being silently
mapped into unknown graphics storage.

See [NOV4 font source safety](NOV4_FONT_SOURCE_SAFETY.md).

### Title rendering preserves native animation ownership

The English title work was changed from "replace what looks like the title" to a
split-ownership model:

- translated background/title art is rebuilt in its proven CHR/nametable areas;
- the animated clock sprite CHR and metasprite data remain native;
- only the separately verified clock-hand origins are intentionally adjusted;
- the final title and the moving monochrome slide are treated as separate
  rendering authorities;
- the title patch verifies protected ranges byte-for-byte.

This prevents a static English title correction from breaking the live clock or
transition animation.

---

## Audio-engine findings that prevented incorrect fixes

### Scene SFX and typewriter SFX are separate paths

During Issue #74, gameplay commands `91 xx` were initially suspicious because
they occur near the visible defect. Reverse engineering established that they
write the scene-overlay latch at `$07E1`.

The native typewriter click instead reaches `$07E0=$04` through NOV2
`$85C5`.

That distinction prevented an incorrect "fix" that would have deleted or
arbitrarily retimed legitimate scene effects.

See [Audio command map](AUDIO_COMMAND_MAP.md).

---

## Candidate-runtime parity

### Incremental playtest ROMs must carry the current NOV2 runtime

A late TT3B playtest exposed catastrophic fixed-menu geometry: the
`Hitler / Simon / Schmidt / Cougar` menu drew labels and selection markers far
outside the normal frame.

The menu descriptors and source-level geometry audit were valid. The candidate
ROM was not running the maintained renderer. Byte comparison against canonical
`entropy_runtime.py` found stale NOV2 code in eleven runtime-owned regions,
including:

- menu width metadata stored at an obsolete `$0433` location instead of
  `$042D+visual_index`;
- obsolete column and draw-count helpers;
- the obsolete trailing-cursor helper;
- an older entropy scanner/category layout;
- an older fixed 51-record NOV2 entropy block;
- missing current no-parent Back/Cancel guard code.

This drift came from repeatedly modifying an older runtime-confirmed candidate
instead of first proving that its engine/runtime bytes still matched current
repository source.

The maintained incremental build now fails closed if the baseline NOV2 payload
does not match every canonical runtime-owned replacement region. Translation-only
incremental rebuilds are therefore permitted only after runtime parity is proven.

A ROM-runtime migration does **not** by itself make an old emulator checkpoint
safe. A Mesen save state can capture transient renderer state created by the old
runtime. The v25 checkpoint used during this investigation was saved with the
four-choice `Crumple / Burn / Tear / Combine` menu already active. Its old
renderer had written live label widths to `$0433-$0436`; the canonical renderer
expects the same active-menu metadata at `$042D-$0430`. Replacing NOV2 code
without migrating those transient bytes therefore loaded the new renderer into
an already-decoded menu with an empty width table and produced menu glitches.

For a save state crossing a renderer-state ABI change, the preferred rule is
stronger: **recreate the checkpoint natively under the new runtime**. A Mesen
state serializes the CPU, PPU, memory manager, mapper, controls, resident RAM,
and other machine state; the CPU snapshot includes PC, SP, A, X, Y, flags, and
cycle state. Therefore an old checkpoint can resume halfway through an old
renderer transaction even if resident NOV2 bytes have been replaced.

The later right-shifted-menu investigation separated two issues that had been
conflated. Save-state ABI migration is real, but the persistent 32-pixel menu
shift was also a **runtime geometry regression** in the modernized NOV2 code.

The v26 breakpoint provides direct runtime evidence: the active
`Crumple / Burn / Tear / Combine` menu begins at the historical/native
positions (left cursor x=`$20`, left text x=`$28`). The modernized renderer
had moved those anchors four tiles right (left cursor x=`$40`, left text
x=`$48`) while changing the width-metadata ABI. That shift was not required by
variable-width rendering.

The corrected runtime therefore keeps the safer per-entry width table at
`$042D+visual_index`, but restores the historical anchors:

- left leading cursor: x=`$20`;
- left text: x=`$28`;
- right text: x=`$38 + left_width`;
- right leading cursor: x=`$30 + left_width`.

This requires only four NOV2 immediate-byte changes relative to the otherwise
modern runtime. A breakpoint state saved in the main loop can be migrated by
installing the corrected NOV2 image and copying the already-decoded active menu
widths from the old `$0433...` table to `$042D...`.

Save-state ABI caution still applies: do not blindly migrate a checkpoint that
is executing inside renderer code or whose live transient ownership is unknown.

Static menu geometry remains a separate invariant: the recovered audit covers all
721 configured labels, 367 primary menu descriptors, and every order-preserving
predicate-compacted subset through eight visible choices. Runtime parity must be
true before those static guarantees are meaningful in a playtest ROM.

## Build-system and regression hardening

### Translation source became singular

The project now has one canonical scenario-English source:
`work/translations/<BANK>.json`. Historical recovered output is retained only
as evidence/regression material. This removed ambiguity over which layer should
be edited after a bug fix.

### Release inputs are hash-locked

The private baseline, active translation maps, and frozen compiler payloads are
tracked by a release-source lock. Intentional source edits require an explicit
lock refresh; stale hashes are treated as build failures rather than silently
accepted.

### Runtime patches are source-guarded

Engine patches verify the expected original bytes before writing replacements.
A patch therefore fails closed on an unknown engine revision instead of
applying because an offset happens to exist.

### Save states are candidate-specific evidence

A Mesen state may contain resident scenario/NOV2 Work RAM from the candidate
that created it. When a runtime patch or resident bank changes, a checkpoint
must either be recreated from scratch or migrated by replacing the resident
bytes consistently with the new ROM. Renaming a state is not sufficient.

This became especially important during the Issue #74 v18-v20 sequence, where
the ROM and resident NOV2 Work RAM had to match for audio timing evidence to be
valid.

---

## Selected defect-to-invariant summary

| Observed defect | Root cause | Durable fix/invariant |
| --- | --- | --- |
| Text overwrites bottom dialogue row | Physical staging-row ownership not modeled | Four-row/24-column dialogue-flow validator |
| Cross-record continuation corrupts retained text | Leading presentation control re-enters retained row | Cross-record continuation contracts |
| Typing noise before visible `In fact...` | Stale cells re-uploaded during leading-control flush | Suppress through control flush; clear at decoder resume |
| Typing begins ~1 second late | Suppression cleared at state `$04`, after first new clause | Clear at semantic decoder-resume boundary |
| Long/full menu labels misalign cursors | Fixed-width menu geometry | Runtime-recorded per-label pixel widths |
| Experimental menu graphics corruption | Scratch helper overlapped live palette RAM | Keep `$9390-$93AF` untouched |
| TT2 menu selection path lost | Relocated secondary-prefix block truncated | Byte-for-byte relocation integrity guard |
| Back from root/invalid parent behaves incorrectly | Native parent state accepted invalid value | Guarded Back/Cancel parent validation |
| Candidate save state behaves unlike ROM | Resident Work RAM from older candidate | Patch/recreate resident state with matching ROM |
| Suspected TT3A scene SFX near typing bug | `$07E1` scene effects confused with `$07E0` typewriter | Keep audio paths separately mapped and tested |
| Title/font edit breaks unrelated graphics | Shared CHR ownership assumed free | Source-verified ownership and protected-range checks |

---

## Maintenance rule

When a future playtest exposes a defect:

1. record the exact ROM hash, emulator version, route, and checkpoint;
2. distinguish visible text, staging RAM, PPU upload, script VM, and audio paths;
3. identify the smallest instruction/data event that separates good and bad
   behavior;
4. patch that event rather than introducing a timing delay or record-specific
   special case;
5. turn the discovered invariant into a regression test;
6. add the engine-level result to this ledger if it changes the maintained
   runtime model.

That process is what converted the project's late-stage playtest failures into
reusable engine knowledge rather than a collection of fragile per-scene hacks.
