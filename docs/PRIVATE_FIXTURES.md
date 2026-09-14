# Private integration fixtures

The public repository deliberately excludes original FDS images, extracted ROM
banks, emulator memory dumps, emulator packages, and third-party binary patches.
Some integration tests still need those source materials to prove exact behavior
against the recovered game revision. Derived English banks and candidate images
are rebuilt during the tests instead of serving as fixtures.

## Public versus private suites

| Suite | Command | Distributed publicly | Purpose |
| --- | --- | --- | --- |
| Unit | `python work/run_tests.py unit` | Yes | Parsers, codecs, workbook rules, synthetic FDS behavior, and release-control logic |
| Integration | `python work/run_tests.py integration` | No fixtures | Exact ROM-bank transforms, full release hashes, title/UI/font scope, and FDS replacement behavior |
| All | `python work/run_tests.py all` | No fixtures | Unit plus integration |

The test runner rejects skips. Before discovering integration tests it checks
all required local files against `work/integration_fixtures.json`. A missing,
modified, or wrong-revision fixture stops the run with a setup error.

## Overlay layout

A maintainer's private fixture archive is extracted at the project root, so
paths such as these become available locally:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
work/extracted_zenpen/<required source banks>.bin
work/extracted_kouhen/<required source banks>.bin
work/runtime_capture/zenpen_title_cpu.dmp
work/private/TimeTwist-Zenpen-newlogo.ips
```

The definitive title IPS is a maintainer-supplied third-party input and is not
redistributed by the repository or Python package. The title builder accepts the
private checkout path above, or an explicit path supplied through the
`TIME_TWIST_DEFINITIVE_TITLE_IPS` environment variable. Before applying it, the
builder requires SHA-256
`915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2`.
Base64 encoding or any other textual embedding of the complete IPS is not used
as a distribution workaround.

These paths remain ignored by Git. The private fixture archive is not part of
the public source release and is not covered by the project's MIT License.

## Creating or updating local fixtures

Only update the fixture manifest when a supported source revision or the
source-locked runtime capture changes. Regenerate the files from legally
obtained sources, inspect the binary difference, run the complete integration
suite, and record the reason for every changed hash. Do not add derived English
banks or release outputs to the private fixture contract; current tests must
produce them through the canonical release builder.

For the definitive title IPS, do not substitute a similar patch or a rebuilt
PNG. The exact reviewed IPS hash above is the authority. If the patch is stored
outside the checkout, point `TIME_TWIST_DEFINITIVE_TITLE_IPS` at that exact file.

Do not weaken a hash, delete a fixture check, or add `skipTest()` merely to
accept an unexplained local difference.
