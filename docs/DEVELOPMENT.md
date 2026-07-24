# Development guide

## Environment

- Python 3.11 or newer is recommended.
- Core parsing/patching uses the standard library.
- Pillow is required for title and image-rendering code.
- Mesen is optional and used only for manual playtesting/debugging.

The package is intentionally run from `work/` without installation:

```powershell
cd work
python -m time_twist.cli --help
```

## Test suite

Run:

```powershell
python -m unittest discover -s tests -v
```

Test modules are organized by contract:

| Test module | Contract |
| --- | --- |
| `test_fds.py` | Lossless FDS parsing, side order, changed-file scope, padding |
| `test_textcodec.py` | Prefix tree, separators, bit ordering, encoder symmetry |
| `test_scenario.py` | Character map, dictionaries, bank rebuilds, font, footprint |
| `test_ui.py` | Exact source guards, fixed tables, menu/input/UI behavior |
| `test_title.py` | Title assets, palettes, split, Nintendo phase, clock preservation |
| `test_comparison.py` | Bilingual comparison coverage and control sequences |
| `test_translation_workbook.py` | 2,052-record workbook integrity and patch safety |

ROM-derived fixtures are not committed. Tests that need them call
`skipTest(...)` when the local fixture is absent. A high skip count in a fresh
clone is expected; a release build should run with the complete local fixture
set.

## Adding or changing a binary patch

1. **Identify the owning FDS file.** Do not search the combined ROM and patch
   the first matching byte sequence.
2. **Record the load address and file offset.** Name constants so it is clear
   which coordinate system they use.
3. **Capture the expected source.** Use exact bytes for a short instruction or
   SHA-256 for a complete fixed table/asset.
4. **State the invariant.** Examples: individual record sizes, total file size,
   tail address, clock bytes, or one-choice-only input behavior.
5. **Write a pure patch function.** Accept `bytes`, validate first, return new
   `bytes`, and avoid filesystem/emulator state.
6. **Verify the output.** Re-decode data or assert the exact changed range.
7. **Add rejection coverage.** A deliberately modified source must raise the
   patch's error class.
8. **Add scope coverage.** When possible, compare the rebuilt FDS image and
   prove that only the named FDS file changed.
9. **Run all tests and playtest.**

Never weaken a source check because a patch fails on a different build. Add an
explicit supported revision with its own evidence instead.

## Editing packed text safely

Use the highest-level representation available:

- story dialogue: edit `work/translations/BANK.json`;
- detailed linguistic analysis: edit/regenerate workbook bank data;
- fixed UI labels: edit the named record tuple in `ui.py` and its required
  dictionary terms;
- font glyph: edit `PIXEL_FONT_5X7` and mapping tables;
- title art: edit the target image and title conversion, not raw CHR by hand.

After changing text:

1. run `scenario-merge`;
2. run `scenario-footprint`;
3. rebuild the scenario;
4. run the matching fixed-table UI patch;
5. run tests;
6. inspect the rendered output and playtest.

## Dictionary debugging

When a bank no longer fits:

- compare literal and compressed sizes from `scenario-footprint`;
- inspect repeated complete words/speaker prefixes;
- check bank-specific `BANK_REQUIRED_DICTIONARY_TEXT`;
- remember that a dictionary reference costs 9 bits;
- remember that the encoded dictionary entry itself consumes bytes;
- avoid nested English entries, which the compressor intentionally forbids;
- verify that fixed tables still have the words they require.

Changing a required entry can save scenario space but make a two-byte fixed
record impossible to encode. Treat scenario and fixed-table use as one budget.

## Display debugging

Text problems usually belong to one of four layers:

| Symptom | Likely layer |
| --- | --- |
| Wrong letters everywhere | Font or English tile mapping |
| Japanese renders as English gibberish | Untranslated packed record using English font |
| End of old line remains visible | Menu/dialogue clearing or transparent tail behavior |
| Final character wraps/gets overwritten | 24-column segmentation or control placement |

Do not solve a line-clearing bug by padding every dialogue line with visible
or opaque spaces. The typewriter renderer may process them as silent
characters and alter timing. NOV2 menu clearing and dialogue scrolling use
different paths.

## Title debugging

Use deterministic rendered previews and the title tests before emulator work.
Check separately:

- palette-index assignment;
- tile border/diagonal fidelity;
- exact upper/lower pattern counts;
- second-nametable slide positions;
- Nintendo overlay/restore ranges;
- clock background center;
- clock sprite origin and unchanged animation bytes;
- transition and exit helper call/stack semantics.

The title code appends data and patches 6502 control flow. A visually correct
static image is not enough; START, B, the swipe, raster split shutdown, and the
next game state must all be tested.

## Python documentation standard

Production Python follows PEP 257 structure and uses PEP 8 explanatory-comment
style. A public or non-obvious class/function contract should state the parts
that a maintainer cannot safely infer from its name:

- purpose and project context;
- arguments and return value;
- accepted coordinate system, byte layout, or source assumptions;
- deliberate side effects and generated files;
- domain exceptions and the invariant each one protects;
- why a non-obvious implementation strategy was chosen;
- what the function validates and what still requires recompression, rendering,
  or gameplay verification.

Use an imperative, standalone summary line ending in punctuation. Separate a
multi-line description from that summary with a blank line. Keep exact ROM
evidence distinct from inferred editorial data in both prose and identifiers.
Simple properties may use a concise one-line docstring when their complete
contract is genuinely obvious from the documented owning class.

Comments explain constraints, causality, or design intent. They are complete
phrases or sentences, begin with `# `, and appear immediately above the code
they illuminate. Do not narrate syntax. If a comment must explain a public
caller contract, failure condition, or side effect, move that information into
the docstring so documentation tools can expose it.

## Generated and ignored files

The following remain local:

- original/patched `.fds` images;
- extracted and rebuilt `.bin` banks;
- emulator `.dmp` captures;
- Mesen archives/settings;
- Python caches.

Commit source, tests, translation JSON, documentation, review workbooks, and
small reference/preview images. Do not commit ROMs or firmware.

## Review checklist

- [ ] Public functions/classes have clear docstrings.
- [ ] New offsets specify component and coordinate system.
- [ ] Source bytes or hashes are validated.
- [ ] Error messages identify the component and failed invariant.
- [ ] Control-code order is unchanged.
- [ ] Fixed record/table/bank sizes are preserved.
- [ ] Tests include success, rejection, and scope where possible.
- [ ] Full test suite passes.
- [ ] Manual playtest covers the affected scene and adjacent transitions.
