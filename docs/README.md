# Documentation index

The maintained documentation describes the current source-only translation and
release pipeline. Retired implementation snapshots and commands remain in Git history.

## Start here

- **Play a candidate:** [Playtesting guide](../PLAYTESTING.md)
- **Set up a checkout:** [Quickstart](../QUICKSTART.md)
- **Improve English text:** [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md)
- **Change Python tooling or tests:** [Code contributor guide](../CONTRIBUTING_CODE.md)
- **Reverse-engineer or fix runtime behavior:** [Text and graphics reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md)
- **Tour the implementation:** [Code tour](CODE_TOUR.md)

The public repository contains no original or patched FDS images, BIOS files,
extracted retail payloads, emulator states, or other private fixtures.

## Translation and review

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [Workbook pipeline](WORKBOOK_PIPELINE.md)
3. [Cross-bank editorial decisions](../work/audits/final_cross_bank_consistency.md)
4. [Scenario-bank format](FORMATS.md#scenario-bank-layout)

Scenario English is composed from locked source layers: `work/translations/*.json`
provides stable IDs and certified native control topology, registered
`review/production_retranslation/*.json` provides the reviewed production wording,
and an optional `work/production_overrides/*.json` file is the final explicit
last-mile layer. `work/source_records/*.json` contains decoded Japanese, stable
record IDs, and source structure only. Generated workbooks are review surfaces,
not replacement sources.

## Binary and release architecture

1. [Reverse-engineering guide](REVERSE_ENGINEERING_GUIDE.md)
2. [Architecture](ARCHITECTURE.md)
3. [Formats](FORMATS.md)
4. [Development guide](DEVELOPMENT.md)
5. [Module map](MODULE_MAP.md)
6. [CLI reference](CLI_REFERENCE.md)
7. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)
8. [Private fixtures](PRIVATE_FIXTURES.md)

The reverse-engineering guide is the maintainer-level runtime map: it connects FDS
file offsets, CPU load addresses, packed-text streams, NOV2 renderer behavior,
scenario/menu addressing, font/CHR ownership, NOV4 title PPU/NMI sequencing, known
failure modes, debugger breakpoints, and a repeatable evidence-to-fix workflow.

Candidate and strict release builds use the single source-locked release builder.
Low-level parsing and inspection commands remain available, but obsolete standalone
bank/UI construction commands are no longer part of the public CLI.

## Menus, fixed UI, title, and font

- [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)
- [English dialogue pagination policy](ENGLISH_PAGINATION_POLICY.md)
- [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md)
- [Title sequence](TITLE_SEQUENCE.md)
- [Runtime playtest matrix](PLAYTEST_MATRIX.md)

## Authority map

| Representation | Purpose |
| --- | --- |
| `work/translations/*.json` | Certified base scenario English and native control topology |
| `review/production_retranslation/*.json` | Registered reviewed production wording layered over the base maps |
| `work/production_overrides/*.json` | Optional final explicit per-record overrides, when intentionally present |
| `work/source_records/*.json` | Decoded Japanese/source structure; no English authority |
| `work/time_twist/ui.py` and `ui_fixed_tables.py` | Playable fixed/interface text and guarded patch logic |
| `work/title_assets/Time Twist approved native title.png` | Native ROM-bound title geometry |
| `work/title_assets/Time Twist approved native slide.png` | Native ROM-bound swipe geometry |
| `work/release_sources.json` | Approved non-code input hashes |
| `work/release_target.json` | Reviewed release-output authority after promotion |
| `work/translation_workbook_banks/*.json` | Generated per-bank linguistic review |
| `outputs/Time_Twist_complete_translation_workbook.*` | Generated aggregate review artifacts |
| User-supplied FDS bytes | Authoritative original binary layout |

Never replace exact Japanese evidence with reconstructed kanji, and never use an
archived or generated English string as the playable source.

## Completed source reviews

- [Japanese-source review evidence](../audit/AUTHENTICITY_SECOND_PASS.md):
  semantic findings and manual terminology.
- [Editorial change ledger](../audit/EDITORIAL_CHANGELOG.md): source readings,
  recorded edits, and scene checks used by the playtest matrix.
- [`../audit/third_party/`](../audit/third_party/README.md): completed third-party
  comparison evidence.
- Git history: exact deleted code, old command implementations, and prior file states.
