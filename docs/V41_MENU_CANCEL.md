# v41 menu cancellation

Reproduced in v40 using its supplied museum save: A opens Look's Sky / Area /
Museum menu, but B does not return. The earlier parent guard mistook menu flag
bit 3 being clear for "no parent". In fact that flag controls saving a new Back
destination. A submenu with the bit clear must retain its inherited destination.

A second defect appears when B is rejected at the root: the dispatcher returns
before the normal redraw path, leaving an invisible but active menu.

## Exact changes

| CPU address | Before | After | Effect |
| --- | --- | --- | --- |
| $6BA9 | BEQ $6B70 | BEQ $6BBB | Preserve inherited Back destination |
| $99DE | BEQ $99DB | BEQ $998C | Redraw when no saved parent exists |
| $99E3 | BEQ $99DB | BEQ $998C | Redraw when saved parent is current menu |

Only the three branch operands change. The existing $6A2E pointer comparison,
parentless check, title-exit state clearing, decoder and all scenario data stay
identical. The obsolete clearing stub is unreachable from menu setup.

The builder first reproduces and verifies v40, verifies the exact setup,
dispatch and self-parent-guard bytes, applies these changes, then checks the
v41 output hash. The immutable recovery compiler is unchanged. Historical
engineering paths may still contain the superseded guard; this correction is
in the canonical release builder.

SHA-256 (262,000-byte four-side image):
`0e9d93ede88231fd5a864b172d32d035d6aad3a378574ceffd633df4cedd5530`.

## Verification

- Native 6502 execution: all 256 descriptor flag values preserve or install the
  appropriate parent; 24 Back cases cover absent, self and distinct parents,
  including one-choice menus. Total 280 cases pass.
- Mesen CE 2.2.1: Look submenu returns to Look / Talk / Move with B; another B
  keeps that root menu visible; A then opens Look again.
- v41's converted museum save updates exactly the three engine bytes. Reload
  verifies the full resident NOV2 against the v41 ROM before exercising input.
- All scenario banks and text-renderer routines are byte-identical to v40.
  The existing 1,299-record dialogue audit remains applicable.

This is a targeted menu correction, not a complete game playthrough. Save and
load menus, chapter transitions and every story-specific menu were not all
replayed. The generic native Back tests cover pointer cases independently of
visible choice count. Use the v41 save with the v41 ROM.
