# Time Twist: On the Outskirts of History — English Translation

This repository contains the reverse-engineering tools, translation data,
tests, and review workbooks for an English translation of Nintendo's 1991
Famicom Disk System adventure game *Time Twist: Rekishi no Katasumi de...*
(`タイムツイスト 歴史のかたすみで…`).

The project covers both halves of the game:

- `Zenpen` (first part)
- `Kouhen` (second part)

## Current status

- All 2,052 extracted text records are represented in the translation
  workbook.
- Scenario, interface, font, title-screen, and FDS container tooling is under
  `work/time_twist/`.
- Bank-by-bank translation sources are under `work/translations/`,
  `work/translated_scripts/`, and `work/translation_workbook_banks/`.
- The current playable builds are still **playtest builds**. Manual end-to-end
  testing and translation correction remain release gates.
- The complete reviewed workbook is not yet guaranteed to be fully inserted
  into the playable ROMs.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Architecture, formats, CLI, editing workflow, and development guides |
| `work/time_twist/` | FDS parsing, compression, text, font, title, and UI patch code |
| `work/tests/` | Regression and format-safety tests |
| `work/translations/` | Patch-oriented bank translation maps |
| `work/translated_scripts/` | Extracted and revised script records |
| `work/translation_workbook_banks/` | Completed linguistic review by bank |
| `work/title_assets/` | English title reference art |
| `outputs/` | Translation workbooks, glossary, reports, and visual previews |

The searchable translation workbook is:

[`outputs/Time_Twist_complete_translation_workbook.html`](outputs/Time_Twist_complete_translation_workbook.html)

Machine-readable versions are provided as CSV and JSON beside it.

## Documentation

Start with [`docs/README.md`](docs/README.md). The documentation is organized
by the kind of work you want to do:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) explains the complete data
  flow and module boundaries.
- [`docs/FORMATS.md`](docs/FORMATS.md) documents the FDS container, scenario
  pointers, packed-text prefix tree, dictionary references, fixed tables,
  font layout, and title assets.
- [`docs/TRANSLATION_WORKFLOW.md`](docs/TRANSLATION_WORKFLOW.md) is a
  bank-by-bank extraction, editing, rebuilding, and verification tutorial.
- [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md) lists every command and its
  safety role.
- [`docs/WORKBOOK_PIPELINE.md`](docs/WORKBOOK_PIPELINE.md) explains how the
  immutable comparison corpus becomes the review workbook and bank checkpoints.
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) covers tests, fixtures,
  debugging, and safe ways to add a new patch.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) summarizes the invariants a contribution
  must preserve.

## Running the tools

Most parsing and patching code uses Python's standard library. Pillow is also
required for the title-screen and image-preview commands exposed by the CLI.
From `work/`:

```powershell
python -m time_twist.cli --help
python -m unittest discover -s tests -v
```

The command-line interface supports FDS inventory/extraction, byte-identical
round trips, four-side combination, scenario extraction/insertion, fixed-bank
footprint checks, font/title/UI patches, and file replacement.

Run `python -m time_twist.cli COMMAND --help` for command-specific examples and
argument descriptions.

## Required game files

No original or patched ROM images, extracted ROM banks, BIOS/firmware, emulator
packages, or memory dumps are committed here.

To work with the project locally, provide legally obtained copies of the two
Japanese FDS images at:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

Generated `.fds` and `.bin` files remain ignored by Git.

## Translation constraints

Time Twist uses packed bitstream text, per-bank dictionaries, fixed record
addresses, and strict RAM/storage limits. Translation changes are validated
against those constraints; raw byte replacement is not sufficient.

Control codes, message ordering, dictionary shape, fixed-address UI text, and
bank footprints must remain stable unless a deliberate code relocation makes
additional space available.

## Legal

This is an unofficial fan-translation and reverse-engineering project. It is
not affiliated with or endorsed by Nintendo or the original rights holders.
Game software and firmware are not distributed in this repository.

No open-source license has been selected yet. All original-game names,
graphics, text, and other assets remain the property of their respective
rights holders.
