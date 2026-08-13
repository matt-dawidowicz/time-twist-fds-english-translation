# Menu label audit and full-label fit pass

This pass audits fixed menu/choice labels across the game candidate, verifies command meanings against the source glossary, expands every high-confidence label that fits its existing packed record slot, and records the labels that still require a more invasive capacity solution.

## Result

- Fixed labels validated: 721
- Literal-fit improvements applied: 73
- Remaining desired full labels constrained by slot/dictionary capacity: 282
- Candidate FDS SHA-256: `D6D21104560D03B8EB20E8691004DAA3771EC4F6C7CCE28A231A07B5F5F4BBF4`

## Applied changes by bank

| Bank | Applied changes |
|---|---:|
| T25 | 4 |
| TT3A | 17 |
| TT3B | 3 |
| TT4 | 8 |
| TT5 | 13 |
| TT6A | 5 |
| TT6B | 13 |
| TT6C | 10 |

## Applied changes by category

| Category | Count |
|---|---:|
| object | 23 |
| name | 14 |
| action | 8 |
| quiz | 8 |
| compass | 5 |
| place | 4 |
| navigation | 2 |
| person | 2 |
| choice | 2 |
| plant | 1 |
| animal | 1 |
| direction | 1 |
| role | 1 |
| color | 1 |

## Command abbreviation audit

The compact command labels are not random abbreviations. They are constrained labels for specific Japanese verbs. Where full words fit, the UI uses the full word. Where they do not fit, the compact label remains rather than changing the bank layout unsafely.

| Compact label | Confirmed meaning | Japanese/source sense | Current status |
|---|---|---|---|
| `SE` | Look | 見る / examine | Still constrained in several 3-byte slots |
| `GT` | Take | 取る / get, take | Still constrained in several 3-byte slots |
| `AS` | Ask | 聞く・訊く / ask or listen by context | Still constrained in several 3-byte slots; do not translate as Talk |
| `SM` | Smell | 嗅ぐ | Still constrained in 3-byte slots |
| `DR` | Drink | 飲む | Still constrained in 3-byte slots |
| `WR` | Wear | 着る / put on, context-dependent | Still constrained in a 3-byte slot |
| `On` | Wear / put on | 着る in the clothing context | `Wear` would need dictionary/capacity work |
| `Of` | Remove / take off | 脱ぐ | `Remove` would need dictionary/capacity work |

## Compass choices

- `E` was expanded to `East` everywhere it fit.
- `N`, `W`, and `S` remain compact in fixed 3- or 4-byte slots because `North`, `West`, and `South` require dictionary/capacity changes in those banks.
- `LEFT` and `UP` were expanded to `Left` and `Up` where they fit. `R` remains constrained; `Right` does not fit its slot.

## Why the remaining full labels were not forced

The attempted dictionary-forced pass was rejected by the same footprint checks that protect the release build. The affected banks already have tight scenario/dictionary footprints, and adding required menu-label dictionary entries either overran the preserved text region or failed the full-dictionary requirement for fixed-UI banks.

| Rejection reason | Count |
|---|---:|
| needs dictionary low priority | 219 |
| required dictionary overran bank | 63 |

The safe choice is to keep these compact labels until a separate, playtested capacity project can free bank space, relocate fixed records, or implement a carefully justified font/encoding trick.

## High-priority labels still constrained

| Bank | Index | Current | Desired | Slot bytes | Needed literal bytes | Reason |
|---|---:|---|---|---:|---:|---|
| TT3A | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT3A | 2 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| TT3A | 6 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT3A | 32 | `WR` | `Wear` | 3 | 4 | required dictionary overran bank |
| TT3A | 36 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT3A | 56 | `N` | `North` | 3 | 5 | required dictionary overran bank |
| TT3A | 58 | `W` | `West` | 3 | 4 | required dictionary overran bank |
| TT3A | 64 | `S` | `South` | 4 | 5 | required dictionary overran bank |
| TT3A | 67 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT3B | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT3B | 2 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| TT3B | 16 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT2 | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT2 | 2 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| TT2 | 4 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT2 | 9 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT2 | 13 | `DR` | `Drink` | 3 | 5 | required dictionary overran bank |
| TT2 | 23 | `On` | `Wear` | 3 | 4 | required dictionary overran bank |
| TT2 | 24 | `Of` | `Remove` | 3 | 6 | required dictionary overran bank |
| T22 | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| T22 | 3 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| T22 | 14 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| T22 | 25 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT6C | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT6C | 3 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| TT6C | 6 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT6C | 14 | `MY BOD` | `My body` | 6 | 7 | required dictionary overran bank |
| TT6C | 16 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT6C | 25 | `YS` | `Yes` | 3 | 4 | required dictionary overran bank |
| TT6C | 27 | `N` | `North` | 3 | 5 | required dictionary overran bank |
| TT6C | 29 | `W` | `West` | 3 | 4 | required dictionary overran bank |
| TT6C | 30 | `S` | `South` | 4 | 5 | required dictionary overran bank |
| TT6C | 93 | `R` | `Right` | 3 | 5 | required dictionary overran bank |
| TT6B | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT6B | 1 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT6B | 2 | `SM` | `Smell` | 3 | 5 | required dictionary overran bank |
| TT6B | 8 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT6B | 19 | `N` | `North` | 3 | 5 | required dictionary overran bank |
| TT6B | 21 | `W` | `West` | 3 | 4 | required dictionary overran bank |
| TT6B | 22 | `S` | `South` | 4 | 5 | required dictionary overran bank |
| TT6B | 23 | `FWD` | `Forward` | 4 | 7 | required dictionary overran bank |
| TT6B | 24 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT6A | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT6A | 1 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT6A | 2 | `SM` | `Smell` | 3 | 5 | required dictionary overran bank |
| TT6A | 7 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT6A | 13 | `DR` | `Drink` | 3 | 5 | required dictionary overran bank |
| TT4 | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT4 | 30 | `BOD` | `Body` | 4 | 5 | required dictionary overran bank |
| TT4 | 51 | `N` | `North` | 3 | 5 | required dictionary overran bank |
| TT4 | 53 | `W` | `West` | 3 | 4 | required dictionary overran bank |
| TT4 | 66 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT5 | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| TT5 | 2 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |
| TT5 | 10 | `N` | `North` | 3 | 5 | required dictionary overran bank |
| TT5 | 12 | `W` | `West` | 3 | 4 | required dictionary overran bank |
| TT5 | 13 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| TT5 | 23 | `YS` | `Yes` | 3 | 4 | required dictionary overran bank |
| TT5 | 76 | `BCK` | `Back` | 4 | 5 | required dictionary overran bank |
| TT5 | 107 | `SM` | `Small` | 4 | 5 | required dictionary overran bank |
| T25 | 0 | `SE` | `Look` | 3 | 4 | required dictionary overran bank |
| T25 | 22 | `GT` | `Take` | 3 | 4 | required dictionary overran bank |
| T25 | 30 | `AS` | `Ask` | 3 | 4 | required dictionary overran bank |

## Representative applied changes

| Bank | Index | Old | New | Slot bytes |
|---|---:|---|---|---:|
| TT3A | 10 | `HIT` | `Hit` | 4 |
| TT3A | 14 | `CHARM` | `Charm` | 5 |
| TT3A | 23 | `STOVE` | `Stove` | 5 |
| TT3A | 24 | `BED` | `Bed` | 5 |
| TT3A | 40 | `GUN` | `Gun` | 4 |
| TT3A | 49 | `NOTES` | `Notes` | 6 |
| TT3A | 50 | `PASS` | `Pass` | 5 |
| TT3A | 54 | `TEAR` | `Tear` | 4 |
| TT3A | 57 | `E` | `East` | 4 |
| TT3A | 59 | `MILL` | `Mill` | 7 |
| TT3A | 68 | `TRASH` | `Trash` | 5 |
| TT3A | 75 | `G-BT` | `G-boat` | 7 |
| TT3A | 76 | `NAZI` | `Nazi` | 6 |
| TT3A | 77 | `UBOAT` | `U-boat` | 6 |
| TT3A | 78 | `BANANA` | `Banana` | 7 |
| TT3A | 79 | `GABN` | `Gabin` | 5 |
| TT3A | 83 | `TRUFT` | `Truffaut` | 7 |
| TT3B | 6 | `MILL` | `Mill` | 7 |
| TT3B | 9 | `GUN` | `Gun` | 4 |
| TT3B | 10 | `CHARM` | `Charm` | 5 |
| TT6C | 11 | `MARY` | `Mary` | 4 |
| TT6C | 28 | `E` | `East` | 4 |
| TT6C | 61 | `AMACH` | `Amacha` | 7 |
| TT6C | 68 | `FRED` | `Fred` | 5 |
| TT6C | 69 | `BOB` | `Bob` | 4 |
| TT6C | 75 | `PUMA` | `Puma` | 5 |
| TT6C | 85 | `MEYER` | `Meyer` | 5 |
| TT6C | 87 | `NIK` | `Nick` | 4 |
| TT6C | 91 | `LEFT` | `Left` | 4 |
| TT6C | 92 | `UP` | `Up` | 3 |
| TT6B | 7 | `MARY` | `Mary` | 4 |
| TT6B | 16 | `TENT` | `Tent` | 4 |
| TT6B | 20 | `E` | `East` | 4 |
| TT6B | 32 | `DNG` | `Dung` | 4 |
| TT6B | 35 | `ISIS` | `Isis` | 4 |
| TT6B | 38 | `IRQ` | `Iraq` | 4 |
| TT6B | 41 | `EGYPT` | `Egypt` | 5 |
| TT6B | 42 | `DAVID` | `David` | 5 |
| TT6B | 54 | `WAG` | `Wag` | 7 |
| TT6B | 55 | `FLEA` | `Fleas` | 5 |
| TT6B | 59 | `HOOF` | `Hoof` | 4 |
| TT6B | 60 | `TAIL` | `Tail` | 4 |
| TT6B | 61 | `MANE` | `Mane` | 5 |
| TT6A | 9 | `NOD` | `Nod` | 5 |
| TT6A | 15 | `ELDER` | `Elder` | 5 |
| TT6A | 27 | `MARY` | `Mary` | 4 |
| TT6A | 29 | `MILL` | `Mill` | 4 |
| TT6A | 39 | `BK` | `Tile` | 4 |
| TT4 | 24 | `LCK` | `Lick` | 4 |
| TT4 | 41 | `DN` | `Down` | 4 |
| TT4 | 52 | `E` | `East` | 4 |
| TT4 | 59 | `GRIND` | `Grind` | 5 |
| TT4 | 60 | `BOIL` | `Boil` | 5 |
| TT4 | 70 | `PLATO` | `Plato` | 5 |
| TT4 | 78 | `ARIS` | `Aris` | 4 |
| TT4 | 93 | `FIG` | `Fig` | 5 |
| TT5 | 11 | `E` | `East` | 4 |
| TT5 | 27 | `SCHED` | `Schedule` | 7 |
| TT5 | 28 | `CALL` | `Call` | 7 |
| TT5 | 31 | `ROOF` | `Roof` | 6 |
| TT5 | 56 | `MARINE` | `Marine` | 6 |
| TT5 | 58 | `RED` | `Red` | 4 |
| TT5 | 65 | `WHITNY` | `Whitney` | 7 |
| TT5 | 67 | `ETNA` | `Etna` | 4 |
| TT5 | 71 | `GIN` | `Gin` | 5 |
| TT5 | 72 | `PLOW` | `Plow` | 5 |
| TT5 | 90 | `TENS` | `Tens` | 6 |
| TT5 | 91 | `ONES` | `Ones` | 5 |
| TT5 | 109 | `MEYER` | `Meyer` | 5 |
| T25 | 11 | `MEYR` | `Meyer` | 5 |
| T25 | 14 | `POT` | `Pot` | 4 |
| T25 | 24 | `DK` | `Desk` | 4 |
| T25 | 38 | `ME` | `Me` | 3 |

## Validation

Passed:

```bash
PYTHONPATH=/mnt/data/time_twist_full_label/work python -m unittest /mnt/data/time_twist_full_label/work/tests/test_ui_unit.py -v
PYTHONPATH=/mnt/data/time_twist_full_label/work python -m compileall -q /mnt/data/time_twist_full_label/work/time_twist /mnt/data/time_twist_full_label/work/tests/test_ui_unit.py /mnt/data/time_twist_full_label/work/integration_tests/test_ui.py
PYTHONPATH=/mnt/data/time_twist_full_label/work python /mnt/data/validate_full_label_menu_audit.py
```

The full public unit-suite command still does not complete in this source-only handoff because the environment is missing `hypothesis`, generated comparison outputs, and the full project checkout markers expected by some release tests.

## Full-word experiment follow-up

A later experimental pass pushed the fixed menu/choice labels further by using
existing dictionary entries and a small number of safely reused dictionary
reservations. See [`FULL_WORD_MENU_EXPERIMENT.md`](FULL_WORD_MENU_EXPERIMENT.md)
for the applied labels, remaining blockers, and validation results.
