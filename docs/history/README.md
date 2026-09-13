# Historical engineering records

Files in this directory are permanent development records. Do not delete them during ordinary stale-code or stale-documentation cleanup. Superseded conclusions should be amended or annotated rather than erased.

Maintained/current documentation outside this directory should describe the current architecture only. Historical files may retain obsolete constants, failed experiments, superseded limits, and environment-specific validation notes when they explain the project's development.

When later evidence changes current status without making the original historical statement false in its original context, add a dated amendment rather than rewriting history.

Current modernization records:

- `CONSTRAINT_MODERNIZATION_20260913.md` — original constraint-audit chronology, evidence, retired assumptions, and modernization proof.
- `POST_INTEGRATION_VALIDATION_20260913.md` — later combined PR #60/#62 integration and GitHub Actions run #1264 validation, including Black, Ruff, pydocstyle, mypy, unit, build, wheel-smoke, and CLI gates.
