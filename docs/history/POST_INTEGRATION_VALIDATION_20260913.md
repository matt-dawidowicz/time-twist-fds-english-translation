# Post-integration modernization validation — 2026-09-13

This is a permanent amendment to `CONSTRAINT_MODERNIZATION_20260913.md`. It preserves later evidence without rewriting facts that were true during the earlier local modernization pass.

## Why this amendment exists

The original modernization record notes that Black, Ruff, and mypy were not available in the local execution environment used for that phase. That remains historically accurate for that phase and should not be erased.

Subsequent GitHub Actions runs provided the missing validation. Current maintainers should use this amendment together with the original record when determining the present validation state.

## Integrated scope

The constraint-modernization branch later incorporated the complete changes from:

- **PR #60** — contextual fixed-menu localization corrections, including `Jar`, `Old man`, `Ground`, `Forward`, `Time Belt`, `Offer`, and `Plantain`;
- **PR #62** — source-specific TT1B museum-owner speaker labels using `Old man:` for Japanese `ろうじん`, while preserving TT6A `Elder:` for `ちょうろう`.

The combined integration commit was `075b354b982b4ca3bd5ee892b99ddd9ff68c68e0`.

## CI validation

GitHub Actions **run #1264** completed successfully on the combined modernization/localization state.

Both supported Python jobs passed:

- Python 3.11 — success;
- Python 3.14 — success;
- aggregate supported-version gate — success.

The successful run included:

- public-tree validation;
- focused canonical runtime tests;
- bilingual-comparison generation;
- translation-workbook generation;
- generated-artifact freshness checks;
- production translation materialization and source snapshot on Python 3.14;
- Black;
- Ruff;
- pydocstyle;
- mypy;
- unit tests;
- package build and installed-wheel smoke checks on Python 3.14;
- CLI help gates.

Therefore the earlier statement that those lint/type tools had not been run is superseded only as a statement of **current validation status**. It remains valid as a description of the earlier local environment.

## Cleanup policy after integration

Maintained code and documentation should describe only the current architecture. Obsolete implementation scaffolding and obsolete current-tense claims should be removed rather than retained for nostalgia.

Historical records are different: they should retain superseded designs, failed experiments, old constants, and obsolete constraints when those facts explain how the project evolved. When later evidence changes the interpretation, add an amendment or annotation rather than deleting the historical data.

The known examples include:

- the historical six/eight-glyph menu limits;
- the retired `TT2=96` optimizer cap;
- the unsafe `$9391-$93AF` variable-width helper experiment;
- the distinction between native/source-analysis constraints and production entropy constraints.

These belong in history, not in maintained runtime policy.
