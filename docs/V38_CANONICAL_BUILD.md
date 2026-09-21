# Canonical build: v40 dialogue flow

`time-twist release-build --candidate` builds v40 using the frozen v38 compiler
and explicitly reviewed layout/dictionary revisions. The four-side result is
262,000 bytes with SHA-256:

`18baaecda65e2cf2406672da3c803669c3e5bafbe43af1c5b06216c93dfd2f03`

See [the v40 audit](V40_DIALOGUE_FLOW_AUDIT.md) for scope, fixes and limitations.
The earlier v39 gate correction is included.

## Inputs and authority

- `work/translations/<BANK>.json` supplies all 1,299 scenario records.
- The private four-side v25 baseline is
  `work/baseline/time_twist_v25_safe_encoding.fds`, SHA-256
  `813cdceb190e9714f7489c1bd5500f8e2ead3b3942f789ccf68bc6f3696bfc19`.
- `recovery/v38/repro_bundle` remains immutable. Its manifest and 17 encoded
  payloads are source-locked and individually hash checked before use.
- `v40_checkpoint.py` records approved hashes for 77 layout revisions and the
  reviewed dictionary additions. It does not contain alternate English prose.

The builder compares changed records with their approved hashes and verifies
that visible wording matches the immutable archive after normalizing controls
and whitespace. All other records must match the archive exactly. It replaces
both recovered scenario inputs with active-map values before compilation, then
compares every decoded output record with the active maps and checks the whole
ROM hash. Updating the source lock alone cannot approve different text.

TT3A dictionary entries are recompressed using earlier IDs only, preserving
all existing literal expansions. Five entries are appended. TT1B keeps all
128 existing entries byte-for-byte and appends one. Wait/scroll controls are
forbidden inside dictionary expansions because a renderer return with pending
dictionary stack frames corrupts execution. Only ordinary row advances occur
in the new dictionary phrases.

The baseline supplies the existing font, title and unchanged engine. This is
reproduction from a patched v25 baseline, not a demonstrated build from original
Japanese disks. Historical engineering work remains available through
`time-twist-runtime build-historical`.

## Validation and future edits

Public CI needs no ROM. It checks all 1,299 active records, rejects unauthorized
changes to any record, checks native line-state geometry and retained-buffer
safety for all 63 registered source continuations, and rejects unsafe dictionary
wait controls. Ordinary prose has no non-greedy checkpoint exceptions; eight
exact quiz layouts retain the full native 24-column width.

With the private baseline installed, the focused release suite builds twice,
checks deterministic outputs and manifests, validates the approved hash and
unchanged non-scenario payloads, and verifies that strict release mode rejects
an unpromoted candidate:

```sh
PYTHONPATH=work python -m unittest work.integration_tests.test_release -v
```

Future edits must revise the reviewed checkpoint and expected output hash with
corresponding runtime evidence. The full historical suite also requires the
private fixtures in `work/integration_fixtures.json`; those fixtures were not
available for this audit. The candidate remains unpromoted pending complete
runtime review. No ROM, BIOS, emulator or save state is committed.

Old save states retain loaded bank data. Use the converted v40 state with v40,
or reset the new ROM; loading an old state does not establish that new text runs.
