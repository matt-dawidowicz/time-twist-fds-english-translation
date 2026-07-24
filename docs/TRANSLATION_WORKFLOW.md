# Translation and rebuild workflow

This guide uses PowerShell and assumes the current directory is `work/`.
Replace `python` with the full path to your Python executable if it is not on
`PATH`.

## 1. Supply clean source images

Place legally obtained Japanese images at:

```text
baseline/time_twist_zenpen_japan.fds
baseline/time_twist_kouhen_japan.fds
```

These files are ignored by Git. Keep an untouched backup and record hashes
before doing any work.

## 2. Validate the FDS container

Create a manifest:

```powershell
python -m time_twist.cli manifest `
  baseline/time_twist_zenpen_japan.fds `
  --output manifests/zenpen.json
```

Prove that the parser is lossless:

```powershell
python -m time_twist.cli roundtrip `
  baseline/time_twist_zenpen_japan.fds `
  build/zenpen_roundtrip.fds
```

The command prints both SHA-256 values and fails unless the images are
byte-identical.

## 3. Extract named FDS files

```powershell
python -m time_twist.cli extract `
  baseline/time_twist_zenpen_japan.fds `
  extracted_zenpen
```

Names include the side, file index, FDS filename, and load address:

```text
side1_01_TT1A_A200.bin
```

Do not edit an extracted bank in a general text editor. It contains code,
pointers, packed text, and fixed binary data.

## 4. Extract a scenario document

```powershell
python -m time_twist.cli scenario-extract `
  extracted_zenpen/side1_01_TT1A_A200.bin `
  translated_scripts/TT1A.json
```

Each record contains:

- a stable ID such as `TT1A/g0/r6`;
- exact decoded Japanese;
- an English field;
- the raw decoded symbol kinds and values.

If the output file already exists, `scenario-extract` retains English entries
with the same group and record numbers. This allows a clean-bank refresh
without throwing away translation work.

## 5. Edit the ID-keyed translation map

The compact maps under `translations/` are ordinary JSON objects:

```json
{
  "TT1A/g0/r6": "Do you prefer consommé{CTRL:0}to miso soup?"
}
```

Editing rules:

- retain the exact record ID;
- provide a nonempty string;
- preserve the ordered `{CTRL:n}` values;
- use only characters supported by `english.py`;
- keep ordinary segments within 24 columns;
- read neighboring records and the full workbook before changing meaning.

Do not edit the Japanese field to insert probable kanji. Use the workbook's
reconstructed-Japanese field for that analysis.

## 6. Validate and merge English

```powershell
python -m time_twist.cli scenario-merge `
  translated_scripts/TT1A.json `
  translations/TT1A.json `
  --output translated_scripts/TT1A_english.json
```

By default the map must cover every record. Use `--allow-partial` only during
active translation, never as evidence that a bank is complete.

The merge validates IDs, completeness, control order, glyph support, and row
width.

## 7. Check the fixed footprint

```powershell
python -m time_twist.cli scenario-footprint `
  extracted_zenpen/side1_01_TT1A_A200.bin `
  --translations translations/TT1A.json
```

For a complete map the command builds the English dictionary and reports:

- fixed text capacity;
- compressed bytes used;
- bytes remaining or the overrun.

A negative remainder is a real build failure. Shorten or intelligently
rephrase text, improve repeated dictionary terms, or make a deliberate,
tested relocation. Do not overwrite the fixed tail.

## 8. Rebuild the scenario

```powershell
python -m time_twist.cli scenario-insert `
  extracted_zenpen/side1_01_TT1A_A200.bin `
  translated_scripts/TT1A_english.json `
  build/TT1A_english_scenario.bin
```

With a complete translation, the command creates a compact English dictionary.
With a partial translation, it preserves the Japanese dictionary so
untranslated records still render.

## 9. Patch fixed text

For banks with command/object/quiz tables, run the matching UI component on the
rebuilt scenario:

```powershell
python -m time_twist.cli ui-patch `
  build/TT1A_english_scenario.bin `
  build/TT1A_english.bin `
  --component TT1A
```

For dictionary-dependent fixed tables, always use the scenario build whose
dictionary was generated with the bank's required entries.

Shared components are patched in the same way:

```powershell
python -m time_twist.cli ui-patch NOV2.bin NOV2_english.bin --component NOV2
python -m time_twist.cli ui-patch NOV4.bin NOV4_ui.bin --component NOV4
python -m time_twist.cli ui-patch SON-KOUH.bin SON-KOUH_english.bin --component SON-KOUH
```

## 10. Patch the font and title

Both operations target NOV4. Font and UI changes are size-neutral; the title
step validates the original NOV4 layout and appends relocated data, so perform
it last:

```powershell
python -m time_twist.cli font-patch NOV4_ui.bin NOV4_font_ui.bin

python -m time_twist.cli title-patch `
  NOV4_font_ui.bin `
  "title_assets/Time Twist full-screen logo reference.png" `
  NOV4_english_title.bin `
  --subtitle "On the Outskirts of History..."
```

Do not repeatedly run a patch on its own output. Source guards expect the
known pre-patch bytes.

## 11. Replace files in an image

`replace-file` changes one named FDS file:

```powershell
python -m time_twist.cli replace-file `
  baseline/time_twist_zenpen_japan.fds `
  1 `
  TT1A `
  build/TT1A_english.bin `
  build/zenpen_with_tt1a.fds
```

Use the output image as the input to the next replacement. The side number is
zero-based. The named FDS file must occur exactly once on that side.

After all replacements, compare the manifest and run the FDS regression tests
to prove that only intended files changed.

## 12. Combine the two game images

Mesen and some other emulators can use one four-side image:

```powershell
python -m time_twist.cli combine `
  final_zenpen.fds `
  final_kouhen.fds `
  --output time_twist_english_four_side.fds
```

The side disk-info blocks are not rewritten. The game uses their original
identifiers when validating disk changes.

## 13. Run automated checks

From `work/`:

```powershell
python -m unittest discover -s tests -v
```

Fixtures derived from uncommitted ROM data are skipped when absent. A clean
release-working directory should include the legal local fixtures needed for
the full binary assertions.

## 14. Playtest

Automated checks cannot prove scene progression, animation timing, input
behavior, disk swapping, visual line clearing, or every translation choice.

At minimum test:

- new game and the personality questionnaire;
- every command/object menu;
- normal and wrong-side disk prompts;
- transition from Zenpen into Kouhen;
- save/load if used;
- title animation and START/B behavior;
- all story branches, quizzes, and endings;
- long/short line replacement and page clearing.

Record the exact build hash with each screenshot or bug report.
