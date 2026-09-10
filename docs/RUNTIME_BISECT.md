# Runtime bisect: 2026-08-29 vs current

This branch is intentionally optimized for one comparison: the last mainline
state from 2026-08-29 versus the current runtime work.

Baseline commit:

`ad5ebe9fced6807c6398691db1b36c58e9b1d095`

The cleanup branch is squashed directly onto that commit, so `git diff HEAD^ HEAD`
is the complete old-vs-current source delta instead of a walk through hundreds of
intermediate experimental commits.

## Fast commands

After an editable install (`python -m pip install -e .`):

```text
time-twist-runtime code
time-twist-runtime fds OLD.fds CURRENT.fds
time-twist-runtime smoke
time-twist-runtime build --zenpen ZENPEN.fds --kouhen KOUHEN.fds
```

`time-twist-runtime` is intentionally entropy-only. The discarded production /
Adaptive255 runtime is no longer exposed as a parallel debug mode.

The default build output is `build/runtime/current.fds`. Translation maps default
to `work/translations`; title assets default to the reviewed repository assets.
Pass `--all-images` only when the separate Zenpen/Kouhen images are actually
needed.

`code` invokes one `git diff` process. `fds` parses each FDS once and compares
named payloads in memory. `smoke` runs the focused runtime tests in one Python
interpreter instead of launching a process per test module. `build` calls the
entropy release builder directly instead of spawning wrapper scripts. The
remaining Python loops are intentionally in-memory passes; replacing them with
per-item subprocesses would be slower.

## Current blank-gameplay regression

The discarded Adaptive255 crash and the current entropy blank-gameplay failure
are separate bugs. Adaptive255 allowed scenario data to cross `$D7B5`, the load
address of resident NOV3. The entropy layout enforces `$D7B5` as the exclusive
ceiling, and the generic spill allocator now also defaults to that boundary. The
old `$E000` ceiling exists only as an explicitly named legacy diagnostic constant.

The active entropy regression was narrowed to NOV2 decoder state preservation.
The entropy scanner used X internally without restoring the caller's X, and both
the scanner and frontend borrowed zero-page `$74` as a temporary category byte.
`$74` is native engine state, not entropy scratch. The runtime now preserves X
across scanner calls and keeps the category on the 6502 stack instead of `$74`.
The focused regression tests freeze the generated scanner/frontend/category
binaries and forbid entropy scanner/frontend accesses through `$74`.

## Direct entropy installation

Entropy no longer stages the discarded Adaptive255 runtime before overwriting it.
The direct path is:

```text
Japanese NOV2
  -> patched_nov2_ui
  -> proven non-Adaptive production runtime fixes
  -> two nested-dictionary depth patches ($82C5 / $8311)
  -> frozen entropy scanner/frontend/category runtime
```

The five other Adaptive255 runtime changes were dead staging: the entropy scanner,
top-level initializer, frontend, and category decoder overwrite those regions
immediately. They are no longer installed or accepted as entropy source state.

The only retained Adaptive-era semantics are the four-byte dictionary-depth
increment/decrement patches. Those are now explicit entropy prerequisites rather
than an implicit dependency on `patch_nov2(..., adaptive_dictionary=True)`.

Do not create another R1/R2/R3/R4/C0/C1/C2 candidate family for this issue. The
older runtime artifacts remain useful as binary observations only. New work
should be expressed as source changes on this branch and inspected through
`time-twist-runtime`.

## Scope

This is a debugging branch, not a release branch. It deliberately keeps the
2026-08-29 baseline as the sole parent comparison point and avoids using the
intermediate R1/R2/R3/R4/C0/C1/C2 artifacts as source-history milestones.
Those ROM artifacts remain useful as observations, but they are not part of the
code-history comparison.

The old standalone `build_entropy_candidate.py`, `build_production_candidate.py`,
and `apply_production_runtime_hardening.py` wrappers are intentionally removed on
this branch; the maintained runtime-debug operations are consolidated under the
entropy-only `time-twist-runtime` interface.
