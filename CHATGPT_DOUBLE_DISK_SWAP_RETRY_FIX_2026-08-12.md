# Time Twist double disk-swap retry fix build notes — 2026-08-12

## Summary

Mesen save states from the double disk-swap path showed that the normal prompt remained correct before the swap, but after swapping twice back to the original/wrong side the retry screen displayed a corrupted first line followed by the correct `Try again.` line.

The corrupted first line matched the byte-aligned NOV2 record at file offset `$269A` in the previous candidate. Earlier code treated this record as bit-aligned, leaving the high three source bits in place. Runtime evidence shows the visible renderer starts at byte `$269A`, so the full eight-byte record must be replaced.

## Source change

Updated `work/time_twist/ui.py`:

- Replaced the old bit-range `Bad Disk` patch for `$269A` with a byte-aligned, source-guarded eight-byte patch.
- The new visible heading is `Wrong side.`.
- The shared retry record at `$26DE` remains `{CTRL:0}Try again.`.
- The normal disk prompt records remain unchanged:
  - `Part 1`
  - `Side A` / `Side B`
  - `Insert now.`

Updated tests:

- `work/tests/test_ui_unit.py`
- `work/integration_tests/test_ui.py`

## New candidate SHA-256

```text
Four-side: 981DACF834E12FA8830479C9CF2D3E9CEB1C1A676EC06CA879A22605C3BC10FE
Zenpen:    DB0103AE074844D226F33CED8B047AE0D5F776A07AB8FE7FF9CC727DBB79F2AF
Kouhen:    E8B4F40ECC021BB3C31A896C899C1BCA4A88831B17A3A20A26C8DCC316F15368
```

Kouhen is unchanged.

## Validation

Passed:

```bash
PYTHONPATH=work python3 -m compileall -q work/time_twist work/tests/test_ui_unit.py work/integration_tests/test_ui.py work/tools
PYTHONPATH=work python3 -m unittest work.tests.test_ui_unit -v
PYTHONPATH=work python3 -m unittest work.tests.test_title_unit work.tests.test_ui_unit -v
PYTHONPATH=work python3 -m time_twist.cli release-build --project-root . --candidate --output-dir /mnt/data/tt_disk_swap_fix_release
PYTHONPATH=work python3 work/tools/audit_fixed_menu_labels.py --candidate-fds ... --targets-csv docs/full_word_menu_targets_all_records.csv --output-csv ...
PYTHONPATH=work python3 work/tools/check_public_tree.py
```

Menu audit result:

```text
audited 721 fixed labels; full-word=374; blocked=347; failures=0
```

`python work/run_tests.py unit` was attempted and still fails in this source-only environment for the known reasons: missing `hypothesis` and missing generated comparison/workbook outputs.

## Runtime proof still needed

The fix is grounded in the supplied Mesen save states and candidate record decoding, but the new candidate still needs one runtime confirmation in Mesen:

1. Start from the normal side-change prompt.
2. Swap disks twice back to the original/wrong side.
3. Confirm the retry screen now displays exactly:

```text
Wrong side.
Try again.
```
