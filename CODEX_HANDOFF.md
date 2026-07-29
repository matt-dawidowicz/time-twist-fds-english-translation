# Codex handoff: Time Twist FDS English translation

This archive is the cleaned, hardened public source tree for the *Time Twist*
Famicom Disk System English translation project. It is intended to be opened as
a repository root in Codex.

## Current state

- Both Zenpen and Kouhen translation tooling is present.
- All 1,299 scenario records have playable English entries.
- The public fixture-free suite passes 38 tests with zero skips.
- The full maintainer suite passes 105 tests with zero skips when the separate
  private ROM-derived fixture overlay is present.
- Release inputs are source-locked and promoted outputs are target-locked.
- Public source, private test fixtures, and generated ROM releases are kept
  separate.

## Start here

Read, in order:

1. `README.md`
2. `FIXES_APPLIED.md`
3. `docs/README.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DEVELOPMENT.md`

Then run:

```bash
python work/tools/check_public_tree.py
python -m pip install -e ".[dev]"
python work/run_tests.py unit
```

Expected public result: **38 tests passed, 0 skipped**.

## Important constraints

- Do not add original or patched ROM images, extracted/rebuilt ROM banks,
  memory dumps, emulator packages/state, caches, or private fixtures to the
  public tree.
- Do not edit generated ROMs or rebuilt banks as source material.
- Playable scenario text is authoritative in `work/translations/*.json`.
- Fixed UI text and binary transformations are authoritative in
  `work/time_twist/`.
- Keep workbook patch-safe text synchronized with playable sources.
- Preserve deterministic builds unless making an intentional candidate and
  promotion through the documented release workflow.
- The private fixture overlay is intentionally not included in this handoff.

## Remaining substantive work

The code and release workflow have been hardened. The main remaining release
requirement is a complete emulator playthrough of both halves, checking obscure
branches, disk changes, save/load behavior, line wrapping, punctuation, fonts,
and interface visuals. Code changes prompted by playtest findings should add or
update regression coverage without weakening the public/private separation.
