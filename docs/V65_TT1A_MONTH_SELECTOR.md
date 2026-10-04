# v65 TT1A safe twelve-month Fortune Teller selector

v65 supersedes and withdraws v64.

## Player-visible result

The English release still presents all twelve real months directly:

```text
Jan   May   Sep
Feb   Jun   Oct
Mar   Jul   Nov
Apr   Aug   Dec
```

The retail `Jul-Dec` doorway record remains physically present for address
compatibility but is unreachable from the active descriptor. All months still
converge on the existing `$A305` personality-test continuation; birth month
does not affect the displayed profile.

## Safety architecture

v65 is rebuilt from the v63 runtime rather than layering another fix on v64.

- Per-choice width metadata lives at `$0470-$047B`.
- The native predicate scratch range ends at `$046F`.
- Persistent event flags begin at `$0480`.
- Modern `$043B` maximum-width state is left intact.
- The `$814A` Back/Cancel parent guard is byte-identical to v63.
- Menus with eight or fewer choices use the v63 geometry path.
- 9-12 choice menus use leading cursor X values `$20/$68/$B0`.
- Text columns are 5/14/23.
- The special text helper rejoins at `$94A4`, before the normal code adds row
  offset and the `$22xx/$23xx` nametable high byte.
- The canonical v63 trailing-span helper at `$8137` is retained. The old v5
  third-column +8 compensation is not used.

For the twelve month slots, text starts are statically proven as:

`$2245 $2285 $22C5 $2305 $224E $228E $22CE $230E $2257 $2297 $22D7 $2317`

All are nametable addresses; no month-render path targets `$00xx` CHR RAM.

## Candidate

`Time-Twist-v65-12-month-safe-candidate.fds`

SHA-256:

`1114116674CBFCD390FD05A022201F63AFB2786A2C1A313AB0F7D5E5055FFACA`

Static verification:

- four FDS sides parse;
- only NOV2 and TT1A differ from v63;
- NOV2 changes: 73 bytes;
- TT1A changes: 9 bytes;
- all 39 scored quiz result tables still pass;
- all twelve month navigation states remain bounded;
- v64's `$043B` collision is absent;
- v64's `$00xx` CHR-write path is absent.

Runtime certification still requires a clean v65 Mesen session. Do not reuse a
v64 save state that may contain resident NOV2 state from the broken build.
