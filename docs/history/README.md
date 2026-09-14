# Historical engineering records

Files in this directory are permanent development records. Do not delete them during ordinary stale-code or stale-documentation cleanup. Superseded conclusions should be amended or annotated rather than erased.

Maintained/current documentation outside this directory should describe the current architecture only. Historical files may retain obsolete constants, failed experiments, superseded limits, and environment-specific validation notes when they explain the project's development.

When later evidence changes current status without making the original historical statement false in its original context, add a dated amendment rather than rewriting history.

Current historical records:

- `CONSTRAINT_MODERNIZATION_20260913.md` — original constraint-audit chronology, evidence, retired assumptions, and modernization proof.
- `POST_INTEGRATION_VALIDATION_20260913.md` — later combined PR #60/#62 integration and GitHub Actions run #1264 validation, including Black, Ruff, pydocstyle, mypy, unit, build, wheel-smoke, and CLI gates.
- `RUNTIME_BISECT_20260829.md` — preserved runtime-bisect/debugging-branch record covering the discarded Adaptive255 path, entropy-only migration, and the NOV4/TT1A codec-ownership failures.
- `GAMEPLAY_VM_COMPLETION_20260912.md` — preserved second-pass gameplay-VM reachability and semantic audit. Its verified conclusions have been folded into the maintained `../GAMEPLAY_SCRIPT_ENGINE.md`; this copy remains the dated evidence record.
