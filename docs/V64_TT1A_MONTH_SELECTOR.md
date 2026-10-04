# v64 TT1A twelve-month Fortune Teller selector — WITHDRAWN

**v64 is unsafe and must not be used.** It is retained only as defect history.

Runtime testing exposed whole-screen graphics corruption while navigating the
month selector. Two independent root causes were confirmed:

1. v64 stored twelve menu-width bytes at `$0433-$043E`. The modern NOV2
   runtime already owns `$043B` as live first-column maximum-width state.
   Width slot 8 therefore collided with `$043B`.
2. v64 copied the historical v4 helper at `$821B` unchanged. That helper
   jumped to `$94AE`, after the modern renderer's `$22xx` PPU-address setup.
   The special middle/third-column path could therefore write glyph data to
   `$00xx` CHR pattern RAM, producing screen-wide tile corruption.

The broken candidate hash is retained for identification only:

`0D3B432A15A8757C55B803972D1D867D1CD8793DDCBD7B35ECEBA2AA01EB2F84`

Use **v65 or later**. The v64 builder intentionally aborts.
