# Maintainer release process

This page is for maintainers who have the legally obtained private inputs
needed to build and evaluate a candidate. Regular contributors and playtesters
do not need those inputs; start with the [Quickstart](../QUICKSTART.md) or
[playtesting guide](../PLAYTESTING.md) instead.

## The boundary

The public repository contains source, tests, documentation, translation maps,
and title artwork. It must never contain original or patched FDS images, FDS
BIOS files, extracted retail banks, emulator settings, save states,
screenshots, or generated candidate bundles.

Private inputs belong only in ignored local paths. A candidate is evidence for
testing, not a file to commit.

## Private fixtures and integration tests

The fixture-free public suite is the required baseline for every change:

```powershell
python work/tools/check_public_tree.py
python work/run_tests.py unit
```

Maintainers who have the private fixture overlay must then run:

```powershell
python work/run_tests.py integration
python work/run_tests.py all
```

The integration runner verifies the overlay against
`work/integration_fixtures.json` before it runs tests. A missing overlay is an
expected setup limitation; do not add test skips or substitute public fixtures.
See [private integration fixtures](PRIVATE_FIXTURES.md) for its local layout.

## Build an unpromoted candidate

Place legal Japanese inputs only at the ignored local paths:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

First validate the approved inputs. If this fails, stop and investigate; do
not rewrite the lock merely to make the command pass.

```powershell
time-twist release-lock
time-twist release-build --candidate --output-dir build/candidate
```

Keep the generated `release_manifest.json` with the candidate during review.
It binds the code tree, source lock, component hashes, build environment, and
Zenpen/Kouhen/four-side output hashes to one candidate.

For a candidate using the full-word menu path, generate and retain its decoded
label audit as well:

```powershell
python work/tools/audit_fixed_menu_labels.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --output-csv build/candidate/fixed_menu_label_audit.csv
```

Promotion review requires `full-word=721`, `blocked=0`, and `failures=0` for
the current menu inventory.

## Establish clean emulator state before runtime review

A clean boot is not sufficient if the emulator still has persistent disk state
for an older build. Mesen can keep FDS writes in a filename-matched `.ips`
sidecar under its `Saves` directory. Rebuilding a candidate under the same
filename can therefore cause stale disk writes to be overlaid on new candidate
bytes and produce a false runtime regression.

Before the **first boot of each newly built candidate** in Mesen, close Mesen
and run the read-only preflight against the actual candidate and Mesen save
directory. Replace `<MESEN-SAVES-DIRECTORY>` with the actual Mesen `Saves`
directory on the test machine:

```powershell
python work/tools/check_mesen_fds_state.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --mesen-save-dir "<MESEN-SAVES-DIRECTORY>"
```

If the check fails, quarantine the reported `.ips` by moving or renaming it.
Do not delete it blindly; it can be useful evidence when diagnosing a false
regression. Re-run the preflight until it passes, then begin the cold-boot
runtime review.

This preflight is intentionally local and read-only. It must not be added to
CI, because CI neither has nor should have access to a maintainer's emulator
state.

Once the newly built candidate has started from clean state, do **not** clear
new persistence created by that same candidate during its save/load tests.
That state is part of the behavior being certified.

## Review and playtest

Run the candidate from a clean boot and clean pre-existing emulator disk state,
and record the candidate hash, emulator version, FDS BIOS hash, disk/side,
inputs, and observations. The minimum runtime gates are:

- title sequence and `Start`/`B` behavior;
- normal disk requests and one wrong-side recovery;
- Zenpen-to-Kouhen continuity without a reset;
- in-game save and normal reload;
- menus on both sides of the record-32/64/96 page boundaries and changed
  high-risk text;
- no progression, rendering, input, or audio-timing regression.

Use the [runtime playtest matrix](PLAYTEST_MATRIX.md) for complete coverage.
Automated tests and static previews do not replace this step.

If a runtime defect disappears when the exact same candidate bytes are opened
under a new filename, suspect emulator persistence before changing ROM code or
graphics. Check for the original filename's active `.ips` sidecar and preserve
it for diagnosis.

## Promote only a reviewed candidate

After the public checks, private integration checks, and manual evidence pass,
promote the exact manifest that was reviewed:

```powershell
time-twist release-promote build/candidate/release_manifest.json `
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Promotion performs a fresh rebuild and rejects a manifest whose source,
components, or output hashes do not reproduce. Commit only the intended source
and release metadata changes; explicitly inspect the staged file list before
committing. Never stage the candidate images or any private fixture.

## If anything fails

Stop before promotion. Preserve the failure output, candidate hash, exact
command, changed-file summary, and relevant emulator persistence state. For a
runtime issue, add the reproduction route and media location to the report
template in the [playtesting guide](../PLAYTESTING.md).
