# Performance-only maintenance: entropy parsing and file hashing

## Behavior contract

This change is intended to preserve every byte of the existing translation.
It does not alter translation maps, source records, disk layout, patch payloads,
published release hashes, compression grammar, or public CLI interfaces.

**Entropy parser:** `_make_parser` creates a closure over an immutable
dictionary revision. The optimizer repeatedly evaluates the same immutable
literal records and optional maximum reference index. The parser now memoizes
those results using a bounded `lru_cache(maxsize=4096)` scoped to the closure,
so different dictionary revisions have independent caches. The same
deterministic tie-breaking and packed stream are retained.

**Release file SHA-256:** `sha256_file` now reads 1 MiB chunks instead of
loading the entire file. Digests are still uppercase SHA-256. Input files,
record order, normalization, lock manifests, and release decisions are not
modified.

## Reproducible acceptance checks

- `python work/run_tests.py unit`
- `python -m ruff check work`
- `python -m black --check work`
- `python -m mypy`
- `python work/tools/check_public_tree.py`
- `python release_patcher/test_public_patcher.py`
- `python work/tools/quick_check.py`

`work/tests/test_performance_equivalence.py` records a frozen SHA-256 for
the packed output of an 80-record synthetic corpus and checks streamed file
digests against independent in-memory SHA-256 on empty, small, and multi-block
files. These are ROM-free public checks suitable for GitHub Actions.

## Local performance observations

Prior local diagnostic runs on the same synthetic 80-record corpus showed
approximately 87 ms before caching and 30 ms after caching. For a 28 MiB
synthetic file, the streaming hasher reduced peak Python-traced allocation
from approximately 28 MiB to 2 MiB. These are environment-specific
observations, not CI performance guarantees. Cache efficiency depends on
repeated record frequency, so changes should be assessed on broader corpora
before claiming a universal speedup.

## Preservation and private release certification

The public release patcher takes the owner's legally obtained canonical
Zenpen and Kouhen sources and produces three existing v1.1 images. Those
output hashes are:

| Output | SHA-256 |
| --- | --- |
| Zenpen | `0784FE632DB3DB424E963CCA840982942F689A4385EFE9BDE3E7940F325599F7` |
| Kouhen | `8327F1130563C3C6E87CBE67DA227429BAAC59E596B49D67BE1018FD3A2E398F` |
| Four-side | `4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A` |

No retail ROMs or generated English FDS files may be committed. The public
tests demonstrate optimizer byte stability and unchanged hash semantics; full
private v25-based release rebuilding and emulator validation remain separate
maintainer gates. The patcher production output is independently checked by
`docs/PUBLIC_PATCHER_INTERNALS.md` and its existing golden hashes.

Historical alternative implementations remain recoverable in Git history
and `docs/history/`; this patch removes no source or explanatory records.
