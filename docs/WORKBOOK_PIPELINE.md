# Translation workbook pipeline

The workbook is the complete review surface for 2,052 extracted records. It is
not the packed byte stream inserted into the game, but its patch-safe field is
generated from and must mirror the playable sources.

## Data flow

```text
decoded Japanese records             playable English sources
          |                         scenario maps + fixed UI code
          +-------------------------+--------------------------+
                                    |
                 generate_bilingual_comparison.py
                                    |
                    ordered 2,052-record corpus
                                    |
                 generate_translation_workbook.py
                                    |
          HTML / CSV / JSON workbook, glossary, voice guide,
                    progress report, bank checkpoints
```

The exact-Japanese column is copied from decoded source records and is never
normalized in place. Romaji, reconstructed Japanese, linguistic labels,
literal readings, and natural English are editorial layers.

## Source locations

| Path | Role |
| --- | --- |
| `work/translated_scripts/BANK.json` | Decoded scenario records and stable IDs |
| `work/translations/BANK.json` | Authoritative playable scenario English |
| `work/time_twist/ui.py` | Authoritative fixed-address and graphics text |
| `outputs/Time Twist Japanese-English script comparison.json` | Ordered comparison corpus |
| `work/translation_workbook_banks/BANK.json` | Per-bank workbook checkpoints |
| `outputs/Time_Twist_complete_translation_workbook.*` | Aggregate review output |

## Generate the corpus and workbook

From the repository root:

```powershell
python work/generate_bilingual_comparison.py
python work/generate_translation_workbook.py
```

The corpus generator walks banks in canonical order, verifies one playable
scenario entry per decoded record, decodes fixed tables through the real
parser/dictionary, records controls and source locations, and rejects duplicate
IDs.

The workbook generator applies editorial layers such as:

- human-reviewed natural translations;
- notes, speaker/scene metadata, and glossary decisions;
- conservative reconstructed Japanese;
- fixed-address explanations.

It then derives patch-safe text under this policy:

- scenario rows come directly from `work/translations/*.json`;
- fixed-address and graphics rows retain the exact installed English from the
  patch definitions;
- natural-translation alternatives stay editorial and cannot silently enter a
  ROM build.

The generator validates:

- exactly 2,052 unique rows;
- byte-for-byte exact Japanese source retention;
- complete playable scenario coverage;
- patch-safe/playable equality;
- ordered control-code retention;
- nonempty natural and patch-safe translations;
- nonempty glossary output;
- absence of known unsafe reconstruction patterns.

`NOV2/wait` is the one documented fixed-UI control-layout exception: the engine
patch intentionally changes its display segmentation. It is explicit in code
and tests rather than treated as unexplained drift.

## Correcting a translation

Choose the true source layer:

1. If decoded Japanese is wrong, fix extraction/parsing and investigate the
   binary evidence.
2. If the in-game scenario line is wrong, edit `work/translations/BANK.json`.
3. If fixed UI text is wrong, edit the source-verified definition in `ui.py`.
4. If only the unconstrained interpretation changes, update the editorial
   natural-translation decision.
5. If a term recurs, update the glossary and all affected records.
6. Regenerate the workbook and inspect the affected bank checkpoint.
7. Run tests, rebuild a candidate, and playtest.

Never edit generated HTML, CSV, JSON, or a checkpoint as the only source
change; regeneration will overwrite it.

## Control codes

Controls are rendered as `{CTRL:n}` or `⟦CTRL:n⟧` depending on output context.
The generator compares their ordered sequence. A mismatch aborts generation
unless it is the single documented fixed-UI override.

`insert_controls_by_current_layout()` can preserve control order while
redistributing controls according to an existing record's segment proportions.
It cannot prove ideal dramatic placement. Important lines still require
explicit editorial review and gameplay inspection.

## Generated files

- `outputs/Time_Twist_complete_translation_workbook.html`
- `outputs/Time_Twist_complete_translation_workbook.csv`
- `outputs/Time_Twist_complete_translation_workbook.json`
- `outputs/Time_Twist_translation_progress.md`
- `outputs/Time_Twist_terminology_and_voice_guide.md`
- `work/translation_workbook_banks/*.json`

HTML is for browsing/filtering, CSV for spreadsheet review, and JSON for
lossless tooling.

## Verification

```powershell
python work/generate_bilingual_comparison.py
python work/generate_translation_workbook.py
python work/run_tests.py unit
```

Then confirm:

- 2,052 rows were emitted;
- no source fingerprint changed unexpectedly;
- the affected checkpoint contains the intended natural and patch-safe text;
- every scenario patch-safe field equals its playable map;
- controls, terminology, width, and bank recompression remain valid.

A playable revision becomes an approved release only through the source-lock,
candidate, review, and promotion workflow described in
[`TRANSLATION_WORKFLOW.md`](TRANSLATION_WORKFLOW.md).
