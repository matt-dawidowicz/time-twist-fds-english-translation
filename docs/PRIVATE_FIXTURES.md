# Private integration inputs

The public repository deliberately excludes original/patched FDS images and
emulator memory captures. Private integration testing needs only the smallest
irreducible evidence set: the two approved original game images and four
historical emulator captures. Everything else is regenerated from those inputs
and the current source tree.

## Public versus private suites

| Suite | Command | Private inputs required | Purpose |
| --- | --- | --- | --- |
| Unit | `python work/run_tests.py unit` | No | Parsers, codecs, synthetic FDS behavior, source/release contracts, generated-review drift, and fixture-boundary guards |
| Integration | `python work/run_tests.py integration` | Yes | Exact original-bank behavior, runtime captures, current UI/title/font transforms, and deterministic end-to-end release rebuilds |
| All | `python work/run_tests.py all` | Yes | Unit plus integration |

Supported suites reject skips.

## Private input layout

Overlay only these private inputs at the project root:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
work/runtime_capture/zenpen_opening_chr.dmp
work/runtime_capture/zenpen_opening_cpu.dmp
work/runtime_capture/zenpen_title_chr.dmp
work/runtime_capture/zenpen_title_cpu.dmp
```

`work/integration_fixtures.json` locks the exact size and SHA-256 of those six
files. The runner validates them before test discovery.

## Derived integration workspace

For `integration` and `all`, `work/run_tests.py` regenerates
`work/extracted_zenpen/` and `work/extracted_kouhen/` directly from the validated
baselines. It also removes the obsolete `work/build/` and
`work/translated_banks/` fixture directories before discovery so historical
intermediate binaries cannot influence current tests.

The following are **not** fixture authorities and must not be added back to the
manifest:

```text
work/extracted_*/
work/translated_banks/
work/build/
build/candidate/
build/release/
outputs/*.fds
```

Current generated binaries are tested by rebuilding them from the active source
lock and release code. This keeps translation edits, menu relocation, and code
changes from being compared against stale historical outputs.

These private paths remain ignored by Git. Original game images and emulator
captures are not part of the public source release and are not covered by the
project's MIT License.

## Updating private evidence

Do not refresh a private-input hash merely because current generated output
changed. A manifest hash should change only when the project intentionally
supports a different original source revision or replaces a runtime capture with
new evidence whose provenance is understood.

For ordinary translation, UI, compression, or release-code changes:

1. leave the six private-input hashes alone;
2. run the full integration suite, which regenerates source extracts;
3. build a fresh release candidate from the active source lock;
4. inspect and playtest that candidate;
5. promote only the exact reviewed candidate.

Never weaken a hash or add `skipTest()` to accept an unexplained private-input
difference.
