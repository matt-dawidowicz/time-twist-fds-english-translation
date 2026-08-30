# Runtime Playtest Matrix

## Candidate under test

**A fresh candidate is required after the final pre-playtest hardening.** The
previously listed candidate predates release-code changes and must not be used
for the continuity run, even if a fresh build happens to reproduce the same FDS
byte hashes. Build from the exact revision you intend to test, then copy the new
manifest values into this section before starting.

| Build | SHA-256 | Bytes |
| --- | --- | ---: |
| Four-side | `PENDING FRESH CANDIDATE BUILD` | Pending |
| Zenpen | `PENDING FRESH CANDIDATE BUILD` | Pending |
| Kouhen | `PENDING FRESH CANDIDATE BUILD` | Pending |

Candidate manifest SHA-256: `PENDING FRESH CANDIDATE BUILD`.

Release-code tree SHA-256: `PENDING FRESH CANDIDATE BUILD`.

Source-lock SHA-256: `238E98039F1D6FDD2E8A287766106C1C4F456B88DD25D9190E2CB32B98E7BD44`.
The approved non-code inputs are unchanged by the final hardening; the fresh
candidate is required because the release-code provenance changed.

## Test protocol

1. Record emulator name/version, FDS BIOS hash, platform, controller mapping, and whether automatic FDS disk switching is disabled.
2. For the continuity run, cold-boot the four-side candidate and do not reset or open Kouhen as a new game. Save states may be used only for isolated reproduction after a clean continuity pass has reached the same scene.
3. At `PART 1 / SIDE B`, select the second side (`TT1` Side B). At `PART 2 / SIDE A`, select the third side (`TT2` Side A). Record every later side request and follow the in-game prompt; never substitute a reset.
4. Exercise the wrong-disk path once, confirm `WRONG DISK! / TRY ANOTHER SIDE`, then recover through the disk menu without resetting.
5. Capture a screenshot before advancing every changed line listed in `audit/EDITORIAL_CHANGELOG.json`, prioritizing the high-risk records named in the integration regression test.
6. For each text box, watch separately for wrapping/clipping, stale right-edge tiles, accidental blank lines, and typewriter/audio continuing over blank output.
7. Save and reload through the game's own save system. Do not count emulator save states as save/load validation.
8. Mark a row `PASS` only when progression, display, audio timing, input, and adjacent transitions all remain correct.

## Continuity and scene matrix

| ID | Side / bank focus | Scene and path | Required checks | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| NEG-01 | Kouhen direct boot / `SON-KOUH` | Boot Kouhen by itself as a negative test | Centered `PLEASE START WITH / PART 1`; no crash or stray Japanese | Screenshot + emulator/version | Pending |
| Z-01 | TT1 Side A / `NOV4` | Cold boot, Nintendo phase, title build, clock, PUSH START | Exact split-logo animation; subtitle; lower machine art; blue hand center/rotation; no seam; START exits; B behavior unchanged | Video or frame sequence | Pending |
| Z-02 | `TT1A` | Opening news and personality-test introduction | `TT1A/g0/r1` reads naturally; no invented TV wording; all narration clears; no overflow | Screenshot + record IDs | Pending |
| Z-03 | `TT1A` | Complete personality questionnaire and every result profile | All yes/no prompts; every profile; punctuation; `consommé` accent baseline; no wrap corruption | Screenshots of all result pages | Pending |
| Z-04 | `TT1A` → `TT1B` | Fortune result, city narration, museum approach | Scene transition, narration rhythm, no stale letters, no blank typewriter line | Screenshots + notes | Pending |
| Z-05 | `TT1B` | Museum exterior and object/menu navigation | `MUSEUM / EAST / WEST`; no isolated letters; all selectable objects/actions are clear | Screenshot of every menu state | Pending |
| Z-06 | `TT1B` | Girl, exhibits, Devil reveal, priest, Dr. Simon, Time Belt | Museum question remains a question; stammer/telepathy timing; father’s collection; Time Belt meaning; speaker voice | Changed-record screenshots | Pending |
| Z-07 | `TT1B` | Forest, church, television, city narration | `When did I last see it?`; `AROUND / GROUND`; `ROOM / PRIEST / MEMBER`; complete chant; `Wars still rage abroad,`; no audio/text mismatch | Screenshots + audio observation | Pending |
| DISK-01 | TT1 A→B | In-game `PART 1 / SIDE B` request | Correct English prompt; select second side; resume without reset or state loss | Before/after screenshots | Pending |
| DISK-02 | Disk error path | Intentionally select a wrong side once | `WRONG DISK! / TRY ANOTHER SIDE`; choose correct side and recover without reset | Screenshot + recovery steps | Pending |
| Z-08 | `TT2` | 1428 France arrival, Pierre, town, commands, quizzes | Location/date; medieval register; all command/object labels; memo and drink lines; quiz answers and failure paths | Scene screenshots | Pending |
| Z-09 | `TT2` / `T22` | Jeanne, Bishop, witch hunt, prison and execution-ground flow | Bishop commands; pyre line; all puzzle requirements unchanged; no branch dead ends | Record IDs + progression notes | Pending |
| Z-10 | `T22` | Pact discovery and Jeanne rescue | Pact grammar and blasphemous reversal; candle; armor instruction; scene transition; controls/timing | Changed-record screenshots | Pending |
| Z-11 | `TT3A` | POW camp, tunnel, town, Rebecca network, torn note | “Anti-Hitler plot”; Rebecca as organization; separate scientist/POW logic; note spatial layout; all command states | Screenshots, especially torn note | Pending |
| Z-12 | `TT3A` / `TT3B` | Gestapo reveals, Schmidt, Hitler, border | Gestapo grammar; Schmidt’s reveal; military ranks; Hitler confrontation; charm/prayer; transition integrity | Changed-record screenshots | Pending |
| SAVE-01 | Zenpen | Save before a major puzzle and before a disk request; power-cycle; reload | Correct position, inventory, puzzle flags, font/UI, and next transition | Save/load log | Pending |
| DISK-03 | Zenpen→Kouhen | In-game `PART 2 / SIDE A` request | Select third side without opening a new game or resetting; engine/font/progression persist | Before/after screenshots | Pending |
| K-01 | `TT4` | Ancient Athens, Nicras, priest, Athena, town treatment | Period voice; no imported “Yomi”; commands; item acquisition; transitions | Changed-record screenshots | Pending |
| K-02 | `TT4` | Hermes, Artemis, Hades, Cerberus, underworld riddles | “the underworld” consistency; riddle wording/answers; Alexander reveal; rival-city quiz | Screenshots of every riddle state | Pending |
| K-03 | `TT5` | 1864 Atlanta opening, Belle, emancipation, racist violence | Historical register preserved without unsupported “Dixie”; Belle label not duplicated; no sanitizing or embellishment | Changed-record screenshots | Pending |
| K-04 | `TT5` | Plantation work loop and farm commands | Exact quantities/measurements; every work state; menu clarity; no altered puzzle requirements | Step-by-step work log | Pending |
| K-05 | `TT5` / `T25` | Meyer, Lincoln, mansion, kidnapping, river escape | Sarcasm/politeness; Lincoln voice; river math/puzzle exactness; faint-voices narration; all transitions | Screenshots + puzzle inputs | Pending |
| SAVE-02 | Kouhen | Save in Kouhen, power-cycle from Part 1 as required, reload through normal flow | Inventory/flags/chapter continuity; correct disk prompts; no direct-boot shortcut | Save/load log | Pending |
| K-06 | `TT6A` | Nazareth, Joseph, Mary, Kashim, angel/fiend transition | Pregnancy explanation complete; donkey voice; prophecy/census setup; article/punctuation fixes display correctly | Changed-record screenshots | Pending |
| K-07 | `TT6B` / `TT6C` | Bethlehem, inn, Magi, child naming | Biblical names/register; gifts and puzzle states; `The perfect name`; no accidental theological rewrite | Screenshots + progression notes | Pending |
| K-08 | `TT6C` | Return to final museum and date entry | September 25, 1995 transition; museum state; text clearing; no old tiles after short replacements | Video or screenshot sequence | Pending |
| K-09 | `TT6C` fixed quiz table | Retrospective quiz | Every question; every correct and wrong answer; compact labels; no clipping/address-shift artifacts | Screenshot per question/branch | Pending |
| K-10 | `TT6C` | Devil confrontation | Self-identification, prejudice/conflict speech, savior line, choices/commands, menace and rhythm | Changed-record screenshots | Pending |
| K-11 | `TT6C` / `TT6D` | Final invocation, ending, post-ending behavior | Invocation punctuation; final text; ending/credits; no lockup, stale tiles, or missing line; expected final state | Full ending capture | Pending |
| UI-01 | All chapters | Exhaustive command/object/answer menus | Each label intelligible; selection cursor and input unchanged; address-locked labels do not bleed into neighbors | Menu screenshot set | Pending |
| TEXT-01 | All changed records | Long-to-short and short-to-long replacement stress | No clipping, stale letters, unintended blanking, or extra typewriter sounds | Before-advance screenshots | Pending |
| BRANCH-01 | All chapters | Obscure optional inspections, wrong answers, repeated actions, backtracking | No untranslated text, broken speaker identity, softlock, or state corruption | Branch log | Pending |

## Runtime issue record

Create one entry per defect. Do not merge distinct failure modes such as stale tiles and typewriter/audio mismatch.

```text
Issue ID:
Candidate SHA-256:
Emulator/version/platform/FDS BIOS SHA-256:
Severity: blocker | major | minor | cosmetic
Status: open | fixed-static | fixed-runtime-verified | deferred
Screenshot/video path or exact scene:
Disk/product/side:
Bank and record ID (if identifiable):
Japanese source:
Current English:
Observed behavior:
Expected behavior:
Root cause:
Smallest safe source-level fix:
  - scenario prose: work/translations/<BANK>.json
  - engine/font/title/UI: src/time_twist/
Controls before/after:
Fixed address/tail/capacity affected:
Regression test to add:
Official rebuild command:
Unit/integration/source-lock/hash evidence:
Targeted runtime reproduction steps:
Adjacent scenes rechecked:
Remaining risk:
```

## Release gate

Do not promote `work/release_target.json` or call the game release-ready until every blocker/major row passes in an end-to-end Zenpen→Kouhen continuity run, both documented disk changes succeed without reset, game saves reload correctly, and the final ending has been reached from a fresh boot.
