# Translation and rebuild workflow

Commands below run from the repository root after:

```powershell
python -m pip install -e .
```

## 1. Supply clean source images

Place legally obtained Japanese images at:

```text
work/baseline/time_twist_zenpen_japan.fds
work/baseline/time_twist_kouhen_japan.fds
```

Keep untouched backups. `time-twist release-lock` verifies the supported
revisions before a release build.

## 2. Validate and extract

```powershell
time-twist manifest work/baseline/time_twist_zenpen_japan.fds `
  --output work/manifests/zenpen.json

time-twist roundtrip work/baseline/time_twist_zenpen_japan.fds `
  work/build/zenpen_roundtrip.fds

time-twist extract work/baseline/time_twist_zenpen_japan.fds `
  work/extracted_zenpen
```

An extracted filename includes side, index, FDS name, and load address, such as
`side1_01_TT1A_A200.bin`. Do not edit a bank in a normal text editor; it also
contains pointers, code, and fixed binary data.

## 3. Extract a scenario document

```powershell
time-twist scenario-extract `
  work/extracted_zenpen/side1_01_TT1A_A200.bin `
  work/translated_scripts/TT1A.json
```

Each record has a stable ID, exact decoded Japanese, an English field, and raw
symbol information. Refreshing an existing document retains English at matching
coordinates.

## 4. Edit the playable map

Authoritative scenario maps are ordinary JSON objects under
`work/translations/`:

```json
{
  "TT1A/g0/r6": "Do you prefer consommé{CTRL:0}to miso soup?"
}
```

Rules:

- keep the exact record ID;
- provide a nonempty string;
- preserve ordered `{CTRL:n}` values;
- use supported English glyphs;
- keep ordinary segments within 24 columns;
- review neighboring records and the workbook context.

The workbook's exact-Japanese field is immutable recovered evidence. Put
probable kanji or expanded interpretation in editorial fields, not the source
field.

## 5. Validate, size, and rebuild one bank

```powershell
time-twist scenario-merge `
  work/translated_scripts/TT1A.json `
  work/translations/TT1A.json `
  --output work/translated_scripts/TT1A_english.json

time-twist scenario-footprint `
  work/extracted_zenpen/side1_01_TT1A_A200.bin `
  --translations work/translations/TT1A.json

time-twist scenario-insert `
  work/extracted_zenpen/side1_01_TT1A_A200.bin `
  work/translated_scripts/TT1A_english.json `
  work/build/TT1A_english_scenario.bin

time-twist ui-patch `
  work/build/TT1A_english_scenario.bin `
  work/build/TT1A_english.bin `
  --component TT1A
```

A complete map gets a new English dictionary. Fixed UI tables may depend on
specific dictionary entries, so apply the bank's UI patch to the matching
rebuilt scenario. A negative footprint remainder is a real failure; do not
write through the fixed tail.

## 6. Shared UI, font, and title work

```powershell
time-twist ui-patch work/NOV2.bin work/NOV2_english.bin --component NOV2
time-twist ui-patch work/NOV4.bin work/NOV4_ui.bin --component NOV4
time-twist font-patch work/NOV4_ui.bin work/NOV4_font_ui.bin
time-twist title-patch `
  work/NOV4_font_ui.bin `
  "work/title_assets/Time Twist full-screen logo reference.png" `
  work/NOV4_english_title.bin `
  --subtitle "On the Outskirts of History..."
```

The title step deliberately relocates data and should be last. Do not reapply a
patch to its own output; source guards expect the known pre-patch bytes.

These low-level commands are useful for diagnosis. The authoritative complete
composition path is `release-build`.

## 7. Regenerate review artifacts

```powershell
python work/generate_bilingual_comparison.py
python work/generate_translation_workbook.py
python work/run_tests.py unit
```

The workbook's patch-safe scenario text must equal the playable maps exactly.
Natural translations may remain more expansive for editorial review.

## 8. Create and review a candidate

After an intentional playable change:

```powershell
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
```

The candidate manifest records every scenario-bank capacity/hash and all final
output hashes. Candidate mode is not approval. Inspect the diff and playtest the
exact files in `build/candidate`.

Maintainers with the private fixture overlay should also run:

```powershell
python work/run_tests.py integration
```

## 9. Promote and reproduce

```powershell
time-twist release-promote build/candidate/release_manifest.json `
  --release-id english-playtest-YYYY-MM-DD
time-twist release-build
```

Promotion verifies candidate files and ties the new target to the active source
lock. Strict rebuilding must then reproduce it byte for byte.

## 10. Playtest

Automated checks cannot prove scene progression, animation timing, input
behavior, disk swapping, visual clearing, or every translation choice.

At minimum test:

- new game and personality questionnaire;
- every command/object menu;
- normal and wrong-side disk prompts;
- Zenpen-to-Kouhen transition;
- save/load if used;
- title animation plus START/B behavior;
- all story branches, quizzes, and endings;
- long/short line replacement and page clearing.

Record the candidate or verified output SHA-256 with every report.
