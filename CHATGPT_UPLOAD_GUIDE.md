# Time Twist FDS English Translation — Complete ChatGPT Review Bundle

This is the complete working bundle requested for diagnosis and repair. It contains the current hardened source/tooling tree, the private ROM-derived fixture overlay required to rebuild it, and a freshly reproducible FDS playtest set.

## Start here

1. Read `README.md`, `CODEX_HANDOFF.md`, `FIXES_APPLIED.md`, and `docs/PRIVATE_FIXTURES.md`.
2. Treat `work/translations/*.json` as the editable English source and `work/time_twist/` as the rebuild engine.
3. Treat all `.fds` files as outputs or fixtures, not hand-edit targets.
4. Preserve record IDs and ordering, inline controls, fixed record addresses, source guards, and every bank's footprint. Do not use raw byte surgery on compressed banks.

`CHATGPT_REVIEW_GUIDE.md` explains the review workflow in more detail. `docs/ARCHITECTURE.md`, `docs/FORMATS.md`, and `docs/TRANSLATION_WORKFLOW.md` describe the relevant formats and constraints.

## Included private fixture overlay

- Original Japanese disks: `work/baseline/`
- Extracted stock resources: `work/extracted_zenpen/` and `work/extracted_kouhen/`
- Current fixed-footprint translated banks: `work/translated_banks/`
- Build intermediates: `work/build/`
- Runtime capture fixtures: `work/mesen_capture/`
- Integration source locks and tests: `work/integration_fixtures.json` and `work/integration_tests/`

## Latest reproducible playtest candidates

`latest-playtest/` contains the current four-side build plus standalone Zenpen and Kouhen images and its `release_manifest.json`.

Expected SHA-256 values:

- `Time Twist - reproducible English four-side playtest.fds`: `21A48E6F0B955E7E970E3AAF86F147B366BB5AC02AFCEB681169ADD17E7C657F`
- `Time Twist Zenpen - reproducible English playtest.fds`: `60F646296635B13391A8666BA99F8B025D4A75865BD25DFD830F540BBE51F3FE`
- `Time Twist Kouhen - reproducible English playtest.fds`: `18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421`

## Verification

From the bundle root, run:

```powershell
python work/run_tests.py all
python -m time_twist.cli release-lock
```

The automated checks cover structural and source-lock invariants. Release readiness still requires emulator playthrough coverage of Zenpen and Kouhen, disk swaps, saves/reloads, progression, text wrapping/clearing, and title/UI visuals.
