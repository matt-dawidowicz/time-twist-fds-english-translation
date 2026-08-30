# Time Twist: On the Outskirts of History — English Translation

This repository contains the reverse-engineering tools, translation data,
tests, and review workbooks for an English translation of Nintendo's 1991
Famicom Disk System adventure game *Time Twist: Rekishi no Katasumi de...*
(`タイムツイスト 歴史のかたすみで…`). It covers both halves:

- `Zenpen` (first part)
- `Kouhen` (second part)

## Start here

This is a source-only project. It intentionally contains no original or
patched game images, FDS BIOS files, extracted retail data, emulator bundles,
or save states.

Choose the shortest path for what you want to do:

- **Play a candidate and report problems:** [Playtesting guide](PLAYTESTING.md)
- **Set up a local source checkout:** [Quickstart](QUICKSTART.md)
- **Improve English text:** [Translation contributor guide](CONTRIBUTING_TRANSLATION.md)
- **Improve tools or tests:** [Code contributor guide](CONTRIBUTING_CODE.md)
- **Check project-wide contribution rules:** [Contributing](CONTRIBUTING.md)
- **Understand the project before editing:** [Documentation index](docs/README.md)
- **Take a guided tour of the implementation:** [Code tour](docs/CODE_TOUR.md)

If you are new to the project, read the playtesting guide or one contributor
guide first. The deeper release and reverse-engineering documents are linked
from those pages.

## Current status

- All **2,052 extracted text records** are represented in the translation
  workbook.
- All **1,299 scenario records** have playable English entries.
- All **721 fixed menu labels** in the canonical candidate decode to their
  complete configured wording: no abbreviated fallbacks and no mismatches.
- Scenario, fixed UI, font, title, and FDS-container changes are built by one
  source-locked release pipeline.
- The release jointly packs dialogue and menus with a guarded 68-entry English
  dictionary extension while preserving every overlay's fixed suffix.
- The workbook's patch-safe field mirrors the actual playable sources;
  alternative editorial rewrites remain in the natural-translation field.
- The generated images remain **playtest builds**. A complete emulator
  playthrough is still required before calling the translation final.

## Source of truth

| Material | Authority |
| --- | --- |
| `work/translations/*.json` | Playable scenario dialogue and narration |
| `work/time_twist/ui_fixed_tables.py` and `ui.py` | Playable full-word menu and fixed-interface text |
| `work/time_twist/font.py` and `title.py` | Playable font/title transformations |
| `work/release_sources.json` | Approved non-code release inputs and hashes |
| `work/release_target.json` | Created only by promotion; reviewed v2 output/provenance authority |
| `outputs/Time_Twist_complete_translation_workbook.*` | Review surface; patch-safe text mirrors the playable sources |

Do not edit generated ROMs or rebuilt banks as source material.

## Where to look

| If you are looking at... | Start here |
| --- | --- |
| Dialogue, narration, or a scenario choice | `work/translations/<BANK>.json` and [translation contributor guide](CONTRIBUTING_TRANSLATION.md) |
| A fixed menu, disk prompt, Save/Load label, or other shared UI | `work/time_twist/ui.py`, `ui_fixed_tables.py`, [full-word menu implementation](docs/FULL_WORD_MENU_IMPLEMENTATION.md), and [implementation notes](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md) |
| Font glyphs or the title sequence | `work/time_twist/font.py`, `work/time_twist/title.py`, and [title sequence](docs/TITLE_SEQUENCE.md) |
| Candidate creation, source locks, or reproducibility | `work/time_twist/release.py`, `release_metadata.py`, and [release commands](docs/CLI_REFERENCE.md#release-commands) |
| A problem seen while playing | [playtesting guide](PLAYTESTING.md) |
| Binary/format concepts | [architecture](docs/ARCHITECTURE.md) and [format reference](docs/FORMATS.md) |

For a source-level account of the verified game fixes, fixed-address records,
font corrections, title-screen memory map, 6502 hooks, native swipe geometry,
and validation evidence, read the
[bug-fix and title-screen implementation guide](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md).
The [release risk assessment](docs/RELEASE_RISK_ASSESSMENT.md) records which
non-playtest risks are closed, mitigated, accepted, or still dependent on the
manual Zenpen-to-Kouhen playthrough.

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Architecture, formats, CLI, workflow, and development guides |
| `work/time_twist/` | FDS parsing, compression, text, font, title, UI, and release code |
| `tests/unit/` | Fixture-free public unit tests |
| `tests/integration/` | ROM-derived integration tests for maintainers |
| `work/translations/` | Authoritative playable scenario maps |
| `work/translated_scripts/` | Extracted/review-oriented scenario records |
| `work/translation_workbook_banks/` | Per-bank linguistic review checkpoints |
| `work/title_assets/` | Contributor-created English title reference art |
| `outputs/` | Workbooks, glossary, reports, and previews |
| `PLAYTESTING.md` | Player-focused setup, high-priority checks, and issue template |
| `CONTRIBUTING_TRANSLATION.md` | Safe path from a reviewed line to its playable source |

The searchable workbook is
[`outputs/Time_Twist_complete_translation_workbook.html`](outputs/Time_Twist_complete_translation_workbook.html).
CSV and JSON versions sit beside it.

The workbook deliberately preserves two English versions when hardware limits
force a scenario-line compromise. `final_natural_english_translation` is the complete,
unconstrained translation that a future engine expansion or bank-optimization
effort should aim to display. `patch_safe_english_translation` is the exact
wording used by the current playable build after accounting for line width,
control-code layout, compression, and fixed bank footprints. A shortened
patch-safe scenario line therefore does **not** mean that the full translation
was lost. The canonical release now installs the complete configured fixed-menu
labels through the recovered page-indexed layout.
See [`docs/WORKBOOK_PIPELINE.md`](docs/WORKBOOK_PIPELINE.md#preserving-the-full-translation)
before moving natural-field text into the ROM.

## Install and test

Python 3.11 or newer is required. The release dependency set pins Pillow
12.3.0 so title generation uses one exact imaging-library version.

```powershell
python tools/maintenance/check_public_tree.py
python -m pip install -r requirements.txt
time-twist --help
python -m tools.maintenance.run_tests unit
```

The public suite is fixture-free and permits no skips. Public
CI runs source/style/type/unit checks on both Python 3.11 and 3.12. Python 3.12
also builds and force-installs the wheel, proves the smoke test imports the
installed package rather than the checkout, and exercises the CLI.

Maintainers with legally obtained local ROM-derived fixtures can overlay the
private fixture bundle at the repository root and run:

```powershell
python -m tools.maintenance.run_tests integration
python -m tools.maintenance.run_tests all
```

The integration suite contains **75 tests** and also permits no skips. The
runner validates every fixture against `tests/fixtures/integration_fixtures.json` before
test discovery, so missing fixtures produce an explicit setup failure rather
than a misleading green run with skipped tests. See
[`docs/PRIVATE_FIXTURES.md`](docs/PRIVATE_FIXTURES.md).

Private-suite results are recorded separately from public CI evidence. A result
from an earlier release-code revision is historical evidence, not a claim that
the private suite was rerun against the current commit.

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

Repository state note: **No release target is checked in.** A maintainer with
the legal baselines must build and playtest a new candidate, then explicitly
promote that exact reviewed candidate before a normal strict `release-build`
can succeed.

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

Candidate manifests record an authoritative platform-independent SHA-256 over
the Python release tree. Before building or promoting, the command hashes both
the imported `time_twist` package and `<project-root>/work/time_twist` under the
same logical `work/time_twist/...` paths and requires them to match. Optional Git
commit/dirty metadata is informational; the deterministic code-tree digest is
authoritative.

**Promotion independently proves reproducibility.** `release-promote` validates
the reviewed candidate and source lock, performs a fresh candidate-mode rebuild
from the current locked inputs and current release code, and requires the rebuilt
scenario-bank reports, fixed-component hashes, and Zenpen/Kouhen/four-side
output records to equal the reviewed manifest. A self-consistent hand-edited
manifest therefore cannot promote arbitrary candidate bytes.

Promotion also requires the manifest subtitle to match the source lock, rechecks
candidate files immediately before target publication, and rejects custom
source-lock/target destinations that collide with authoritative inputs,
release-critical code, the candidate manifest, or candidate outputs.

Release manifests record the Python implementation/version and exact Pillow
version as build-environment metadata. The Pillow dependency is also pinned in
package metadata; the manifest field remains useful for auditing the environment
that actually produced a candidate. Source, code, component, and output hashes
remain the release authority.

The installed wheel contains code only. It intentionally does not package
translation project data, title assets, ROMs, or generated banks. From outside
the checkout, point it at the project explicitly:

```powershell
time-twist release-build --project-root C:\path\to\time-twist
```

## Documentation

Start with [`docs/README.md`](docs/README.md). Important guides:

- [`PLAYTESTING.md`](PLAYTESTING.md)
- [`CONTRIBUTING_TRANSLATION.md`](CONTRIBUTING_TRANSLATION.md)
- [`CONTRIBUTING_CODE.md`](CONTRIBUTING_CODE.md)
- [`docs/MAINTAINER_RELEASE_PROCESS.md`](docs/MAINTAINER_RELEASE_PROCESS.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMATS.md`](docs/FORMATS.md)
- [`docs/TRANSLATION_WORKFLOW.md`](docs/TRANSLATION_WORKFLOW.md)
- [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md)
- [`docs/WORKBOOK_PIPELINE.md`](docs/WORKBOOK_PIPELINE.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- [`docs/MODULE_MAP.md`](docs/MODULE_MAP.md)
- [`docs/PRIVATE_FIXTURES.md`](docs/PRIVATE_FIXTURES.md)
- [`docs/PROJECT_RETROSPECTIVE.md`](docs/PROJECT_RETROSPECTIVE.md)

## Translation constraints

Time Twist uses packed bitstream text, per-bank dictionaries, several recovered
record-addressing models, and strict RAM/storage limits. Translation changes are validated
against those constraints; raw byte replacement is not sufficient.

Control codes, message ordering, dictionary contracts, scenario tails, and
bank footprints must remain stable. A record boundary may move only when its
complete runtime addressing model is recovered and every affected pointer is
regenerated by a source-verified relocation.

## Copyright and license

Contributor-created code, tests, documentation, and other original materials
are licensed under the [MIT License](LICENSE). The license does not grant
rights to the original game or any third-party software or assets. See
[`THIRD_PARTY_NOTICE.md`](THIRD_PARTY_NOTICE.md).

This is an unofficial fan-translation and reverse-engineering project. It is
not affiliated with, authorized by, or endorsed by Nintendo or the original
rights holders. The public source archive contains no original or patched ROM
images, extracted ROM banks, firmware, emulator packages, or memory dumps.
