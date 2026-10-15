# Code health, performance, and safe refactoring guide

**Maintained guidance for contributors.** This page explains which Time Twist
code is safe to simplify, why apparently duplicated pieces exist, how to
reproduce performance measurements, and what constitutes proof that a cleanup
has not changed the English game.

The source state before this audit is permanently recorded in
[the 13 October 2026 baseline](history/CODE_HEALTH_BASELINE_20261013.md),
including a full module-to-Git-blob inventory and the exact Git commit. Use
[Code tour](CODE_TOUR.md) for the normal architecture walkthrough and
[Maintainer release process](MAINTAINER_RELEASE_PROCESS.md) for binary
reconstruction. The historical record and this maintained guide have different
purposes: preserve exact old code with Git and historical tests, and document
current practices here.

## Executive findings

A recursive Git tree audit covered 359 tracked files totaling about 33.1 MB,
including 53 Python package modules (about 691 KB), 50 ordinary test files,
16 public tooling scripts, six private-integration test scripts, and
three GitHub Actions workflows. Most bytes are **not** active Python code:
the committed release binaries, translation evidence, and title assets are
deliberate parts of a reproducible fan translation.

Three deterministic code paths had avoidable work:

| Area | Previous behavior | Safe change | Preservation proof |
| --- | --- | --- | --- |
| Native dictionary analysis (`compression.py`) | Python loop repeatedly called `bytes.find` and advanced by the match length | `bytes.count` handles the same non-overlapping search in native code; empty candidates explicitly rejected | Original algorithm kept in `test_native_compression_scan.py`, with overlap/binary/random cases |
| Incremental bank allocator (`incremental_build.py`) | Rebuilt mask membership and re-summed complete groups for each split point; stored all acceptable plans | Compute each resident-mask membership and byte totals once, then account only for split prefix/suffix changes; retain priority tuple and mask order | Exact legacy exhaustive allocator retained as `_reference_allocate_groups`; deterministic differential tests cover mixed capacities, ties, splits, and infeasible cases |
| Production entropy writer (`entropy_codec.py`) | Called a Python method once per individual prefix bit | Emit each fixed category prefix with one multi-bit write | Prefix-byte and cursor test covers all sixteen frozen categories in unaligned positions; existing entropy tests cover full encoding |

**Important scope:** these edits reduce computation, not the number of
dictionary entries, game bytes, source records, or disk-side operations.
They are not permissions to change the frozen compressor's search objective
or its result ordering. The official v83 translation should remain identical.

Many internal entropy and runtime helpers also used generic, mechanically
generated docstrings. This pass replaces a group of those with actionable
format, validation, and deterministic-choice descriptions. Clear explanations
are more valuable here than deleting comments or shortening modules.

## Performance evidence and how to measure it

Two microbenchmarks were executed on equivalent standalone Python algorithms
under Python 3.13.5 before this change:

- A 5.1 KB repetitive byte input with 600 matches per search, 500 operations:
  repeated `find` took about **0.0227 s**; native `count` took about
  **0.0009 s** (roughly 25x for the counting operation).
- A 16-prefix sample repeated 50 times per writer, 120 write batches:
  the old per-bit method took about **0.1585 s**; the combined-prefix
  method took about **0.0974 s** (roughly 1.6x for the writing operation).

These numbers are **local, synthetic microbenchmarks**, not measured
translation-build speedups. Their ratio depends on Python version, machine,
input entropy, and surrounding workflow. No whole-project performance
regression/speedup claim is justified from them alone.

Run the repeatable, ROM-free project benchmark locally:

```powershell
python work/tools/benchmark_hotpaths.py
```

It asserts exact old-versus-new result parity before printing best-of-five
latencies for byte searches, entropy prefix writing, and a batch of
scenario-group allocations. It deliberately does not enforce timing
thresholds in CI: virtualized runners and competing workloads make such
gates flaky. Record the Python version, CPU, input size, and before/after
commit IDs when publishing a performance claim.

For larger realistic workloads, profile the **same licensed private input**
before and after the change without sharing it or its recovered game data:

```powershell
python -m cProfile -s cumulative work/tools/quick_check.py
python work/run_tests.py unit
```

The first command profiles only a quick feedback runner and its subprocess
overhead; it is not a substitute for profiling a real incremental or release
build. Profile the actual `time-twist build` or `inspect-layout` command
separately against identical legally obtained private candidates, documenting
the exact input SHA-256 and whether warm filesystem caches were present.

## Areas requiring particular care

| Modules | Review finding | Next justified action |
| --- | --- | --- |
| `ui.py` (about 1,342 lines), `ui_fixed_tables.py` (about 892) | Dense fixed-address UI, text geometry and patch contracts. Size alone is not evidence of dead code. | Separate validated data declarations from patch logic only when the facade and all byte-guard tests remain intact; require manual menu and disk prompt playtests |
| `incremental_build.py` (about 1,162 lines) | Allocation has avoidable repeated mask computations; other paths enforce source topology and dictionary constraints. | Keep the allocator differential oracle; profile bank loading and dictionary inference before further changes |
| `release_metadata.py` (about 1,148 lines) | Source hashes, locks, path safety, manifest schemas and code provenance sit together for a reason. | Consider later internal extraction of schema validation only with frozen manifest fixtures and no changes to lock payloads |
| `production_translation_core.py` (about 960 lines) | Semantic reflow is a behavioral specification of dialogue layout. | Add realistic before/after control-layout cases prior to any speed rewrite |
| `entropy_compression.py` and `compression.py` | Candidate enumeration and dictionary optimization can be expensive, but objective ordering and tie breaks affect the binary output. | Profile candidate counting and parser suffix copying; improve only with byte-exact differential and full-corpus tests |
| `entropy_codec.py` | Small frozen prefix grammar and bit alignment are part of the NOV2 runtime ABI. | Optimize overhead only while locking exact per-category bytes and stream round trips |
| `release_patcher/` | Official Windows EXE and ZIP are built from source and carry pinned BPS checksums. | Rebuild and smoke-test artifacts on Windows for any patcher change; do not confuse Python source passing with the distributed EXE being updated |
| `recovery/`, `audit/`, `docs/history/` | Contains checkpoint deltas, reverse-engineering provenance, and failures/constraints no longer used at runtime. | Treat as **historical evidence**, not disposable unused code; preserve it for reproduction and future reversals |

## What *not* to delete in a generic cleanup

- The `v38`, `v41`, `v50`, and `v83` checkpoint lineage and guarded
  deltas, including recovered compilers, even when not called by the ordinary
  incremental builder.
- `work/source_records/`, canonical `work/translations/`, fixed UI source
  tables, origin/provenance manifests, the current walkthrough, and historical
  engine notes.
- Stable public import facades such as `cli.py`, `release.py`, `title.py`,
  and `ui.py` without migration and import tests.
- The `release/` executable, ZIP, or BPS files merely to reduce Git storage
  size. Their duplication is intentional public distribution. Moving downloads
  exclusively to GitHub Releases would require a separate versioned release
  decision, link migration, and artifact checks.
- The private-fixture exclusion and `check_public_tree.py` controls.

Unused imports, unreachable paths, and confusing names should be proven by
import-graph inspection plus public/private test coverage before removal.
A static search that finds no textual import is insufficient for CLI plugins,
reflection, recovered binaries, historical reproduction, or documentation
entry points.

## Cleanup acceptance criteria

1. Identify the pre-change Git commit and explain why the code is active,
   historical, or a public compatibility facade.
2. State the invariant before editing. For compressors: exact text bytes,
   dictionary indices, grammar and tie breaks. For allocators: record/group
   placement, pointer bounds and deterministic plan priority. For releases:
   unchanged source lock, manifest identity and output SHA-256.
3. Keep an independent old-behavior reference in a test for optimized hot paths,
   rather than "optimizing" the oracle at the same time.
4. Run ROM-free checks locally and in pull-request CI:
   ```powershell
   python work/tools/quick_check.py
   python work/run_tests.py unit
   python -m black --check work
   python -m ruff check work
   python -m pydocstyle --convention=pep257 work
   python -m mypy
   ```
5. Run private integration tests when the legally obtained overlay is
   available. If a change affects engine behavior or binary output, rebuild
   the candidate and follow `PLAYTESTING.md` and `PLAYTEST_MATRIX.md`
   in an emulator. Do not call missing private validation a pass.
6. Verify release-critical workflows, wheel imports, source provenance and
   published binary hashes before merging or publishing.
7. Update this maintained guide for newly discovered risks. Add a **dated**
   record to `docs/history/` for decisions or superseded algorithms;
   Git preserves complete old sources and diffs.

## Next audit passes, in recommended order

1. **Compressor profiling:** create a representative, redistributable
   synthetic corpus and a maintainer-only real corpus timing harness;
   analyze repeated dynamic-programming suffix tuple construction without
   changing dictionary-result ranking.
2. **Module-boundary cleanup:** separate read-only diagnostics from mutation
   paths within `incremental_build.py` and `ui.py` behind stable public
   facades, with snapshot tests for all public entry points.
3. **Source/manifest validation:** test malformed and adversarial
   source-lock/manifest inputs before isolating release schema validators.
4. **Documentation drift audit:** verify links, current paths, CLI examples,
   and lifecycle/version language; keep `docs/history/` dated and immutable.
5. **Release artifact storage decision:** independently assess whether
   distributing large binaries both in Git and GitHub Releases remains useful.
   Do not remove a working download link as part of a code-efficiency PR.

The expected outcome is a maintainable repository with less unnecessary
computation and clearer code ownership, **not** a smaller but less
reproducible ROM translation.
