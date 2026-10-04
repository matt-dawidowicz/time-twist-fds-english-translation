# v64 TT1A twelve-month Fortune Teller selector

v64 corrects a release-lineage regression in the TT1A Fortune-Telling Service
Center.

## Regression

The intended English localization had already replaced the retail two-stage
birth-month selector with one direct twelve-month screen. A later historical
release checkpoint restored the native presentation:

```text
Jan   May
Feb   Jun
Mar   Jul-Dec
Apr
```

Selecting `Jul-Dec` then opened July through December on a second menu. Because
birth month is not stored or scored by the Fortune Teller, that doorway adds no
gameplay meaning.

## v64 behavior

v64 restores the reviewed 4-by-3 English selector:

```text
Jan   May   Sep
Feb   Jun   Oct
Mar   Jul   Nov
Apr   Aug   Dec
```

The twelve real month records are directly selectable. The old `Jul-Dec`
doorway record is retained in the fixed-text table for address compatibility but
is unreachable from the active month descriptor.

All twelve choices continue to the existing personality-test entry at `$A305`.
The underlying Fortune Teller algorithm is unchanged: blood type alone selects
the displayed personality profile.

## Runtime geometry

The restored NOV2 path is the runtime-tested September v4/v5 design, adapted so
it coexists with the later Back/Cancel parent guard.

- 9-12 visible choices use three columns of four rows.
- Choice IDs occupy `$0423-$042E`.
- Width metadata is relocated to `$0433-$043E`.
- Leading-cursor X coordinates are `$20`, `$68`, and `$B0`.
- Text columns are 5, 14, and 23.
- Slots 8-11 use the historical +8-pixel trailing-arrow correction.
- Menus with eight or fewer visible choices retain the existing two-column path.
- The v63 parent-menu Back/Cancel semantics are preserved.

The maintained implementation is
`work/time_twist/tt1a_month_menu.py`, with the reproducible candidate tool at
`work/tools/build_v64_month_menu.py`.

## Candidate verification

Four-side candidate:

`Time-Twist-v64-12-month-fortune-menu-candidate.fds`

SHA-256:

`0D3B432A15A8757C55B803972D1D867D1CD8793DDCBD7B35ECEBA2AA01EB2F84`

Size: 262,000 bytes.

Relative to v63:

- 105 bytes differ total;
- NOV2: 96 changed bytes;
- TT1A: 9 changed bytes;
- every other FDS file is byte-identical;
- all 39 scored quiz result tables still pass the static route audit.

The month descriptor resolves all twelve labels exactly once and excludes the
`Jul-Dec` doorway. Static navigation checks cover every slot and all four
directions.

Final visual/input certification should still be performed in Mesen from a clean
v64 state, especially Sep/Oct/Nov/Dec so the third column and trailing cursor are
exercised. Do not validate this runtime change with a save state that contains
resident NOV2 state from v63 or an earlier candidate.
