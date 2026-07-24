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

- Do not commit original or patched ROMs, firmware, extracted banks, or memory
  dumps.
- Keep the exact Japanese source field unchanged.
- Preserve control-code values and order.
- Preserve fixed record boundaries and fixed scenario-tail addresses.
- Reject unknown source revisions instead of patching them optimistically.
- Keep names and terminology consistent across all banks and workbook output.
- Do not claim emulator/runtime validation unless it was actually performed.

## Translation changes

Include:

- the affected record IDs;
- the Japanese reading and scene context;
- why the revised English is more accurate or natural;
- any nuance lost in the patch-safe version;
- footprint/display validation results.

Update repeated terminology everywhere if later context changes an established
reading.

## Code changes

Keep binary operations deterministic and testable. Prefer pure functions that
accept and return `bytes`. Add comments for recovered addresses and explain why
the replacement is safe.

Run:

```powershell
cd work
python -m unittest discover -s tests -v
```

Report which ROM-derived tests ran and which were skipped because local
fixtures were unavailable.

## Manual verification

For runtime-affecting changes, provide:

- the exact build SHA-256;
- emulator and version;
- reproduction steps;
- before/after screenshots when visual;
- disk side and story location;
- confirmation that adjacent transitions still work.

Automated tests are not a substitute for full-game playtesting.
