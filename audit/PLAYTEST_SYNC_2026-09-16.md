# Playtest sync — 2026-09-16

## Scope

This update synchronizes the repository's production text and fixed-menu declarations with the current playtested **v36** ROM.

The supplied v35 and v36 ROMs differ semantically at exactly one scenario record:

- `TT3A/g2/r7`: `Voice: Wait, Cougar…` -> `Frankie: Wait, Cougar…`

Runtime playtest evidence identifies the off-screen speaker: the immediately following interaction is Frankie handing Cougar the pendant (`Frankie: Take this…`). The previous staging-dependent speaker ambiguity is therefore resolved.

## Production-text synchronization

The production override maps were refreshed from the current materialized v36 scenario text for the banks changed during the playtest cycle:

- `TT1B`
- `TT2`
- `T22`
- `TT3A`
- `TT3B`
- `TT4`
- `TT5`
- `T25`
- `TT6A`
- `TT6B`
- `TT6C`

This captures the accumulated wording, retranslation, line-flow, and control-code fixes made during playtesting, including the France dialogue revisions, Bishop/Jeanne retranslation, T22 continuation-scroll correction, Germany polishing, later-chapter English cleanup, and finale punctuation/wording changes.

## Fixed-menu synchronization

`work/time_twist/ui_fixed_tables.py` now matches the playtested fixed labels, including:

- context-appropriate `Outside`/`Enter` labels instead of generic `Out`/`In` where verified;
- `Data` -> `Info`;
- France labels `Empty bottle`, `Notice`, `Bottles`, and `Old Man`;
- compact quiz answers `daVinci`, `DePalma`, `DeNiro`, and `UThant` required by the two-column menu width;
- matching fixed-menu regression-test expectations.

## Remaining staging-dependent ambiguities

Three runtime-evidence items remain unresolved:

1. `TT3A/g2/r30` — exact spatial reconstruction/order of the torn-note fragments.
2. `TT3B/g0/r24` — whether the line is Hitler speaking normally or the Devil speaking through Hitler.
3. `TT4/g4/r14` — identity of the unlabeled `Wait` warning.

`TT3A/g2/r7` is no longer unresolved; playtest evidence identifies the speaker as Frankie.

## Source-layer policy

The certified base maps remain intact where the change is production wording or layout. The playable release authority is represented in `work/production_overrides/*.json` plus the fixed UI declarations, consistent with the repository's layered translation architecture.
