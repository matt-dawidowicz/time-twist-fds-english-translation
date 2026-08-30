# Developer tools

Developer-facing commands are separated from the installable `time_twist`
runtime package and grouped by responsibility:

- `analysis/` — reverse-engineering and static inspection.
- `audit/` — source-grounded translation and build-candidate audits.
- `generation/` — deterministic bilingual-comparison and workbook generators.
- `maintenance/` — repository/publication integrity checks and test orchestration.
- `preview/` — font, CHR, and title-development renderers.

`tools/paths.py` is the shared repository-path abstraction for developer tooling.
Do not add new `Path(__file__).resolve().parents[n]` assumptions when a canonical
repository path is available there.

Prefer module execution from the repository root after installing development
dependencies:

```bash
python -m tools.generation.generate_translation_workbook
python -m tools.maintenance.check_public_tree
python -m tools.maintenance.run_tests unit
```

Production binary behavior belongs in `src/time_twist/`. A tool that grows
reusable binary behavior should move that behavior into the package and remain a
thin orchestration, analysis, or reporting layer.
