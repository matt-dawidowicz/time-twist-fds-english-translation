# Full-word menu experiment

> Superseded for target planning by `docs/FULL_WORD_MENU_TARGETS.md`, which now covers every fixed menu/choice record as an explicit full-word target.

# Time Twist full-word menu label experiment — 2026-08-12

## Summary

- Base: previous full-label literal-fit/menu consistency source and FDS candidate.
- Goal: keep pushing menu/choice labels toward full English words instead of accepting abbreviations by default.
- New fixed label expansions in this experiment: **21**.
- Dictionary entries deliberately changed/reused: **3**.
- Remaining constrained full-word targets: **261**.
- Candidate FDS SHA-256: `19D7EC58A2CFF17185F990BAF13C3892E70C5D83BC4B61ED95644A99D3465D09`.

This pass does not claim the remaining abbreviations are final. It identifies them as targets for a deeper recompression/relocation branch.

## Applied label expansions by bank

| Bank | Count |
| --- | ---: |
| T22 | 2 |
| T25 | 5 |
| TT2 | 2 |
| TT3B | 1 |
| TT4 | 1 |
| TT5 | 3 |
| TT6A | 2 |
| TT6B | 4 |
| TT6C | 1 |

## Dictionary changes

| Bank | Entry/index | Old | New | Method |
| --- | ---: | --- | --- | --- |
| TT2 | 1 | `CROWD` | `Crowd` | dictionary_entry_replace |
| T22 | 7 | `SCAFFOLD` | `Look` | dictionary_entry_replace |
| T22 | 8 | `CROWD` | `Crowd` | dictionary_entry_replace |

## Applied labels

| Bank | Index | Old | New | Method |
| --- | ---: | --- | --- | --- |
| TT3B | 8 | `WMN` | `Woman` | existing_dictionary |
| TT2 | 8 | `PIER` | `Pierre` | existing_dictionary |
| TT2 | 58 | `CROWD` | `Crowd` | required_dictionary_case_update |
| T22 | 0 | `SE` | `Look` | required_dictionary_reuse |
| T22 | 30 | `CROWD` | `Crowd` | required_dictionary_case_update |
| TT6C | 86 | `HITLR` | `Hitler` | existing_dictionary |
| TT6B | 12 | `TONG` | `Tongue` | existing_dictionary |
| TT6B | 17 | `CML` | `Camel` | existing_dictionary |
| TT6B | 30 | `SHP` | `Sheep` | existing_dictionary |
| TT6B | 31 | `CW` | `Cow` | existing_dictionary |
| TT6A | 8 | `JOS` | `Joseph` | existing_dictionary |
| TT6A | 22 | `HL` | `Hill` | existing_dictionary |
| TT4 | 73 | `SE` | `Sea` | existing_dictionary |
| TT5 | 19 | `DRAW` | `Drawer` | existing_dictionary |
| TT5 | 55 | `TRDR` | `Trader` | existing_dictionary |
| TT5 | 73 | `CAM` | `Camera` | existing_dictionary |
| T25 | 5 | `SOL` | `Soldier` | existing_dictionary |
| T25 | 6 | `COFE` | `Coffee` | existing_dictionary |
| T25 | 8 | `MANR` | `Mansion` | existing_dictionary |
| T25 | 25 | `DRAW` | `Drawer` | existing_dictionary |
| T25 | 36 | `COY` | `Coyote` | existing_dictionary |

## Remaining high-priority blockers

These are still not acceptable as final polish; they are simply not proven safe in this branch without deeper compression/table work.

| Bank | Index | Current | Target | Category | Reason |
| --- | ---: | --- | --- | --- | --- |
| TT3A | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 2 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 6 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 32 | `WR` | `Wear` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 36 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 56 | `N` | `North` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 58 | `W` | `West` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 64 | `S` | `South` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3A | 67 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3B | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3B | 2 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT3B | 16 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 2 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 4 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 9 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 13 | `DR` | `Drink` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 23 | `On` | `Wear` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT2 | 24 | `Of` | `Remove` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| T22 | 3 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| T22 | 14 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| T22 | 25 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 3 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 6 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 14 | `MY BOD` | `My body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 16 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 25 | `YS` | `Yes` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 27 | `N` | `North` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 29 | `W` | `West` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 30 | `S` | `South` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6C | 93 | `R` | `Right` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 1 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 2 | `SM` | `Smell` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 8 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 19 | `N` | `North` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 21 | `W` | `West` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 22 | `S` | `South` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 23 | `FWD` | `Forward` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6B | 24 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6A | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6A | 1 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6A | 2 | `SM` | `Smell` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6A | 7 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT6A | 13 | `DR` | `Drink` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 18 | `CONT` | `Continuous` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 42 | `LVL` | `Level` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 30 | `BOD` | `Body` | object | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 51 | `N` | `North` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 53 | `W` | `West` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT4 | 66 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 77 | `ANS` | `Answer` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 78 | `PROB` | `Problem` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 2 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 10 | `N` | `North` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 12 | `W` | `West` | compass | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 13 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 23 | `YS` | `Yes` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 76 | `BCK` | `Back` | navigation | requires new dictionary/compression work beyond existing or safely reusable slots |
| TT5 | 107 | `SM` | `Small` | choice | requires new dictionary/compression work beyond existing or safely reusable slots |
| T25 | 0 | `SE` | `Look` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| T25 | 22 | `GT` | `Take` | command | requires new dictionary/compression work beyond existing or safely reusable slots |
| T25 | 30 | `AS` | `Ask` | command | requires new dictionary/compression work beyond existing or safely reusable slots |

## Remaining blockers by bank

| Bank | Count |
| --- | ---: |
| T22 | 10 |
| T25 | 8 |
| TT2 | 14 |
| TT3A | 43 |
| TT3B | 5 |
| TT4 | 47 |
| TT5 | 34 |
| TT6A | 21 |
| TT6B | 29 |
| TT6C | 50 |

## Validation

- `PYTHONPATH=work python -m unittest work.tests.test_ui_unit -v`: passed, 22 tests.
- `PYTHONPATH=work python -m compileall -q work/time_twist work/tests/test_ui_unit.py work/tools`: passed.
- `PYTHONPATH=work python work/tools/audit_fixed_menu_labels.py --candidate-fds ...`: passed, 721 labels audited, 0 failures.
- Custom candidate validation: passed, 721 fixed labels decoded back to source constants, 0 width failures.
- Full `python work/run_tests.py unit`: not clean in this source-only handoff because the environment lacks `hypothesis` and the generated comparison/workbook outputs are not present. The real repository should already have the actual translation/title asset directories; this handoff zip includes only placeholder directories so the source-tree check can run.
