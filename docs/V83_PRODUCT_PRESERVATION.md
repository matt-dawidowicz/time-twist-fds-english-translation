# v83 preservation and release provenance (22 October 2026)

## Scope and invariant

The currently working v83 English game is a **frozen product**. Maintenance
must not rebuild, repatch, replace, or retag its distribution without a
separate, intentional release decision. The canonical combined four-side
output SHA-256 is
`4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A`.
The translated halves and all four BPS patch hashes are pinned in
`release_patcher/patch_manifest.json`.

The fixture-free test
`work/tests/test_release_artifact_immutability.py` records the **current
Git-tracked** Windows EXE, ZIP, and four BPS files by their Git blob ID and
byte count. It fails if those exact files change or the directory gains/loses
files. These are identities of the *repository copies*; they do **not** claim
the same bytes are served from GitHub Releases.

## Distinct release surfaces (do not conflate them)

- The `v1.1.0` Git tag resolves to commit
  `1005e8ca4ab66a3bf18d79fab65c27de828db44a` (6 October).
- The GitHub Release's assets were refreshed on 13 October through
  successful publishing workflow
  `38352451846` (source commit
  `27b67b82e08f90046ad4cf9df595f0800de3cd6f`).
- The GitHub Release Windows ZIP reported 11,015,123 bytes on 22 October,
  while `main:release/Time-Twist-English-v1.1-Windows.zip` had 11,012,383.
  The old-tag checkout, current release assets, and checked-in binaries
  cannot be assumed identical.
- Branch `automation/refresh-v1.1-release-38352451846` carries EXE/ZIP
  changes only but was 77 commits behind `main` on inspection. **Do not
  merge it blindly** or overwrite current distribution artifacts merely to
  silence a drift warning.

These differences are a release-provenance/distribution maintenance concern,
not evidence that the translated game is broken. This documentation change
**does not** change either distribution surface.

## Safe next steps, without changing the final game

1. Preserve exact public-tree and GitHub Release artifact digests in a signed
   or independently archived release manifest; do not replace existing bytes.
2. Confirm which EXE and ZIP should be advertised, including a real Windows
   smoke test with clean supported Japanese source images and their expected
   translated output digests. Treat the No-Intro variant separately.
3. If a distinct binary distribution is needed, publish under a **new tag**
   after a separate, explicit review. Never move the old `v1.1.0` tag.
4. For maintenance-only pull requests, require the public unit suite and this
   frozen-artifact check to pass. Private ROM integration and emulator
   recertification remain distinct and cannot be inferred from fixture-free CI.
5. Treat `docs/PLAYTEST_MATRIX.md` as an evidence ledger: `Pending` means
   *not recorded there*, not *known defective*. Leave the proven v83 ROM
   untouched while documenting any additional historical runtime evidence.

**Out of scope:** translation edits, compression, FDS patches, 6502 changes,
engine optimizations, executable rebuilds, ZIP regeneration, and tag moves.
