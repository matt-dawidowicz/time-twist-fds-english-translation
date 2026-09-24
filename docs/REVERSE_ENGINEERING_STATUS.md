# Reverse-engineering status

This page is the maintainer index for what has actually been recovered. It
prevents a solved subsystem from being treated as unknown and, equally
importantly, prevents an inference from being promoted into architecture.

Status vocabulary follows [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md):
**VERIFIED**, **OBSERVED**, **DERIVED**, **INFERRED**, and **UNKNOWN**.

| Subsystem | Status | Canonical reference | Remaining work |
| --- | --- | --- | --- |
| NOV2 dialogue row geometry | **VERIFIED** | [Text layout engine reference](TEXT_LAYOUT_ENGINE_REFERENCE.md) | Runtime playtest of changed records |
| Text controls 0-7 | **VERIFIED** | [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md) | No structural unknown |
| English pagination/control policy | **VERIFIED policy** | [English pagination policy](ENGLISH_PAGINATION_POLICY.md) | Editorial review remains scene-specific |
| Typewriter SFX after leading controls | **VERIFIED** | [Text-control state machine](TEXT_CONTROL_STATE_MACHINE.md#typewriter-sfx-after-a-leading-presentation-control) | Runtime regression coverage |
| Fixed/full-word menu addressing | **VERIFIED** | [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md) | Manual coverage of all runtime menu call sites |
| Dynamic menu width/cursor geometry | **VERIFIED implementation** | [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md#dynamic-selection-brackets) | Manual page/cursor/Back testing |
| Root-menu Back/Cancel guard | **VERIFIED implementation** | `work/time_twist/entropy_runtime.py` | Manual nested/root menu regression testing |
| Gameplay script/event VM structure | **VERIFIED** | [Gameplay script engine](GAMEPLAY_SCRIPT_ENGINE.md) | A few higher-level narrative command names |
| Retail VM opcode reachability | **VERIFIED structural audit** | [Gameplay VM reachability audit](GAMEPLAY_VM_REACHABILITY_AUDIT.md) | Value-level semantics for narrow residual cases |
| Gameplay CHR ownership/load composition | **VERIFIED** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md) | Story-facing naming only |
| Same-address `$A200` overlay inheritance | **VERIFIED** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md#4-same-address-a200-overlays-deliberately-inherit-data) | No structural unknown |
| Metasprites/static placements/actor tables | **VERIFIED** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md) | Scene-specific edits only |
| Gameplay background map descriptors/RLE | **VERIFIED** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md) | No structural unknown |
| Hotspot rectangle structure and FD/FE directions | **VERIFIED** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md) | Higher-level event naming where useful |
| Palette definitions | **VERIFIED structural** | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md#11-palette-engine-at-a208) | Exact narrative meaning of some tag values |
| Palette-animation state machine | **VERIFIED** | [Gameplay palette-animation engine](PALETTE_ANIMATION_ENGINE.md) | Story-facing effect naming |
| FDS scene transitions | **VERIFIED** | [FDS scene-transition map](FDS_SCENE_TRANSITIONS.md) | No structural unknown |
| Part 1 -> Part 2 handoff | **VERIFIED** | [Part 1 to Part 2 handoff](PART1_PART2_HANDOFF.md) | End-to-end release playtest |
| TT1A Fortune Teller | **VERIFIED externally; repo doc pending** | Decision-tree analysis / gameplay VM evidence | Add dedicated maintained repo reference |

## Cross-cutting rules

### Overlay composition comes before isolated-file analysis

`TT1A` overlays `TT1B`, `T22` overlays `TT2`, and `TT3B` overlays
`TT3A`. The smaller later overlay replaces only its own loaded range and
deliberately inherits high RAM tables from the earlier file. Pointers beyond a
small overlay's own payload are therefore not automatically invalid.

The same rule applies to partial CHR overlays. Always reconstruct the active
scene load composition before diagnosing an apparently out-of-range pointer or
missing graphic.

### Native behavior and localization policy are separate

The renderer controls have deterministic machine semantics. English may make a
record-scoped editorial decision to remove a source pagination-only wait, but
that does not change the native meaning of the opcode.

### Static proof and runtime proof are complementary

Binary guards, parsers, and tests can prove table structure, pointer bounds,
encoding round trips, and many geometry invariants. They cannot prove that
every menu call site, dramatic pause, scene transition, or visual composition
looks correct in motion. Candidate promotion therefore still requires the
maintained playtest route.

## Current highest-value unresolved work

The project is no longer blocked by broad engine unknowns. Remaining work is
primarily:

1. complete runtime playtesting of the current candidate;
2. convert newly recovered one-off analyses (especially TT1A Fortune Teller)
   into maintained repo documentation/tests;
3. give higher-level names to the few gameplay commands/palette effects only
   when scene evidence proves those names;
4. treat any new visual/text defect as a narrow regression until evidence
   demonstrates a missing engine rule.

This status page should be updated whenever a subsystem moves from
OBSERVED/INFERRED to VERIFIED.
