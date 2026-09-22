# Canonical v38 build

The recovered v38 bundle remains the immutable historical checkpoint for the
approved v38 image. When the active maps are restored to the exact v38 text,
`time-twist release-build --candidate` must still reproduce that image.
Current source-locked maps may contain later reviewed wording/layout changes.

The four-side result is 262,000 bytes with SHA-256
`62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400`.

## Inputs and authority

- `work/translations/<BANK>.json` supplies all 1,299 active scenario records.
- `work/baseline/time_twist_v25_safe_encoding.fds` is the private four-side v25
  baseline, SHA-256
  `813cdceb190e9714f7489c1bd5500f8e2ead3b3942f789ccf68bc6f3696bfc19`.
- `recovery/v38/repro_bundle` supplies the original frozen compiler, codec,
  dictionary allocations, menu changes and engine patches. Its manifest and
  all 17 encoded payloads are covered by the release source lock. Each restored
  payload is independently checked against its original size and hash.

The recovery bundle remains unchanged. Its scenario layout snapshot is used
only as an immutable regression oracle. Before compilation, both restored
scenario text inputs are replaced with values generated from the active maps.
Any missing or added record ID aborts the build. After compilation, every
decoded output record is compared with the active maps. If those maps are
exactly the v38 text, the full ROM must match the approved v38 hash. Otherwise
the build is a later candidate whose exact identity is recorded in its manifest
and must be explicitly promoted after review.

The baseline supplies the existing font, title and unchanged engine. This is
reproduction from a patched v25 baseline, not a demonstrated build from original
Japanese disks. The historical Japanese-baseline compiler remains available for
engineering work as `time-twist-runtime build-historical`.

## Layout and future edits

The historical v38 snapshot intentionally preserves its original controls and
layout. The active maps are no longer required to preserve obsolete non-greedy
prose solely for byte-identical v38 reproduction: reviewed post-v38 reflows are
source-locked separately. Seven hash-scoped v38 exceptions remain only for
audited structural quiz/UI geometry, while explicit presentation records may
also opt out of generic greedy wrapping.

Do not modify the recovered v38 bundle itself. Later candidate changes belong in
the active maps, require runtime evidence, and receive a new promoted output
identity rather than claiming byte-identical v38 reproduction.

## Verification

Public CI protects the restored v38 checkpoint against any one-record mutation,
requires active maps to retain all 1,299 recovered record IDs, validates current
layout/control policy, and verifies the checked-in source lock. It needs no game
files.

With the private v25 baseline installed, the focused release integration suite
builds twice, compares all three images and manifests, checks deterministic
candidate hashes, unchanged non-scenario payloads and FDS structure, and checks
that strict release mode rejects an unpromoted candidate:

```sh
PYTHONPATH=work python -m unittest work.integration_tests.test_release -v
```

The full historical integration suite requires the additional private fixtures
listed in `work/integration_fixtures.json`. Passing the focused v38 suite does
not imply that the unavailable historical suite or complete playthrough passed.

The release remains unpromoted pending complete runtime review. No ROM, BIOS,
emulator or save state is committed.
