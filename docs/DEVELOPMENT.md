# Development guide

## Environment

- Python 3.11 or newer is required.
- Core parsing/patching uses the standard library.
- Pillow is required for title and image-rendering code.
- Mesen is optional and used only for manual playtesting/debugging.

Install from the repository root:

```powershell
python -m pip install -e ".[dev]"
time-twist --help
```

The wheel contains the Python package only. Translation maps, title assets,
source locks, and ROM inputs remain project-checkout data. An installed command
can drive any checkout with `--project-root PATH`.

## Code style

Python code is formatted for Python 3.11 at a 79-column line length. Public
modules, classes, functions, and methods follow the PEP 257 docstring
conventions used throughout the tooling. Run the complete style gate with:

```powershell
python -m black --check work
python -m ruff check work
python -m pydocstyle --convention=pep257 work
```

Use `python -m black work` and `python -m ruff check --fix work` for safe
mechanical corrections, then review docstring changes manually.

## Test suites

### Public unit suite

```powershell
python work/run_tests.py unit
```

This suite is fixture-free, runs in public CI, and currently contains 38 tests.
It covers codecs, synthetic FDS behavior, comparison/workbook integrity, and
release-control logic. Skips are treated as failures.

### Private integration suite

```powershell
python work/run_tests.py integration
```

This suite currently contains 67 exact-ROM tests. Before discovery, the runner
validates the private local overlay against `work/integration_fixtures.json`.
Missing or changed fixtures stop the run as a setup error; integration tests do
not quietly disappear behind `skipTest()`.

Run both suites with:

```powershell
python work/run_tests.py all
```

See [`PRIVATE_FIXTURES.md`](PRIVATE_FIXTURES.md) for the public/private split.

## CI and wheel checks

Public CI performs:

```powershell
python work/tools/check_public_tree.py
python -m pip install -e ".[dev]"
python -m black --check work
python -m ruff check work
python -m pydocstyle --convention=pep257 work
python work/run_tests.py unit
python -m build
python -m pip install --force-reinstall dist/*.whl
time-twist --help
time-twist release-build --help
```

This catches both source-tree import accidents and incomplete wheel packaging.
The release command itself requires a project checkout and user-supplied
baselines; those data are intentionally not embedded in the wheel.

## Adding or changing a binary patch

1. **Identify the owning FDS file.** Do not search the combined ROM and patch
   the first matching byte sequence.
2. **Record the load address and file offset.** Name constants so the coordinate
   system is unambiguous.
3. **Capture the expected source.** Use exact bytes for a short instruction or
   SHA-256 for a complete fixed table/asset.
4. **State the invariant.** Examples: record sizes, file size, tail address,
   clock bytes, or one-choice-only input behavior.
5. **Write a pure patch function.** Accept `bytes`, validate first, return new
   `bytes`, and avoid filesystem/emulator state.
6. **Verify the output.** Re-decode data or assert the exact changed range.
7. **Add rejection coverage.** A deliberately modified source must raise the
   patch's domain error.
8. **Add scope coverage.** With private fixtures, prove that only the intended
   FDS file changed.
9. **Run both supported suites and playtest.**

Never weaken a source check because a patch fails on a different build. Add an
explicit supported revision with evidence instead.

## Editing packed text safely

Use the highest-level playable source:

- story dialogue: `work/translations/BANK.json`;
- fixed UI labels: the named record definition in `work/time_twist/ui.py`;
- font glyphs: `PIXEL_FONT_5X7` and mapping tables;
- title art: the title reference image and conversion code.

The complete workbook is regenerated review output. Its patch-safe field mirrors
the playable text; the natural-translation field may preserve a less constrained
editorial alternative.

After changing text:

1. run `scenario-merge` and `scenario-footprint` for the bank;
2. regenerate the workbook;
3. run the public and private tests available to you;
4. refresh the approved source lock intentionally;
5. create a candidate release;
6. inspect and playtest the affected scenes;
7. promote the exact reviewed candidate.

## Dictionary debugging

When a bank no longer fits:

- compare literal and compressed sizes from `scenario-footprint`;
- inspect repeated complete words and speaker prefixes;
- check bank-specific required dictionary entries;
- remember that a dictionary reference costs 9 bits;
- remember that the encoded dictionary entry consumes bytes;
- avoid nested English entries, which the compressor forbids;
- verify that fixed tables still have the words they require.

A dictionary change can save scenario space while making a tiny fixed record
impossible to encode. Treat scenario and fixed-table use as one budget.

## Display debugging

| Symptom | Likely layer |
| --- | --- |
| Wrong letters everywhere | Font or English tile mapping |
| Japanese renders as English gibberish | Untranslated record using English font |
| End of old line remains visible | Menu/dialogue clearing or transparent-tail behavior |
| Final character wraps/gets overwritten | 24-column segmentation or control placement |

Do not solve a line-clearing bug by padding every line with visible or opaque
spaces. The typewriter renderer can process them as silent characters and
alter timing.

## Title debugging

Check separately:

- palette-index assignment;
- upper/lower exact tile counts;
- second-nametable slide positions;
- all 21 recovered nine-bit swipe origins and the NT0/NT1 wrap boundary;
- the one-shot post-Nintendo `$B0-$D5` CHR restoration before state 3;
- Nintendo overlay/restore ranges;
- clock background center;
- unchanged clock sprite/animation bytes;
- transition and exit helper call/stack behavior.

A correct static preview does not prove START, B, the swipe, raster-split
shutdown, or the next game state.

## Release lifecycle

`work/release_sources.json` locks all approved non-code inputs. Strict builds
also require `work/release_target.json`, whose hashes are tied to that exact
source lock.

Verify the current target:

```powershell
time-twist release-lock
time-twist release-build
```

Promote a deliberate change:

```powershell
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
# Review/playtest build/candidate.
time-twist release-promote build/candidate/release_manifest.json `
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Candidate output is not approval. `release-promote` re-hashes every candidate
file and verifies its active source lock. A strict build stages everything and
publishes only after target validation succeeds.

External source-lock paths are supported. Manifests record a project-relative
path when possible and an absolute path otherwise.

## Generated and ignored files

Keep these local:

- original/patched `.fds` images;
- extracted and rebuilt `.bin` banks;
- emulator `.dmp` captures;
- emulator archives/settings;
- build/dist directories and Python caches.

Commit code, fixture-free tests, integration-test source, translation JSON,
source/target manifests, documentation, review workbooks, and permissible
reference/preview images.

## Review checklist

- [ ] New offsets identify component and coordinate system.
- [ ] Source bytes or hashes are validated.
- [ ] Error messages identify the failed invariant.
- [ ] Control-code order is unchanged or the exception is documented/tested.
- [ ] Fixed record/table/bank sizes and tail addresses are preserved.
- [ ] Black, Ruff, and pydocstyle checks pass.
- [ ] Public tests pass with zero skips.
- [ ] Private integration tests pass with zero skips when fixtures are available.
- [ ] Wheel build/install smoke test passes.
- [ ] Candidate manifest and outputs were reviewed before promotion.
- [ ] Manual playtest covers the affected scene and adjacent transitions.
