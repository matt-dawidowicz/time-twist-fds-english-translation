# Playtesting Time Twist

This is the short guide for players helping test the English translation.
You do not need to understand the source code to submit a useful report.

## Before you start

Get the current candidate and its SHA-256 from the project maintainer or the
playtest announcement. This public repository deliberately contains source
code and documentation only: it does not host game images, FDS BIOS files,
emulator packages, save states, or screenshots.

Record the following before playing:

- candidate filename and SHA-256;
- emulator name and version;
- FDS BIOS SHA-256, if the emulator uses one;
- controller mapping, especially `Start` and `B`;
- whether overscan cropping is disabled.

Use a clean cold boot for a continuity run. Emulator save states are welcome
for reproducing an issue, but they do not prove the game's own save/load
behavior.

### Mesen FDS state must also be clean

Mesen can persist FDS disk writes in a filename-matched `.ips` file in its
`Saves` directory. If a candidate is rebuilt later under the same filename,
that older sidecar can be applied to the new image and create a false runtime
regression even when the candidate bytes are correct.

Before the **first cold boot of a newly built candidate** in Mesen:

1. close Mesen;
2. check its `Saves` directory for `<candidate stem>.ips`;
3. if one exists, move or rename it as evidence instead of deleting it
   blindly;
4. then launch the candidate and begin runtime certification.

If you have a source checkout, the maintainer preflight is read-only and can
perform this check:

```powershell
python work/tools/check_mesen_fds_state.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --mesen-save-dir "D:\Emulation\Mesen\Saves"
```

Do **not** keep clearing the sidecar during the same candidate's save/load
testing. Once the first boot starts from clean state, any new persistence made
by that exact candidate is part of the behavior being tested.

## What to test first

Start with the four-side candidate unless the maintainer asks for a focused
test. These checks are especially valuable:

1. Watch the full title sequence before pressing `Start`. The Nintendo-to-title
   handoff should remain blank while the display state changes; it must not
   flash the old Nintendo screen with English title graphics.
2. At a one-choice menu with nowhere to go back, press `B`. It should do
   nothing. On a normal multi-choice menu with a real parent, `B` should still
   go Back/Cancel.
3. Follow the in-game disk prompts without resetting. At `PART 1 / SIDE B`,
   choose the second side; at `PART 2 / SIDE A`, choose the third side.
4. Try one wrong side deliberately, then recover through the in-game disk
   flow. The short retry copy should be readable: `Bad side.` / `Try again.`
5. Save through the game's own Save command, power-cycle or reopen as the game
   requires, then Load through the normal flow.
6. Exercise command, object, topic, answer, and quiz menus. Report clipped,
   garbled, abbreviated, stale, or untranslated labels.

The current candidate's static audit decodes all 721 configured menu labels as
full-word matches. Runtime testing should concentrate on what static decoding
cannot prove: opening menus on both sides of records 32, 64, and 96, moving the
cursor across those page boundaries, selecting each kind of entry, and using
Back/Cancel without stale or misaddressed text.

For the complete story-by-story checklist, use
[the runtime playtest matrix](docs/PLAYTEST_MATRIX.md). It is intentionally
more detailed than a first-session playtest.

## What makes a report actionable

Submit one issue per problem. You do not need to fill in every field below;
just include enough detail for someone else to reproduce the problem. A
screenshot or short video is especially helpful for visual bugs, but a clear
written route is useful too.

```text
Candidate SHA-256:
Emulator/version/platform:
FDS BIOS SHA-256 (if applicable):
Disk, side, scene, and menu or record ID (if known):
Inputs/reproduction steps:
Expected behavior:
Actual behavior:
Screenshot/video/save-state location (if any):
Severity: blocker | major | minor | cosmetic
```

For a suspected original-game bug, also test the same route on the Japanese
release if you can. That distinction prevents a native game behavior from
being mislabeled as a translation regression.

## Please do not put these in the repository

Do not attach or commit original or patched FDS images, FDS BIOS files,
extracted retail data, emulator settings, save states, or generated candidates to
a pull request. Report the candidate hash and your observations instead.

## Want to help beyond playtesting?

- Improve dialogue: [translation contributor guide](CONTRIBUTING_TRANSLATION.md)
- Improve tooling or tests: [code contributor guide](CONTRIBUTING_CODE.md)
- Understand the project: [documentation index](docs/README.md)
- Review the complete route checklist: [runtime playtest matrix](docs/PLAYTEST_MATRIX.md)
