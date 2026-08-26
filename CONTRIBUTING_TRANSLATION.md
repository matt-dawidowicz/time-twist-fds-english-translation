# Contributing translation

This guide is for editors and reviewers who want to improve the English text
without modifying the FDS engine or working with game-image bytes.

## Start with the right source

The playable scenario text is in `work/translations/<BANK>.json`.
The searchable workbook in
[`outputs/Time_Twist_complete_translation_workbook.html`](outputs/Time_Twist_complete_translation_workbook.html)
is the best review surface, but it is generated. Do not edit a workbook row as
the only source change.

Each record has two useful English fields:

- `patch_safe_english_translation` is the exact text used by the current
  playable build.
- `final_natural_english_translation` preserves a fuller editorial reading
  when the current renderer, control layout, or bank budget cannot display it
  safely. The canonical release already installs the configured full-word menu
  labels; this distinction still matters for constrained scenario prose.

Read [the translation workflow](docs/TRANSLATION_WORKFLOW.md) before changing
a record. It explains the record IDs, control codes, width limits, and bank
footprints that are not visible in ordinary prose.

## Safe contribution workflow

1. Find the stable record ID in the workbook and read its Japanese source,
   scene context, and existing notes.
2. Edit the matching entry in `work/translations/<BANK>.json`.
3. Keep the exact Japanese source and the sequence of control tags unchanged.
4. Keep the patch-safe text within the existing display, packing, and capacity
   limits. If the natural wording does not fit, retain it in the natural field
   and explain the tradeoff instead of silently weakening the translation.
5. Run the public tests:

   ```powershell
   python -m pip install -e ".[dev]"
   python work/run_tests.py unit
   ```

6. In your pull request, name every changed record ID, give the scene context,
   explain the wording decision, and report the checks you ran.

## Do not do these things

- Do not edit generated FDS images, extracted banks, or workbook outputs as
  authoritative translation source.
- Do not change `exact_japanese` to match a reconstruction or a guess.
- Do not reorder, remove, or invent control tags.
- Do not expand a fixed record, scenario tail, or bank footprint without a
  separately proven engine-level plan.
- Do not commit game images, private fixtures, save states, screenshots, or
  generated candidates.

## Need more context?

- [Workbook pipeline](docs/WORKBOOK_PIPELINE.md)
- [Scenario-bank format](docs/FORMATS.md#scenario-bank-layout)
- [Project architecture](docs/ARCHITECTURE.md)
- [General contribution rules](CONTRIBUTING.md)
