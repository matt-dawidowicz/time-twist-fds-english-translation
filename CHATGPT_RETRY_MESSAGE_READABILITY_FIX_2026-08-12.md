# ChatGPT retry-message readability fix — 2026-08-12

## Runtime finding

Mesen playtest showed that the double disk-swap retry path no longer rendered
gibberish, but the first line looked visibly cramped:

```text
Wrong side
Try again.
```

The cramped letters came from the private `de.` ligature used to force exact
`Wrong side.` wording into NOV2's eight-byte `$269A` retry-heading slot.

## Fix

For the size-locked eight-byte retry heading, use the fully readable ordinary
packed text:

```text
Bad side.
Try again.
```

This keeps the retry meaning clear, uses only normal glyphs, and remains exactly
size-neutral. The ten-byte disk-number path still uses ordinary packed
`Wrong side.` where the binary layout has enough room.

## Source impact

Changed:

- `work/time_twist/ui.py`
- `work/tests/test_ui_unit.py`
- `work/integration_tests/test_ui.py`

No ROM/FDS images are included in this source archive.

## Validation

Targeted validation passed:

```bash
PYTHONPATH=work python3 -m unittest work.tests.test_title_unit work.tests.test_ui_unit -v
python3 -m compileall -q work/time_twist work/tests/test_title_unit.py work/tests/test_ui_unit.py work/tools
PYTHONPATH=work python3 -m time_twist.cli release-build --project-root . --candidate --output-dir /mnt/data/tt_retry_readable_release
PYTHONPATH=work python3 work/tools/audit_fixed_menu_labels.py --candidate-fds /mnt/data/tt_retry_readable_release/Time\ Twist\ -\ reproducible\ English\ four-side\ playtest.fds --targets-csv docs/full_word_menu_targets_all_records.csv --output-csv /mnt/data/tt_retry_readable_fixed_menu_label_audit.csv
PYTHONPATH=work python3 work/tools/check_public_tree.py
```

Results:

```text
27 targeted title/UI tests passed
Candidate build succeeded
721 fixed labels audited; failures=0
public source tree check: PASS
```

`PYTHONPATH=work python3 work/run_tests.py unit` was attempted but still fails in
this source-only environment because `hypothesis` is unavailable and generated
comparison/workbook outputs are not present.
