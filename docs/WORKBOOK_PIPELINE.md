# Translation workbook pipeline

The workbook is the complete review surface for 2,058 extracted records. It is
not the packed byte stream inserted into the game. Its patch-safe scenario field
tracks the certified base maps and conservative native-layout analysis; the
canonical release separately composes the registered production-review layer and
any explicit final overrides before entropy encoding.

## Data flow

```text
decoded Japanese records             workbook/base English sources
          |                         base scenario maps + fixed UI code
          +-------------------------+-------------------------------+
                                    |
                 generate_bilingual_comparison.py
                                    |
                    ordered 2,058-record corpus
                                    |
                 generate_translation_workbook.py
                                    |
          HTML / CSV / JSON workbook, glossary, voice guide,
                    progress report, bank checkpoints
```

The exact-Japanese column is copied from decoded source records and is never
normalized in place. Romaji, reconstructed Japanese, linguistic labels,
literal readings, and natural English are editorial layers.

The workbook's comparison-corpus fingerprint uses LF-normalized SHA-256, so
Windows CRLF checkouts and Unix LF checkouts report the same text-source
identity. JSON metadata records `source_hash_normalization: "lf"`. This changes
only fingerprint calculation; source files and Japanese record data are not
rewritten. Generated-artifact and optional diagnostic-file hashes remain
byte-exact.

## Source locations

| Path | Role |
| --- | --- |
| `work/source_records/BANK.json` | Decoded scenario records and stable IDs |
| `work/translations/BANK.json` | Certified base scenario English and native control topology |
| `review/production_retranslation/*.json` | Registered production wording consumed by `release-build` |
| `work/production_overrides/BANK.json` | Optional final explicit release override when intentionally present |
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

It then derives workbook patch-safe text under this policy:

- scenario rows come directly from the certified base maps in
  `work/translations/*.json`;
- fixed-address and graphics rows retain the configured English from the
  full-word menu definitions or fixed-interface patch definitions;
- natural-translation alternatives remain editorial workbook data. The
  registered production-review JSON is a separate locked source layer and enters
  a ROM only through the canonical materializer used by `release-build`.

## Preserving editorial and base-map views

The workbook preserves both an unconstrained editorial reading and the certified
base-map rendering used for conservative analysis. The current production release
may display fuller reviewed prose because `production_translation.py` can
regenerate safe row/scroll geometry before entropy encoding. Two workbook fields
still remain distinct:

| Field | Meaning |
| --- | --- |
| `final_natural_english_translation` | The complete natural English reading, without treating the current row width or compressed-bank budget as an editorial limit |
| `patch_safe_english_translation` | The certified base-map rendering used by workbook validation and conservative native/flat fit checks |

This distinction lets future contributors improve the renderer, recover
compressed space, or relocate data without having to translate the Japanese
again. It also prevents a compact gameplay line from becoming the only
surviving record of the intended meaning.

For example, record `TT1B/g0/r1` preserves:

```text
Japanese:     さいごにあおぞらをみたのは いつだっけ
Full English: When was the last time I saw a blue sky?
ROM-safe:     Blue sky--how long gone?
```

The optimized compact wording is now `Blue sky--how long gone?`. The full
English is 40 visible characters, but this source record has no line or page
control and the renderer limits its single segment to 24 columns. Compression
headroom cannot solve that display-layout constraint by itself. Inserting a new
control is not merely punctuation, so that larger change would require testing
the object's rendering, clearing, and repeat-inspection behavior.

### Promoting editorial wording into the playable build

Do not copy a natural-field value directly into a generated ROM or workbook
artifact. Instead:

1. Put reviewed current-production wording in the bank's registered file under
   `review/production_retranslation/`; change `work/translations/BANK.json` only
   when the certified base wording or native semantic-control topology itself is
   intentionally changing.
2. Use `work/production_overrides/BANK.json` only for a narrow, explicit final
   correction that should supersede both base and review text.
3. Preserve native semantic-control order. Ordinary English row/scroll geometry
   is regenerated by `production_translation.py`.
4. Build the complete entropy candidate and prove every bank remains below NOV3.
5. Run private integration checks and playtest the changed scene.
6. Refresh the source lock only after the source-layer change is reviewed.

The workbook can therefore remain a stable base/editorial review surface while
the canonical release consumes the separately registered production layer.

The generator validates:

- exactly 2,058 unique rows;
- byte-for-byte exact Japanese source retention;
- complete certified base-map scenario coverage;
- patch-safe/base-map equality;
- ordered control-code retention;
- nonempty natural and patch-safe translations;
- nonempty glossary output;
- absence of known unsafe reconstruction patterns.

`NOV2/wait` is the one documented fixed-UI control-layout exception: the engine
patch intentionally changes its display segmentation. It is explicit in code
and tests rather than treated as unexplained drift.

## Compression evidence

Generation recomputes conservative fit measurements from the current playable
scenario maps and configured full-word menu labels. It uses the 68-entry greedy
baseline, includes structural pointers, and counts the recovered movable menu
reservation in relocated banks. A bank that exceeds this conservative capacity
stops generation before workbook outputs are written.

The HTML workbook, Markdown progress report, and JSON
`patch_validation.revised_bank_footprints` all carry those same fresh results.
`footprint_method` identifies the method. Recovered native capacities and movable
menu reservations live in `work/time_twist/capacity.py`; usage is recomputed
from current text rather than copied from a historical candidate.

Actual release measurements, including any optimizer fallback, belong to a
fresh ROM-backed candidate manifest. Public fit checks do not replace source
layout validation, private integration tests, or emulator playtesting.

## Correcting a translation

Choose the true source layer:

1. If decoded Japanese is wrong, fix extraction/parsing and investigate the
   binary evidence.
2. If current production wording is wrong, edit the registered review JSON (or
   an intentional final override); edit the base map only for a deliberate
   baseline/topology correction.
3. If fixed UI text is wrong, edit the source-verified definition in `ui.py`.
4. If only the unconstrained workbook interpretation changes, update the
   editorial natural-translation decision.
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

- 2,058 rows were emitted;
- no source fingerprint changed unexpectedly;
- the affected checkpoint contains the intended natural and patch-safe text;
- every scenario patch-safe field equals its certified base map;
- controls, terminology, width, and bank recompression remain valid.

A playable revision becomes an approved release only through the source-lock,
candidate, review, and promotion workflow described in
[`TRANSLATION_WORKFLOW.md`](TRANSLATION_WORKFLOW.md).
