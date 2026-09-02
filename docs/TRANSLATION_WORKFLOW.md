# Translation workflow

This is the maintained path from Japanese source evidence to a reviewable English
candidate. Scenario English has one authority: `work/translations/*.json`.

## 1. Provide private source images

Place legally obtained clean Japanese images in the private overlay:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

Validate and extract them without committing the retail data:

```powershell
time-twist manifest work/baseline/time_twist_zenpen_japan.fds --output work/manifests/zenpen.json
time-twist manifest work/baseline/time_twist_kouhen_japan.fds --output work/manifests/kouhen.json
time-twist roundtrip work/baseline/time_twist_zenpen_japan.fds work/build/zenpen_roundtrip.fds
time-twist roundtrip work/baseline/time_twist_kouhen_japan.fds work/build/kouhen_roundtrip.fds
time-twist extract work/baseline/time_twist_zenpen_japan.fds work/extracted_zenpen
time-twist extract work/baseline/time_twist_kouhen_japan.fds work/extracted_kouhen
```

See [Private fixtures](PRIVATE_FIXTURES.md) for the complete overlay policy.

## 2. Refresh decoded source records only when source evidence changes

`scenario-extract` writes Japanese/source-structure records. It deliberately does
not carry English forward from an older output. Example:

```powershell
time-twist scenario-extract `
  work/extracted_zenpen/side1_01_TT1A_A200.bin `
  work/source_records/TT1A.json
```

The checked-in source record contains stable IDs, exact decoded Japanese, and raw
symbol metadata. It is not a translation file.

## 3. Edit the authoritative English map

Edit the matching ID-keyed map directly:

```text
work/translations/TT1A.json
```

Preserve source control-event order, supported characters, character voice,
terminology, and renderer limits. The shared validators enforce the technical
contracts; translation review still requires reading the Japanese and gameplay
context.

## 4. Optionally generate a merged review document

`scenario-merge` is a validator/review utility. It requires a separate output so
it cannot silently turn a checked-in source record into a second English source:

```powershell
time-twist scenario-merge `
  work/source_records/TT1A.json `
  work/translations/TT1A.json `
  --output work/build/TT1A_review.json
```

Do not commit merged review JSON as a translation authority.

For a quick bank-capacity diagnostic with private source bytes:

```powershell
time-twist scenario-footprint `
  work/extracted_zenpen/side1_01_TT1A_A200.bin `
  --translations work/translations/TT1A.json
```

## 5. Regenerate public review artifacts

```powershell
python work/generate_bilingual_comparison.py
python work/generate_translation_workbook.py
python work/run_tests.py unit
```

CI uses the fixture-free comparison generator and requires checked-in generated
review artifacts to match their sources. `work/translation_workbook_banks/` holds
per-bank review checkpoints; `outputs/Time_Twist_translation_progress.md` is the
canonical aggregate progress report.

## 6. Build one canonical candidate

There is no separate maintained scenario/UI construction path. The release builder
encodes dialogue, shared menus, fixed UI, font, title, and container changes under
one source lock:

```powershell
time-twist release-lock
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
```

Use `release-lock` without `--update` first to inspect drift. Refresh the lock only
for reviewed intentional source changes.

Audit full-word fixed-menu output:

```powershell
python work/tools/audit_fixed_menu_labels.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --output-csv build/candidate/fixed_menu_label_audit.csv
```

The expected canonical inventory is 721 full-word labels with zero blocked or
failed entries.

## 7. Run private integration tests and playtest

With the complete legal private overlay:

```powershell
python work/run_tests.py integration
python work/run_tests.py all
```

Then play the exact candidate named by its manifest. Focus on disk transitions,
save/load, long lines, menus, page clearing, title behavior, and the records still
flagged for gameplay/visual verification in the generated progress report.

## 8. Promote only the reviewed candidate

```powershell
time-twist release-promote build/candidate/release_manifest.json `
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Promotion independently rebuilds and verifies the candidate before establishing a
strict release target. Never edit generated ROMs, merged review JSON, workbooks, or
archived documents as a substitute for changing the authoritative source.
