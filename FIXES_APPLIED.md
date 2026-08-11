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
- Source-lock schema v2 records `lf` normalization for translation JSON and
  `raw` identity for ROM/title assets. Equivalent Windows CRLF and repository
  LF text now share one digest without weakening binary guards.
- The source-lock document hash is LF-normalized, making candidate/target
  linkage platform-independent.
- A promoted `work/release_target.json` records reviewed output sizes and
  hashes tied to the active source-lock SHA-256.
- Candidate provenance hashes both the imported/executing package and the
  supplied checkout under identical logical paths and fails closed if they
  differ.
- Release manifest schema v4 requires the complete audit record: source-lock and
  code provenance, build environment, all scenario-bank reports, fixed-component
  hashes, target state, and canonical output records.
- Candidate manifests record Python implementation/version and Pillow version
  as informational diagnostics. Source, code, and output hashes remain the
  release authority.
- `release-promote` validates every candidate output twice: once during review
  validation and again immediately before the atomic target write, closing the
  candidate-output time-of-check/time-of-use window.
- Source locks, manifests, targets, and provenance fields receive strict
  structural validation; JSON booleans cannot masquerade as sizes or counts.
- `release-build --candidate` creates reviewable unapproved output.
- Strict `release-build` stages all files and publishes only after source-lock
  and target validation.
- The obsolete v1 target was removed. No target is checked in until the current
  candidate is reviewed, playtested, and explicitly promoted.
- Publication atomically replaces files from destination-local temporary files,
  preserving the output directory's Windows ACL inheritance so desktop
  emulators can open newly built ROMs.
- Publication invalidates an older manifest before replacing outputs, so an
  interrupted multi-file update cannot leave stale metadata attesting a mixed
  output set.
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
- CI builds and force-installs the wheel, proves `time_twist` imports outside
  the checkout, and then smoke-tests the command.
- Personal workstation paths were removed from scripts and generated metadata.

## Tests

- Public tests and ROM-derived integration tests are separated.
- `python work/run_tests.py unit` runs 78 fixture-free tests in CI.
- `python work/run_tests.py integration` runs 75 exact tests with the private
  overlay.
- The fixture manifest is validated before discovery.
- Supported suites reject all skips.
- The private overlay was recovered locally and all 92 fixture records matched
  their manifest before the 75-test integration run. The proprietary files
  remain excluded from the repository.

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

## Playtest handoff

The previously recorded image hashes remain evidence for the pre-schema-v4
candidate, but manifest schema v4 deliberately changes the release-code and
audit metadata. Build a fresh candidate with the current code, playtest those
exact files, and promote only that retained reviewed candidate.

Static and reproducible verification does not replace a complete emulator
playthrough.
