# Documentation index

The maintained documentation describes the current source-only translation and
release pipeline. Historical implementation snapshots live in [`archive/`](archive/README.md)
and must not be treated as operating instructions.

## Start here

- **Play a candidate:** [Playtesting guide](../PLAYTESTING.md)
- **Set up a checkout:** [Quickstart](../QUICKSTART.md)
- **Improve English text:** [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md)
- **Change Python/Rust tooling or tests:** [Code contributor guide](../CONTRIBUTING_CODE.md)
- **Tour the implementation:** [Code tour](CODE_TOUR.md)

The public repository contains no original or patched FDS images, BIOS files,
extracted retail payloads, emulator states, or other private fixtures.

## Translation and review

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [Workbook pipeline](WORKBOOK_PIPELINE.md)
3. [English dialogue layout](ENGLISH_LAYOUT.md)
4. [Compression optimizer](COMPRESSION_OPTIMIZER.md)
5. [Native compression accelerator](NATIVE_ACCELERATOR.md)
6. [Scenario-bank format](FORMATS.md#scenario-bank-layout)

`work/translations/*.json` is the only scenario-English authority.
`work/source_records/*.json` contains decoded Japanese, stable record IDs, and
source structure only. Generated workbooks are review surfaces, not replacement
sources.

The editorial-compression workflow treats exact Japanese meaning, sentiment,
speaker stance, register, character voice, subtext, and dramatic rhythm as
translation constraints. Renderer width and packed-bank capacity remain hard
ROM constraints, but layout and compression are expected to solve those limits
before natural English is shortened. Deep editorial search may use the optional
Rust accelerator; Python remains the authoritative codec and verifier.

## Binary and release architecture

1. [Architecture](ARCHITECTURE.md)
2. [Formats](FORMATS.md)
3. [Development guide](DEVELOPMENT.md)
4. [Module map](MODULE_MAP.md)
5. [CLI reference](CLI_REFERENCE.md)
6. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)
7. [Private fixtures](PRIVATE_FIXTURES.md)

Candidate and strict release builds use the single source-locked release builder.
Low-level parsing and inspection commands remain available, but obsolete standalone
bank/UI construction commands are no longer part of the public CLI.

## Menus, fixed UI, title, and font

- [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)
- [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md)
- [Title sequence](TITLE_SEQUENCE.md)
- [Runtime playtest matrix](PLAYTEST_MATRIX.md)

## Authority map

| Representation | Purpose |
| --- | --- |
| `work/translations/*.json` | Authoritative playable scenario English |
| `work/source_records/*.json` | Decoded Japanese/source structure; no English authority |
| `work/time_twist/ui.py` and `ui_fixed_tables.py` | Playable fixed/interface text and guarded patch logic |
| `work/time_twist/textcodec.py` | Canonical packed-text codec behavior |
| `work/time_twist/compression_native.py` | Optional verified bridge to the Rust editorial optimizer |
| `native/compression_optimizer/` | Optional deterministic search accelerator; not codec authority |
| `work/title_assets/Time Twist approved native title.png` | Native ROM-bound title geometry |
| `work/title_assets/Time Twist approved native slide.png` | Native ROM-bound swipe geometry |
| `work/release_sources.json` | Approved non-code input hashes |
| `work/release_target.json` | Reviewed release-output authority after promotion |
| `work/translation_workbook_banks/*.json` | Generated per-bank linguistic review |
| `outputs/Time_Twist_complete_translation_workbook.*` | Generated aggregate review artifacts |
| User-supplied FDS bytes | Authoritative original binary layout |

Never replace exact Japanese evidence with reconstructed kanji, and never use an
archived or generated English string as the playable source.

## Historical records

- [`archive/`](archive/README.md): retired implementation, hardening, retrospective,
  and dated release-review documents.
- [`../audit/third_party/`](../audit/third_party/README.md): completed third-party
  comparison evidence.
- Git history: exact deleted code, old command implementations, and prior file states.
