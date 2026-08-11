# Release risk assessment

This document records the non-playtest risks that can be assessed with static,
synthetic, and private-fixture evidence. It deliberately separates those risks
from story progression, disk swapping in an emulator, presentation timing, and
translation judgment, which still require a human playthrough.

## Assessment scope

The assessment uses four evidence levels:

1. fixture-free unit and property tests for formats and release controls;
2. exact tests against the hash-verified private fixture overlay;
3. two independent candidate rebuilds from the approved Japanese baselines;
4. fault injection against multi-file publication.

No test result promotes a candidate. Promotion remains a separate maintainer
decision after review and playtesting.

## Validation snapshot: 2026-08-11

- all 92 private fixture records matched their exact size and SHA-256;
- all 75 fixture-free public tests passed with no skips;
- all 75 private integration tests passed with no skips;
- the private release test produced two byte-identical candidates;
- the v2 source-lock identity was
  `9078242151C414E802D83D2C849836A3574D33003EB2824180BA5CA91709B7FC`;
- the 13-file release-code tree identity was
  `F9F57B8892E17434F7EEB564A984F7F83C1F5B58BB20436C1B117EBCC24D0AD6`;
- public-tree, Black, Ruff, pydocstyle, and mypy checks passed.

The private overlay was assembled only in an isolated temporary directory and
removed after testing. No ROM-derived file was added to the public checkout.

## Findings and disposition

| Risk | Finding | Disposition |
| --- | --- | --- |
| Windows versus Unix translation bytes | Git stores the translation JSON with LF, while a Windows checkout may contain CRLF. The v1 lock treated those equivalent files as different release inputs. | Fixed by source-lock schema v2 and explicit `lf` normalization. |
| Accidental binary normalization | Applying text rules to FDS or PNG data could conceal a real byte change. | Prevented: baselines and title artwork declare `raw`, and metadata validation rejects a different policy. |
| Source-lock document identity | The checked-in JSON lock itself could acquire CRLF and therefore a different raw hash. | Fixed: target/candidate linkage hashes the lock document after LF normalization. |
| Installed tool differs from checkout | An installed wheel could execute code different from `<project-root>/work/time_twist`. | Fixed by independently hashing the executing and checkout package trees under the same logical paths and failing closed. |
| Expanded NOV4 diff audit | The original NOV4 is 9,077 bytes and the patched component is 12,209 bytes. Strictly zipping both entire byte strings raises before the test can inspect the changed prefix. | Fixed: the scope audit compares the exact shared prefix; separate assertions validate every appended region and final memory bound. |
| Obsolete checked-in target | The historical v1 target lacked code provenance and referred to superseded output hashes. | Fixed: the obsolete record was removed. Unit metadata validation accepts only a valid current-schema target or the documented absent state; integration proves strict publication fails while unpromoted. |
| Candidate reproducibility | Repeated generation might produce different banks, images, or manifests. | Assessed: two isolated candidate builds are required to match byte-for-byte. |
| FDS/container integrity | Rebuilding could alter unrelated blocks, side count, or serialization. | Assessed by exact parse/serialize, replacement-scope, side-composition, and image-hash tests. |
| Bank overflow | English compression could exceed a fixed bank footprint. | Assessed on every bank; release reports retain exact capacity, packed size, and remaining bytes. The narrowest current bank has two bytes free. |
| Title memory collision | Relocated title data could overlap resident NOV3 or damage clock assets. | Assessed by exact addresses, stream decoding, helper bounds, protected hashes, and the `$D1B1` patched end below NOV3 at `$D7B5`. |
| Interrupted multi-file publication | The process can stop after replacing one image but before replacing the rest. | Mitigated, not eliminated: the prior manifest is removed first, each file replacement is atomic, and no mixed set remains attested. Retry the build to replace the complete set. |
| Hostile in-process mutation | A malicious process could monkeypatch imported functions without changing source files. | Outside the trusted local-build threat model. Source provenance attests files, not arbitrary runtime memory. |
| Complete gameplay behavior | Static and integration evidence cannot prove every transition, disk prompt, save/load path, visual frame, or line in context. | Open until the manual Zenpen-to-Kouhen playtest matrix is complete. |

## Source-lock schema v2

Each non-code input record now states how its bytes are interpreted:

```json
{
  "normalization": "lf",
  "sha256": "...",
  "bytes": 3657
}
```

`lf` is permitted only for `work/translations/*.json`. CRLF and bare CR are
converted to LF before the digest and byte count are calculated. This changes
only representation: JSON text, punctuation, control tags, key order, spacing,
and every other byte remain bound by the digest.

`raw` is mandatory for the two FDS baselines and indexed title PNG. Their
digest and size cover the exact on-disk bytes. A lock that labels a binary
input as text is rejected structurally rather than trusted.

The `source_lock_sha256` stored in candidate and target metadata also uses LF
normalization for the lock JSON document. The checked-in `.gitattributes`
reinforces the same policy, but release correctness does not depend on Git or
its checkout settings.

## Expanded-title audit

NOV4 expansion requires two different proof obligations:

- offsets that existed in the 9,077-byte source may change only within the
  documented pointer, helper-call, palette, origin, and CHR ranges;
- bytes appended after the source end must form the documented helper/data
  layout, decode to the exact two 1,024-byte nametables, terminate at the file
  end, and remain below resident NOV3.

The integration test now compares the original to
`patched[:len(original)]`. It does not silently ignore the appended portion:
other assertions lock its total size, addresses, hashes, stream terminators,
helper code, and `$0604`-byte gap before NOV3.

## Candidate and strict-release policy

The private release test builds two candidates with `verify_target=False` and
requires identical manifest dictionaries, manifest bytes, individual FDS
bytes, and four-side composition. This tests reproducibility without granting
approval to the result.

A separate test calls strict mode with the intentionally absent target and
requires a missing-target rejection before an output directory is published.
Unit tests still cover legacy-v1 rejection synthetically, so backward-safety
behavior remains tested without keeping obsolete release metadata.

The current reproducible but **unpromoted** ROM hashes are:

| Output | SHA-256 |
| --- | --- |
| Zenpen | `203B0D72731A3CD31345DB3658AE290731CFFCAB38AB596BAF0D3F4F1CA1C84C` |
| Kouhen | `0975E9AE9B097375FBF785C56D84F2C75A7EB41135F5D9AA90AB57701A416CE6` |
| Four-side | `21C96A5A2B032D68C6894C094C2659971E6345124FC17C09D213968EC5C42D95` |

These hashes are reproducibility evidence, not a promoted release target.
They must not be copied into `work/release_target.json` by hand.

## What the maintainer still must do

After completing the manual playtest matrix:

1. retain the exact candidate that was tested;
2. confirm its manifest and image hashes are unchanged;
3. run `release-promote` against that reviewed candidate manifest;
4. commit the resulting v2 target intentionally; and
5. run a strict `release-build` to reproduce the promoted hashes.

See [the playtest matrix](PLAYTEST_MATRIX.md) for runtime coverage and
[the development guide](DEVELOPMENT.md#release-lifecycle) for commands.
