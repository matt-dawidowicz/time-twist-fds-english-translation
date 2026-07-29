# Contributing

Contributions are welcome for translation review, reverse engineering,
tooling, tests, and documentation.

## Before editing

Read:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMATS.md`](docs/FORMATS.md)
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)

For dialogue changes, also read
[`docs/TRANSLATION_WORKFLOW.md`](docs/TRANSLATION_WORKFLOW.md).

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

The patch-safe workbook field is generated from the playable sources. To
change in-game scenario text, edit `work/translations/BANK.json`; do not edit a
generated workbook row as the sole source change.

## Code changes

Keep binary operations deterministic and testable. Prefer pure functions that
accept and return `bytes`. Add comments for recovered addresses and explain why
a replacement is safe.

Run the public suite:

```powershell
python -m pip install -e ".[dev]"
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
time-twist release-promote build/candidate/release_manifest.json `
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
