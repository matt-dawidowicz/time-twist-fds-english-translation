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

## Runtime regression findings

The discarded Adaptive255 crash and the entropy blank-gameplay failure are
separate bugs. Adaptive255 allowed scenario data to cross `$D7B5`, the load
address of resident NOV3. The entropy layout enforces `$D7B5` as the exclusive
ceiling, and the generic spill allocator now also defaults to that boundary. The
old `$E000` ceiling exists only as an explicitly named legacy diagnostic constant.

Two additional NOV2 ABI defects were found during the entropy investigation. The
entropy scanner used X internally without restoring the caller's X, and both the
scanner and frontend borrowed zero-page `$74` as a temporary category byte. `$74`
is live native engine state. The runtime now preserves X across scanner calls and
keeps category state on the 6502 stack. Focused tests freeze the generated
scanner/frontend/category binaries and forbid entropy scanner/frontend accesses
through `$74`.

Those fixes were necessary but did not explain the remaining R5 blank screen.
Deterministic MesenCE execution reproduced the first visible failure immediately
after leaving the title: the menu box appeared but its `Start` label was blank.
The failing scanner began at NOV4 `$A285`, before TT1A or TT1B gameplay.

The underlying architectural defect was partial codec migration. NOV2's decoder
at `$815E` had been replaced globally with the entropy frontend, but the entropy
builder had not converted every stream that could reach it. NOV4's title/menu
text and TT1A's special selector table were still native packed text. Both byte
formats are valid independently, so source-level helpers and offline codec
round-trip tests all passed while the complete ROM remained internally
inconsistent.

Native records and entropy records also have incompatible framing. Native
`pack_records()` byte-aligns after every control-5 separator. Entropy records are
bit-contiguous inside an independently addressed stream and pad only at the end.
Feeding native-aligned bytes to the entropy trie therefore changes both token
interpretation and the next-record cursor. In the reproduced R5 failure, this
quickly produced bogus dictionary references and runaway expansion instead of a
clean `Start` terminator.

## Entropy-only decoder contract

The repair intentionally does not add a hybrid runtime decoder. Address-based
format guesses are unsafe because different overlays reuse the same PRG-RAM
address range. A new zero-page mode flag would add save/restore state across
nested dictionary expansion, and previously proposed `$7F7A` scratch storage is
actually executable NOV2 code.

Instead, the builder now enforces one format contract:

> Every packed-text stream that can reach the entropy-patched NOV2 decoder is
> entropy encoded before the image is emitted.

The normal scenario builder already owns scenario groups, dictionaries, and the
11 large page-indexed menu tables. `entropy_fixed_ui.py` now owns the two
previously omitted surfaces:

- NOV4: 26 menu records, seven internal text records, and a four-entry local
  dictionary. The packed streams occupy 97/134, 47/60, and 19/28 bytes of their
  existing reservations respectively.
- TT1A: all 19 blood-type/month/confirmation records are packed as one continuous
  60-byte entropy stream inside the original 80-byte table allocation.

Padding is allowed only after the last record of each independently addressed
stream. In particular, TT1A may not preserve the old per-record byte slots:
doing so would insert zero padding between records that the bit-contiguous
entropy scanner would interpret as real prefix bits.

The NOV4 entropy conversion runs after the size-neutral font patch and before
title expansion. The font patch deliberately retains its strict whole-bank source
hash guard; changing the order would force that guard to accept arbitrary new
intermediates. The title builder uses narrower recovered-region guards and can
safely run after the fixed-text conversion.

The entropy manifest reports `decoder_format: entropy-only` plus the fixed-stream
coverage/capacity inventory. The runtime smoke suite includes exact binary and
semantic oracles for these surfaces, including NOV4 menu record 3 = `Start` and
the full contiguous 19-record TT1A stream.

## Direct entropy installation

Entropy no longer stages the discarded Adaptive255 runtime before overwriting it.
The direct NOV2 path is:

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
increment/decrement patches. Those are explicit entropy prerequisites rather than
an implicit dependency on `patch_nov2(..., adaptive_dictionary=True)`.

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
