# Full-word menu repacking pass — 2026-08-12

## Purpose

This pass follows the retry-readability build and tries to fit more full English menu/choice labels without changing the native dictionary format, moving fixed tables, or weakening source guards.

The working rule remains: prefer full readable labels, and only leave an abbreviation when the current fixed-slot/dictionary layout cannot fit the target safely.

## What changed

`work/time_twist/project.py` now reserves additional bank-specific dictionary entries for fixed-address menu labels. The entries were selected only when a fresh candidate build still preserved the original memory footprints.

This is deliberately conservative. It does **not** change the game's 31-entry dictionary/token format and does **not** relocate fixed text tables.

## Candidate audit result

Compared with the previous retry-readability candidate:

| Metric | Previous | This pass |
|---|---:|---:|
| Fixed menu/choice records audited | 721 | 721 |
| Full-word labels | 374 | 405 |
| Blocked fallback labels | 347 | 316 |
| Newly full labels | — | 31 |
| Regressions | — | 0 |
| Label mismatches | 0 | 0 |

Breakdown for this pass:

- Full labels rendered literally: 257
- Full labels rendered through dictionary entries: 148
- Remaining blocked fallback labels: 316
- Mismatches: 0

## Newly fitted labels

See:

```text
/docs/full_word_menu_repack_newly_full_labels.csv
```

The new wins are concentrated in banks with enough remaining compression headroom:

- TT6A: 11 newly full labels
- T25: 8 newly full labels
- TT2: 3 newly full labels
- TT6B: 3 newly full labels
- TT3A: 2 newly full labels
- TT3B: 2 newly full labels
- T22: 2 newly full labels

## Remaining blockers

See:

```text
/docs/full_word_menu_repack_remaining_blockers.csv
```

The remaining blockers are not hidden. They are explicit fixed-slot/dictionary/capacity blockers. In broad terms, they need one of the following:

1. more scenario compression savings in the same bank,
2. a safe relocation/repointing of fixed records or tables,
3. a verified layout change, or
4. a human decision that a compact label is actually correct for that screen.

## Why this does not finish every label

Every fixed UI bank still has only 31 dictionary entries. Many labels are stored in records of only two to six packed bytes. A full label can often fit only if a dictionary entry is available for it, but those same dictionary entries are also needed to keep the scenario script inside the bank's original RAM footprint.

A more aggressive dictionary reservation set was tested separately and could make more labels encodable, but it exceeded bank footprints by tens to hundreds of bytes in several banks. Those are real compression/layout blockers, not just untried replacements.

## Candidate build

A fresh candidate build succeeded from the original Japanese FDS inputs.

```text
Four-side SHA-256: B544EC34D4A8766216869ECA436A8FD8EB0157AC44C324EB800FE260D0136FE0
Zenpen SHA-256:    8E05E6CCF1C7554DEF724D4832EA55BBB6F8652F2A019BBFB69D5A517347456F
Kouhen SHA-256:    FBEE6321B8044E163001E6F95E84EDCF3A976BC6A5019501DF771E6661F6200E
```

## Validation

Passed:

```bash
PYTHONPATH=work python3 -m time_twist.cli release-build --project-root . --candidate --output-dir /mnt/data/tt_full_menu_repack_safe_release
PYTHONPATH=work python3 work/tools/audit_fixed_menu_labels.py --candidate-fds /mnt/data/tt_full_menu_repack_safe_release/Time\ Twist\ -\ reproducible\ English\ four-side\ playtest.fds --targets-csv docs/full_word_menu_targets_all_records.csv --output-csv /mnt/data/tt_full_menu_repack_candidate_audit.csv
PYTHONPATH=work python3 -m unittest work.tests.test_title_unit work.tests.test_ui_unit -v
python3 -m compileall -q work/time_twist work/tests/test_title_unit.py work/tests/test_ui_unit.py work/tools
```

`python work/run_tests.py unit` is still not fully runnable in this handoff environment because `hypothesis` is unavailable and generated comparison/workbook outputs are absent.

## Next safe route

The next pass should not add visual squeeze glyphs. For the remaining labels, use one of these approaches:

1. produce additional scenario compression savings first,
2. identify fixed tables whose record references can be safely repointed,
3. relocate only those records/tables with source guards and candidate-FDS decode tests,
4. keep the full-word target CSV as the desired player-facing state.
