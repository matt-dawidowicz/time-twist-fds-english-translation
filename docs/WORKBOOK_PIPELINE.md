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
| `work/source_records/BANK.json` | Decoded scenario records and stable IDs |
| `work/translations/BANK.json` | Authoritative playable scenario English |
| `work/time_twist/ui_fixed_tables.py` | Authoritative full-word scenario menu labels |
| `work/time_twist/ui.py` | Fixed-interface/graphics text and menu relocation logic |
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
  full-word menu definitions or fixed-interface patch definitions;
- natural-translation alternatives stay editorial and cannot silently enter a
  ROM build.

## Preserving the full translation

The workbook is also the preservation layer for scenario English that is
accurate but cannot yet be installed within renderer or control-layout
constraints. Fixed-menu expansion solved the former menu-slot abbreviations;
dialogue layout is handled separately through source-exact controls by default
and explicitly audited presentation breaks where the recovered runtime behavior
supports them. Two fields must remain distinct:

| Field | Meaning |
| --- | --- |
| `final_natural_english_translation` | The complete natural English reading, without treating the current row width or compressed-bank budget as an editorial limit |
| `patch_safe_english_translation` | The exact English currently safe to encode and use in the playable ROM |

This distinction lets future contributors improve the renderer, recover
compressed space, or relocate data without having to translate the Japanese
again. It also prevents a compact gameplay line from becoming the only
surviving record of the intended meaning.

For example, record `TT1B/g0/r1` is now the reference case for the
intent-first workflow:

```text
Japanese:     さいごにあおぞらをみたのは いつだっけ
Natural:      When was the last time I saw a blue sky?
Playable:     When was the last time{CTRL:0}I saw a blue sky?
Rendered:     When was the last time
              I saw a blue sky?
```

The earlier playable wording compressed the sentence into telegraphic English.
That compromise is no longer accepted merely because it is short. A recovered,
audited `CTRL:0` presentation break makes the complete natural reading safe in
two rows, and whole-bank optimization proves it fits the fixed ROM allocation.

This is the governing editorial rule: preserve the Japanese record's denotation,
emotional valence, speaker attitude, register, subtext, and dramatic rhythm as
recorded in the exact-Japanese, literal, linguistic, speaker, voice, sentiment,
and natural-translation review layers. Renderer width and packed-bank capacity
remain hard technical constraints, but the tooling should solve those constraints
before prose is shortened.

The editorial optimizer may use the verified Python-Rust hybrid described in
[`NATIVE_ACCELERATOR.md`](NATIVE_ACCELERATOR.md). Rust accelerates deterministic
search; Python remains the codec authority and independently verifies every
native result before it can be accepted.

### Using a full translation in a future build

Do not copy a natural-field value directly into a generated ROM or workbook
artifact. Instead:

1. Copy the intended wording into the authoritative playable source in
   `work/translations/BANK.json` (or the relevant fixed-UI definition).
2. Check every visible segment against the renderer's width limit.
3. Preserve the source control sequence exactly by default. If English requires
   an additional row, use only an explicitly audited presentation-break record;
   the shared scenario policy must preserve every source control in order and
   permit only additional `CTRL:0` row advances.
4. Recompress the entire affected bank and prove that it stays within its
   original footprint, or implement and document a safe relocation.
5. Rebuild a candidate and playtest entry, clearing, repetition, progression,
   save/reload, and disk switching where applicable.
6. Regenerate the workbook so the patch-safe field mirrors the newly proven
   playable source while the natural field retains the editorial target.

If those checks cannot yet pass, keep the full wording in
`final_natural_english_translation` and use the best accurate compact wording
in `patch_safe_english_translation`. That is a documented hardware compromise,
not an incomplete translation.

The generator validates:

- exactly 2,052 unique rows;
- byte-for-byte exact Japanese source retention;
- complete playable scenario coverage;
- patch-safe/playable equality;
- source controls preserved exactly or accepted by an explicit audited control
  policy;
- nonempty natural and patch-safe translations;
- nonempty glossary output;
- absence of known unsafe reconstruction patterns.

Control-layout exceptions are explicit rather than treated as unexplained drift:

- `NOV2/wait` is the documented fixed-UI segmentation override;
- scenario IDs in `PRESENTATION_BREAK_RECORD_IDS` may add only the recovered
  `CTRL:0` row advance, while every source control remains in original order.

The scenario rule is enforced by `scenario_controls_match_policy()` and is used
by scenario validation, the bilingual comparison generator, and the workbook
validation path. A new presentation exception therefore cannot be made valid by
changing only a generated artifact or a single test.

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
For ordinary scenario records, English must retain the Japanese/source control
sequence exactly. For an allowlisted presentation-break record, the English may
insert additional `CTRL:0` row advances only when every source control still
appears in the original order. Arbitrary waits, page controls, timing/state
controls, removals, or reordering remain invalid.

The bilingual comparison keeps the raw source and English sequences in separate
fields. Its `control_match` field reports whether the sequence is valid under
this reviewed policy, not merely whether the two raw tuples are textually equal.
The workbook separately records the exceptional IDs so reviewers can find every
non-exact control layout.

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

For deep editorial compression/layout work, stable Rust may additionally be used
as documented in [`NATIVE_ACCELERATOR.md`](NATIVE_ACCELERATOR.md); Python still
performs the authoritative verification of native output.

Then confirm:

- 2,052 rows were emitted;
- no source fingerprint changed unexpectedly;
- the affected checkpoint contains the intended natural and patch-safe text;
- every scenario patch-safe field equals its playable map;
- controls, terminology, width, and bank recompression remain valid.

A playable revision becomes an approved release only through the source-lock,
candidate, review, and promotion workflow described in
[`TRANSLATION_WORKFLOW.md`](TRANSLATION_WORKFLOW.md).
