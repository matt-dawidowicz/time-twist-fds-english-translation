# October 13, 2026 — source audit and byte-preserving performance work

This is a **permanent historical record**, not a replacement for the current
[code tour](../CODE_TOUR.md), [module map](../MODULE_MAP.md), or
[maintainer release procedure](../MAINTAINER_RELEASE_PROCESS.md).
Keep it when implementation details change; annotate outdated conclusions
instead of silently erasing the reasoning.

## Preservation contract and scope

At the starting GitHub revision
`27b67b82e08f90046ad4cf9df595f0800de3cd6f`, the public tree contained
392 tracked entries, including 141 Python sources. The audit tooling parses
every current public Python file, reports source locations, oversized
functions, structural duplicate candidates, missing function documentation,
and a few risky AST patterns. This is comprehensive **mechanical source
coverage**, not a claim that a human has proven every one of its ~35,000 lines
free of defects. A simple call-site search cannot establish that a function is
unused: public API entry points and private integrations can call it.

Do not delete historical or recovery directories, translation maps, decoded
source records, frozen compiler bundles, failed-attempt documentation, or
private-build rationale because an automated scan sees no imports. The public
repository is intentionally not a distribution channel for retail or patched
game images.

## Exact canonical release fingerprint

Both locally supplied Japanese retail inputs were 131,000 bytes and matched
the version-locked Zenpen/Kouhen full-file SHA-256 digests. Applying the
unchanged release patcher produced exactly the English v1.1 files below:

| Output | Bytes | Independently pinned SHA-256 |
| --- | ---: | --- |
| English Zenpen | 131,000 | `0784FE632DB3DB424E963CCA840982942F689A4385EFE9BDE3E7940F325599F7` |
| English Kouhen | 131,000 | `8327F1130563C3C6E87CBE67DA227429BAAC59E596B49D67BE1018FD3A2E398F` |
| Combined four-side | 262,000 | `4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A` |

Use `work/tools/verify_public_release_identity.py` with legally obtained
retail Zenpen and Kouhen paths to reproduce this evidence. It runs the real
public patcher and independently verifies each generated file inside a
temporary folder, then removes all images. **Never attach these inputs or
outputs to issues, commits, CI logs, or release-source audits.**

## Profile-driven implementation changes

Measurements: Python 3.13.5, warm filesystem cache, three runs with
`tracemalloc`. Times depend on the machine and are not promised performance
targets.

| Deterministic workload | Before | After | What stays fixed |
| --- | ---: | ---: | --- |
| Entropy optimizer, 18 repeated records | 10.3 ms | 7.1 ms | Symbol/dictionary output |
| Entropy optimizer, 40 repeated records | 47.0 ms | 21.4 ms | Symbol/dictionary output |
| Entropy optimizer, 80 repeated records | 86.8 ms | 29.5 ms | Encoded byte stream |
| SHA-256 of a ~28 MB archive | 19.37 ms; ~28.1 MB peak traced | 18.6 ms; ~2.1 MB peak traced | Exact SHA-256 digest |

**Entropy optimizer:** `entropy_compression._make_parser` originally ran
the same dynamic-programming record parse many times for identical corpus
entries. The parser captures an immutable dictionary revision. A private,
bounded `lru_cache(maxsize=4096)` on the nested parser caches by immutable
record **and** `maximum_index`, so different dictionary revisions never
share stale results and candidate ranking/tie-breaking are unchanged.
For the 80-record golden case, both implementations yield nine dictionary
entries, 187 optimizer bytes, and a 110-byte packed stream with SHA-256
`9C58D5F731997F1B69EE2DDD9F28176FBFBFB0FEDC41D00DAC3757FF157B3AC3`.
A new fixture-free regression test pins these bytes and verifies lossless
round-tripping.

**File hashing:** `release_metadata.sha256_file` previously called
`path.read_bytes()`, allocating an entire file. It now hashes 1 MiB chunks,
preserving the uppercase SHA-256 contract, including at empty-file and
chunk-boundary sizes. Source-lock CRLF normalization and the special
length-prefixed release-code-tree fingerprint remain **unchanged**.

To replicate an approximate local profile (using synthetic data and no ROM):
```text
python work/tools/benchmark_public_hotpaths.py --repetitions 7
```
This emits peak traced memory, median timings, and immutable byte hashes.
Performance timings are intentionally **not** CI acceptance thresholds;
a correct output digest is mandatory, regardless of speed.

## Reviewed duplication and complexity

The AST report identifies especially large routines:
`cli_parser.build_parser` (mostly declarative arguments),
`title_assets.build_title_assets`, `title_patch.patched_nov4_title`,
`incremental_build._rebuild_loaded_bank`, and
`production_translation_core._split_visible_text`. These are candidates for
future narrow, test-backed extraction. Title layout, FDS bank allocation, and
6502 timing must not be reorganized merely to reduce source-line counts.

Three duplicate-body groups in the archived version have plausible distinct
ownership: `BitReader.align_to_next_byte` vs
`BitWriter.align_to_next_byte`; `ui._encode_disk_prompt` vs
`ui._encode_side_number_error`; and two test-local `_production` helpers.
Their explanatory interfaces matter more than trivial line reduction. None
was deleted. The limited static scan found no literal `eval()`, `exec()`,
wildcard imports, bare exception handlers, or `shell=True` calls. That is
**not** a formal security assessment.

The in-memory retail BPS patching path measured around 8 ms. A speculative
rewrite of its CRC, source-copy, or target-copy logic offers poor payoff for
a comparatively high correctness risk, so it was deliberately left intact.

## Testing evidence and unresolved release gate

- Local public-source-tree checker: PASS.
- Original public BPS unit tests: PASS.
- Entropy production and new golden-output tests: PASS.
- Full local public unittest discovery: 310 tests passed; one additional
  module could not import because the local environment lacked
  `hypothesis`. The full GitHub CI matrix is required before merging.
- Canonical Zenpen, Kouhen, and four-side v1.1 patcher output: exact SHA-256
  identities reproduced from the user's original disks, with images kept
  private.

**Important:** Changing `work/time_twist` Python code *necessarily*
changes its provenance tree hash, even if compiled ROM bytes stay identical.
Do not falsify the code provenance or overwrite the version-locked source
manifest to hide this. Full v25-based candidate regeneration still requires
the private v25 seed, private integration overlay, reproducibility gates,
and emulator playtesting. Those inputs were **not** supplied as part of this
cleanup. The public release's byte identity is verified; the complete
private builder has **not** been independently recertified.

## Commands for future maintainers

```text
python work/tools/audit_python_maintainability.py --format json
python work/tools/audit_python_maintainability.py --format markdown
python work/tools/benchmark_public_hotpaths.py --repetitions 7
python work/tools/check_public_tree.py
python release_patcher/test_public_patcher.py
python work/run_tests.py unit
python work/tools/verify_public_release_identity.py <ZENPEN.fds> <KOUHEN.fds>
```

The last command must only be run locally with legitimate original images;
never execute it on public CI. For any ROM-affecting refactor, additionally
follow the entire [private candidate and emulator checklist]
(../MAINTAINER_RELEASE_PROCESS.md) before promotion.
