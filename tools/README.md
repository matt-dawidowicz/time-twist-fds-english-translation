# Developer tools

Developer-facing commands are separated from the installable `time_twist`
runtime package and grouped by responsibility:

- `analysis/` — reverse-engineering and static inspection.
- `audit/` — source-grounded translation and build-candidate audits.
- `generation/` — deterministic bilingual-comparison and workbook generators.
- `maintenance/` — repository/publication integrity checks.
- `preview/` — font, CHR, and title-development renderers.

Prefer module execution from the repository root after installing development
dependencies:

```bash
PYTHONPATH=work python -m tools.generation.generate_translation_workbook
PYTHONPATH=work python -m tools.maintenance.check_public_tree
```

Production binary behavior belongs in `work/time_twist/`. A tool that grows
reusable binary behavior should move that behavior into the package and remain a
thin orchestration or reporting layer.
