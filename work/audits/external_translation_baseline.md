# External translation baseline

This audit exists to identify places where the current English script deserves
human review. The external patch is a diagnostic comparison target only. It is
not a translation source, and its script text is not stored here. Any wording
change in this repository must be independently justified from the original
Japanese.

## Input identity

| Role | Size | SHA-256 |
| --- | ---: | --- |
| Japanese Kouhen | 131000 | `f62a7424fe489cbe479c3ebaabe4ce62d85127601ffd3d08abd4e5a0dc39442a` |
| Japanese Zenpen | 131000 | `b9424dd29ee195a9fa9ac4f844f058c380e30f7aca741218789fa8611f741916` |
| Current English Kouhen | 131000 | `cb66e4fd8c64cf4e1e9c68e34a4d4ddbeb263f8414a9d86d2e77325a82e266c5` |
| Current English Zenpen | 131000 | `3e82bcd2fdf1e4aff67ff90d97a03554ccf06a794a8f854c482dd86470f52e89` |
| External English Kouhen input | 250706 | `df9bd6d6c8fc4fb1b12531dd0ce628126215d0091df980a12c183f10b644a9f2` |
| External English Zenpen input | 250706 | `027ca6a4945c0bcb3c934750947f3a95b6b2a3188ca7fce348ba0f4f5e05ce78` |

The Japanese and current-English inputs are normal 131000-byte raw two-side FDS
images. Both supplied external inputs contain the same 119706-byte extension.
Structural probing shows that the extension carries later Kouhen FDS data at
absolute offsets expected from a four-side combined image. The comparison tool
therefore models this as an external-patch quirk; the production FDS/scenario
parser remains unchanged.

Using the two independently patched inputs as evidence, the sparse external
payload's write hunks are recoverable by coalescing changed bytes when no more
than five unchanged bytes lie between them. A six-byte gap creates false writes
against bytes whose touched/untouched state can be proven from the two inputs.

## Scenario alignment

Japanese group and record counts are structural truth. The external decoder is
allowed to follow relocated and non-monotonic external group pointers without
relaxing the production parser's invariants.

| Bank | Half | Groups | Records | Exact English | Different English |
| --- | --- | ---: | ---: | ---: | ---: |
| TT3A | Zenpen | 5 | 152 | 10 | 142 |
| TT3B | Zenpen | 2 | 58 | 1 | 57 |
| TT1B | Zenpen | 5 | 137 | 1 | 136 |
| TT1A | Zenpen | 2 | 35 | 2 | 33 |
| TT2 | Zenpen | 6 | 169 | 4 | 165 |
| T22 | Zenpen | 2 | 58 | 6 | 52 |
| TT6C | Kouhen | 4 | 106 | 3 | 103 |
| TT6B | Kouhen | 3 | 94 | 4 | 90 |
| TT6A | Kouhen | 4 | 100 | 5 | 95 |
| TT6D | Kouhen | 1 | 8 | 0 | 8 |
| TT4 | Kouhen | 6 | 183 | 5 | 178 |
| TT5 | Kouhen | 4 | 123 | 4 | 119 |
| T25 | Kouhen | 3 | 76 | 5 | 71 |
| **Total** | | | **1299** | **50** | **1249** |

All 1299 aligned scenario records decode on both English versions with zero
unresolved external-token records. Only 50 are exact wording matches. This does
not imply that the other 1249 are defects; independent translations are expected
to differ.

A deliberately conservative first-pass heuristic marks 406 scenario records for
human review. That is a triage count, **not** a mistranslation count. Each flagged
record still has to be read against its Japanese source before any edit.

## Current editorial findings

The first TT3A review already found a real omission in `TT3A/g0/r14`: the
Japanese identifies the location as a POW camp in southern Germany and gives
Cougar's U.S. air-force lieutenant rank. The old English reduced this to
`PLACE: S. GERMANY` and `U.S. AIR LT.`. The revision restores the omitted POW-camp
context and rank detail while keeping the current presentation-control sequence.

`TT3A/g1/r21` also compressed its route instructions enough to lose useful
information. The Japanese directs Cougar west from the woods until he reaches a
park, then tells him to seek Rebecca's instructions; Rebecca is an escape-network
code name and a separate password follows. The revised English restores those
distinctions without using external-patch prose.

The same review also rejected several false positives. For example,
`TT3A/g0/r15` and `TT3A/g1/r25` are materially faithful to the Japanese despite
wording differences from the external translation. This is why comparison
differences must never be treated as automatic replacement candidates.

## Still pending

- Align and count fixed-UI records so the audit covers more than scenario text.
- Produce the current-English per-bank byte-headroom table and identify the truly
  constrained banks.
- Complete the TT3A source-grounded review, then continue bank by bank.
- Keep generated review artifacts synchronized after source edits.
- Obtain a fully green CI run after the new comparison helper passes all lint,
  docstring, type, unit, build, and wheel-smoke gates.
