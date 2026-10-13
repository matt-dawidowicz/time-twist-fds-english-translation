# Repository modernization and historical preservation audit

Status: initial inventory and risk assessment. This is a plan, **not** a
claim that every code path has been profiled or tested.

## Baseline inventory

The main branch currently contains 359 tracked blobs: 141 Python files, 70
Markdown files, 45 JSON files, plus release artifacts and archived recovery
material. The largest files include a roughly 11 MB Windows executable and
11 MB Windows ZIP under `release/`, source-record JSON banks, and title art.
The repository already has a code tour, module map, historical documentation,
strict source-byte guards, public tests, private integration tests, and
canonical release hashes. These are preservation assets, not cleanup targets.

## Rules before any optimization

1. Keep accepted translation text, game behavior, binary layout, input/output
   hashes, and public CLI/import interfaces stable unless a change is
   separately approved as intentional.
2. Do not commit retail or translated FDS images, extracted copyrighted
   payloads, private emulator state, or private integration fixtures.
3. Preserve old investigations in `docs/history/` or Git history, and keep
   durable *explanations* of rejected approaches, byte layouts, and source
   evidence. Historical facts must not be silently rewritten.
4. Every code move requires tests before and after; every binary-affecting
   change requires the private candidate and emulator gates described in
   `docs/MAINTAINER_RELEASE_PROCESS.md`.
5. Optimize only measured bottlenecks. Record baseline and revised timings,
   input size, Python version, memory peak, and output digest.

## Audit areas and prioritized work

| Priority | Area | Work | Required evidence |
| --- | --- | --- | --- |
| P0 | Reproducibility | Inventory release and patcher SHA-256 identities, source locks, and CI protections | Existing release and candidate digests unchanged |
| P0 | Source provenance | Map all active modules and public facades to tests and documents | No undocumented ownership changes |
| P0 | Test safety | Ensure public patcher tests and public-tree guard run in CI; inspect gaps around alternate ROMs and four-side output | Passing CI and synthetic edge cases |
| P1 | Dead code | Search call sites for unused functions, legacy command entry points, and retired codecs; distinguish historical research from production imports | Static call-site inventory plus tests |
| P1 | Duplication | Compare hash helpers, BPS/CRC routines, FDS side validation, scenario decoding, and release-manifest handling | Before/after behavioral equivalence |
| P1 | Performance | Profile packed-text encoding, bank validation, FDS parsing, release hashing, and candidate generation | Repeatable benchmark, no hash changes |
| P1 | CLI / modules | Simplify large modules such as `ui.py` only behind stable facades | Import and CLI compatibility tests |
| P2 | Release packaging | Review duplication between committed EXE/ZIP, published releases, and build scripts | Verified reproducible release downloads |
| P2 | Documentation | Clarify current vs retired implementations; link decisions to current code and tests | Updated index and decision records |
| P2 | Dependencies | Audit Python 3.11/3.14, pin policy, lint/test consistency, and workflow action versions | Green matrix CI |

## Proposed sequence of focused pull requests

1. **Inventory and benchmarks:** add deterministic benchmark scripts using
   synthetic fixtures; establish module/dependency maps, duplicate candidates,
   and baseline hashes. No behavior changes.
2. **Pure-code cleanup:** consolidate duplicated helpers and simplify error
   paths, retaining existing APIs and verifying fixture-free unit tests.
3. **Measured hot paths:** optimize one profiled subsystem at a time with
   regression tests, timing tables, and unchanged output hashes.
4. **Packaging and CI:** eliminate *proven* redundant packaging work while
   retaining downloadable artifacts and rollback provenance.
5. **Documentation consolidation:** update code tour, module map, contributor
   guides, and architectural decision records. Preserve historical narratives
   with explicit 'retired' labels and links.

## Refactor review checklist

- What behavior is unchanged? What exact test establishes that?
- Does the change touch packed bitstreams, FDS metadata, CRC, file order,
  source guards, compression, or 6502 timing?
- Were canonical hashes compared before and after?
- Is there a measured runtime or maintenance benefit?
- Are public imports, CLI flags, file names, and patcher UX unchanged?
- Does documentation explain *why*, not just restate the code?
- Was any historic rationale removed without a permanent replacement?
- Was private runtime validation performed where required?

## Initial concrete observations

- `docs/CODE_TOUR.md` and `docs/MODULE_MAP.md` already define facade
  boundaries; refactors must follow them rather than renaming modules broadly.
- `work/tools/quick_check.py` is intentionally a lightweight subset of CI.
  Avoid adding expensive full checks to every local edit.
- `work/run_tests.py` distinguishes public unit tests from verified private
  integration fixtures; keep that separation.
- `pyproject.toml` already configures Black, Ruff, mypy, and Python 3.11+.
  Avoid adding overlapping formatters without a demonstrated gap.
- `release/` contains large built binaries. Decide whether to remove them
  only after proving that release distribution and reproducibility will not
  regress; their mere size is not evidence of redundancy.

Next step: collect a complete source/dependency graph and actual benchmark
results before selecting any performance or dead-code deletions.
