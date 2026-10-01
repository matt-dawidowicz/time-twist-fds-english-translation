# Contributing

Contributions are welcome for translation review, reverse engineering,
tooling, tests, documentation, and experimental engine work.

This repository is intentionally both a finished English fan translation and a
technical reference for further study of *Time Twist*. A large amount of the
game's text, rendering, graphics, menu, FDS, and runtime behavior has already
been reverse-engineered. Please build on the documented model rather than
starting from zero.

## Canonical release versus experimental work

The `main` branch is the canonical, maintainer-controlled release line.

Do not use `main` as a development sandbox. Make changes in a fork or feature
branch. You are encouraged to experiment aggressively there: rewrite tools,
investigate unknown routines, prototype engine changes, test alternative
implementations, or pursue fixes that may never belong in the official release.

If you believe a change should become part of the canonical project, open a
pull request targeting `main`. A pull request is a proposal for review, not
automatic permission to change the canonical release.

The maintainer decides what is merged into `main`. Experimental forks and
branches may diverge as much as their authors want.

## How to get a proposed change reviewed

Open a pull request against `main` and complete the repository pull-request
template. The repository's CODEOWNERS configuration requests review from
`@matt-dawidowicz` for changes anywhere in the project.

For release-affecting changes, include enough evidence that the change can be
reproduced and evaluated without rediscovering the relevant subsystem.

## Choose your contribution path

- **Playtest a candidate:** [Playtesting guide](PLAYTESTING.md)
- **Review or improve English:** [Translation contributor guide](CONTRIBUTING_TRANSLATION.md)
- **Change tools or tests:** [Code contributor guide](CONTRIBUTING_CODE.md)
- **Reverse-engineer or experiment:** [Open reverse-engineering work](docs/OPEN_REVERSE_ENGINEERING.md)
- **Understand the current recovered model:** [Reverse-engineering status](docs/REVERSE_ENGINEERING_STATUS.md)

The remainder of this page covers rules shared by all source contributions.

## Before editing

Read:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMATS.md`](docs/FORMATS.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- [`docs/REVERSE_ENGINEERING_GUIDE.md`](docs/REVERSE_ENGINEERING_GUIDE.md)

For dialogue changes, also read
[`docs/TRANSLATION_WORKFLOW.md`](docs/TRANSLATION_WORKFLOW.md).

For runtime or binary changes, inspect the specialized engine documentation
linked from [`docs/REVERSE_ENGINEERING_STATUS.md`](docs/REVERSE_ENGINEERING_STATUS.md)
before treating a subsystem as unknown.

## Reverse-engineering contributions

Reverse-engineering discoveries are valuable contributions even when they do not
immediately produce a patch.

When possible, document:

- FDS component and source revision;
- file offset and loaded CPU address;
- pointer or caller chain;
- runtime state or emulator evidence;
- observed behavior;
- verified interpretation;
- bytes or addresses that may change;
- bytes or addresses that must remain stable;
- a regression test or playtest route;
- remaining unknowns.

Use the evidence vocabulary from
[`docs/REVERSE_ENGINEERING_GUIDE.md`](docs/REVERSE_ENGINEERING_GUIDE.md):
**VERIFIED**, **OBSERVED**, **DERIVED**, **INFERRED**, and **UNKNOWN**.

Do not replace an existing verified model with a plausible guess. If new
evidence contradicts the documentation, show the evidence and update the model
explicitly.

## Non-negotiable constraints

- Do not commit original or patched ROMs, firmware, extracted banks, emulator
  archives/settings, or memory dumps.
- Keep the exact Japanese source field unchanged.
- Preserve control-code values and order, except for a documented and tested
  engine-level override.
- Preserve fixed record boundaries and fixed scenario-tail addresses.
- Reject unknown source revisions instead of patching them optimistically.
- Keep names and terminology consistent across all banks and workbook output.
- Do not claim emulator/runtime validation unless it was actually performed.
- Never refresh a source lock or promote output hashes as a way to hide an
  unexplained binary change.

## Translation changes

Include:

- affected record IDs;
- Japanese reading and scene context;
- why the revised English is more accurate or natural;
- any nuance retained only in the natural-translation field;
- footprint/display validation results.

The patch-safe workbook field is generated from the playable source composition.
Change the registered production-review JSON for current reviewed wording, the
base map only when its certified baseline/topology is intentionally changing, or
an explicit final override for a narrow last-mile correction. Do not edit a
generated workbook row as the sole source change.

## Code changes

Keep binary operations deterministic and testable. Prefer pure functions that
accept and return `bytes`. Add comments for recovered addresses and explain why
a replacement is safe.

Run the public suite:

```powershell
python -m pip install -r requirements.txt
python work/run_tests.py unit
python -m build
```

Maintainers with the private fixture overlay must also run:

```powershell
python work/run_tests.py integration
```

Supported suites reject skipped tests. Missing private fixtures must be
reported as unavailable, not converted into test skips.

## Release-affecting changes

After tests pass:

```powershell
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
```

Review and playtest the candidate. Promote only the exact candidate manifest
that was reviewed:

```powershell
time-twist release-promote build/candidate/release_manifest.json \
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Commit `work/release_sources.json` and `work/release_target.json` only when the
source and output changes are intentional and explained.

## Manual verification

For runtime-affecting changes, provide:

- exact build SHA-256;
- emulator and version;
- reproduction steps;
- before/after screenshots when visual;
- disk side and story location;
- confirmation that adjacent transitions still work.

Automated tests are not a substitute for full-game playtesting.
