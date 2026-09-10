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
time-twist-runtime patch-runtime INPUT.fds OUTPUT.fds
time-twist-runtime build --zenpen ZENPEN.fds --kouhen KOUHEN.fds
time-twist-runtime build --mode production --zenpen ZENPEN.fds --kouhen KOUHEN.fds
```

The default build output is `build/runtime/current.fds`. Translation maps default
to `work/translations`; title assets default to the reviewed repository assets.
Pass `--all-images` only when the separate Zenpen/Kouhen images are actually
needed.

`code` invokes one `git diff` process. `fds` parses each FDS once and compares
named payloads in memory. `smoke` runs the focused runtime tests in one Python
interpreter instead of launching a process per test module. `build` and
`patch-runtime` call library functions directly instead of spawning wrapper
scripts. The remaining Python loops are intentionally in-memory passes; replacing
them with per-item subprocesses would be slower.

## Current blank-gameplay regression

The discarded Adaptive255 crash and the current entropy blank-gameplay failure
are separate bugs. Adaptive255 allowed scenario data to cross `$D7B5`, the load
address of resident NOV3. The entropy layout already enforces `$D7B5` as the
exclusive ceiling, so that old spill failure is not part of the active bisect.

The active entropy regression was narrowed to NOV2 decoder state preservation.
The entropy scanner used X internally without restoring the caller's X, and both
the scanner and frontend borrowed zero-page `$74` as a temporary category byte.
`$74` is native engine state, not entropy scratch. The runtime now preserves X
across scanner calls and keeps the category on the 6502 stack instead of `$74`.
The focused regression test also forbids entropy scanner/frontend accesses through
`$74`.

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
this branch; their maintained operations are consolidated under
`time-twist-runtime`.