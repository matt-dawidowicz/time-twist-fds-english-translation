# Translation workbook pipeline

This document explains how the large review artifacts are generated and where
to make each kind of edit. The workbook is a review and localization artifact;
it is not itself the packed byte stream inserted into the game.

## Data flow

```text
decoded Japanese bank records        current patch-oriented English maps
              |                                      |
              +------------------+-------------------+
                                 |
             generate_bilingual_comparison.py
                                 |
          immutable 2,052-record comparison corpus
                                 |
             linguistic review HTML + manual decisions
                                 |
             generate_translation_workbook.py
                                 |
       HTML / CSV / JSON workbook, glossary, voice guide,
                 progress report, bank checkpoints
```

The exact Japanese column is copied from decoded source-bank records and must
never be normalized in place. Romaji, reconstructed Japanese, linguistic
labels, literal readings, and English translations are editorial layers.

## Source locations

| Path | Role |
| --- | --- |
| `work/translated_scripts/BANK.json` | Decoded Japanese scenario records and their stable IDs |
| `work/translations/BANK.json` | Current patch-oriented English scenario maps |
| `work/time_twist/ui.py` | Fixed-address and graphics-text definitions |
| `outputs/Time Twist Japanese-English script comparison.json` | Canonical ordered comparison corpus |
| `work/translation_workbook_banks/BANK.json` | Per-bank completed workbook checkpoints |
| `outputs/Time_Twist_complete_translation_workbook.*` | Searchable and machine-readable aggregate workbook |

## Comparison-corpus generator

Run from `work/`:

```powershell
python generate_bilingual_comparison.py
```

`generate_bilingual_comparison.py`:

1. walks scenario banks in `BANK_ORDER`;
2. verifies that every decoded record has exactly one translation-map entry;
3. decodes fixed-address tables through the real dictionary and record parser;
4. adds standalone interface and graphics text;
5. records control-code sequences, source location, storage type, script
   profile, mechanical romaji, and conservative review hints;
6. rejects duplicate IDs;
7. emits TSV, JSON, HTML, and a review guide.

Its linguistic detection is intentionally conservative. Marker detection is a
review aid, not a substitute for reading a full record group. In particular,
the code masks names and loanwords before suggesting kanji, and it uses
grammatical boundaries for voice markers that are prone to substring false
positives.

## Complete-workbook generator

Run from `work/`:

```powershell
python generate_translation_workbook.py
```

`generate_translation_workbook.py` separates decisions into several layers:

- `MANUAL_FINAL` holds human-reviewed natural translations that override the
  provisional draft.
- `MANUAL_PATCH` holds tested, control-code-preserving versions intended for
  the byte-constrained patch.
- `MANUAL_NOTES`, speaker overrides, scene metadata, and glossary seeds record
  analysis that should remain globally consistent.
- safe reconstruction tables may restore likely kanji or katakana only in the
  editorial reconstruction field.
- fixed-address expansion rules explain terse UI labels without changing the
  bytes used by the actual fixed record.

The generator then creates every `WorkbookRow`, emits the aggregate artifacts,
writes one checkpoint per bank, and validates:

- exactly 2,052 rows;
- unique record IDs;
- byte-for-byte exact Japanese source retention;
- control-code sequence retention in patch-safe English;
- non-empty final and patch-safe translations;
- non-empty glossary output;
- absence of known unsafe reconstruction patterns.

## Adding or correcting a translation

Choose the smallest authoritative layer:

1. If the decoded Japanese is wrong, fix the parser or source extraction and
   investigate why. Do not hand-edit the workbook's exact-source field.
2. If the natural interpretation is wrong, update the relevant reviewed/manual
   translation decision.
3. If only the in-game line needs shortening, update the patch-safe decision
   while preserving the natural translation.
4. If the term recurs, update the glossary and every affected occurrence.
5. Regenerate the comparison corpus only when its underlying decoded sources or
   current translation maps changed.
6. Regenerate the complete workbook and inspect the affected bank checkpoint.
7. Insert the bank translation using the workflow in
   [`TRANSLATION_WORKFLOW.md`](TRANSLATION_WORKFLOW.md).

Never edit generated HTML, CSV, or JSON as the only change. Regeneration will
overwrite it and leave the real source of the decision unchanged.

## Control codes

The corpus generator renders controls as explicit `{CTRL:n}` or `⟦CTRL:n⟧`
markers depending on the output context. The workbook generator compares the
ordered sequence in exact Japanese with the ordered sequence in patch-safe
English. A mismatch aborts generation.

`insert_controls_by_current_layout()` is a fallback that distributes existing
controls across a revised sentence according to the current record's segment
proportions. It preserves control order, but it cannot prove that each control
has the ideal dramatic placement. Important lines should use an explicit
manual patch decision and be checked in gameplay.

## Generated files

The main outputs are:

- `outputs/Time_Twist_complete_translation_workbook.html`
- `outputs/Time_Twist_complete_translation_workbook.csv`
- `outputs/Time_Twist_complete_translation_workbook.json`
- `outputs/Time_Twist_translation_progress.md`
- `outputs/Time_Twist_terminology_and_voice_guide.md`
- `work/translation_workbook_banks/*.json`

The HTML is for browsing and filtering. CSV is convenient for spreadsheet
review. JSON is the lossless machine-readable form and should be preferred by
new tooling.

## Review checklist

After changing workbook logic:

```powershell
python generate_bilingual_comparison.py
python generate_translation_workbook.py
python -m unittest discover -s tests -v
```

Then check:

- the generator reports 2,052 records;
- no source fingerprints changed unexpectedly;
- the affected bank checkpoint contains the intended wording;
- exact Japanese and control sequences did not drift;
- repeated names and terminology remain consistent;
- patch-safe records still pass native character, display-width, and bank
  recompression checks.
