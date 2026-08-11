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
python -m mypy
```

Use `python -m black work` and `python -m ruff check --fix work` for safe
mechanical corrections, then review docstring changes manually.

## Test suites

### Public unit suite

```powershell
python work/run_tests.py unit
```

This suite is fixture-free, runs in public CI, and currently contains 83 tests.
It covers codecs, synthetic FDS behavior, compression invariants,
comparison/workbook integrity, declarative patch guards, and release-control
logic. Skips are treated as failures.

### Private integration suite

```powershell
python work/run_tests.py integration
```

This suite currently contains 75 exact-ROM tests. Before discovery, the runner
validates the private local overlay against `work/integration_fixtures.json`.
Missing or changed fixtures stop the run as a setup error; integration tests do
not quietly disappear behind `skipTest()`.

Run both suites with:

```powershell
python work/run_tests.py all
```

Private results must be attributed to the exact release-code revision on which
they were run. An older private run remains historical evidence, but it is not a
fresh validation of a later release-tool commit.

See [`PRIVATE_FIXTURES.md`](PRIVATE_FIXTURES.md) for the public/private split.

## CI and wheel checks

Public CI runs the public-tree gate, style checks, type checking, and fixture-free
unit suite on Python 3.11 and 3.12. Python 3.12 additionally performs the
packaging and installed-wheel smoke checks:

```powershell
python work/tools/check_public_tree.py
python -m pip install -e ".[dev]"
python -m black --check work
python -m ruff check work
python -m pydocstyle --convention=pep257 work
python -m mypy
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

`work/release_sources.json` locks all approved non-code inputs. Schema v2
declares `lf` normalization for `work/translations/*.json` and `raw` for the
Japanese FDS baselines and indexed title PNG. This makes equivalent LF/CRLF
translation checkouts portable while retaining byte-exact binary guards. The
lock document's own SHA-256 is likewise calculated after LF normalization.
`.gitattributes` reinforces this representation, but validation does not
depend on Git.

Strict builds also require a promoted `work/release_target.json`, whose hashes
are tied to that exact logical source lock and to the active release-critical
Python code.

No target is checked in while the current candidate awaits playtesting. The
obsolete v1 target was removed rather than being converted by hand. Therefore,
the strict command below becomes usable only after a maintainer with legal
baselines has built, reviewed, playtested, and explicitly promoted the exact
candidate.

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

Candidate output is not approval. Manifest schema v4 binds promotion to a
complete audit record: source-lock and release-code provenance, informational
Python/Pillow environment versions, all scenario-bank reports, fixed-component
hashes, target state, and canonical output records. Legacy v3 candidate
manifests must be rebuilt with the current release code before promotion.

Promotion independently proves the reviewed candidate rather than trusting its
manifest. `release-promote` validates the active lock and code provenance, binds
the candidate subtitle to the lock, then performs a fresh candidate-mode rebuild
with the current code and approved inputs. The fresh rebuild's complete
`scenario_banks`, `component_sha256`, and `outputs` records must exactly equal
the reviewed manifest before a target can be written.

Candidate files are checked both before that proof and immediately before target
publication; the manifest itself is re-hashed at the final publication boundary.
These checks strongly mitigate local time-of-check/time-of-use changes but do not
claim hostile-filesystem transactional semantics across several independent
files. The release threat model remains a trusted local build environment.

Custom metadata destinations are fail-closed. A source-lock update cannot
overwrite an approved source, project metadata, release code, or the release
target. Promotion cannot write its target over the active source lock, candidate
manifest, candidate outputs, approved sources, project metadata, or release
code. The canonical source-lock and target locations remain valid exceptions for
their respective commands.

Git commit and dirty-state metadata are recorded when Git is available, but the
platform-independent code-tree hash is authoritative. Python and Pillow versions
are diagnostic metadata only; component and output identities decide whether a
candidate reproduces.

External source-lock paths are supported. Manifests record a project-relative
path when possible and an absolute path otherwise.

The private release integration test can build two candidates and require their
manifests and images to be byte-identical when the legal fixture overlay is
available. A separate test requires the unpromoted checkout to reject strict
publication because its target is absent. Candidate reproducibility evidence is
not promotion; promotion repeats the reproducibility proof independently.

See [`RELEASE_RISK_ASSESSMENT.md`](RELEASE_RISK_ASSESSMENT.md) for the audited
failure modes, mitigations, accepted threat boundary, and remaining manual
playtest obligations.

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
- [ ] Black, Ruff, pydocstyle, and mypy checks pass.
- [ ] Public tests pass with zero skips on supported Python versions.
- [ ] Private integration tests pass with zero skips when fixtures are available.
- [ ] Wheel build/install smoke test passes.
- [ ] Candidate manifest and outputs were reviewed before promotion.
- [ ] Promotion's fresh rebuild matches the reviewed candidate exactly.
- [ ] Manual playtest covers the affected scene and adjacent transitions.
