# Public Windows patcher: architecture and verification

This document explains the source of trust in the public Time Twist v1.1
patcher, its BPS implementation, the deliberately narrow No-Intro compatibility
exception, how to test it, and how to maintain the published Windows package.

## Scope and entry points

- `release_patcher/TimeTwistPatcher.py` contains the independent Tk GUI, CLI,
  SHA-256-based image verification, BPS interpreter, output validation, and safe
  file-writing logic. The release builds it into a self-contained EXE.
- `release_patcher/patches/` stores the compressed/base64-encoded BPS patch
  resources. These are byte deltas, **not** retail or translated ROM images.
- `release_patcher/patch_manifest.json` records the identity of each published
  patch, its source, its target, and the release's canonical outputs.
- `release_patcher/test_public_patcher.py` is the fixture-free public test
  entry point; it validates patch resources, BPS semantics, output safety, and
  the canonical/alternate source routes using synthetic data.
- `release_patcher/build_windows.ps1`, `package_release.py`, and
  `.github/workflows/publish-v1.1.yml` build and publish the Windows package.
- `docs/MAINTAINER_RELEASE_PROCESS.md` describes the separate, private
  candidate-building and emulator playtesting process.

## Accepted retail sources

Each Japanese part must be a **raw, headerless, 131,000-byte** FDS image.
The two inputs may be supplied in either order. The patcher first reads the
whole file, rejects invalid sizes, and identifies its part.

| Part / variant | Required whole-file identity |
| --- | --- |
| Zenpen | SHA-256 `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Release-locked Kouhen | SHA-256 `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |
| No-Intro Kouhen | **All** of MD5 `134F65BD93A5E5C0ABAB3E560FF146A8`, SHA-1 `E0747E6BA6111FAD733C832E6CA7C0172F4C056E`, and CRC-32 `A7D51BFA` |

The No-Intro exception is exact and specific to Kouhen. It is not a generic
"ignore checksum errors" switch. An unknown or edited image must remain
rejected. No-Intro support should use a pinned whole-file SHA-256 as well
once an independently verified copy of that variant is available; do not
invent the missing fingerprint.

The supplied maintainer-retail inputs checked for this fix were the two
**canonical**, release-locked SHA-256 images above. They do not constitute a
runtime test of the different No-Intro variant.

## Patch and verification flow

1. `_identify` checks length and **whole-file** identity, classifies each
   part, and rejects two of the same part.
2. `_patch_bytes` reconstructs the embedded BPS resource and compares its
   SHA-256 to the pinned digest.
3. `apply_bps` verifies the patch CRC, decodes BPS variable-length fields and
   actions, bounds-checks reads/copies, and verifies source and target CRCs.
   The BPS modes are SourceRead, TargetRead, SourceCopy, and TargetCopy.
4. The canonical Zenpen result must match its pinned target SHA-256.
5. Canonical Kouhen must match its pinned target SHA-256. Exact No-Intro
   Kouhen may instead satisfy the pinned No-Intro source fingerprint plus
   its *specific* alternate BPS source and target CRC allowances
   (`A7D51BFA` and `308FCE52`). These allowances do **not** apply to other
   inputs. Differences in source-copied retail metadata/padding explain why
   the alternate target is not necessarily byte-for-byte identical to the
   release-locked canonical target.
6. If requested, the four-side image is Zenpen followed by Kouhen. The
   canonical pairing is verified against the canonical combined SHA-256.
   The No-Intro pairing is validated by the exact alternate-source identity,
   verified BPS CRC result, validated Zenpen hash, and the expected combined
   length. **Do not** compare the alternate pairing to the canonical combined
   hash: they are distinct byte sequences.
7. `build_outputs` rejects accidental input/output path aliasing and existing
   files unless overwrite is explicitly requested. Only after all in-memory
   validation succeeds does it write outputs using temporary files and
   `os.replace` per destination.

The patcher does not rewrite original inputs. It supports two translated
131,000-byte parts, one 262,000-byte four-side image, or both. Successful
creation is not a substitute for emulator testing.

## Running the public tests

From the repository root:

```powershell
python release_patcher/test_public_patcher.py
python work/tools/check_public_tree.py
python work/run_tests.py unit
```

The public patcher tests contain no Nintendo data. Their in-memory fixtures
replace source fingerprints, patch resources, and expected hashes with
synthetic 512-byte image pairs; they exercise the real input-selection and
output-generation functions. Both a canonical and an alternate Kouhen route
are checked, as are reversed input order and rejection of an unknown dump.
Separate synthetic BPS fixtures exercise corrupted patch rejection and
approved alternate CRC verification.

**Limitations:** synthetic fixtures test code paths, not a real No-Intro dump's
playability or whether its recorded BPS target CRC is correct. Confirm that
separately using a legally obtained, independently identified No-Intro image
before claiming full retail compatibility. Never upload retail FDS images to
GitHub, attach them to CI, or commit generated translated ROM files.

## Local maintainer smoke test with retail inputs

For the canonical Zenpen and Kouhen images, select both files in the patcher
(or run `python release_patcher/TimeTwistPatcher.py ZENPEN.fds KOUHEN.fds
-o output`). Confirm that both translated parts match the SHA-256 values in
`release_patcher/README.md` and that the combined file matches SHA-256
`4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A`.

For the *actual* No-Intro Kouhen variant, first verify all its published
fingerprints; select it with the canonical Zenpen source and request **both**
output layouts. Confirm the alternate translated Kouhen CRC-32 is
`308FCE52` and that the combined output is the verified Zenpen bytes
followed by the verified alternate Kouhen bytes. Check it in an emulator,
including the Part 1-to-Part 2 handoff and persistent disk state. Record
input/output hashes and emulator observations privately.

A generic BPS patch utility may reject the No-Intro dump because the
published `.bps` source CRC refers to the release-locked canonical image.
The special exception belongs only to our fingerprint-gated public patcher.

## Maintaining compatibility and packaging

When changing input support, review every gate in order: `_identify`,
`_known_source_variant`, `apply_bps` CRC allowances,
`_prepare_outputs` target verification, and `build_outputs` output
safety. Keep the SHA-256 canonical checks; an alternate source must not
silently change the canonical baseline.

When changing BPS resources, synchronize the patch manifest, embedded
resource hashes, frozen EXE, package checksums, release notes, and unit
tests. Run `./release_patcher/build_windows.ps1` on Windows; smoke-test
`--version`, `--verify-resources`, the GUI, and real retail inputs before
publishing. A source change alone does **not** update the executable already
shipped under `release/` or the GitHub release download.

Do not merge a patcher source fix and claim users already have it: first let
the release-publishing workflow rebuild and upload binaries, check the final
GitHub Actions result, and verify the published artifacts against their
recorded fingerprints.
