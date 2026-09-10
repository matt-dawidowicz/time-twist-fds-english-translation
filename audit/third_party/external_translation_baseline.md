# External translation baseline

This completed audit records the comparison against the input hashes below.
Its wording-match counts describe those reviewed inputs. The external patch
served as a diagnostic comparison target; Japanese remained the translation
authority, and external script text is not stored here. Current English comes
from `work/translations/*.json` and the fixed-UI code.

## Input identity

| Role | Size | SHA-256 |
| --- | ---: | --- |
| Japanese Kouhen | 131000 | `f62a7424fe489cbe479c3ebaabe4ce62d85127601ffd3d08abd4e5a0dc39442a` |
| Japanese Zenpen | 131000 | `b9424dd29ee195a9fa9ac4f844f058c380e30f7aca741218789fa8611f741916` |
| Reviewed English Kouhen | 131000 | `cb66e4fd8c64cf4e1e9c68e34a4d4ddbeb263f8414a9d86d2e77325a82e266c5` |
| Reviewed English Zenpen | 131000 | `3e82bcd2fdf1e4aff67ff90d97a03554ccf06a794a8f854c482dd86470f52e89` |
| External English Kouhen input | 250706 | `df9bd6d6c8fc4fb1b12531dd0ce628126215d0091df980a12c183f10b644a9f2` |
| External English Zenpen input | 250706 | `027ca6a4945c0bcb3c934750947f3a95b6b2a3188ca7fce348ba0f4f5e05ce78` |

The Japanese and reviewed English inputs are normal 131000-byte raw two-side FDS
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

TT3A contributes 17 candidates to that conservative queue. All 17 were
adjudicated against the original Japanese, and the review then continued through
every remaining record. **All 152 TT3A scenario records have now been reread
against Japanese.** Nine source-grounded revisions survived that full pass;
differences that were merely alternate but faithful wording were left unchanged.

## Fixed-UI baseline

The external fixed-UI comparison now covers all eleven major scenario-bank tables
plus TT1A's blood-type, month, and confirmation selectors. Because the external
patch relocates many tables in roughly 32-record pages, the comparison tool
reconstructs physical segments into source-record order without relaxing the
production parser.

| Scope | Records | Exact English | Different English | Unresolved |
| --- | ---: | ---: | ---: | ---: |
| Major scenario-bank fixed tables | 721 | 375 | 346 | 0 |
| TT1A selectors | 19 | 18 | 1 | 0 |
| **Total** | **740** | **393** | **347** | **0** |

The detailed per-bank segment map is stored in
[external_fixed_ui_baseline.json](external_fixed_ui_baseline.json). Differences remain diagnostic
only and must be resolved from Japanese and gameplay context.

The pass reviewed **740/740 fixed-UI records** against Japanese and gameplay
context. Confirmed corrections are recorded in the
[source-review change ledger](../../work/audits/translation_quality_changes.json).
Current releases use the
[full-word menu implementation](../../docs/FULL_WORD_MENU_IMPLEMENTATION.md).

That comparison also exposed six NOV2 save/system records that had never been
translated in the current runtime image. They are now source-verified, translated
in place with zero byte growth, covered by source-drift regression tests, and
represented in the canonical review corpus. The external NOV2 layout is repacked,
so those six records are not yet included in the 740 external-alignment count.

## Source-review findings

The TT3A review has already found several concrete compression losses. In
`TT3A/g0/r14`, the Japanese identifies a POW camp in southern Germany and gives
Cougar's U.S. air-force lieutenant rank; both details are now restored.
`TT3A/g1/r21` now preserves the route west from the woods to the park, Rebecca's
role as the instruction contact/code name, and the distinct password.

A second small batch restored three more source details without changing the
existing presentation-control sequences. `TT3A/g0/r11` once again reports that
an escapee was *found*. `TT3A/g1/r26` names America and Germany as the competing
powers and preserves the source's secret-weapon-to-atomic-bomb reveal.
`TT3A/g3/r4` now states that Simon was confined and forced to develop a secret
weapon before refusing to help the Nazis kill further.

Two further Japanese-only checks exposed subtler losses. `TT3A/g3/r20` now uses
escape-network terminology for `とうぼうそしき` instead of broadening it to the
Resistance, and restores the source's reported-information nuance. In
`TT3A/g0/r28`, Hitler's oath now retains `おきて` (law/code/rule) and the
pointed-stakes image rather than flattening the ritual phrase to "human fat and
stakes."

The final full-bank sweep found two further improvements that the heuristic queue
had not required. `TT3A/g2/r0` now gives Ralph's clothing instruction in natural
English while preserving the post-escape timing and dirt warning. `TT3A/g3/r18`
now directly renders the source statement that the object is hard to see because
it is underwater.

The same review has rejected many false positives. For example,
`TT3A/g0/r15`, `TT3A/g0/r30`, `TT3A/g0/r31`, `TT3A/g1/r25`, and several short
sound/action lines are materially faithful to the Japanese despite wording or
length differences from the external translation. Comparison differences are
therefore never automatic replacement candidates.

## System-text coverage and current validation

The [fixed-UI evidence](external_fixed_ui_baseline.json) also records recovered
locations for 15 external NOV2 records and NOV4's Start and Load records. Two
source disk-error records remained Japanese in the external inputs and were
left unaligned. System records are counted separately from the 740 menu and
selector records.

For current compression measurements, use the
[generated progress report](../../outputs/Time_Twist_translation_progress.md).
Build and runtime acceptance follow the
[maintainer release process](../../docs/MAINTAINER_RELEASE_PROCESS.md) and
[playtest matrix](../../docs/PLAYTEST_MATRIX.md).
