# Fixes applied

This revision closes the code-audit findings across binary validation,
reproducibility, public packaging, tests, and editorial/build authority.

Implementation details, recovered addresses, source/replacement byte tables,
6502 helper behavior, and the title-screen construction process are documented
in [`docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md`](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md).

## Binary correctness

- Scenario pointers must be strictly increasing; duplicate group pointers are
  rejected.
- Dictionary reference zero is rejected.
- Font patching verifies a supported NOV4 source revision, not merely length.
- Production patch paths use explicit domain exceptions instead of removable
  `assert` statements.
- Scenario bank-name inference is validated and has an explicit override.
- Fixed-UI dictionary contracts are explicit and release-checked.

## Deterministic performance

- Compressor scoring avoids repeatedly repacking every group and caches byte
  searches while preserving exact output.
- A complete two-part release rebuild completes in roughly 19 seconds in the
  review environment rather than taking several minutes per subset of banks.

## Release workflow

- `work/release_sources.json` locks both baselines, the title asset, and all 13
  playable scenario maps.
- `work/release_target.json` records promoted output sizes and hashes tied to
  the active source-lock SHA-256.
- `release-build --candidate` creates reviewable unapproved output.
- `release-promote` verifies every candidate file and atomically updates the
  target.
- Strict `release-build` stages all files and publishes only after source-lock
  and target validation.
- Publication now atomically replaces files from destination-local temporary
  files, preserving the output directory's Windows ACL inheritance so desktop
  emulators can open newly built ROMs.
- External `--lock` paths are handled safely in manifests.
- Intentional source updates no longer dead-end on hashes hardcoded in Python.
- Known CLI failures produce concise `time-twist: error:` messages.
- Commands work from any directory in a checkout or through `--project-root`.

## Public source and installed package

- Proprietary/local artifacts are excluded from the public archive: FDS images,
  extracted/rebuilt banks, memory dumps, emulator archives/settings, caches,
  and build products.
- Public source and the private ROM-derived fixture overlay are separate.
- CI runs `work/tools/check_public_tree.py` before installation to reject ROMs,
  extracted banks, dumps, emulator state, build debris, and personal paths.
- The wheel contains code only and can drive an external checkout explicitly.
- CI builds and force-installs the wheel before smoke-testing the command.
- Personal workstation paths were removed from scripts and generated metadata.

## Tests

- Public tests and ROM-derived integration tests are separated.
- `python work/run_tests.py unit` runs 39 fixture-free tests in CI.
- `python work/run_tests.py integration` runs 73 exact tests with the private
  overlay.
- The fixture manifest is validated before discovery.
- Supported suites reject all skips.
- The current candidate run discovers 112 tests with zero skips: 111 pass and
  the sole expected release-target gate rejects the intentionally unpromoted
  title candidate.
- Four obsolete intermediate-build tests were removed rather than retained as
  permanent skips.

## Title-sequence candidate

- The final title uses a reviewed 256-by-240 indexed native asset derived from
  the approved target geometry; production never resizes or requantizes it.
- The upper title fits exactly in 236 patterns, the lower title remains exactly
  55 patterns, and the clock-source tail `$EC-$FF` remains byte-identical.
- Both swipe nametables contain all 32 mechanically derived logo columns.
- Nintendo's temporary `$B0-$D5` patterns are restored before the swipe, so no
  stale opening-logo patterns can leak into the English title.
- The original 21 nine-bit scroll origins and attribute-mask reveal are
  preserved. The first reconstructed frame is blank and the last contains all
  9,348 approved nontransparent logo pixels.
- NOV4 offset `$0995` is source-guarded and changed from `$0F` to `$30`, making
  the settled monochrome outline match the final colored geometry.
- The preserved hand sprites are moved 16 pixels left and 8 pixels up to remain
  centered in the corrected clock face; their source graphics and animation
  tables are unchanged.
- Patched NOV4 is 12,209 bytes, ends at CPU `$D1B1`, and retains 1,540 bytes of
  space before resident NOV3 at `$D7B5`.

## Workbook/build authority

- Every scenario patch-safe workbook row now comes directly from the playable
  translation map.
- Fixed/graphics patch-safe rows mirror installed English definitions.
- Alternative reviewed wording remains in the natural-translation field.
- The one intentional `NOV2/wait` control-layout exception is named and tested.
- Workbook generation no longer depends on personal absolute paths.

## Verified promoted outputs

| Image | SHA-256 |
| --- | --- |
| Zenpen | `60F646296635B13391A8666BA99F8B025D4A75865BD25DFD830F540BBE51F3FE` |
| Kouhen | `18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421` |
| Four-side | `21A48E6F0B955E7E970E3AAF86F147B366BB5AC02AFCEB681169ADD17E7C657F` |

Static and reproducible verification does not replace a complete emulator
playthrough.

## Unpromoted title test candidate

Two independent source builds produced byte-identical manifests and images.
The Zenpen candidate was also cold-booted twice through the complete title
sequence in Mesen with byte-identical frame evidence.

| Image | SHA-256 |
| --- | --- |
| Zenpen | `10C893513CC97C3D8657DDF3BF1DC333DC9B0960D0061A227B5D89621F35769B` |
| Kouhen | `EA56360D36730FDE372F7FC118B81D3C7C2937FD54D30288B7F56D6BCA7DD718` |
| Four-side | `908A73606DFDC08D8A3F88BF5C389BB82D10BE866196A0677F4BE1ED6EAC7856` |
