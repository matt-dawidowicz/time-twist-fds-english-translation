# Native compression accelerator

The optional native optimizer accelerates the expensive **offline** dictionary
search used by editorial compression audits. It does not run on the Famicom,
does not change the packed-text format, and is not required to install or use
the normal Python tooling.

The canonical format model remains `work/time_twist/textcodec.py`. The canonical
reference search remains `work/time_twist/compression.py`. Rust is an accelerator
for the same deterministic search policy, not a second definition of correctness.

## Why Rust is justified

Real-bank profiling showed that the deeper Python search can take tens of
seconds for one bank evaluation. Early measurements on the engineering branch
included:

| Bank | Fast | Deep Python | Extra bytes recovered |
| --- | ---: | ---: | ---: |
| TT1A | 0.934 s | 17.327 s | 4 |
| TT3B | 1.292 s | 52.949 s | 4 |
| T25 | 1.219 s | 29.549 s | 5 |
| TT6D | 0.065 s | 0.677 s | 0 |

A compression-aware layout audit may evaluate several legal wraps of the same
sentence, so a 30-50 second whole-bank search quickly becomes too slow for
iterative prose work.

## Architecture

The native component is a standalone Rust binary:

```text
native/compression_optimizer/
    Cargo.toml
    src/main.rs
```

It intentionally has no third-party Rust runtime dependencies. Python invokes
one process per **complete bank optimization problem**, so process startup is
negligible relative to the combinatorial search and no Python extension ABI is
introduced.

Normal setuptools packaging is unchanged. A contributor without Rust simply
uses the Python backend.

## Building

From the repository root:

```text
cargo build --release --manifest-path native/compression_optimizer/Cargo.toml
```

The executable is then located at:

```text
native/compression_optimizer/target/release/time-twist-compression-optimizer
```

or, on Windows:

```text
native\compression_optimizer\target\release\time-twist-compression-optimizer.exe
```

The Python bridge also honors the explicit environment variable:

```text
TIME_TWIST_NATIVE_OPTIMIZER=/absolute/path/to/executable
```

No native executable is auto-downloaded.

## Protocol

The process boundary uses a small versioned line protocol rather than Python
objects or an FFI ABI. Each symbol is represented as a collision-free 16-bit
hex token:

| High byte | Meaning |
| ---: | --- |
| `00` | common glyph |
| `01` | extended glyph |
| `02` | dictionary reference |
| `03` | control |

The low byte is the native value. This is deliberately different from the
internal one-byte search key in `compression.py`; dictionary references 64-68
would otherwise overlap control-key values.

A request contains:

- protocol version;
- maximum dictionary entries;
- optional packed-byte limit;
- whether the caller requires a full dictionary;
- fixed required dictionary prefix;
- every group and record in order.

The result contains:

- protocol version;
- claimed packed size;
- ordered flat dictionary;
- compressed groups and records.

The protocol is an internal accelerator boundary, not a ROM format.

## Python verification

`work/time_twist/compression_native.py` treats native output as untrusted until
it is independently proved correct.

Before returning a native candidate, Python verifies all of the following:

1. group and record counts are unchanged;
2. dictionary size is within the decoder limit;
3. required dictionary entries remain the exact prefix;
4. full-dictionary requirements are satisfied when applicable;
5. every dictionary entry is nonempty, unique, and contains only literal glyphs;
6. every compressed record expands through the returned dictionary to the exact
   original Python symbol stream;
7. canonical Python `packed_size()` equals the native claimed size;
8. the result remains within the requested packed-byte limit.

Any disagreement raises `NativeCompressionError`; there is no permissive or
best-effort acceptance path.

## Search equivalence

The Rust implementation mirrors the current Python optimizer policy:

- required-prefix installation;
- pruned greedy search;
- exhaustive greedy fallback when required;
- default bounded beam search;
- fixed-prefix-safe dictionary-order hill climb;
- wider beam when the baseline is within 16 bytes of capacity;
- exact byte-aligned scoring;
- deterministic tie ordering.

CI builds the Rust binary and runs synthetic cross-language equivalence tests.
It also compares a real TT1A deep result against the Python reference before the
native backend is accepted for editorial benchmarking.

## Using the backend

The normal release path remains Python. Native search is opt-in for editorial
tools:

```text
python work/tools/compression_headroom.py --bank TT1A --backend native
```

and:

```text
python work/tools/editorial_layout_audit.py \
  --bank TT1B \
  --record TT1B/g0/r1 \
  --text "When was the last time I saw a blue sky?" \
  --backend native
```

This separation prevents release output from silently depending on whether a
particular machine happens to have Rust installed.

## Determinism

Speed is not allowed to weaken reproducibility. Both implementations define
deterministic ordering for candidate ranking, beam successors, dictionary
identity, and final result selection. CI equivalence tests are intended to catch
any platform or implementation divergence before the accelerator is used for
translation decisions.

The native backend may later use internal parallelism only if the final ordering
remains explicitly deterministic and cross-platform equivalent.
