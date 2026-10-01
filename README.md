# Time Twist: On the Outskirts of History — English Translation

This repository contains the reverse-engineering tools, canonical English text,
tests, and build system for an English translation of Nintendo's 1991 Famicom
Disk System adventure game *Time Twist: Rekishi no Katasumi de...*
(`タイムツイスト 歴史のかたすみで…`).

It covers both halves:

- `Zenpen` (Part 1)
- `Kouhen` (Part 2)

The repository contains no original or patched game images, FDS BIOS files,
emulator bundles, save states, or extracted retail payloads. Public patcher
binaries and BPS patch files are provided under `release/`.

## Download the English patch

For most Windows users:

- **[Download TimeTwistEnglishPatcher.exe](release/TimeTwistEnglishPatcher.exe)** — self-contained patcher with both BPS patches built in
- **[Download the complete Windows package](release/Time-Twist-English-v1.0-Windows.zip)** — EXE, README, license, checksums, and both BPS patches

Manual BPS patches:

- [Zenpen BPS patch](release/Time-Twist-English-v1.0-Zenpen.bps)
- [Kouhen BPS patch](release/Time-Twist-English-v1.0-Kouhen.bps)

The executable takes the two clean Japanese retail FDS images, identifies
Zenpen/Kouhen automatically, and can create the two translated disks, the
combined four-side v1.0 image, or both. It never contains or distributes the
original game data.

## Start here

- **Play a candidate and report problems:** [PLAYTESTING.md](PLAYTESTING.md)
- **Set up a local checkout:** [QUICKSTART.md](QUICKSTART.md)
- **Improve English text:** [CONTRIBUTING_TRANSLATION.md](CONTRIBUTING_TRANSLATION.md)
- **Improve tools or tests:** [CONTRIBUTING_CODE.md](CONTRIBUTING_CODE.md)
- **Read the architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **See what is reverse-engineered:** [docs/REVERSE_ENGINEERING_STATUS.md](docs/REVERSE_ENGINEERING_STATUS.md)
- **Review major engine changes and bug fixes:** [docs/ENGINE_CHANGELOG.md](docs/ENGINE_CHANGELOG.md)
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
renderer-control layout for all **1,299 scenario records**. They are the
editorial source of truth and are source-locked as release inputs. The exact
v1.0 binary build also validates their complete record topology, while binary
reproduction follows the separately verified historical checkpoint lineage.

`work/source_records/*.json` is the Japanese/source-structure evidence. It is
not an alternate English source.

The completed **v50** ROM remains the project's end-to-end playtest baseline,
SHA-256
`820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43`.
The public release applies the reviewed TT1A fortune-menu handoff correction and
the Dr. Simon dialogue-scroll regression fix on top of that baseline. Its SHA-256 is
`39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5`.

Exact release reproduction uses the private v25 safe-encoding image to rebuild
the frozen v38 checkpoint, applies the hash-guarded v38-to-v41 and
late-v41-to-v50 checkpoint deltas, applies the guarded TT1A correction, and then
applies the reviewed Dr. Simon dialogue-fix delta.
The older checkpoints remain historical implementation inputs and regression
evidence, **not** competing release authorities.

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
| Final v50 ROM behavior | End-to-end playtest baseline |
| Corrected final release | v50 plus the guarded TT1A fortune-menu handoff fix |
| `recovery/v38/repro_bundle/` | Frozen compiler/recovery material that reproduces exact v38 |
| `recovery/v41/` | Hash-guarded checkpoint deltas that reproduce the validated v38 -> late-v41 -> v50 lineage |
| Private v25 safe-encoding seed image | Required historical seed for exact v38 reconstruction |
| `work/release_sources.json` | Approved non-code release inputs and hashes, including checkpoint payloads |
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

The reproducible release command starts from the exact private v25
safe-encoding **seed image**. Put that locally supplied image at:

```text
work/baseline/time_twist_v25_safe_encoding.fds
```

Required SHA-256:
`813CDCEB190E9714F7489C1BD5500F8E2EAD3B3942F789CCF68BC6F3696BFC19`.
It is a 262,000-byte four-side image, not either Japanese retail image.

```powershell
time-twist release-lock
time-twist release-build --candidate --output-dir build/candidate
```

The exact binary lineage is explicit and fail-closed:

1. the recovered compiler rebuilds the immutable v38 checkpoint,
   SHA-256 `62C5DBC2DE33C484DE9F8C1318FC903642EB08E2B4D5FA8E28384DC699C4C400`;
2. the reviewed `TTD1` source-copy delta promotes exact v38 to the validated
   late-v41 checkpoint,
   SHA-256 `13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1`;
3. a second guarded delta promotes that checkpoint to final v50,
   SHA-256 `820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43`.
4. a guarded one-byte TT1A control correction produces the pre-Simon public
   release, SHA-256 `BB3D147FE2245987EFAE579A4130DD8B8599AD7049C264696EA4B52C8CED4D4B`;
5. a final guarded delta changes only `TT1B/g3/r6` semantically, removing the
   unnecessary intermediate dialogue scroll in the Dr. Simon scene and producing
   SHA-256 `39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5`.

Each bridge verifies its source, delta, and target identities. The final build
also reproduces the two translated 131,000-byte disk halves exactly. No complete
ROM image is stored in the checkpoint source tree.

The source lock covers the v25 seed, all 1,299 canonical translation records,
the frozen v38 compiler bundle, and the checkpoint payloads. The current maps
must retain the complete record topology and remain the authoritative editorial
English. The historical compiler is deliberately **not** claimed to compile
post-v38 text/layout changes that exceed its recovered packing model.

After review, a maintainer can still promote a candidate manifest:

```powershell
time-twist release-promote build/candidate/release_manifest.json \
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Future wording, layout, graphics, or runtime changes require a new reviewed
lineage, refreshed source locks, targeted runtime validation, and a new final
hash. The existing v38, late-v41, and v50 checkpoints are immutable provenance.

No release target is checked in yet. Promotion metadata remains separate from
the already verified behavioral and binary authority of final v50.

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
- [docs/ENGINE_CHANGELOG.md](docs/ENGINE_CHANGELOG.md)
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