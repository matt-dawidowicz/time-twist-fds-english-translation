# Native compression accelerator

## Purpose

Time Twist keeps Python as the canonical implementation of the packed-text
format, release validation, ROM construction, and translation workflow. The
optional Rust program in `native/compression_optimizer` accelerates only the
expensive deterministic dictionary/search stage used by editorial optimization.

The reason for the hybrid is translation quality. The project should preserve as
much of the Japanese as English can carry: denotation, implication, sentiment,
speaker stance, register, humor, hesitation, emphasis, characterization, and
dramatic rhythm. Fixed FDS memory and renderer limits remain non-negotiable, but
they should be attacked with better packing and layout search before natural
English is shortened.

## Authority boundary

Rust is an optimizer, not a codec authority. `work/time_twist/textcodec.py` and
the Python compression/validation code remain the executable specification.
`work/time_twist/compression_native.py` serializes one complete optimization
problem, runs the native helper, parses its answer, and verifies it independently.

Python rejects a native result unless all of the following hold:

- group and record counts are unchanged;
- dictionary size is within the recovered decoder limit;
- any required dictionary prefix is byte-for-byte semantically preserved;
- dictionary entries are unique, nonempty, flat glyph strings;
- every dictionary reference expands legally;
- every expanded record is symbol-for-symbol identical to the intended English;
- canonical Python `packed_size()` agrees with the native claimed size;
- the fixed bank byte limit is not exceeded.

This makes native failure fail-closed: an unavailable, crashing, malformed, or
incorrect helper cannot silently change the ROM text.

## Protocol

The bridge uses a versioned plain-text whole-bank protocol:

- request magic: `TIME_TWIST_COMPRESSION_V1`;
- result magic: `TIME_TWIST_COMPRESSION_RESULT_V1`;
- each packed symbol becomes a collision-free 16-bit token containing symbol
  kind and value;
- the request carries the maximum dictionary count, byte limit, full-dictionary
  requirement, required prefix, and every group/record;
- the result returns the claimed packed size, complete ordered dictionary, and
  compressed groups.

A whole-bank process boundary is intentional. It avoids per-candidate FFI
overhead and keeps the normal Python package independent of CPython ABI or PyO3
wheel concerns.

## Discovery and build

Normal Python use does not require Rust. Editorial/native mode discovers the
helper in this order:

1. `TIME_TWIST_NATIVE_OPTIMIZER`;
2. the checkout release target under
   `native/compression_optimizer/target/release`;
3. `time-twist-compression-optimizer` on `PATH`.

Build from the repository root with stable Rust:

```text
cargo fmt --check --manifest-path native/compression_optimizer/Cargo.toml
cargo test --manifest-path native/compression_optimizer/Cargo.toml
cargo build --release --manifest-path native/compression_optimizer/Cargo.toml
```

Windows uses the standard stable `x86_64-pc-windows-msvc` toolchain. No nightly
features are required.

## Determinism and equivalence

The native search must use explicit deterministic ordering for ties. Hash-map
iteration order, thread scheduling, platform-specific integer behavior, or random
seeds must not affect selected dictionaries or streams. CI cross-checks the Rust
optimizer against the Python reference on representative corpora, and a real
bank benchmark requires equal optimized size and dictionary count.

The editorial path still prefers English quality over a tiny size difference
once every candidate fits. Compression ranking chooses technically efficient
layouts; the editor may select a slightly larger layout when it better preserves
phrasing, sentiment, voice, or dramatic cadence and the bank retains safe
headroom.

## Measured result

On GitHub Actions, TT1A measured approximately:

| Backend | Optimized bytes | Dictionary | Deep-search time |
| --- | ---: | ---: | ---: |
| Python reference | 1594 | 26 | 17.3 s |
| Rust accelerator | 1594 | 26 | 0.43 s |

That roughly 40x acceleration is large enough to change the editorial workflow:
natural prose and legal line layouts can be explored directly instead of being
shortened pre-emptively to keep optimization time manageable.

## Release policy

Routine builds may continue to use the fast Python path. Native mode is intended
for editorial/headroom optimization and final translation engineering. Any
release candidate produced from native search must still pass the same Python
codec validation, source locks, tests, fixed-bank capacity checks, and runtime
playtest gates as any other candidate.
