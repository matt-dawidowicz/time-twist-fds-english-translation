# Final Technical Editor Report

## Status

**Candidate generated; not promoted; not release-ready.**

This pass made **85 focused scenario-record edits across 10 banks**. Playable story text was edited only in `work/translations/*.json`. No source changes were made to `work/time_twist/` engine, font, title, or fixed UI code because the static audit did not prove a defect there that justified runtime-risking binary behavior changes.

Runtime playtesting was **not performed** in this environment. No Mesen/MesenCE or alternate FDS emulator binary and no FDS BIOS were present. Existing Mesen Lua probes and prior RAM/CHR captures were inspected, but they are not evidence of the new candidate running end to end.

## Milestone 1 — Baseline and authority

### 1. What changed

Before editorial work, the bundle was unpacked and the required documentation was read in the requested order. The baseline pipeline, release lock, candidate rebuild, manifest, private fixtures, fixed tables, and bank capacities were inspected.

The line endings of `work/release_sources.json` were normalized from CRLF to LF. This corrected a packaging-only hash mismatch: the archive bytes hashed to `F385F0E35658111BB480E1053D251654423A91E49B88855CB6895AFB6C025BA1`, while the canonical LF file used by the prior promoted target hashed to `630E451F64D882DDED36C07622F4D42DDD4F892C15F01A902072935B1699A4AD`.

### 2. Why it is correct

The initial candidate rebuild still reproduced all three previously promoted ROM hashes exactly, proving that the baseline failure was the source-lock file's newline representation, not changed game content or nondeterministic rebuilding.

### 3. Deliberately left unchanged

No finished `.fds` file or rebuilt bank was hex-edited as the source of a fix. Record IDs/order, controls, source guards, fixed tails, dictionary rules, and release validation were retained.

### 4. Tests, hashes, and evidence

- Initial tests: 104/105 passed; the only error was the strict source-lock tie.
- Baseline release lock: all 16 approved inputs validated.
- Baseline rebuild reproduced the prior Zenpen, Kouhen, and four-side hashes byte-for-byte.

### 5. Remaining risks

Static reproducibility did not establish scene progression, input behavior, disk swaps, saves, animation timing, clearing, or ending continuity.

## Milestone 2 — Translation and editorial polish

### 1. What changed

The complete 1,299-record playable scenario corpus and the generated 2,052-row bilingual/fixed-text workbook were reviewed. **85 source records** were revised:

| Bank | Changed records |
| --- | ---: |
| `T22` | 9 |
| `TT1A` | 6 |
| `TT1B` | 8 |
| `TT2` | 8 |
| `TT3A` | 11 |
| `TT3B` | 5 |
| `TT4` | 14 |
| `TT5` | 14 |
| `TT6A` | 3 |
| `TT6C` | 7 |

The edits address objective meaning, grammar, voice, register, terminology, historical context, and puzzle clarity. High-impact examples include:

- removing an unsupported television reference and repairing Dr. Simon's prologue description;
- restoring the museum girl's question and the protagonist's stammer/Devil telepathy characterization;
- making the demonic pact grammatical without softening its deliberate blasphemy;
- changing the ambiguous “Hitler's murder plot” to an anti-Hitler plot;
- treating Rebecca as the resistance network rather than a woman;
- replacing Japanese-cosmology “Yomi” with the Greek-setting “underworld” throughout TT4;
- removing unsupported “Dixie,” repairing Belle's incomplete/duplicated lines, and tightening work measurements;
- completing Mary's pregnancy explanation and sharpening the final Devil confrontation.

The machine-readable record-by-record evidence is in `audit/EDITORIAL_CHANGELOG.json`.

### 2. Why it is correct

Each edit was checked against the Japanese source/literal reconstruction and the scene's speaker/register. Edits use idiomatic English without adding unsupported interpretation. Every final string was encoded with the actual English character map and compressed with the real flat-dictionary path rather than estimated by character count.

### 3. Deliberately left unchanged

- Narrative events, puzzle answers/requirements, timing controls, disk flow, saving, and chapter structure.
- Deliberately ugly or racist period material in the Civil War chapter; it was clarified, not sanitized.
- Fixed-address command abbreviations that may be cosmetically awkward but were not proven unusable at runtime.
- Banks `T25`, `TT6B`, and `TT6D`, where no source edit was sufficiently justified.

### 4. Tests, hashes, and evidence

- All changed records preserve their exact control-code sequences.
- Automated display-width, glyph, ID/order, fixed-tail, dictionary, and footprint validation passes.
- A new exact regression test protects the highest-risk meaning/terminology corrections.
- Final remaining bank capacity includes TT1B **1 byte**, TT5 **2 bytes**, TT4 **5 bytes**, TT3B **9 bytes**, and TT3A/TT6C **22 bytes** each.

### 5. Remaining risks

Speaker identity in rare branches, spatial torn-note layout, typewriter cadence, and context-sensitive menu clarity still require live playtesting.

## Milestone 3 — Screen-level and fixed-asset audit

### 1. What changed

Generated title/font/workbook artifacts were regenerated from the revised authoritative sources. Private fixed-footprint translated-bank fixtures and named FDS playtest outputs were rebuilt/synchronized through the official tooling.

### 2. Why it is correct

Static previews and exact tests confirm the expected title phases, split logo, Nintendo phase, clock/time-machine composition, font encoding, fixed UI table boundaries, wrong-disk prompt, and Kouhen direct-boot guard.

### 3. Deliberately left unchanged

No `work/time_twist/ui.py`, `font.py`, or `title.py` source was changed. Cosmetic redesign was rejected because it was not supported by runtime evidence and would risk the original title animation/composition.

### 4. Tests, hashes, and evidence

- Fixed-record end addresses remain exact.
- Source-byte guards and translated-bank fixture hashes pass.
- Candidate component hashes: NOV2 `4450C063B939CFBF2F307E758BF9CC0E1089B8446A67049B6204CA677360A206`; NOV4 `1005C9758FBD1157BE77368155B4E6613480A82DFA1E782D72FD29AF3502ED9E`; SON-KOUH `99D913F6C055A360C57BD2972ACABE5F377446385CF3289A9EA4FE58A1B553AC`.

### 5. Remaining risks

Static previews cannot prove one-frame raster seams, live clock animation, START/B input, stale tiles, line clearing, audio/typewriter synchronization, or menu usability in context.

## Milestone 4 — Candidate rebuild and validation

### 1. What changed

`work/release_sources.json` was updated for the intentional scenario-source edits. A new unpromoted candidate was built. The candidate build was repeated independently into a second directory.

### 2. Why it is correct

Both candidate runs produced an identical manifest and byte-identical Zenpen, Kouhen, and four-side images. This establishes deterministic composition from the active source lock.

### 3. Deliberately left unchanged

`work/release_target.json` was **not** promoted or retied. Promotion is intentionally blocked pending runtime approval.

### 4. Tests, hashes, and evidence

- Active source-lock SHA-256: `238E98039F1D6FDD2E8A287766106C1C4F456B88DD25D9190E2CB32B98E7BD44`.
- Zenpen: `B499CA548A0012EDA77450873EF66545D4420C02D654674608BBD64344AFCDE9`.
- Kouhen: `EA56360D36730FDE372F7FC118B81D3C7C2937FD54D30288B7F56D6BCA7DD718`.
- Four-side: `CC58DDAFAB3C3E85FE6E06E9A7657AE0D17FE2AFFC34560F0615D415BD805C37`.
- Final test run: **105/106 pass**.
- The sole error is the strict promoted-target test, which correctly reports that the target belongs to a different source lock and requires candidate review/promotion. No test was weakened, skipped, or changed to accept assumptions.

### 5. Remaining risks

The candidate hashes are stable, but stability is not playability. The strict release build must remain red until the reviewed candidate is promoted after runtime testing.

## Milestone 5 — Runtime plan and release gate

### 1. What changed

A hash-bound end-to-end matrix was created at `docs/PLAYTEST_MATRIX.md`, covering cold boot/title exit, both documented disk changes, wrong-disk recovery, game save/load, every chapter, major puzzle/menu state, all requested story scenes, obscure branches, text clearing, typewriter/audio behavior, final quiz, Devil confrontation, and ending.

### 2. Why it is correct

The matrix forces evidence per scene and separates distinct defect classes. Its issue template records exact scene/screenshot, bank/record, Japanese/current English, root cause, smallest source fix, regression test, rebuild evidence, adjacent-scene checks, and runtime reproduction.

### 3. Deliberately left unchanged

No runtime result is fabricated from static tests, previews, prior captures, or rebuild hashes.

### 4. Tests, hashes, and evidence

Runtime evidence: **none for this candidate**. Environment inspection found no emulator binary or FDS BIOS. The prior capture files are useful reverse-engineering fixtures only.

### 5. Remaining risks

All rows in `docs/PLAYTEST_MATRIX.md` remain pending. Full Zenpen→Kouhen continuity, in-game saves, correct disk selection, puzzle progression, obscure branches, and the ending must be completed before promotion or any release-ready claim.

## Final disposition

The source is materially cleaner, meaning corrections are regression-protected, bank footprints remain exact, private fixtures are synchronized, and the new candidate is deterministic. It is a **playtest candidate**, not a final release.
