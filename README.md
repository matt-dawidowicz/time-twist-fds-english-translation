# Time Twist: On the Outskirts of History — English Translation

This repository contains the reverse-engineering tools, canonical English text,
tests, and build system for an English translation of Nintendo's 1991 Famicom
Disk System adventure game *Time Twist: Rekishi no Katasumi de...*
(`タイムツイスト 歴史のかたすみで…`).

It covers both halves:

- `Zenpen` (Part 1)
- `Kouhen` (Part 2)

The repository is source-only. It contains no original or patched game images,
FDS BIOS files, emulator bundles, save states, or extracted retail payloads.

## Start here

- **Play a candidate and report problems:** [PLAYTESTING.md](PLAYTESTING.md)
- **Set up a local checkout:** [QUICKSTART.md](QUICKSTART.md)
- **Improve English text:** [CONTRIBUTING_TRANSLATION.md](CONTRIBUTING_TRANSLATION.md)
- **Improve tools or tests:** [CONTRIBUTING_CODE.md](CONTRIBUTING_CODE.md)
- **Read the architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **See what is reverse-engineered:** [docs/REVERSE_ENGINEERING_STATUS.md](docs/REVERSE_ENGINEERING_STATUS.md)
- **See what the English ROM actually changes:** [docs/ROM_MODIFICATION_INVENTORY.md](docs/ROM_MODIFICATION_INVENTORY.md)
- **Tour the implementation:** [docs/CODE_TOUR.md](docs/CODE_TOUR.md)

## Playing Part 2 (Kouhen)

Part 2 does **not** start by booting the Kouhen disk directly. Time Twist uses
the completed Zenpen disk state to unlock the second half.

After finishing Part 1:

1. Keep the completed Zenpen FDS write/save state.
2. Power-cycle or reopen the **same candidate** with **Part 1 / Side A**
   (`TT1` Side A) selected.
3. Continue through the title/start flow and choose **Part 2** when it becomes
   available.
4. When the game asks for **Part 2 / Side B**, switch to `TT2` Side B. In the
   combined four-side image this is the **fourth side**.
5. Continue normally into Kouhen.

Booting `TT2` Side A directly is a negative/guard path and should direct the
player back to Part 1.

## Current translation authority

There is exactly **one active scenario-English source**:

```text
work/translations/<BANK>.json
```

The 13 bank files contain the complete current wording **and** the approved
renderer-control layout for all **1,299 scenario records**. The release builder
validates and consumes those maps directly.

`work/source_records/*.json` is the Japanese/source-structure evidence. It is
not an alternate English source.

The completed **v50** ROM is the project's behavioral release baseline. Its
verified SHA-256 is
`820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43`.
Maintained source and build tooling are expected to reproduce that behavior.

The pipeline still uses recovered v38 compiler material and the private v25
safe-encoding image as implementation inputs while source parity is completed.
Those older artifacts are historical recovery/regression evidence, **not** the
behavioral baseline. When an old input disagrees with verified v50 behavior,
v50 wins and the maintained source must be advanced accordingly.

Generated ROMs remain build products rather than editable source material.

## Current status

- **1,299 scenario records** have one canonical playable English entry.
- Canonical scenario maps are validated against the four-row, 24-column NOV2
  renderer model.
- Every recognized new speaker heading must start on a fresh row.
- Generic editing tools fill rows greedily; seven exact v38 exceptions remain
  only for audited structural quiz/UI geometry.
- Quiz prompts, identity/info cards, and explicitly registered presentation
  records may retain intentional non-greedy geometry.
- Fixed UI, title, font, scenario text, and FDS-container changes are built by
  one source-locked release pipeline.
- The complete gameplay route and final ending/credit presentation have been
  playtested; **v50 is the canonical behavioral baseline** for release parity.

## Source of truth

| Material | Authority |
| --- | --- |
| `work/translations/*.json` | Sole current scenario-English wording and approved control layout |
| `work/source_records/*.json` | Decoded Japanese/source evidence and stable record IDs |
| Final v50 ROM behavior | Canonical release baseline and source-parity target |
| `recovery/v38/repro_bundle/` | Historical compiler/recovery material and immutable regression oracle |
| Private v25 safe-encoding seed image | Historical build seed for unchanged retail payloads while source parity is completed |
| `work/release_sources.json` | Approved non-code release inputs and hashes |
| `work/release_target.json` | Promoted output/provenance authority when present |
| `docs/history/` and `audit/` | Historical engineering evidence only; never release input |

## Repository layout

| Path | Contents |
| --- | --- |
| `docs/` | Current architecture, formats, workflow, and development guides |
| `docs/history/` | Retired architecture and engineering history |
| `audit/` | Historical/source-analysis evidence; never build input |
| `work/time_twist/` | FDS parsing, compression, text, font, title, UI, and release code |
| `work/tests/` | Fixture-free public tests |
| `work/integration_tests/` | ROM-derived maintainer tests |
| `work/translations/` | Sole canonical scenario-English maps |
| `work/source_records/` | Decoded Japanese/source records |
| `work/title_assets/` | Contributor-created English title reference art |
| `outputs/` | Current terminology/glossary references only |

## Translation layout rules

Scenario records use packed bitstream text and a four-row dialogue staging
buffer. The current canonical maps must obey these rules:

1. Preserve the intended Japanese meaning, speaker identity, and scene logic.
2. A recognized new speaker heading starts on a **fresh physical row**.
3. Within a speaker turn, fill each ordinary row as far as possible up to the
   24-column limit.
4. Never split a speaker heading.
5. Preserve audited semantic waits/re-entry controls.
6. Treat quiz and identity/info-card row geometry as structural UI state.
7. Never shorten or substitute wording merely because an older representation
   was easier to pack; if a current line cannot fit safely, document the exact
   engine constraint and solve it deliberately.

See [docs/TRANSLATION_WORKFLOW.md](docs/TRANSLATION_WORKFLOW.md),
[docs/ENGLISH_PAGINATION_POLICY.md](docs/ENGLISH_PAGINATION_POLICY.md), and the
maintainer-facing [docs/TEXT_LAYOUT_ENGINE_REFERENCE.md](docs/TEXT_LAYOUT_ENGINE_REFERENCE.md).

## Install and test

Python 3.11 or newer is required.

```powershell
python work/tools/check_public_tree.py
python -m pip install -r requirements.txt
time-twist --help
python work/run_tests.py unit
```

Maintainers with legally obtained local ROM-derived fixtures can additionally
run:

```powershell
python work/run_tests.py integration
python work/run_tests.py all
```

Private fixtures are hash-described in `work/integration_fixtures.json` and
are not committed.

## Build and promote a release

The normal command currently rebuilds from recovered v38 compiler material and the
exact private v25 safe-encoding **seed image** while the maintained pipeline is
being brought to parity with the final v50 baseline. Put that locally supplied
seed image at:

```text
work/baseline/time_twist_v25_safe_encoding.fds
```

Required SHA-256:
`813cdceb190e9714f7489c1bd5500f8e2ead3b3942f789ccf68bc6f3696bfc19`.
It is a 262,000-byte four-side image, not either Japanese retail image.

```powershell
time-twist release-lock
time-twist release-build --candidate --output-dir build/candidate
```

The lock covers the seed image, all 1,299 active maps, and every frozen compiler
payload. Active records must retain the recovered v38 record topology, but
reviewed wording/layout may advance beyond v38. If the active maps are exactly
the v38 text, the historical four-side SHA-256
`62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400`
is still enforced. Later candidates receive their output identity through the
candidate manifest and explicit promotion. The executing package is
independently hashed, and compilation/source checks finish before publication.

After complete playtesting and review, a maintainer can promote that candidate:

```powershell
time-twist release-promote build/candidate/release_manifest.json \
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Future wording or layout changes require review, source-lock refresh, targeted
runtime validation, and a newly promoted candidate output. The historical v38
checkpoint itself remains immutable; see
[the v38 integration notes](docs/V38_CANONICAL_BUILD.md).

No release target is checked in yet. That promotion metadata is distinct from the
behavioral authority: final v50 is already the project baseline. Remaining
candidate/promotion machinery describes build provenance, not authority over game
behavior; source work is complete only when it reproduces the final baseline.

## Documentation

- [PLAYTESTING.md](PLAYTESTING.md)
- [CONTRIBUTING_TRANSLATION.md](CONTRIBUTING_TRANSLATION.md)
- [CONTRIBUTING_CODE.md](CONTRIBUTING_CODE.md)
- [docs/README.md](docs/README.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/FORMATS.md](docs/FORMATS.md)
- [docs/TRANSLATION_WORKFLOW.md](docs/TRANSLATION_WORKFLOW.md)
- [docs/ENGLISH_PAGINATION_POLICY.md](docs/ENGLISH_PAGINATION_POLICY.md)
- [docs/REVERSE_ENGINEERING_GUIDE.md](docs/REVERSE_ENGINEERING_GUIDE.md)
- [docs/REVERSE_ENGINEERING_STATUS.md](docs/REVERSE_ENGINEERING_STATUS.md)
- [docs/ROM_MODIFICATION_INVENTORY.md](docs/ROM_MODIFICATION_INVENTORY.md)
- [docs/TEXT_LAYOUT_ENGINE_REFERENCE.md](docs/TEXT_LAYOUT_ENGINE_REFERENCE.md)
- [docs/TT1A_FORTUNE_TELLER_LOGIC.md](docs/TT1A_FORTUNE_TELLER_LOGIC.md)
- [docs/MAINTAINER_RELEASE_PROCESS.md](docs/MAINTAINER_RELEASE_PROCESS.md)
- [docs/history/README.md](docs/history/README.md)

Git history and `docs/history/` preserve retired engineering context without
participating in current builds.

## Copyright and license

Contributor-created code, tests, documentation, and other original materials
are licensed under the [MIT License](LICENSE). The license does not grant rights
to the original game or any third-party software or assets. See
[THIRD_PARTY_NOTICE.md](THIRD_PARTY_NOTICE.md).

This is an unofficial fan translation and reverse-engineering project. It is
not affiliated with, authorized by, or endorsed by Nintendo or the original
rights holders.
