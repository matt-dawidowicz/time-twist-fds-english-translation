# Full-word menu deep pass phase 1 — 2026-08-12

## Purpose

This pass starts the post-repacking work for fitting more fixed menu/choice labels as full English words.

The rules for this phase were deliberately conservative:

- do not change the 31-entry dictionary/token format;
- do not relocate fixed tables yet;
- do not use visual squeeze glyphs;
- preserve the already runtime-proven title-transition and disk-retry fixes;
- prefer bank-specific dictionary reuse only when a fresh candidate build still preserves the original memory footprint.

## Method

The phase started from the full-word menu repacking candidate and then tested the next least-invasive route: adding single bank-specific required dictionary entries for blocked labels.

Two additions were proven safe:

```text
T22:  Woman
TT6C: Look
```

Both labels are now represented through dictionary tokens in the fixed menu tables.

A broader compressor search was also tested by evaluating every positive-saving candidate instead of the normal candidate limit. It produced identical output, so the remaining blockers are not caused by the compressor's candidate-search cap.

## Candidate audit result

```text
Fixed menu/choice records audited: 721
Full-word labels before this pass: 405
Full-word labels after this pass:  407
Newly full labels:                  2
Remaining blocked labels:          314
Label mismatches:                    0
```

The newly fitted labels are listed in:

```text
docs/full_word_menu_deep_phase1_newly_full_labels.csv
```

The remaining blockers are listed in:

```text
docs/full_word_menu_deep_phase1_remaining_blockers.csv
```

## Newly fitted labels

| Bank | Index | Previous visible label | New full label |
|---|---:|---|---|
| T22 | 7 | `WMN` | `Woman` |
| TT6C | 0 | `SE` | `Look` |

## Build outputs

Fresh candidate build from the original Japanese FDS inputs:

```text
Four-side SHA-256: 4EBA6C4A5DAFE56FA24F75033E373087CEF15C638C94FF6B91B51A9C018AF9DB
Zenpen SHA-256:    AEBAAC5DCBC19E33FE0B3DEA992757627D0B87E62C66486ACEB4623AD950123E
Kouhen SHA-256:    F412FED1B43C6ECBEED972056F6923E5E2C0D5CC379218AAEDB78497C87A558B
```

## Validation

Passed:

```bash
PYTHONPATH=work python3 -m time_twist.cli release-build --project-root . --candidate --output-dir /mnt/data/tt_deep_menu_phase1
PYTHONPATH=work python3 work/tools/audit_fixed_menu_labels.py --candidate-fds /mnt/data/tt_deep_menu_phase1/Time\ Twist\ -\ reproducible\ English\ four-side\ playtest.fds --targets-csv docs/full_word_menu_targets_all_records.csv --output-csv /mnt/data/tt_deep_menu_phase1_audit.csv
PYTHONPATH=work python3 work/tools/report_full_word_menu_candidate.py --audit-csv /mnt/data/tt_deep_menu_phase1_audit.csv --manifest-json /mnt/data/tt_deep_menu_phase1/release_manifest.json --output-dir /mnt/data/tt_deep_menu_phase1_reports
PYTHONPATH=work python3 -m unittest work.tests.test_title_unit work.tests.test_ui_unit -v
python3 -m compileall -q work/time_twist work/tests/test_title_unit.py work/tests/test_ui_unit.py work/tools
```

Targeted tests passed: 27 title/UI tests.

## Why only two labels changed

Most remaining labels fail as soon as an extra dictionary reservation is forced. The common failure mode is a preserved-RAM-footprint overrun, usually by a few bytes to a few dozen bytes. That means the next gains need one of the following:

1. scenario text compression savings in the same bank;
2. safe fixed-record/table relocation;
3. verified layout changes;
4. human/context review for labels where the full-word target may be wrong.

## Next route

The next phase should focus on the largest blocker banks:

```text
TT5    68 blockers
TT6C   61 blockers
TT4    52 blockers
TT3A   46 blockers
TT2    32 blockers
TT6B   28 blockers
```

For each bank, measure the byte overrun for each desired full label, then either find scenario-copy savings or prove whether the fixed record can be safely relocated/repointed.
