# Time Twist FDS English translation: source-only continuation handoff

This archive contains the current Python code, tests, Lua debugging probes,
and documentation for the Time Twist FDS English translation project. It is
safe to upload to a regular ChatGPT conversation for code review or planning.

It intentionally excludes all FDS images, extracted disk files, rebuilt
components, title/reference artwork, emulator saves, screenshots, generated
playtest candidates, and translation-script data derived from the game.

## Start here

1. Read `README.md` and `QUICKSTART.md`.
2. Read `docs/ARCHITECTURE.md` and `docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md`.
3. For the current defect, inspect `work/time_twist/ui.py`,
   `work/time_twist/fds.py`, and `work/tools/disassemble_6502.py`.
4. Run the fixture-free test command when the project dependencies are
   available: `python work/run_tests.py unit`.

## Current playtest state

- Preserve all current uncommitted work if this archive is used alongside the
  original checkout. Do not commit, publish, or overwrite the existing build.
- The current valid four-side playtest candidate is **not included**. Its
  SHA-256 is
  `F5C723B2C3FCAF59CDB47F84571228F5A2D8969178BD4C0B68EF6FB43004C964`.
- The post-START title transition repair is present and still needs only manual
  visual confirmation. Do not change the title logo or subtitle during the
  disk-retry investigation.
- `Save` and both `Load` labels are confirmed fixed.
- The normal disk-request labels are correct and must not be changed:
  `Part 1 / Side A`, then `Part 2 / Side B`.

## Same-side disk retry fix candidate

When the game requests a different FDS side and the player chooses the side
that is already inserted, NOV2 reaches a native side-number error message
(`A-B side / disk number / error`) instead of the later `Wrong disk!` recovery
records. With the English font installed, those unpatched Japanese packed bytes
rendered as gibberish.

This handoff now includes a source-guarded, size-neutral text fix for that
path in `work/time_twist/ui.py`:

- `$26CC`: `Wrong sid`
- `$26D4`: `e inserted.`
- `$26DE`: `{CTRL:0}Try again.`

Together they render as `Wrong side inserted.` followed by `Try again.` The
normal disk-request labels remain unchanged: `Part 1 / Side A`, then
`Part 2 / Side B`. This still needs manual Mesen confirmation on a rebuilt
candidate: intentionally select the already inserted side, capture the retry
screen, then select the requested side and confirm recovery without reset.

## Constraints

- FDS text is packed and dictionary-compressed, never ASCII.
- Preserve fixed footprints, control tags, source guards, native behavior, and
  public/private fixture separation.
- `work/translations/*.json` is deliberately absent from this handoff because
  it contains ROM-derived game text. Do not fabricate replacements.
- A static patch, source guard, or test does not substitute for runtime proof.

## Camel dialect patch fragment

A playthrough note reported that the TT6B camel in the Israel/Nazareth chapter
uses Ibaraki-style rural dialect. This public source handoff still excludes the
private `work/translations/*.json` files, so the playable scenario JSON cannot
be edited directly here. Instead, apply this fragment in the full private
checkout:

- `work/translation_patches/TT6B_camel_ibaraki_style.json`

The fragment changes only `TT6B/g0/r29`, `TT6B/g0/r30`, and `TT6B/g0/r31`.
It preserves control-code order and passes display-width/glyph validation. See
`docs/DIALECT_LOCALIZATION_NOTES.md` for the localization rationale.
