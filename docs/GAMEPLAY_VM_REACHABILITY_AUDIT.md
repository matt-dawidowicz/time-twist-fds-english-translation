# Gameplay VM reachability-island audit

This note closes the address-level follow-up to the historical
`23,902 / 24,229 = 98.6504%` gameplay-script reachability result.

## Executive result

The historical completion pass recorded **327 non-reached source bytes**, but
the implementation that produced the address set was not committed.  The
maintained `audit_retail_vm_semantics.py` preserved only the aggregate counts.

Reconstructing the graph against the current composed retail-equivalent script
layout exposed one missing piece of native state propagation:

1. `B9` saves VM continuation state and copies its operand into `$BA`;
2. NOV2 `$768F` uses `$BA` as a **one-based hotspot-group selector** into
   the table at `$A20C`;
3. the selected group's rectangle count is copied to `$91`;
4. the successful rectangle index is maintained in `$A7`;
5. the `30/31` result dispatcher at `$6BFD` consumes `$91/$A7`.

Thus `$91/$A7` are not exclusively menu state.  Exploration can feed the
same result-dispatch machinery.

Applying that recovered contract as a conservative **may-reach** analysis to
normal hotspot rectangles explains **163 bytes** that belonged to the legacy
327-byte remainder.  It does not require a new opcode family, an arbitrary
script-PC write, or speculative decoding.

The remaining conservative set is therefore:

- **164 bytes**;
- **50 contiguous islands**;
- all valid `$A220` route labels are already seeded;
- no additional direct native writer of `$C5/$C6` enters these bytes.

This does **not** replace runtime certification.  A normal hotspot rectangle is
treated as potentially selectable when its geometry is structurally valid; the
analysis does not claim that every such rectangle was exercised in a clean
playthrough.

## Why the historical 327-byte set cannot be treated as an archived oracle

PR #57 and the historical VM-completion note preserve the aggregate:

- 7,283 route-seeded command starts;
- 23,902 covered bytes;
- 24,229 total bytes;
- 327 non-reached bytes.

However, neither the PR source tree nor its CI production-source artifact
contains the address-level worklist/CFG program that generated those numbers.
The maintained source audit later copied the totals as constants.

Accordingly, the address list below is a **reconstruction from the composed
script bytes and recovered native semantics**, not a claim that an unavailable
historical scratch file was recovered byte-for-byte.

The reconstructed legacy-consistent 327-byte remainder is useful as the
comparison surface for the new native-state result because the 164-byte
residual is a strict subset of it and the 163-byte difference is entirely
accounted for by `B9 -> $BA -> hotspot group -> $91/$A7 -> 30/31` paths.

## Newly explained 163 bytes

These ranges were in the legacy-consistent remainder but become structurally
reachable once hotspot result state is propagated:

| Scene | Program | Range | Bytes |
| ---: | --- | --- | ---: |
| 2 | TT1B | `$A538-$A541` | 10 |
| 2 | TT1B | `$A553-$A55E` | 12 |
| 2 | TT1B | `$A5B9-$A5E2` | 42 |
| 3 | TT2 | `$A5D6-$A5DE` | 9 |
| 3 | TT2 | `$A5EB-$A5F0` | 6 |
| 4 | TT2 + T22 | `$A6E1-$A6E9` | 9 |
| 4 | TT2 + T22 | `$A6FA-$A706` | 13 |
| 4 | TT2 + T22 | `$A754` | 1 |
| 4 | TT2 + T22 | `$A762-$A769` | 8 |
| 4 | TT2 + T22 | `$A78C-$A78D` | 2 |
| 4 | TT2 + T22 | `$A79B-$A7AD` | 19 |
| 4 | TT2 + T22 | `$A7FD-$A803` | 7 |
| 4 | TT2 + T22 | `$A82F-$A835` | 7 |
| 4 | TT2 + T22 | `$A87F-$A888` | 10 |
| 5 | TT3A | `$A69F` | 1 |
| 7 | TT4 | `$AA6A-$AA6F` | 6 |
| 12 | TT6B | `$A73E` | 1 |

Total: **163 bytes**.

Several of the large old "islands" are therefore not dead code at all.  They
are target tables and handlers whose incoming selector state originates in
exploration rather than a preceding menu descriptor.

## Remaining 164 bytes

### A. Conditional no-result / fallthrough stubs - 90 bytes

These are valid VM instructions immediately following `30/31` result tables
or equivalent result-dispatch paths.  Native `$6BFD` has an `$A4=$FF`
skip/fallthrough path, but the audit has not proved a retail runtime condition
that produces that no-result state at each listed call site.  They are
therefore **potentially live**, not declared dead.

| Scene | Program | Range | Bytes |
| ---: | --- | --- | ---: |
| 2 | TT1B | `$A542-$A543` | 2 |
| 2 | TT1B | `$A55F-$A560` | 2 |
| 3 | TT2 | `$A4E6-$A4E7` | 2 |
| 3 | TT2 | `$A4F3-$A4F4` | 2 |
| 3 | TT2 | `$A519-$A51A` | 2 |
| 3 | TT2 | `$A6AA-$A6AB` | 2 |
| 3 | TT2 | `$A6C2-$A6C3` | 2 |
| 3 | TT2 | `$A798-$A799` | 2 |
| 3 | TT2 | `$A7B4-$A7B5` | 2 |
| 3 | TT2 | `$A7D8-$A7D9` | 2 |
| 3 | TT2 | `$A862-$A863` | 2 |
| 3 | TT2 | `$A880-$A881` | 2 |
| 3 | TT2 | `$A89F-$A8A0` | 2 |
| 3 | TT2 | `$A927-$A928` | 2 |
| 3 | TT2 | `$A93C-$A93D` | 2 |
| 3 | TT2 | `$AA35-$AA36` | 2 |
| 3 | TT2 | `$AA70-$AA71` | 2 |
| 3 | TT2 | `$AA9C-$AA9D` | 2 |
| 3 | TT2 | `$AB8A-$AB8B` | 2 |
| 3 | TT2 | `$ABB9-$ABBA` | 2 |
| 3 | TT2 | `$AD45-$AD46` | 2 |
| 4 | TT2 + T22 | `$A56F-$A570` | 2 |
| 4 | TT2 + T22 | `$A733-$A734` | 2 |
| 4 | TT2 + T22 | `$A755-$A759` | 5 |
| 4 | TT2 + T22 | `$A78E-$A792` | 5 |
| 4 | TT2 + T22 | `$A7DA-$A7DB` | 2 |
| 7 | TT4 | `$A370-$A371` | 2 |
| 7 | TT4 | `$A4F4-$A4F5` | 2 |
| 7 | TT4 | `$A5ED-$A5EE` | 2 |
| 7 | TT4 | `$A686-$A687` | 2 |
| 7 | TT4 | `$A763-$A764` | 2 |
| 7 | TT4 | `$A817-$A818` | 2 |
| 7 | TT4 | `$A880-$A881` | 2 |
| 7 | TT4 | `$A95A-$A95B` | 2 |
| 7 | TT4 | `$A988-$A989` | 2 |
| 7 | TT4 | `$AA70-$AA74` | 5 |
| 7 | TT4 | `$AE00-$AE01` | 2 |
| 7 | TT4 | `$AE7F-$AE80` | 2 |
| 10 | TT5 + T25 | `$A37E-$A37F` | 2 |
| 10 | TT5 + T25 | `$A424-$A425` | 2 |
| 10 | TT5 + T25 | `$A79F` | 1 |

### B. Bytecode-shaped orphan helper blocks - 61 bytes

These ranges decode cleanly as ordinary source-language commands or small
subroutines, but no current route label, call, branch, scene entry, saved
continuation, or hotspot-result edge enters them.  They are best classified as
**orphan/unused retail bytecode until a runtime predecessor is demonstrated**.

| Scene | Program | Range | Bytes | Shape |
| ---: | --- | --- | ---: | --- |
| 5 | TT3A | `$A2DB-$A2E4` | 10 | two pulse-SFX + delay + return helpers |
| 5 | TT3A | `$A2EA-$A2EE` | 5 | music + delay + return helper |
| 6 | TT3A + TT3B | `$A2F7-$A2FB` | 5 | pulse-SFX + delay + return helper |
| 9 | TT5 | `$A7EB-$A80D` | 35 | complete flag/audio/text/scene-control block |
| 9 | TT5 | `$A836-$A837` | 2 | relative jump |
| 10 | TT5 + T25 | `$A8FF-$A902` | 4 | absolute call followed by current-route jump |

### C. Embedded data / padding - 13 bytes

These bytes do not form a complete source-used VM path under the recovered
grammar and are skipped by surrounding control flow.

| Scene | Program | Range | Bytes | Evidence |
| ---: | --- | --- | ---: | --- |
| 1 | TT1B + TT1A | `$A2FE-$A304` | 7 | skipped by `50 $A305`; begins with source-unused `0A` bytes |
| 10 | TT5 + T25 | `$A8E7-$A8EB` | 5 | begins with source-unused `24`; lies between recovered predicate path and next command |
| 13 | TT6C | `$A978` | 1 | single pad byte immediately before route label `$A979` |

Totals:

```text
conditional/no-result stubs   90
orphan bytecode helpers       61
embedded data/padding         13
                              ---
remaining                    164
```

## Script-PC incoming-edge audit

The active gameplay PC is `$C5/$C6`.  Static native-code inspection accounts
for its writers as follows:

- `$695D` scene initialization from `$A222`;
- `$6Cxx` predicate/result branches;
- `$6Dxx-$6Fxx` absolute/relative jumps, calls, returns, and `$A220` route
  dispatch;
- `$79xx-$7Bxx` FDS/scene-transition state;
- `$7E4C/$7E6F` restore of saved continuation from `$9B/$9C`;
- `$95E5` and `$9Cxx` native PC-advance helpers.

No exploration/hotspot routine writes an arbitrary script address directly.
Instead, exploration supplies `$91/$A7` selector state and later returns
through the normal VM result dispatcher.  This closes the suspected
"hidden PC writer" avenue.

Saved continuation likewise does not create a hidden source entry: the restore
paths reload the PC previously saved by resumable menu/exploration commands.

## Status of the old 98.6504% figure

Keep **98.6504%** when referring specifically to the historical, deliberately
conservative route-seeded baseline.

For current reverse engineering, the more informative figures are:

```text
script bytes                                  24,229
historical conservative covered bytes         23,902
historical remainder                             327

bytes explained by recovered hotspot state       163
residual conservative islands                     164

structural may-reach coverage                   24,065 / 24,229
structural may-reach percentage                 99.3231%
```

The 99.3231% figure is a **structural may-reach** result, not a clean-playthrough
coverage claim.  It must not be promoted to runtime-certified reachability
until the relevant hotspot selections have been exercised or otherwise proved
possible under full scene state.

## What remains to prove

The 327-byte question is therefore substantially closed:

- there is no evidence of a second bytecode format;
- no hidden arbitrary PC writer was found;
- 163 bytes have a concrete missing-state explanation;
- 13 residual bytes are data/padding;
- 61 bytes are bytecode-shaped orphan helpers with no incoming edge;
- 90 bytes are conditional result fallthroughs whose exact retail activation
  conditions remain the only meaningful control-flow uncertainty.

Future clean replay tracing should concentrate on those **90 conditional
fallthrough bytes** and the **61 orphan-helper bytes**, rather than treating all
327 bytes as one undifferentiated unknown region.
