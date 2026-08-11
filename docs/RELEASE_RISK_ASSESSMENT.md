# Release risk assessment

This document records the non-playtest risks that can be assessed with static,
synthetic, reproducibility, and private-fixture evidence. It deliberately keeps
those risks separate from story progression, disk swapping, presentation timing,
and translation judgment, which still require a human playthrough.

## Evidence policy

Evidence is tied to the exact code that produced it. Historical private-fixture
results remain useful evidence for unchanged binary behavior, but they are not
reported as a fresh validation run for later release-tool commits unless the
private suite was actually rerun against that exact revision.

The public repository can validate fixture-free release controls, formatting,
linting, typing, packaging, and installed-wheel behavior. The private overlay is
required for exact ROM-derived integration tests and end-to-end candidate builds.

## Historical private validation

Before the final promotion hardening, the private overlay contained 92 records
whose sizes and SHA-256 values matched the fixture manifest. At that snapshot,
75 private integration tests passed with no skips and two independent candidate
builds were byte-identical. Those results remain historical evidence; the
release-code digest and candidate manifest must be regenerated after any change
to `work/time_twist`.

## Current promotion invariants

| Risk | Control |
| --- | --- |
| Installed tool differs from checkout | The executing package and checkout are independently hashed under identical logical `work/time_twist/...` paths and must match. |
| Candidate manifest is structurally incomplete | Manifest schema v4 requires the exact generated top-level fields, complete scenario reports, fixed-component hashes, target state, environment metadata, and canonical output records. |
| Candidate manifest lies about its subtitle | Promotion requires the manifest subtitle to equal the validated source-lock subtitle. |
| Candidate manifest/output hashes are self-consistent but were not produced by the approved build | Promotion performs a fresh candidate-mode `build_release` from the active source lock and current release code and requires the rebuilt scenario reports, component hashes, and all three output records to equal the reviewed candidate manifest. |
| Candidate file changes during promotion | Candidate outputs are checked before the rebuild proof and again immediately before target publication; the candidate manifest is also re-hashed before publication. This is a strong trusted-local-process mitigation, not a claim of hostile-filesystem atomicity across multiple files. |
| Release metadata overwrites an authoritative input | Source-lock updates and target publication reject exact-path collisions with approved sources, release-critical code, project metadata, the active source lock, candidate manifest, and candidate outputs. |
| Python/Pillow version ambiguity | Candidate and verified manifests record Python implementation/version and Pillow version as diagnostic metadata. Output hashes remain authoritative. |
| Windows versus Unix translation bytes | Source-lock schema v2 uses explicit LF normalization only for translation JSON; FDS and PNG inputs remain raw byte identities. |
| Interrupted multi-file publication | The previous manifest is removed before replacing outputs; each individual replacement is atomic and the new manifest is published last. A retry is required after interruption. |
| Hostile in-process mutation | Outside the trusted local-build threat model. File provenance does not attest arbitrary runtime memory. |
| Complete gameplay behavior | Open until the manual Zenpen-to-Kouhen playtest matrix is complete. |

## Canonical promotion proof

`release-promote` is intentionally more than a metadata copier. Before writing a
release target it proves the reviewed candidate is reproducible from the current
release authority:

```text
validated source lock
        +
current executing code == current checkout code
        |
        v
fresh candidate-mode rebuild
        |
        +--> scenario-bank audit records
        +--> NOV2 / NOV4 / SON-KOUH hashes
        +--> Zenpen / Kouhen / four-side hashes and sizes
        |
        v
must equal reviewed candidate manifest and files
        |
        v
atomic target publication
```

This prevents a hand-edited manifest from promoting arbitrary bytes even when
those bytes match the hand-edited output hashes. A later strict build therefore
should reproduce an already-proven target rather than being the first point at
which an unreproducible promotion is discovered.

The build-environment record is deliberately excluded from the equality proof.
Python and Pillow versions explain discrepancies, but the generated component
and output identities decide whether a candidate is reproducible.

## Destination collision policy

Release metadata writers accept custom paths for legitimate workflows, including
external source locks. Customization must not turn a metadata command into a
source-destruction command.

`release-lock --update` therefore rejects a destination that aliases an approved
baseline, translation JSON, title asset, release target, release-critical Python
source, or project metadata. The canonical `work/release_sources.json` location
is the one protected-path exception for source-lock updates.

`release-promote --target` similarly permits the canonical
`work/release_target.json`, but rejects collisions with authoritative sources,
release-critical code, the active source lock, the reviewed candidate manifest,
and the candidate FDS files.

## Source-lock schema v2

Each non-code input record states how its bytes are interpreted. `lf` is
permitted only for `work/translations/*.json`; CRLF and bare CR are normalized
to LF before digest and byte-count calculation. `raw` is mandatory for the two
FDS baselines and indexed title PNG.

The source-lock document identity is itself LF-normalized, so target/candidate
linkage does not depend on the host checkout's line-ending policy.

## Release manifest schema v4

A v4 manifest contains:

- source-lock identity and path;
- release-code provenance;
- informational Python/Pillow environment provenance;
- candidate or verified target state;
- the approved subtitle;
- all 13 scenario-bank capacity/hash reports;
- fixed-component hashes for `NOV2`, `NOV4`, and `SON-KOUH`; and
- canonical filename, byte count, and SHA-256 records for Zenpen, Kouhen, and
  the combined four-side image.

Schema validation proves structure. Promotion's fresh rebuild proves that the
audit values are true for the current approved inputs and implementation.
Legacy v3 candidate manifests must be rebuilt with the current release code.

## CI policy

The package declares Python 3.11 or newer. Public CI therefore runs the public
source gate, style checks, mypy, and fixture-free unit suite on both Python 3.11
and 3.12. Packaging, force-installed-wheel provenance, and CLI smoke tests run on
3.12 to avoid duplicating packaging work while still exercising the installed
artifact.

A green public workflow does not imply the private ROM-derived integration suite
ran. Private validation must be recorded separately when the legal fixture
overlay is available.

## What the maintainer still must do

After this release-tool revision is validated:

1. build a fresh candidate from the exact code intended for playtesting;
2. retain the exact candidate manifest and FDS files;
3. complete the Zenpen-to-Kouhen playthrough against those exact files;
4. confirm the retained files have not changed;
5. run `release-promote` against that reviewed candidate—the command will
   independently rebuild and prove it again;
6. commit the resulting v2 target intentionally; and
7. run a strict `release-build` to reproduce the promoted hashes.

See [the playtest matrix](PLAYTEST_MATRIX.md) for runtime coverage and
[the development guide](DEVELOPMENT.md#release-lifecycle) for commands.
