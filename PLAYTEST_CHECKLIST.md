# Playtest checklist

Use this for a human playtest of one exact candidate. Automated tests do not
replace this checklist. The detailed scene-by-scene coverage and current
candidate hashes live in [docs/PLAYTEST_MATRIX.md](docs/PLAYTEST_MATRIX.md).

## Candidate and setup

- [ ] Candidate filename, SHA-256, and manifest recorded
- [ ] Emulator name, version, platform, and FDS BIOS hash recorded
- [ ] Controller mapping recorded
- [ ] Overscan correction/cropping disabled during visual checks
- [ ] Clean cold boot used for the continuity run

Do not count an emulator save state as a save/load result. Use save states only
to reproduce an issue after reaching the same scene through normal play.

## Core flow

- [ ] Zenpen boots from a clean start
- [ ] Kouhen direct boot shows its intended warning rather than crashing
- [ ] Title sequence, clock, subtitle, START, and B behavior are correct
- [ ] Zenpen-to-Kouhen transition completes without reset
- [ ] Kouhen boots as part of the continuity run
- [ ] Ending and credits reached, if the path is complete

## Storage and disks

- [ ] Normal disk/side prompts are clear and resume the game
- [ ] One deliberate wrong-disk prompt is tested and recovers correctly
- [ ] Zenpen-to-Kouhen side swap works without reset or lost state
- [ ] In-game save works
- [ ] Saved game reloads through the normal game flow

## Text and UI

- [ ] Major scenario paths and optional inspections are exercised
- [ ] Personality-question sequence and all result profiles are readable
- [ ] Command, object, topic, and quiz menus are understandable
- [ ] Long and short replacements leave no stale letters or blank timing
- [ ] No overflow, bad wrap, clipping, untranslated text, or wrong speaker
- [ ] Cursor, input, and menu clearing remain correct

## Evidence and judgment

- [ ] Screenshots or video captured for changed/high-risk scenes
- [ ] Save point or precise reproduction path kept for each issue
- [ ] Candidate hash and disk/side recorded with each issue
- [ ] Blockers and major issues retested after a fix
- [ ] Final result marked: pass / pass with known minor issues / fail

## Report an issue

Record one problem per entry. Include:

```text
Candidate SHA-256:
Emulator/version/platform/FDS BIOS SHA-256:
Disk, side, scene, and record ID (if known):
Inputs/reproduction steps:
Expected behavior:
Actual behavior:
Screenshot, video, or save-state path:
Severity: blocker | major | minor | cosmetic
```

For a potential game bug, also report whether the same behavior occurs on the
Japanese original. This separates translation regressions from original-engine
behavior. See [Deferred polish and fixes](docs/FUTURE_POLISH_AND_FIXES.md) for
the evidence required before changing native behavior.
