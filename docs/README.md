# Documentation index

The maintained documentation describes the **current** source-only translation
and release pipeline. Retired implementation history lives under
[`docs/history/`](history/README.md) or in Git history and is not release input.

## Start here

- **Play a candidate:** [Playtesting guide](../PLAYTESTING.md)
- **Set up a checkout:** [Quickstart](../QUICKSTART.md)
- **Improve English text:** [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md)
- **Change Python tooling or tests:** [Code contributor guide](../CONTRIBUTING_CODE.md)
- **Reverse-engineer runtime behavior:** [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md)
- **Tour the implementation:** [Code tour](CODE_TOUR.md)

## Translation source

Scenario English has one authority:

```text
work/translations/<BANK>.json
```

Those maps contain both the accepted words and the approved control layout.
Decoded Japanese/source evidence is in `work/source_records/*.json`.

Current translation documentation:

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [English pagination policy](ENGLISH_PAGINATION_POLICY.md)
3. [Scenario-bank format](FORMATS.md#scenario-bank-layout)
4. [Cross-bank terminology decisions](../work/audits/final_cross_bank_consistency.md)

Fixed menus and other interface strings are maintained in
`work/time_twist/ui_fixed_tables.py` and `work/time_twist/ui.py`.

## Binary and release architecture

1. [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md)
2. [Architecture](ARCHITECTURE.md)
3. [Formats](FORMATS.md)
4. [Gameplay script and event VM](GAMEPLAY_SCRIPT_ENGINE.md)
5. [Retail gameplay VM opcode reference](RETAIL_VM_OPCODE_REFERENCE.md)
6. [Gameplay graphics and scene engine](GAMEPLAY_GRAPHICS_ENGINE.md)
7. [Development guide](DEVELOPMENT.md)
8. [Module map](MODULE_MAP.md)
9. [CLI reference](CLI_REFERENCE.md)
10. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)
11. [Private fixtures](PRIVATE_FIXTURES.md)
12. [Permanent engineering history](history/README.md)

The release lock covers only non-code inputs that can affect current output:
the two Japanese baselines, the 13 canonical scenario maps, and approved title
assets. Release-critical Python code has a separate deterministic tree hash.

The public repository contains no original or patched FDS images, BIOS files,
extracted retail payloads, emulator states, or private fixtures.
