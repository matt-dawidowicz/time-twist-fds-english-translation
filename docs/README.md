# Documentation index

This directory contains the maintained description of the **current** translation,
runtime model, and release pipeline. Retired implementations and dated engineering
records belong under [`docs/history/`](history/README.md) or in Git history; they
are evidence, not release input.

## Choose the document by task

| Task | Start here | Then read |
| --- | --- | --- |
| Play/test a candidate | [Playtesting guide](../PLAYTESTING.md) | [Playtest matrix](PLAYTEST_MATRIX.md) |
| Set up or build | [Quickstart](../QUICKSTART.md) | [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md) |
| Edit scenario English | [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md) | [Translation workflow](TRANSLATION_WORKFLOW.md), [English pagination policy](ENGLISH_PAGINATION_POLICY.md) |
| Change Python/tooling | [Code contributor guide](../CONTRIBUTING_CODE.md) | [Code tour](CODE_TOUR.md), [Module map](MODULE_MAP.md) |
| Investigate runtime behavior | [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md) | [Reverse-engineering status](REVERSE_ENGINEERING_STATUS.md) |
| Diagnose dialogue layout | [Text layout engine reference](TEXT_LAYOUT_ENGINE_REFERENCE.md) | [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md) |
| Diagnose gameplay script logic | [Gameplay script engine](GAMEPLAY_SCRIPT_ENGINE.md) | [Retail VM opcode reference](RETAIL_VM_OPCODE_REFERENCE.md) |
| Diagnose graphics/scene composition | [Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md) | [Architecture](ARCHITECTURE.md) |

## Source-of-truth boundaries

Scenario English has one authority:

```text
work/translations/<BANK>.json
```

The 13 maps contain the accepted wording and approved control layout.
`work/source_records/*.json` contains decoded Japanese/source evidence, not a
second English layer. The release pipeline consumes the active maps through the
frozen v38 compiler bundle and the private v25 baseline described in
[V38 canonical build](V38_CANONICAL_BUILD.md).

Current documentation must describe that architecture. Historical documents may
describe retired layering, codecs, limits, or experiments but must not be cited
as current release instructions.

## Translation and presentation

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [Production localization standard](PRODUCTION_LOCALIZATION_STANDARD.md)
3. [English pagination policy](ENGLISH_PAGINATION_POLICY.md)
4. [Text layout engine reference](TEXT_LAYOUT_ENGINE_REFERENCE.md)
5. [Native text-control state machine](TEXT_CONTROL_STATE_MACHINE.md)
6. [Scenario-bank format](FORMATS.md#scenario-bank-layout)
7. [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)
8. [Cross-bank terminology decisions](../work/audits/final_cross_bank_consistency.md)

## Runtime and reverse engineering

1. [Reverse-engineering status](REVERSE_ENGINEERING_STATUS.md) — current solved/unsolved ledger
2. [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md) — evidence model and investigation workflow
3. [Architecture](ARCHITECTURE.md) — runtime/build architecture
4. [Gameplay script and event VM](GAMEPLAY_SCRIPT_ENGINE.md)
5. [Retail gameplay VM opcode reference](RETAIL_VM_OPCODE_REFERENCE.md)
6. [Gameplay VM reachability-island audit](GAMEPLAY_VM_REACHABILITY_AUDIT.md)
7. [Gameplay graphics and scene engine](GAMEPLAY_GRAPHICS_ENGINE.md)
8. [Gameplay palette-animation engine](PALETTE_ANIMATION_ENGINE.md)
9. [Audio command map](AUDIO_COMMAND_MAP.md)
10. [FDS scene-transition map](FDS_SCENE_TRANSITIONS.md)
11. [Part 1 to Part 2 handoff](PART1_PART2_HANDOFF.md)
12. [TT1A Fortune Teller logic](TT1A_FORTUNE_TELLER_LOGIC.md)

## Build, code, and maintenance

1. [Code tour](CODE_TOUR.md)
2. [Module map](MODULE_MAP.md)
3. [Formats](FORMATS.md)
4. [Development guide](DEVELOPMENT.md)
5. [CLI reference](CLI_REFERENCE.md)
6. [V38 canonical build](V38_CANONICAL_BUILD.md)
7. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)
8. [Private fixtures](PRIVATE_FIXTURES.md)

## Historical material

[Permanent engineering history](history/README.md) preserves obsolete constraints,
failed experiments, superseded implementations, and dated validation evidence.
Do not silently rewrite those records to match current architecture; update the
maintained documents instead.

The public repository contains no original or patched FDS images, BIOS files,
extracted retail payloads, emulator states, or private fixtures.
