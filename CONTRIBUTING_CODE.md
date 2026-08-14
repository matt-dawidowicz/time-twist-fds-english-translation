# Contributing code

This guide is for Python tooling, validation, and test changes. It does not
authorize changes to ROM-derived fixtures or release metadata.

If you want to report game behavior rather than change source, start with the
[playtesting guide](PLAYTESTING.md). For prose-only work, use the
[translation contributor guide](CONTRIBUTING_TRANSLATION.md).

## Local setup

Python 3.11 or newer is required. From the repository root:

```powershell
python -m pip install -r requirements.txt
time-twist --help
```

This installs the project plus every public runtime, test, and development
dependency: Pillow, Hypothesis, Black, Ruff, mypy, pydocstyle, and build.
Add a new dependency to `pyproject.toml`; `requirements.txt` automatically
installs it for contributors and CI.

The installed wheel contains the Python package only. Translation maps, title
assets, source locks, and legal game inputs remain checkout data.

## Public test workflow

Run this for every code change:

```powershell
python work/run_tests.py unit
```

For changes to Python code, run the project style and type checks as well:

```powershell
python -m black --check work
python -m ruff check work
python -m pydocstyle --convention=pep257 work
python -m mypy
```

Use `python -m black work` or `python -m ruff check --fix work` only for
mechanical corrections, then review the diff.

## Public tests versus private maintainer tests

`python work/run_tests.py unit` is fixture-free and runs without game data.
`python work/run_tests.py integration` checks exact ROM-derived transforms and
requires a separately maintained private fixture overlay. Missing fixtures are
an expected setup limitation, not a reason to add skips or weaken checks.

Most code contributors only need the public suite. Maintainers with legal
fixtures must also run:

```powershell
python work/run_tests.py integration
```

See [Maintainer release process](docs/MAINTAINER_RELEASE_PROCESS.md#private-fixtures-and-integration-tests)
for the boundary and [Private integration fixtures](docs/PRIVATE_FIXTURES.md)
for the overlay layout.

## Module map

| Area | Main module |
| --- | --- |
| Command-line entry point | `work/time_twist/cli.py` (`cli_commands.py`, `cli_parser.py`) |
| FDS parsing and rebuilding | `work/time_twist/fds.py` |
| Packed symbols and native codec | `work/time_twist/textcodec.py` |
| English encoding and validation | `work/time_twist/english.py`, `scenario_validation.py` |
| Scenario parsing/recompression | `work/time_twist/scenario.py`, `compression.py` |
| Fixed UI patches and data | `work/time_twist/ui.py`, `ui_fixed_tables.py` |
| Font and title patches | `work/time_twist/font.py`, `title.py`, `title_layout.py`, `title_assets.py`, `title_patch.py` |
| Candidate/release assembly | `work/time_twist/release.py`, `release_metadata.py` |

See the [full module map](docs/MODULE_MAP.md) for the public-facade rule and
matching test files.

## Documentation is part of the change

Start with the [code tour](docs/CODE_TOUR.md) before changing an unfamiliar
module. It explains how each layer serves the playable, source-only translation
goal and which constraints belong to packed text, FDS layout, fixed UI, title,
or release assembly.

Every maintained Python module, class, and function must have a purpose
docstring. Explain non-obvious lines with comments that answer **why** a
recovered address, byte sequence, capacity limit, or fail-closed condition
exists. Do not pad routine syntax with line-by-line narration; it makes the
binary constraints harder to find.

`work/tests/test_documentation_contract.py` enforces this baseline in the
public unit suite. A new function without a docstring is an incomplete change.

## High-risk areas

Treat these as evidence-driven changes, not ordinary refactors:

- FDS parsing and rebuilding;
- scenario packing, compression, and dictionary boundaries;
- fixed-address UI patches;
- font and title patching;
- source-lock, provenance, candidate, and release-target code.

For a high-risk change, identify the owning FDS file, distinguish file offsets
from CPU addresses, guard the expected source bytes, state the size/address
invariant, add a focused regression test, and provide runtime evidence when the
change affects gameplay or display behavior.

Do not "fix" a guard by accepting a new unknown byte sequence. Add support for
another revision only with evidence that it is the same intended target.

## Safe change process

1. Keep binary transformations deterministic and testable.
2. Prefer functions that accept `bytes`, validate first, and return new bytes.
3. Add both success and rejection coverage for source-verified patches.
4. Preserve record boundaries, scenario tails, control order, and clock/title
   ownership unless the change explicitly proves a safe alternative.
5. Run public checks and private integration tests when available.
6. For runtime behavior, supply the candidate hash, emulator/version,
   reproduction steps, and before/after evidence.

## A good code pull request

Include the problem being solved, affected modules, safety invariant, tests
run, unavailable private checks, and any required manual-playtest evidence.
Avoid committing ROMs, extracted banks, emulator dumps, build directories, or
private fixture files.

## Deeper references

- [Architecture](docs/ARCHITECTURE.md)
- [Format reference](docs/FORMATS.md)
- [CLI reference](docs/CLI_REFERENCE.md)
- [Technical implementation notes](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md)
- [Maintainer release process](docs/MAINTAINER_RELEASE_PROCESS.md)
