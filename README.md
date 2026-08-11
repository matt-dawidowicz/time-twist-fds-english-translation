# Time Twist: On the Outskirts of History — English Translation

This repository contains the reverse-engineering tools, translation data,
tests, and review workbooks for an English translation of Nintendo's 1991
Famicom Disk System adventure game *Time Twist: Rekishi no Katasumi de...*
(`タイムツイスト 歴史のかたすみで…`). It covers both halves:

- `Zenpen` (first part)
- `Kouhen` (second part)

## Current status

- All **2,052 extracted text records** are represented in the translation
  workbook.
- All **1,299 scenario records** have playable English entries.
- Scenario, fixed UI, font, title, and FDS-container changes are built by one
  source-locked release pipeline.
- The workbook's patch-safe field now mirrors the actual playable sources;
  alternative editorial rewrites remain in the natural-translation field.
- The generated images remain **playtest builds**. A complete emulator
  playthrough is still required before calling the translation final.

## Source of truth

| Material | Authority |
| --- | --- |
| `work/translations/*.json` | Playable scenario dialogue and narration |
| `work/time_twist/ui.py` | Playable fixed-address/interface text |
| `work/time_twist/font.py` and `title.py` | Playable font/title transformations |
| `work/release_sources.json` | Approved non-code release inputs and hashes |
| `work/release_target.json` | Promoted output and release-code provenance hashes |
| `outputs/Time_Twist_complete_translation_workbook.*` | Review surface; patch-safe text mirrors the playable sources |

Do not edit generated ROMs or rebuilt banks as source material.

For a source-level account of the verified game fixes, fixed-address records,
font corrections, title-screen memory map, 6502 hooks, native swipe geometry,
and validation evidence, read the
[bug-fix and title-screen implementation guide](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md).

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Architecture, formats, CLI, workflow, and development guides |
| `work/time_twist/` | FDS parsing, compression, text, font, title, UI, and release code |
| `work/tests/` | Fixture-free public unit tests |
| `work/integration_tests/` | ROM-derived integration tests for maintainers |
| `work/translations/` | Authoritative playable scenario maps |
| `work/translated_scripts/` | Extracted/review-oriented scenario records |
| `work/translation_workbook_banks/` | Per-bank linguistic review checkpoints |
| `work/title_assets/` | Contributor-created English title reference art |
| `outputs/` | Workbooks, glossary, reports, and previews |

The searchable workbook is
[`outputs/Time_Twist_complete_translation_workbook.html`](outputs/Time_Twist_complete_translation_workbook.html).
CSV and JSON versions sit beside it.

The workbook deliberately preserves two English versions when hardware limits
force a compromise. `final_natural_english_translation` is the complete,
unconstrained translation that a future engine expansion or bank-optimization
effort should aim to display. `patch_safe_english_translation` is the exact
wording used by the current playable build after accounting for line width,
control-code layout, compression, and fixed bank footprints. A shortened
patch-safe line therefore does **not** mean that the full translation was lost.
See [`docs/WORKBOOK_PIPELINE.md`](docs/WORKBOOK_PIPELINE.md#preserving-the-full-translation)
before moving natural-field text into the ROM.

## Install and test

Python 3.11 or newer is required.

```powershell
python work/tools/check_public_tree.py
python -m pip install -e ".[dev]"
time-twist --help
python work/run_tests.py unit
```

The public suite contains **55 fixture-free tests** and permits no skips.
Public CI also builds the wheel, force-installs it, and smoke-tests the
installed `time-twist` command.

Maintainers with legally obtained local ROM-derived fixtures can overlay the
private fixture bundle at the repository root and run:

```powershell
python work/run_tests.py integration
python work/run_tests.py all
```

The integration suite contains **74 tests** and also permits no skips. The
runner validates every fixture against `work/integration_fixtures.json` before
test discovery, so missing fixtures produce an explicit setup failure rather
than a misleading green run with skipped tests. See
[`docs/PRIVATE_FIXTURES.md`](docs/PRIVATE_FIXTURES.md).

## Build and promote a release

Place legally obtained Japanese images at:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

Verify the approved inputs and reproduce the promoted build:

```powershell
time-twist release-lock
time-twist release-build
```

An intentional translation or asset change uses a candidate/promotion cycle:

```powershell
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
# Review and playtest the candidate.
time-twist release-promote build/candidate/release_manifest.json `
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Strict builds are staged and hash-checked before publication. A target mismatch
fails without publishing new ROMs to the requested output directory.
Candidate manifests record the active Git commit and dirty state when Git is
available, plus an authoritative platform-independent SHA-256 over
`work/time_twist/**/*.py`. Promotion copies that provenance into the release
target; strict builds reject targets produced by different release-critical
code. Git is optional because validation relies on the deterministic code-tree
digest.

The installed wheel contains code only. It intentionally does not package
translation project data, title assets, ROMs, or generated banks. From outside
the checkout, point it at the project explicitly:

```powershell
time-twist release-build --project-root C:\path\to\time-twist
```

## Documentation

Start with [`docs/README.md`](docs/README.md). Important guides:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMATS.md`](docs/FORMATS.md)
- [`docs/TRANSLATION_WORKFLOW.md`](docs/TRANSLATION_WORKFLOW.md)
- [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md)
- [`docs/WORKBOOK_PIPELINE.md`](docs/WORKBOOK_PIPELINE.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- [`docs/PRIVATE_FIXTURES.md`](docs/PRIVATE_FIXTURES.md)
- [`docs/PROJECT_RETROSPECTIVE.md`](docs/PROJECT_RETROSPECTIVE.md)

## Translation constraints

Time Twist uses packed bitstream text, per-bank dictionaries, fixed record
addresses, and strict RAM/storage limits. Translation changes are validated
against those constraints; raw byte replacement is not sufficient.

Control codes, message ordering, fixed-address slots, dictionary contracts,
scenario tails, and bank footprints must remain stable unless a deliberate,
source-verified relocation creates space.

## Copyright and license

Contributor-created code, tests, documentation, and other original materials
are licensed under the [MIT License](LICENSE). The license does not grant
rights to the original game or any third-party software or assets. See
[`THIRD_PARTY_NOTICE.md`](THIRD_PARTY_NOTICE.md).

This is an unofficial fan-translation and reverse-engineering project. It is
not affiliated with, authorized by, or endorsed by Nintendo or the original
rights holders. The public source archive contains no original or patched ROM
images, extracted ROM banks, firmware, emulator packages, or memory dumps.
