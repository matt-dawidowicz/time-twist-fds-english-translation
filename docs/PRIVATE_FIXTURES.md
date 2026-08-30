# Private integration fixtures

The public repository deliberately excludes original/patched FDS images,
extracted or rebuilt ROM banks, emulator memory dumps, and emulator packages.
Some integration tests still need those materials to prove exact behavior
against the recovered game revision.

## Public versus private suites

| Suite | Command | Distributed publicly | Purpose |
| --- | --- | --- | --- |
| Unit | `python -m tools.maintenance.run_tests unit` | Yes | Parsers, codecs, workbook rules, synthetic FDS behavior, and release-control logic |
| Integration | `python -m tools.maintenance.run_tests integration` | No fixtures | Exact ROM-bank transforms, full release hashes, title/UI/font scope, and FDS replacement behavior |
| All | `python -m tools.maintenance.run_tests all` | No fixtures | Unit plus integration |

The test runner rejects skips. Before discovering integration tests it checks
all required local files against `tests/fixtures/integration_fixtures.json`. A missing,
modified, or wrong-revision fixture stops the run with a setup error.

## Overlay layout

A maintainer's private fixture archive is extracted at the project root, so
paths such as these become available locally:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
work/extracted_zenpen/*.bin
work/extracted_kouhen/*.bin
work/translated_banks/*.bin
work/build/*.bin
work/runtime_capture/*.dmp
outputs/*.fds
```

These paths remain ignored by Git. The private fixture archive is not part of
the public source release and is not covered by the project's MIT License.

## Creating or updating local fixtures

Only update the fixture manifest when a supported source revision or an
intentional exact-output fixture changes. Regenerate the files from legally
obtained sources, inspect the binary difference, run the complete integration
suite, and record the reason for every changed hash.

Do not weaken a hash, delete a fixture check, or add `skipTest()` merely to
accept an unexplained local difference.
