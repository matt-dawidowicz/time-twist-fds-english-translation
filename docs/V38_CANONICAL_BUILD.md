# Canonical build: v39 gate continuation

`time-twist release-build --candidate` now builds the v39 gate-continuation fix
using the frozen v38 compiler. Before the v38 integration, the recovery bundle
reproduced v38, but the normal builder and
active maps still followed older inputs: 429 records differed in visible wording.

The four-side result is 262,000 bytes with SHA-256
`bb42d56dc80f8d7adbc2e2cf908693307946bee29ae7f13f6d5f9d538ca56546`.

## v39 correction and evidence

`TT1B/g1/r30` lost its Japanese source's leading `{CTRL:0}` during translation.
The renderer resets its cursor when entering this record but retains the text
box, so the gate description overwrote `TT1B/g1/r29` ("Run-down, but stylish.").
v39 restores that one control. The combined display occupies three rows:

```text
Run-down, but stylish.
There's a nameplate and
an intercom on the gate.
```

The paired-record native 6502 check retains the staging buffer between records.
v38 starts the continuation at byte 0 and changes 22 first-row bytes. v39 starts
at byte 48, leaves the first row unchanged, and writes the next two rows. This
executes the actual NOV2 renderer; the harness resumes waits without PPU or
controller emulation. It is not a full emulator playthrough of the scene.

Older save states can contain the old loaded bank. Replacing the ROM and loading
such a state does not establish that the new text is running. Validate after
loading the corrected bank from disk, or start the new build from reset.

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
only as an immutable regression oracle. `v39_checkpoint_records` derives the
new oracle by prepending `{CTRL:0}` to that one archived record; all other
1,298 records remain identical. Before compilation, both restored
scenario text inputs are replaced with values generated from the active maps.
Any deviation from the v39 oracle aborts the build. After compilation, every
decoded output record is compared with those same maps, and the full ROM must
match the approved hash. Neither an old translation layer nor a source-lock
refresh can silently select different English.

The baseline supplies the existing font, title and unchanged engine. This is
reproduction from a patched v25 baseline, not a demonstrated build from original
Japanese disks. The historical Japanese-baseline compiler remains available for
engineering work as `time-twist-runtime build-historical`.

## Layout and future edits

Apart from the explicit gate fix, reproduction preserves v38 controls, including compact
France/Nazareth identity cards. Twelve non-greedy wraps and seven 24-column quiz
records have exact-text hash exceptions to later formatting policy. Changed
text loses the exception. All records still pass the four-row buffer validator.
These exceptions preserve a checkpoint; they do not certify in-game appearance.

A future change must explicitly revise the compiler/checkpoint contract,
review changed text and menus, and establish a new output hash with runtime
evidence. Do not reflow v38 while claiming byte-identical reproduction.

## Verification

Public CI compares every active record with the revised checkpoint and tests
rejection of a change to each of the 1,299 records, plus missing/extra IDs,
control-only changes and an invalid baseline. It also rejects the old gate
record and verifies that only its leading control differs from v38. It needs
no game files.

With the private v25 baseline installed, the focused release integration suite
builds twice, compares all three images and manifests, checks the approved hash,
checks unchanged non-scenario payloads and FDS structure, and checks that strict
release mode rejects an unpromoted candidate:

```sh
PYTHONPATH=work python -m unittest work.integration_tests.test_release -v
```

The full historical integration suite requires the additional private fixtures
listed in `work/integration_fixtures.json`. Passing the focused release suite does
not imply that the unavailable historical suite or complete playthrough passed.

The release remains unpromoted pending complete runtime review. No ROM, BIOS,
emulator or save state is committed.
