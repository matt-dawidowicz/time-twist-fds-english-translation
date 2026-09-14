# Constraint modernization record — 2026-09-13

This document is a permanent historical record of the Time Twist English translation project's transition from conservative early patching assumptions to the recovered production architecture. It is intentionally stored under `docs/history/` so future cleanup of obsolete implementation notes, dead code, or superseded experiments does not erase the reasoning, failures, evidence, and engineering lessons that produced the current design.

## Preservation policy

**Do not delete this file during ordinary stale-code or stale-documentation cleanup.** Amend it when later reverse engineering changes a conclusion. If an implementation described here is removed, preserve the historical description and mark it superseded rather than erasing the record. Do not rely on Git history alone as the only surviving explanation of these architectural transitions.

## Permanent release-size invariant

The final raw four-side FDS release must remain exactly **262,000 bytes**: four archival sides of exactly **65,500 bytes** each.

This is a project release invariant even when the engine permits internal files or overlays to change size. Internal files, menu tables, dictionaries, and scenario groups may move, grow, or shrink only when their runtime ownership and pointers are proven safe and the rebuilt archival sides remain exactly 65,500 bytes each.

The distinction is fundamental:

- fixed **final container size** is intentional and permanent;
- fixed **internal record/component size** is required only where an actual runtime address, memory-ownership, or binary ABI contract proves it.

## Why the constraint audit became necessary

Early translation work repeatedly encoded the safest behavior then known as a general limit. That was appropriate while the runtime was poorly understood. Later reverse engineering recovered the overlay map, entropy decoder, menu-page model, staging buffers, fixed-tail ownership, dictionary ABI, selection geometry, and much of the retail gameplay VM.

Several former “engine limits” were therefore revealed to be implementation limits of an earlier English patch rather than limits of Time Twist or the Famicom Disk System.

The clearest example was the menu renderer. The native renderer drew six glyphs per row. An early English patch increased two loop counts to eight. Documentation then gradually treated eight glyphs as the visible maximum. Historical variable-width work later demonstrated longer labels in live MesenCE execution. The failure that caused that experimental implementation to be abandoned was **not** variable-width rendering itself: experimental helper placement used `$9391-$93AF`, overlapping live palette RAM. The variable-width architecture worked; its code placement was unsafe.

The 2026-09-13 modernization therefore preserves the current safe one-choice-B helper at `$6A2E`, stores menu widths in Work RAM at `$042D+visual_index`, uses a verified in-place trailing helper at `$8137`, leaves `$9390-$93AF` untouched, and restores the historically proven dynamic draw/column/cursor behavior without reviving the palette-RAM mistake.

## Constraints retired or reclassified

### Six/eight-glyph menu labels

**Old rule:** menu labels must fit six or eight visible glyphs.

**Status:** obsolete as a fundamental engine constraint.

The six-glyph limit came from the Japanese renderer loop. The eight-glyph limit came from a conservative English loop-count patch. Neither is a NES hardware maximum.

The reconstructed production renderer uses an 18-glyph staging span, matching the historically tested 36-byte staging clear (`18 glyphs × 2 staging bytes`). The conservative production validator therefore permits up to 18 visible glyphs for one label. That is a verified engineering ceiling for the reconstructed staging design, not a claim about the theoretical maximum the NES could ever display.

For paired two-column rows, actual coordinate geometry remains authoritative. The recovered dynamic layout yields a conservative combined-width bound of 20 glyphs for the pair before the right cursor would leave the safe visible coordinate range.

### Fixed menu-column spacing and fixed bracket span

**Old rule:** two menu columns occupy fixed positions and selection brackets assume a fixed six/eight-glyph label span.

**Status:** obsolete.

Historical width-aware code derived the second column from the first-column label's decoded width and placed both leading and trailing selection markers from actual label geometry. The current safe integration restores that principle rather than abbreviating English merely to preserve the Japanese column spacing.

### 31-entry dictionary as an English production limit

**Old rule:** English text can use only 31 dictionary entries.

**Status:** obsolete for the canonical release; retained as a native/source-analysis fact.

Thirty-one entries belong to the recovered Japanese/native prefix grammar.

### 68-entry extended dictionary as an English production limit

**Old rule:** the historical 68-entry extension is the maximum practical English dictionary.

**Status:** obsolete for the canonical release; retained only for historical/source-analysis tooling.

The 68-entry model was a transitional flat-codec experiment that reused otherwise-unused extended values. The canonical entropy runtime has a dictionary ABI spanning values 1-255.

### Flat dictionary entries only

**Old rule:** dictionary entries may contain literal glyphs only.

**Status:** obsolete for production entropy text.

Production dictionary entries may reference earlier entries. Backward-only references make the grammar acyclic; build-time depth policy and runtime depth tracking bound expansion.

### Byte alignment after every record separator

**Old rule:** every record separator advances to the next byte.

**Status:** native-format behavior only; obsolete for production entropy streams.

Production records are bit-contiguous within each independently byte-addressed stream. Padding occurs only at the end of that stream. Independently addressed units include scenario groups, the entropy dictionary, each 32-record large-menu page, and direct-entry streams such as TT1A selector mirrors.

### Original byte length for every large-menu record

**Old rule:** each command, object, quiz, and menu record must retain its Japanese slot length.

**Status:** obsolete for the eleven recovered paged scenario-menu tables.

The runtime addresses record zero directly and records 32/64/96 through a page-pointer table. Records inside one page are traversed through separators. The canonical builder may therefore repack variable-length records, regenerate page pointers, relocate the two recovered secondary tables with their base pointers, and move scenario group zero coherently.

This does **not** authorize arbitrary relocation of every packed-text surface. Some decoder-visible records remain genuinely address-stable and must retain their proven contracts.

### Scenario text confined to the original Japanese text reservation

**Old rule:** translated scenario groups and dictionaries must remain entirely inside the original text hole.

**Status:** obsolete for the production entropy layout.

The production builder may leave complete groups resident in the old reservation and append other complete groups after the original bank, updating their pointers. The real runtime boundary is the overlay's loaded ownership and the exclusive start of resident NOV3 at `$D7B5`.

### Scenario overlay payload must remain its original file length

**Old rule:** a translated scenario file must remain the same payload length as the Japanese scenario file.

**Status:** obsolete as an internal-file rule.

Scenario overlays reuse the `$A200-$D7B4` memory window at different times. A scenario payload may grow beyond its original FDS-file payload length when its loaded end remains below `$D7B5`, the source-owned fixed tail remains intact, and the containing archival side still fits its fixed 65,500-byte container.

### Preserve every Japanese presentation control literally

**Old rule:** every source control must remain at the same location in English.

**Status:** obsolete as a blanket rule.

Certified source/base maps still preserve recovered control topology as evidence. Production materialization distinguishes semantic/timing controls from Japanese presentation geometry. Interior `CTRL:0` and `CTRL:4` may be regenerated for English layout; semantic controls remain source-governed under the documented pagination policy, with only explicit audited exceptions.

## The menu-audit defect uncovered by this work

The fixed-menu audit tools historically called the generic `validate_display_width()` without a menu-specific width. That default validates the dialogue-oriented 24-column constraint. Therefore a historical report saying all 721 fixed labels had `width_ok=True` did **not** prove that those labels fit their runtime menu renderer.

The modernization replaces that check with a dedicated menu-geometry validator.

At the time of this record:

- all **721** configured fixed-menu labels pass the 18-glyph individual staging limit;
- the recovered `$A210-$A212` primary-menu tables parse cleanly into **367 actual menu descriptors** across all eleven menu banks;
- those 367 descriptors collectively reference **all 721 labels**;
- NOV2 `$9803` compacts predicate-surviving choices in order, so the audit deliberately enumerates every order-preserving visible subset through eight choices rather than assuming one story-flag state;
- that produces **7,823 subset cases** and **162 distinct possible two-column pairings**, all of which pass the recovered dynamic-coordinate model;
- the longest configured labels are 14 glyphs (`60 centimeters`, `65 centimeters`, `70 centimeters`, `75 centimeters`);
- the widest possible pairings are `Montgomery / Churchill` and `Montgomery / MacArthur`, both 19 combined glyphs against the conservative 20-glyph pair bound.

The known historically reviewed wide pairs include:

- Montgomery / Churchill;
- Agamemnon / Parthenon;
- Projector / Airplane;
- Patton / MacArthur;
- Saddam / Zoroaster;
- Strawberry / Pearl;
- Fisherman / Statue;
- Lacoste / U Thant;
- Socrates / Homer;
- Newspaper / Body;
- Scaffold / Crowd.

The project should prefer actual call-site geometry and emulator observation over reintroducing abbreviations solely from static fear of label length.

## Historical variable-width renderer: what actually failed

A previous variable-width implementation was runtime-tested across blood-type and month selectors, repeated Yes/No menus, nested command/object menus, cursor movement, selection, Back/Cancel behavior, and later gameplay scenes.

The implementation was nevertheless unsuitable for release because it repurposed `$9391-$93AF` for helper code/scratch. Later reverse engineering proved `$9390-$93AF` is live palette state. That produced corruption.

This distinction matters historically:

- **variable-width rendering was not disproved;**
- **unsafe palette-RAM code placement was disproved.**

The safe hybrid architecture adopted in this modernization deliberately retains the current `$6A2E` one-choice-B helper and uses the existing safe `$8137` trailing-helper region instead of relocating B behavior into palette RAM.

## Optimizer limits: benchmarked policy, not engine maxima

Before this audit the production optimizer used:

- normal banks: maximum 128 dictionary entries;
- TT2: special maximum 96 entries;
- candidate phrase length: maximum 12 grammar tokens;
- nesting depth: maximum 4;
- trial-candidate width: 8.

The decoder ABI can encode dictionary references through 255, but that does not make 255 a sensible optimizer default.

### TT2 benchmark

Using the actual Japanese source bank and the materialized production English:

| Policy | Selected entries | Optimizer bytes | Result |
| --- | ---: | ---: | --- |
| 96 entries / 12 tokens / depth 4 | 96 | 4,065 | previous special cap |
| 128 entries / 12 tokens / depth 4 | 107 | **4,053** | 12-byte optimizer improvement |
| 128 entries / 16 tokens / depth 4 | 108 | 4,070 | worse |
| 128 entries / 16 tokens / depth 5 | 108 | 4,070 | no depth benefit |

Safe-layout comparison retained the same `$D700` loaded end and 181 bytes of NOV3 headroom. The 128-entry policy reduced the selected layout by 11 bytes without changing runtime placement.

Therefore the obsolete **TT2=96 special cap was removed**. TT2 now uses the normal 128-entry policy.

### Global 128-entry benchmark

Under the common 128/12/depth-4 policy, selected entry counts were:

- TT3A 113;
- TT3B 64;
- TT1B 113;
- TT1A 65;
- TT2 107;
- T22 68;
- TT6C 102;
- TT6B 75;
- TT6A 91;
- TT6D 10;
- TT4 128;
- TT5 119;
- T25 77.

TT5 did not improve when its cap was raised to 160 or 192; it naturally stopped at 119 entries.

TT4 was the only normal bank to reach the 128-entry cap. Raising its search cap to 160/192 let the raw optimizer find a two-byte smaller representation, but safe-layout selection produced the same 4,716-byte final layout, the same `$D7B0` loaded end, and the same **5-byte** NOV3 headroom. There was therefore no production benefit from globally raising the cap.

A 255-entry search was also much more computationally expensive. Runtime encodability and optimizer policy are separate concerns.

**Conclusion:** retain the global 128-entry / 12-token / depth-4 policy; remove only the TT2=96 exception. Future policy changes should be benchmark-driven rather than inferred from the 255-entry ABI.

## Constraints that remain verified and must not be casually relaxed

This audit does not imply that every conservative rule is obsolete. The following remain architectural or project invariants until specifically disproved:

- every raw archival FDS side is exactly 65,500 bytes;
- the final four-side release is exactly 262,000 bytes;
- NOV2 owns `$6000-$A1FF` and is exactly `$4200` bytes;
- the `$A200` overlay must remain below resident NOV3 at `$D7B5`;
- `$9390-$93AF` is live palette state and must not be used for code or scratch;
- large scenario menus use the recovered 32-record page-addressing ABI;
- the current dialogue renderer has 24 visible columns, two staging bytes per glyph, and four logical staging rows;
- TT1A has both direct-entry selector addresses and a sequential generic-renderer path;
- active English NOV4 font-source writes are restricted to the recovered safe `$B0-$FE` source range;
- unknown source-owned fixed-tail bytes remain immovable until relevant ownership and references are recovered;
- exact source-byte/hash guards remain required for revision-specific binary patches.

The 24-column dialogue width is a verified property of the current staging architecture, not a theoretical NES maximum. It may someday be redesigned, but this audit found no evidence justifying its removal.

## Fixed tails remain the next likely frontier

The production builder currently preserves the source suffix beginning at each recovered `dictionary_end_offset` byte-for-byte. That remains the correct fail-closed policy while a suffix may contain executable code, data, absolute pointers, or unknown ownership.

As retail-VM and bank-specific reverse engineering progresses, a fixed tail may eventually be partitioned into:

- known executable code;
- known static data;
- known pointer tables;
- relocatable data;
- demonstrably dead bytes;
- unknown bytes.

Only after inbound and internal references are proved should any subsection be considered for relocation or reuse. This is a future reverse-engineering target, not authorization to reclaim tail space now.

## Development chronology preserved for future maintainers

The project passed through several architectural generations:

1. native exact-slot replacement preserving Japanese record sizes;
2. native/flat dictionary optimization, including the historical 68-entry extension;
3. early full-word and menu experiments;
4. variable-width menu-renderer experiments that worked functionally but used unsafe palette-RAM helper placement;
5. the canonical entropy-only runtime with bit-contiguous streams, nested dictionaries, paged-menu relocation, scenario spill placement, and NOV3-safe loaded-end checks;
6. the 2026-09-13 constraint audit, which formally separated hardware/runtime ABI constraints from historical implementation assumptions, restored a safe variable-width architecture, corrected menu QA, benchmarked optimizer policy, and made exact final-image size an explicit release invariant.

Preserve this chronology even after superseded implementation code disappears. The point of this file is to explain why apparently arbitrary constants existed, which failures were truly architectural, and which failures belonged only to one unsafe implementation.

## Validation record from the modernization campaign

The implementation above was not accepted on documentation alone. The following evidence was collected during the 2026-09-13 modernization pass.

### Unit and property tests

After installing the project's Hypothesis dependency from the preserved wheel, the complete `work/tests` suite was split into two execution batches to avoid the execution-window limit:

- 141 tests passed, with 189 generated subtests;
- 106 tests passed, with 325 generated subtests;
- total: **247 tests passed and 514 subtests passed, with zero failures**.

Focused architecture tests were rerun after the final documentation corrections and remained green. Ruff, Black, and mypy were not available in the execution environment, so this record does not claim that those tools were run.

### Source-backed menu geometry

The new menu-geometry audit was run against the original Japanese Zenpen and Kouhen images. It recovered and checked:

- **721** configured fixed labels;
- **367** primary-menu descriptors;
- **162** distinct possible compacted two-column label pairs after conservatively enumerating order-preserving visible subsets through eight choices;
- **7,823** visible-subset cases in that conservative enumeration.

Every label passed the 18-glyph individual staging rule and every possible pair passed the recovered dynamic-coordinate rule. The widest known pairing was `Montgomery / Churchill` at 19 combined glyphs, below the conservative combined limit of 20.

### Actual-source NOV2 integration

The hybrid renderer was applied to NOV2 extracted from the original Japanese Zenpen image, not only to a synthetic fixture. The result proved:

- NOV2 remained exactly **16,896 bytes (`$4200`)**;
- the live palette range `$9390-$93AF` remained byte-identical;
- the existing one-choice B-button helper at `$6A2E` remained unchanged;
- the dynamic-width hooks, Work RAM width metadata at `$042D+index`, 18-glyph staging clear, and current safe trailing-cursor helper all landed at their source-guarded addresses.

This closes the static source-integration question that blocked the historical palette-RAM implementation.

### Exact final-image-size proof

A four-side v9 playtest image was rebuilt with only the hybrid NOV2 replacement. The result was:

- input image: **262,000 bytes**;
- output image: **262,000 bytes**;
- Zenpen half: **131,000 bytes**;
- Kouhen half: **131,000 bytes**;
- 151 bytes differed inside NOV2;
- the Kouhen/later half was byte-identical;
- the rebuilt image parsed and reserialized to the same 262,000-byte length.

The experimental four-side SHA-256 was:

`70E02E439B7293FAB80B34ADF12C73CC36524F23C2B9945FE890176D2547F5FD`

This hash identifies a local validation artifact and is not a release hash.

The production builder now separately enforces the exact 131,000/131,000/262,000 output lengths so final-size preservation is an explicit release contract rather than an incidental result of current serialization.

### Optimizer policy result

The benchmark justified one policy change only: remove the historical `TT2=96` dictionary-entry exception and let TT2 use the common 128-entry cap. Raising phrase length or nesting depth did not help TT2; raising the general cap did not improve TT5; and TT4's two-byte raw optimizer gain above 128 did not survive safe-layout selection. The global 128-entry / 12-token / depth-4 policy therefore remains intentionally conservative and benchmark-supported.

### Evidence still not claimed

A complete canonical 13-bank release rebuild was started with the materialized production translation layer, but the full optimizer workload exceeded the available single-execution windows before returning a final image. No validation failure was reported, but this historical record therefore **does not claim that that full canonical rebuild completed in this environment**.

Likewise, the restored hybrid architecture has strong historical live-emulator evidence plus current source-level and binary-level proof, but a fresh Mesen run of the exact final modernization build remains a desirable release gate unless separately recorded as completed. The distinction is intentional: static proof, historical runtime proof, and fresh runtime proof must not be conflated.
