# Compression optimizer

The build-side optimizer chooses a legal dictionary and packed symbol stream for
each scenario bank. It does **not** define the runtime format; that contract is
documented in `TEXT_COMPRESSION.md` and modeled by `textcodec.py`.

The optimization objective has two modes:

- ordinary development/release builds prioritize fast deterministic turnaround
  and escalate only when necessary to fit;
- editorial optimization deliberately searches harder even when the fast result
  already fits, because recovered bytes can be spent on more natural English.

## Exact objective

For a candidate result, `packed_size()` repacks the complete group streams and
dictionary and returns the exact byte count. This is intentionally different
from summing estimated token widths because every record terminates with a
seven-bit separator and then aligns to the next byte boundary.

A valid result must also satisfy all bank-specific constraints, including:

- original fixed packed-byte capacity;
- maximum dictionary size supported by the runtime decoder;
- any fixed-address UI records that reserve dictionary entries or require a
  compatible dictionary;
- exact symbol expansion back to the intended English stream.

Among valid candidates, smaller exact packed size is preferred. Deterministic
identity ordering breaks ties so the same inputs produce the same output.

## Greedy search

The normal compressor starts by installing any required fixed dictionary prefix.
It then repeatedly:

1. finds repeated literal substrings of 2 through 32 symbols;
2. estimates their bit savings;
3. ranks positive-saving candidates;
4. exact-scores the best estimated candidates against byte-aligned record size;
5. installs the best candidate that reduces the complete packed footprint.

The normal fast pass exact-scores up to 200 ranked candidates per dictionary
iteration. If a caller supplies a capacity and the pruned greedy result does not
fit, the fallback reruns greedy selection without that candidate limit.

Controls and existing dictionary references split candidate regions. Generated
English dictionary entries therefore remain flat and cannot silently absorb a
control-code boundary.

## Beam search

Greedy selection can make a locally attractive choice that blocks a better
combination of overlapping substrings. The deterministic beam search retains
multiple dictionary states at each depth and evaluates several successors per
state.

Current defaults in `compression.py` are:

| Search | Beam width | Branch factor |
| --- | ---: | ---: |
| normal alternative | 4 | 4 |
| tight-bank alternative | 12 | 8 |

The wider search is added when the greedy baseline is within 16 bytes of the
requested capacity.

These values are policy parameters, not format limits. Editorial benchmarking
may justify deeper settings, but any change must be measured for both packed
size and runtime cost of the offline tool.

## Dictionary-order hill climb

Flat dictionary entries can overlap. Even with the same membership, applying
entry A before entry B can replace a different set of literal occurrences than
applying B before A.

The current optimizer therefore performs a fixed-prefix-safe pairwise order
search. Required UI entries stay at their established indices; optional entries
may swap. A smaller exact packed result becomes the new incumbent and the search
continues for a bounded number of passes.

This improves ordering only. A future optimization pass may also evaluate
membership operations such as drop/add or one-for-one replacement, provided the
result remains deterministic and exact-expansion-equivalent.

## Fast release policy

`release_compression.compress_release_groups()` normally performs this sequence:

1. run the deterministic non-optimized compressor;
2. validate its exact size and any fixed-UI compatibility predicate;
3. return immediately if it fits;
4. otherwise invoke `compress_english_groups(..., optimize=True)`.

That is appropriate for routine development: once a bank fits, additional CPU
time is unnecessary for producing a valid ROM.

## Maximize-headroom policy

Editorial work has a different goal. The new `maximize_headroom=True` policy
skips the fast-accept shortcut and invokes the strongest existing deterministic
optimizer unconditionally.

The capacity remains a hard upper bound. The policy is not permission to change
runtime layout or make output nondeterministic; it merely refuses to stop
searching because an earlier candidate happened to fit.

This matters because every byte recovered from the same fixed allocation can be
spent restoring articles, pronouns, connective language, character voice, or
more natural line wrapping.

## Whole-game headroom audit

`work/tools/compression_headroom.py` rebuilds every real scenario bank twice:

1. normal fast release policy;
2. maximize-headroom policy.

For each bank it reports:

- fixed capacity;
- fast packed bytes;
- optimized packed bytes;
- free bytes under each policy;
- bytes recovered by deeper search;
- dictionary-entry counts;
- wall-clock time.

The audit does not change ROMs or source metadata. It should be run before large
prose revisions so there is a measurable baseline for how much space the current
codec can recover without changing the text.

## Profiling before a native rewrite

The optimizer is written in Python because that makes the format and search
policy easy to audit. A faster language should be introduced only after real
profiles show that deeper editorial search is materially bottlenecked by Python.

Likely hot paths are:

- enumeration/counting of 2-32-symbol substrings;
- repeated exact candidate scoring;
- rebuilding immutable group states for beam successors;
- repeated dictionary application during order search.

Algorithmic improvements should be evaluated first, including compact integer
representations, occurrence indexing, memoization, incremental size deltas, and
membership-local search.

## Native accelerator contract

If a Rust accelerator becomes worthwhile, Python remains the reference and
verifier. The preferred boundary is a whole optimization problem rather than a
per-candidate FFI call.

A native backend may propose:

- an ordered dictionary;
- compressed group symbol streams;
- its claimed packed byte count.

Python must independently:

1. validate dictionary bounds and fixed prefixes;
2. expand every dictionary reference;
3. prove the expanded stream equals the intended English symbols;
4. repack through `textcodec.py`;
5. recompute the exact byte count;
6. reject any disagreement.

Normal contributors should not need a Rust toolchain merely to use the project.
If acceleration is added, Python-only operation remains supported unless a later
measured requirement justifies changing that policy.

## Determinism

Optimization output is part of reproducible ROM construction. Given identical
source translations, codec rules, and optimization parameters, builds must
choose the same dictionary and packed streams across runs.

Searches therefore need explicit tie ordering. Parallel or native
implementations must not let hash iteration order, thread scheduling, platform
integer behavior, or randomized seeds affect output.

Performance is valuable only if reproducibility is preserved.

## Measured hybrid backend

The profiling threshold for a native accelerator has been met. On the real TT1A
bank, the reference Python deep optimizer produced a 1,594-byte result with 26
dictionary entries in about 17.3 seconds. The Rust backend produced the same
size and dictionary count in about 0.43 seconds, roughly a 40x speedup on the
GitHub Actions runner. Synthetic cross-language equivalence tests also require
the ordered dictionary and compressed streams to agree.

The hybrid is therefore a supported editorial optimization path:

1. Python parses authoritative English and encodes canonical symbols.
2. Rust performs the expensive deterministic dictionary/search work.
3. Rust returns an ordered dictionary, compressed group streams, and claimed
   packed size through the versioned text protocol.
4. Python rejects malformed, non-flat, out-of-range, duplicate, over-capacity,
   or required-prefix-incompatible dictionaries.
5. Python expands every dictionary reference and proves the resulting symbol
   stream is identical to the intended English.
6. Python repacks the candidate with the canonical codec and independently
   verifies the exact byte count.

The purpose of the speedup is editorial: search time should not pressure the
translation toward shorter, flatter English. Deeper compression and layout
search are tools for retaining Japanese intent, register, sentiment, character
voice, and dramatic rhythm inside the unchanged ROM footprint.
