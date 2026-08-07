# Time Twist English Translation - Progress Checkpoint

Checkpoint date: July 22, 2026

## Completed foundation

- Preserved immutable local copies of both original FDS images; the source images were not modified.
- Implemented a lossless FDS parser/rebuilder and verified byte-identical round trips.
- Reverse-engineered the packed text codec, dictionary references, control codes, pointers, and Japanese character map.
- Extracted all 13 scenario banks: 1,299 records and about 131,000 Japanese characters.
- Assigned stable IDs to every record and preserved existing English when refreshing extraction files.
- Implemented the English encoder, scenario inserter, font patcher, ID-keyed translation merge command, static UI patcher, and flat native-compatible dictionary compressor.
- Completed all 13 scenario banks: the six Zenpen banks plus `TT4`, `TT5`, `T25`, and `TT6A` through `TT6D` in Kouhen. All 1,299 scenario records now have English text, and every original control-tag sequence is preserved.
- Added automated validation for display width, source identity, fixed-table record addresses, translated-bank contents, title-card assets, Nintendo/title tile restoration and palette order, FDS scope, dialogue-row preservation, the Kouhen direct-boot guard, round trips, complete translation-ID coverage, absence of Japanese characters in English values, and lossless four-side image assembly.

## Recommended four-side Mesen playtest build

- Output: `Time Twist - complete English four-side playtest.fds`
- Size: 262,000 bytes
- SHA-256: `5CE0931DB6D0C7848CC646A2A78670ADE6F7856AE32392CF8DC98B1D508811FC`
- Contains the current Zenpen sides first and the current Kouhen sides second, byte-for-byte: `TT1` Side A, `TT1` Side B, `TT2` Side A, `TT2` Side B.
- Open this one image at the beginning of the playtest. In Mesen, use `Game > Select Disk` for every requested swap. The first two menu entries are Zenpen and the next two are Kouhen, so changing to the second disk keeps the live Zenpen engine and progression state that Kouhen requires.

## Latest complete Kouhen test build

- Output: `Time Twist Kouhen - complete English playtest.fds`
- Size: 131,000 bytes
- SHA-256: `18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421`
- Validated file-by-file against the immutable Japanese Kouhen baseline.
- Only the seven scenario payloads `TT4`, `TT5`, `T25`, and `TT6A` through `TT6D`, plus the direct-boot warning program `SON-KOUH`, differ. Both FDS sides, every file header, all graphics, and all unrelated files remain byte-identical.
- A parse/rebuild round trip reproduces the test image byte-for-byte.
- Kouhen relies on the English NOV2/NOV4 engine and font already resident after swapping from the corrected Zenpen image. Start with the Zenpen build below, then insert this Kouhen build when prompted. If Kouhen is booted directly, its formerly Japanese guard now displays the centered English instruction `PLEASE START WITH` / `PART 1`.

## Latest complete Zenpen test build

- Output: `Time Twist Zenpen - complete English playtest.fds`
- Size: 131,000 bytes
- SHA-256: `442BAA3BEE5A5D800E0FCFC5A6FCA7788B80F77F14E3DA0C553A718CB954DD5F`
- Rebuilt directly from the immutable Japanese Zenpen baseline using all six canonical translated scenario banks plus the current NOV2 UI and NOV4 font/title payloads.
- Only `NOV2`, `NOV4`, `TT1A`, `TT1B`, `TT2`, `T22`, `TT3A`, and `TT3B` differ from the baseline. Every other file and header remains byte-identical, except NOV4's required two-byte size field.
- The larger `NOV4` consumes unused Side A padding without moving file order or load addresses. The output passes a byte-identical FDS parse/rebuild round trip.
- The current `TT1B` includes the museum, forest, and church wording corrections while preserving all 53 fixed table record addresses and retaining three bytes of RAM headroom.

### English animated title card

- The user's final 1,448x1,086 full-screen mockup is now the authoritative title source. It is reduced as one complete 4:3 composition to the FDS's 256x192 visible title region, preserving the intended wordmark scale, margins, clock face, and placement instead of stretching the earlier logo-only crop across the screen. Both 32x30 title nametables in the game's single compressed 2,048-byte stream are replaced, so the slide-in pieces use the same English artwork as the assembled title.
- The subtitle is exactly `On the Outskirts of History...`.
- The blue hand shown in the mockup is removed from the background before conversion. The game's original 20 animated hand frames, eight-sprite metasprites, layout table, and timing remain byte-identical. Both metasprite origins retain their joint `-8,-6` centering correction, so the moving hand pivots at the center of the new face rather than being frozen into the artwork.
- The final title background is a mathematically exact 256x240 indexed-pixel conversion of the authoritative mockup after its static blue hand is removed. Automated validation compares all 61,440 background pixels and reports zero mismatches; no consensus tiles, color substitutions, or approximated border pixels remain.
- A single NES background pattern table cannot hold the 278 distinct patterns required by that exact image. The title now reuses the game's existing two-stage FDS timer raster split: rows 0-15 use 225 exact patterns in background table 1, and rows 16-29 use 55 exact patterns in background table 0. The switch occurs across the original blank band between `PUSH START` and the time-machine graphic, so it does not cut visible artwork. The START exit path explicitly disables the split before normal gameplay resumes.
- A compact block of 38 original Nintendo tiles is still overlaid for the Nintendo phase, reproducing its logo exactly, then restored before title animation starts. The slide-in nametable is built from the same exact upper artwork and does not use those temporary IDs. The live clock-hand patterns remain in sprite table 0 at their original IDs, and the original 20 frames, eight-sprite metasprites, layout table, state order, and timing remain unchanged.
- The first title build incorrectly allowed `$FF` as a 63-byte RLE prefix and omitted the native stream terminator. Because the game's decoder reserves `$FF` exclusively as its end marker, it stopped before the first map's lower rows and almost immediately in the second map. This caused the corrupt footer, black slide-in, and repeated Nintendo-screen tiles. The corrected encoder caps runs at `$FE`/62 bytes and writes exactly one `$FF` after both maps; automated tests decode the native stream to exactly 2,048 bytes.
- The game's palette upload reverses stored four-color groups. The converter now uses the verified runtime index order of black, white, pink, and purple, rather than the misleading order used by the first static preview.
- The title bank grows safely from 9,077 to 11,995 bytes. Loaded at `$A200`, it now ends at `$D0DB`, still 1,754 bytes below the next resident file at `$D7B5`.
- The original compressed title data remains in place for source validation. Appended data contains 880 bytes of exact lower-table CHR, the Nintendo overlay, the matching upper-title restore block, initial/transition/exit helpers, and the corrected two-nametable stream.
- Patched `NOV4_english_title_v16.bin` SHA-256: `CD6EF0F6D3A756AE1ED98B3E3D897A7247BA5EF69ECEB1565AB930AC11B03C88`.
- Exact split-title preview: `outputs\Time Twist exact split-title preview.png` (SHA-256 `E7077033914E128414C40480D7A0F371AEBE21F525E5728C5355186A02B45411`). It overlays one captured live hand frame for placement only; actual motion and raster timing still require manual runtime testing.
- The first exact split-title build crashed immediately after START because its detour changed the source tail `JMP` into a `JSR`. The shared state setter's `RTS` therefore returned into the middle of NOV4 instead of to the main engine. Version 16 restores tail-call semantics with `JMP`, explicitly disables the live FDS timer through `$4022`, clears both split-state bytes, restores background table 1, and only then performs the original state change. A regression test locks the tail jump and complete exit-helper byte sequence.

### Bilingual translation-review corpus

- `outputs\Time Twist Japanese-English script comparison.html` is a searchable comparison of 2,052 entries: all 1,299 scenario records, 750 fixed-address/menu/interface records, and three verified graphics-text entries. SHA-256: `B43CD77F9962F52FD0BE9092FF61096725C5687052CFA967AA28B846CBA122B6`.
- `outputs\Time Twist Japanese-English script comparison.tsv` is the UTF-8 spreadsheet-ready worksheet with blank proposed-translation and reviewer-note columns. SHA-256: `232FC949252CC4A0BA4E7CA591D0E18FCA71F91580E006908E7278FFEC506392`.
- `outputs\Time Twist Japanese-English script comparison.json` contains the same corpus in structured form. SHA-256: `945B7347A8D5ADE4035F6A9E679449015A9AF7C44C29A4D5BDD904E983975ABB`.
- Each row preserves exact Japanese kana, the current English and control sequence, mechanical romaji, script-type counts, fixed-record address/capacity where applicable, conservative voice/dialect/register markers, honorific notes, and contextual kanji/katakana candidates. Suggested orthography is never substituted into the source text because the game's hiragana-only presentation leaves genuine homophone ambiguity.
- The sole intentional control mismatch is NOV2's wait prompt: Japanese uses a forced line break, while the corrected English `PLEASE WAIT...` is deliberately one line. All 1,299 scenario control sequences match exactly.
- The graphics/program-driven staff roll is outside the decoded packed-script corpus. Credit names have not been optically transcribed; this boundary is documented in `outputs\Time Twist bilingual comparison guide.md`.
- Nintendo/slide initialization preview: `outputs\Time Twist clean title Nintendo and slide preview.png` (SHA-256 `4B0A22DF9C19BB73C3105005AEF0308D6D48334E8933A53F719E3F9571F25183`). Runtime supplies phase-specific palette and scrolling changes.

### Safe `TT1A` bank

- Original bank size: 2,416 bytes
- Corrected English bank size: 2,416 bytes
- Literal English packed text: 1,892 bytes
- Flat 31-entry dictionary layout: 1,650 bytes
- Fixed-reservation use including the group table: 1,652/1,669 bytes; 17 bytes remain
- Dictionary references inside dictionary entries: zero
- Bank SHA-256: `FBDF8320F52EE8E43C6330C56D218837EA724C50FDBD875C80AA8C4F5F8966CF`
- All 35 expanded records match the current translation JSON exactly.
- The original fixed-address tail beginning at `$AB47` remains at `$AB47` and is byte-identical.
- The four fixed-address blood-type records at `$A45B` now decode as uppercase `A`, `B`, `O`, and `AB`; their individual record starts and the following `$A46A` data remain unmoved.
- The thirteen fixed-address month records beginning at `$A46A` now decode as `JAN` through `DEC`, with `JUL-DEC` for the second-page branch. Every record retains its original address and the following `$A4A4` data remains unmoved.
- The final fixed-address confirmation records now decode as `YES` and `NO`; the first scenario group still begins at its original `$A4C2` address.
- The birth-month prompt is now `Your birth month?`, keeping its question mark on the same line.

### Safe `TT1B` bank

- All 137 records translated and all control-tag sequences preserved
- Original bank size: 13,360 bytes
- Corrected English bank size: 13,360 bytes
- Fixed text reservation: 4,026 bytes, from `$ADE4` through `$BD9E`
- Literal English packed text: 4,486 bytes
- English text, group table, and flat 31-entry dictionary: 4,005 bytes
- Unused safety margin: 21 bytes
- Dictionary references inside dictionary entries: zero
- Bank SHA-256: `4897335A3C56BD93254DD15266663ED531A0D71ADBC885BF2A6AD9C3C64AEC57`
- The 6,290-byte fixed-address tail beginning at `$BD9E` remains at `$BD9E` and is byte-identical.
- The separate 53-record museum command, object, and interaction table remains exactly 206 bytes at `$ABF7-$ACC5`; every record retains its original start and end address.
- Its main commands now read `LOOK`, `TALK`, `MOVE`, `USE`, and `ASK`. Full words including `MUSEUM`, `SIGN`, `BODY`, `EYES`, `NOSE`, `EARS`, `CHEST`, `HOUSE`, `CHURCH`, `PRIEST`, `BELIEVER`, and `DEVIL` use deliberately reserved flat dictionary entries; only genuinely tiny remaining slots use compact English labels.

### Safe `TT2` bank

- All 169 records translated and all control-tag sequences preserved
- Original and translated bank size: 13,568 bytes
- Fixed text reservation: 3,847 bytes, from `$B028` through `$BF2F`
- English text, five-pointer group table, and flat 31-entry dictionary: 3,841/3,847 bytes
- Unused safety margin: 6 bytes
- Bank SHA-256: `7B3A5C1BD74D9497A866A6845C3E8216392989FC806C50A0DC4DA10A2CF5D756`
- The 6,097-byte fixed-address tail remains at its original address and is byte-identical.
- A separate 70-record command, object, character, and history-quiz table remains exactly 290 bytes at `$ADB6-$AED8`. More importantly, every one of its 70 records now starts and ends at the same address as the corresponding Japanese record. The five correct quiz answers remain recognizable as `JERUS`, `100`, `COM`, `GLD`, and `VINCI`; tiny slots use compact labels where unavoidable.
- `CROWD` and `Bishop` have dedicated dictionary entries so their two-byte records remain fully readable.

### Safe `T22` bank

- All 58 records translated and all control-tag sequences preserved
- Original and translated bank size: 4,096 bytes
- Fixed text reservation: 1,812 bytes, from `$AA4E` through `$B162`
- English text, one-pointer group table, and flat 31-entry dictionary: 1,782/1,812 bytes
- Unused safety margin: 30 bytes
- Bank SHA-256: `57660E975C4055BF09964429D93148E63B2CAE60CF7FE5235E313F68766145B7`
- The 158-byte fixed-address tail remains at its original address and is byte-identical.
- Its separate 33-record command/object table remains exactly 125 bytes at `$A929-$A9A6`, with every individual record boundary preserved. Proper names and important locations remain readable, including `Baron`, `Jailer`, `Chino`, `Jeanne`, `Bishop`, `Lugot`, `SCAFFOLD`, and `CROWD`; tiny object/location slots use compact labels such as `CEL` and `PRIS`.
- Eight dictionary entries are deliberately reserved across dialogue and the fixed table. This avoids relocating any code or data while retaining clearer labels than a table-only abbreviation pass.

### Safe `TT3A` bank

- All 152 records translated and all control-tag sequences preserved
- Original and translated bank size: 13,456 bytes
- Fixed text reservation: 3,741 bytes, from `$AF3B` through `$BDD8`
- English text, four-pointer group table, and flat 31-entry dictionary: 3,736/3,741 bytes
- Unused safety margin: 5 bytes
- Bank SHA-256: `CAA064895722477041ADF700CC3238C92B23023F09DF4A97C15BED230D3A7B92`
- The 6,328-byte fixed-address tail remains at its original address and is byte-identical.
- Its separate 95-record command/object/quiz table remains exactly 424 bytes at `$AC04-$ADAC`, with every individual record boundary preserved. Correct history answers remain recognizable as `Gestapo`, `RESIST`, `UBOAT`, `GABN`, and `EISEN`; decoys and low-risk object labels use compact forms where required.
- The two torn-note records and their combined clue are translated, as are the prison escape, Resistance password, Gestapo recognition signal, and atomic-bomb warning.

### Safe `TT3B` bank

- All 58 records translated and all control-tag sequences preserved
- Original and translated bank size: 3,056 bytes
- Fixed text reservation: 1,840 bytes, from `$A6B5` through `$ADE5`
- English text, one-pointer group table, and flat 31-entry dictionary: 1,837/1,840 bytes
- Unused safety margin: 3 bytes
- Bank SHA-256: `71BDD3C29B2B82FAA9433D67C7A0410E1A151D2F21939ADDA3195DC7CA20A53D`
- The 11-byte fixed-address tail remains at its original address and is byte-identical.
- Its separate 21-record command/object/battle table remains exactly 87 bytes at `$A620-$A677`, with every individual record boundary preserved. Battle actions decode as `FGT`, `GUARD`, and `RUN`; `Cougar` remains fully readable through a dedicated dictionary entry.
- The Hitler/Devil encounter, charm prayer, April 30, 1945 line, dimensional transition, and `TO BE CONTINUED...` ending are translated.

### Safe Kouhen banks

All 690 Kouhen scenario records are translated, completing the 1,299-record script. Each rebuilt overlay retains its original byte length and fixed tail address. Dialogue chunks are limited to 24 columns, dictionaries remain flat, and all scenario text expands back to the current translation JSON exactly.

- `TT4`: 183 records; 4,730/4,741 scenario bytes used; 11 bytes remain. Its 97-record command, treatment, five-sages, and Greek-history table remains exactly 440 bytes at `$AED3-$B08B`. Bank SHA-256: `B5D5BB9EE08C6482A1E007E1122F7A496A4D7598E850D0FAF72740B051AFAC26`.
- `TT5`: 123 records; 3,689/3,702 scenario bytes used; 13 bytes remain. Its 113-record plantation-task, American-history, livestock, and bottle-puzzle table remains exactly 493 bytes at `$ACA5-$AE92`. Bank SHA-256: `C94137F93CCA3543E789D88C140684E1DF34FF31980815A0669F3611C781F8F9`.
- `T25`: 76 records; 2,282/2,374 scenario bytes used; 92 bytes remain. Its 42-record mansion and flooded-island table remains exactly 185 bytes at `$AB8A-$AC43`. Bank SHA-256: `145802FC777423CE3A1DB227B48D181FD232B0FF70166DB22618DDC8B0737E71`.
- `TT6A`: 100 records; 2,694/2,833 scenario bytes used; 139 bytes remain. Its 41-record Nazareth village/workshop table remains exactly 165 bytes at `$A747-$A7EC`. Bank SHA-256: `094559DB356127C7E0CFE2C054783286C0E4030A2389E9111C2AE5661C839D07`.
- `TT6B`: 94 records; 2,296/2,336 scenario bytes used; 40 bytes remain. Its 62-record travel, logic, history-quiz, and stable-animal table remains exactly 263 bytes at `$A780-$A887`. Bank SHA-256: `C15A76C9A59A9224CEAFB16BABD0A4911906057A7AAF10C9C45DE57F61AA79C3`.
- `TT6C`: 106 records; 3,513/3,536 scenario bytes used; 23 bytes remain. Its 94-record finale and retrospective-quiz table remains exactly 407 bytes at `$AAB8-$AC4F`. Bank SHA-256: `6842652A2B5FF14B9575D898EBF14CF52233081C3738605A397297E7F730BC58`.
- `TT6D`: 8 records; 323/332 scenario bytes used; 9 bytes remain. This ending bank has no separate fixed menu table. Bank SHA-256: `C3F88A5E57A6048377FBD823653B7B0A401420A5048BD84BB6EFE58493097ECC`.

Every one of the 449 fixed Kouhen records keeps the exact start and end address of its Japanese counterpart. Tiny original slots necessarily use compact uppercase labels such as `GT`, `BRC`, `CAV`, and `COY`; normal dialogue remains mixed case.

### Readable pixel font

The first font was made by shrinking antialiased Consolas to eight pixels, producing broken diagonals and thin fragments. It has been replaced by a deterministic 5x7 pixel alphabet designed directly for the game's 8x8 source cells. Uppercase and lowercase now have distinct glyphs, so normal dialogue uses mixed case while menus and disk-change instructions remain deliberately uppercase. A dedicated accented `é` glyph now supports `consommé`; it occupies the existing extended slot formerly assigned to an opening parenthesis, which no current translated record uses. The font no longer depends on an installed Windows font.

Preview: `work\build\mixed_case_font_preview.png`

### Static UI now translated

- Opening selection: `START`
- Blood-type menu: `A / B / O / AB`
- Birth-month menu: `JAN` through `DEC`, with `JUL-DEC` as the branch choice
- Confirmation menu: `YES / NO`
- Disk-change prompt: `PART1 / SIDE B / INSERT NOW`, with matching Part 2 and Side A variants
- Pre- and post-switch wait message: `PLEASE WAIT...` on one line

All static UI replacements are packed size-for-size. The separate title-card patch changes one validated NOV4 nametable pointer as documented above; NOV2 code and pointers remain unmoved.

### Short-line and menu clearing

NOV2 used tile `$AC` to initialize unused cells at the end of a new dialogue line and a menu-choice line. Its renderer treats `$AC` as transparent and skips the tile write, so any characters left by a longer previous line remained visible. An intermediate build incorrectly changed these fills to `$B5`, whose original font glyph contains two dot rows; this produced the visible dotted artifacts. The menu clear at NOV2 offset `0x345B` still uses the fully blank common-space tile `$C0`, where the menu does not use the dialogue typewriter cadence.

Making the 24 dialogue-tail cells opaque also made the renderer pace every blank as though it were a typed character. This caused a full row of typing sounds with no visible text after `Maybe it is some spell?`, so the dialogue buffer fill at `0x245F` remains its original transparent `$AC`.

The next attempted clear changed the scroll uploader at `0x2571` from `LDA $87D7,Y` to `LDA #$C0 / NOP`. Runtime screenshots proved that this instruction uploads a valid dialogue row, not an unused tail: it deleted `Maradul Barao Garadura` and `Wars still rage abroad,`, producing the apparent giant spacing gaps. The current NOV2 restores the original `B9 D7 87` bytes exactly. A regression test locks that row-copy instruction and the unchanged transparent-tail fill. Patched NOV2 SHA-256: `620F951FCF650924BAC927AF2155DCE435B6C316C15BB37852EA2A1FB29F4AF3`.

The 25-character line `People always discuss it,` exceeded the 24-column dialogue row and wrapped its comma by itself. It is now the 24-character `Everyone talks about it,`. The wait record no longer contains a forced line-control code and decodes as the single-line `PLEASE WAIT...` with one invisible padding space to preserve its original packed size.

The same audit found 59 over-width chunks across the completed TT1A and TT1B translations. All 172 embedded scenario records now contain only chunks of 24 columns or fewer between control codes. The personality-test introduction is now exactly `First: personality test.` (24 columns), followed by `Answer each question.`. Translation merging and automated tests now reject any future English chunk wider than the display.

All 15 personality-test entries were retranslated against the Japanese source as actual questions rather than compressed statement fragments. The first now displays as `Do you prefer consommé` / `to miso soup?`, matching the following yes/no response format. Other retained distinctions include 50 meters, at least three girls, three or more people, postponing work until tomorrow, self-reliance, helping society someday, and preferring a brief but full life. Long questions use invisible padding to start the next word exactly at the 24-column row boundary; their original control-code sequences remain unchanged. Only the 15 audited question records are permitted to wrap this way, and a dedicated regression test locks their exact decoded rows.

The black strip at the left edge is the game's normal NES/Famicom left-edge clipping. NOV2 sets `PPUMASK` to `$18`, enabling background and sprites while deliberately leaving the two leftmost-eight-pixel enable bits clear. At 2x display scaling this appears as an approximately 16-pixel black bar and is unrelated to the translation.

## Defect findings

### Missed TT1B museum table

The garbled `IM / xbu / e?t` menu outside the museum was not part of TT2. It came from a separate 53-record Japanese command/object table in `TT1B` at `$ABF7-$ACC5`, which the earlier fixed-table inventory had missed. The mixed-case English font interpreted those untouched Japanese tile codes as Latin fragments.

The complete table is now translated. The scenario dictionary reserves the full words needed by its smallest two-byte records, and automated tests prove that all 53 records retain their individual source addresses. The museum direction records now display the full `EAST` and `WEST` instead of the provisional `E` and `W`; `WEST` uses a reusable `EST` dictionary fragment so it still fits its original three-byte record. Two later lines were tightened without changing their meaning (`Footprints continue...` and `A church, way out...`) to recover the six packed bytes required by that extra dictionary entry. The translated TT1B text now ends exactly at its original RAM boundary, with zero bytes of headroom and no overrun.

### Accented e alignment

The acute-accent glyph previously used an eighth source row, placing the body of its lowercase `e` one pixel below every other lowercase letter. Its body now occupies the same rows and baseline as the ordinary `e`, with the acute retained in the two rows above it. Reapplying the font to the existing title bank changes exactly six bytes inside that one glyph tile; the deferred title, clock, slide, and Nintendo graphics are byte-identical to the preceding build.

### Forest and church wording

The fortune prediction's `She leaps into your arms` already occupied all 24
columns, which is why the earlier draft had no terminal punctuation. It now
uses the equally natural `She runs into your arms.` so the complete sentence,
including its period, fits the native row.

The TT1B sky line `さいごにあおぞらをみたのは いつだっけ` explicitly asks when the
protagonist last saw a blue sky. The former `When did I last see it?` fit one
24-column row but hid the explicit image behind a pronoun. The reusable sky
inspection record now reads `A blue sky... how long?`; the workbook retains
the unrestricted natural rendering `When was the last time I saw a blue sky?`.

The forest inspection targets `まわり` and `じめん` now display as `AROUND` and `GROUND`, replacing `AREA` and the opaque abbreviation `GND`. Both words share one reserved `ROUND` dictionary fragment. The church target `しんじゃ` now displays as the six-character contextual label `MEMBER`, replacing `BELIEVER`, which the menu clipped to `BELIEV`. To keep the dictionary count and every record address fixed, the unrelated action `ATTACK` is now the natural literal `HIT` and no longer consumes a dictionary slot. The translated TT1B text has two bytes of RAM headroom.

### Fixed-table record relocation

The museum submenu corruption was caused by repacking TT2's 70-record fixed table while preserving only its total 290-byte size. The game uses absolute addresses for individual labels, so shortening one record and lengthening another made later lookups begin in the middle of compressed text. This produced fragments such as `xou` and `e?t` even though a sequential decoder still saw valid English records.

The fixed-table patcher now preserves the original byte length of every individual record and uses invisible trailing spaces only inside that record's existing allocation. Automated tests compare every translated record end address against its Japanese source. The same correction was applied proactively to T22, TT3A, and TT3B.

### Nested dictionary crash

The first compressor allowed dictionary entries to reference other entries. No original bank does this, and the opening record reached the first nested reference immediately after the date. The compressor now creates only flat entries.

### Apparent disk-screen freeze

The displayed Japanese message was the game's normal request to insert Side B of Part One. It was waiting for a disk switch, not frozen. The prompt is now English.

### Wrong-disk fallback message

The later two-line NOV2 warning at `$26E8-$2700` was separate from the normal five-record disk-change prompt and therefore remained Japanese. With the English font resident, `ちがった でぃすくが / せっとされています` appeared as Latin gibberish. It now displays `WRONG DISK! / TRY ANOTHER SIDE`. Both replacement records retain their exact original packed sizes (11 and 14 bytes), and only 25 bytes in NOV2 differ from the preceding build.

For four-side manual playtesting, disable Mesen's `Automatically switch disks for FDS games` setting. Zenpen and Kouhen are separate products whose original side headers both identify themselves as disk zero; automatic selection can therefore choose the wrong half from the combined image. At a `PART 1 / SIDE B` request select the second entry (`TT1` Side B). Only at `PART 2 / SIDE A` should the third entry (`TT2` Side A) be selected. The new English fallback lets an incorrect choice be corrected through `Game > Select Disk` without resetting.

### Kouhen direct-boot warning

Kouhen is not a standalone boot disk. It expects the live engine, font, and progression state already loaded by Zenpen, so booting it directly intentionally enters a warning screen. That screen's Japanese text was not in any scenario or fixed-label table: `SON-KOUH` draws it from 21 private 1bpp tiles and a 59-byte RLE nametable stream.

The warning now displays `PLEASE START WITH` / `PART 1` horizontally and centered. The patch retains `SON-KOUH`'s exact 739-byte size and changes only its recovered tilemap and glyph ranges; code, vectors, file header, disk layout, and guard behavior are untouched. Patched `SON-KOUH` SHA-256: `99D913F6C055A360C57BD2972ACABE5F377446385CF3289A9EA4FE58A1B553AC`.

### Television-sequence corruption

The previous English `TT1A` was 2,779 bytes, 363 bytes larger than the original overlay. Loading it at `$A200` overwrote the still-resident NOV4 region above the original `$AB70` boundary. That preserved region is first needed during the television sequence, matching the user's corruption screenshot.

The scenario builder now rejects any translated text that exceeds the bank's original RAM footprint. When the compressed text is smaller, it pads before the original tail rather than moving that tail. The revised English was tightened to fit without dropping any records or control tags.

No emulator or desktop application was controlled while diagnosing or building these corrections, at the user's request. Runtime behavior still requires the user's manual test.

## Current resume point

Begin from a fresh boot of `Time Twist - complete English four-side playtest.fds`, not an old save state. Confirm first that START leaves the title normally instead of freezing or crashing. Confirm that the opening swipe uses the exact English logo pieces and that the completed title matches the supplied full-screen layout pixel-for-pixel, retains `On the Outskirts of History...`, keeps the Nintendo phase clean, preserves the lower time-machine graphic, and animates the blue clock hand around the face center. Watch the blank band between `PUSH START` and the machine for any raster seam or one-frame glitch. Confirm that the first personality question renders `consomme` with its accented final `e` aligned to the same baseline as the rest of the word. In the fortune result, confirm `She runs into your arms.` ends with its period. At the museum exterior, confirm that the submenu reads `MUSEUM / EAST / WEST` with no isolated letters. In the forest, select the sky and confirm `A blue sky... how long?`; inspect the scene and confirm `AROUND / GROUND`. In the church, confirm the target list reads `ROOM / PRIEST / MEMBER`. In the television sequence, confirm that `Maradul Barao Garadura` appears between `Say it again and again.` and the final shouted chant. In the following city narration, confirm that `Wars still rage abroad,` appears between `The new age has no peace` and `as they always have.`. Also watch those replacements for any surviving letters at the right edge and listen for any blank line of typewriter sounds; those are separate failure modes and must not be traded for another deleted sentence. When the game requests Kouhen, use Mesen's `Game > Select Disk` menu and select the third side entry (`Disk 2, Side A`); do not open Kouhen as a new game or reset the console.

Play through the Greek chapter, American plantation and Lincoln sequences, Nazareth/Bethlehem chapters, final museum return, retrospective quiz, Devil confrontation, and ending. Check natural dialogue, every command/answer label, clean line replacement, puzzle behavior, overlay transitions, and both disk switches. Pay special attention to the extremely compact quiz/menu labels and the TT6C date transition back to September 25, 1995. The black eight-pixel left-edge strip remains expected original behavior.

The script translation is complete, but this remains a development checkpoint. Full manual playtesting and any resulting wording/layout corrections are the release gate before producing final named FDS images and BPS patches.

## Important artifacts

- Recommended complete-game test ROM: `outputs\Time Twist - complete English four-side playtest.fds`
- Separate source builds retained for validation: `outputs\Time Twist Zenpen - complete English playtest.fds` and `outputs\Time Twist Kouhen - complete English playtest.fds`
- English title preview: `outputs\Time Twist exact split-title preview.png`
- Nintendo/slide structural preview: `outputs\Time Twist clean title Nintendo and slide preview.png`
- Corrected fixed-footprint banks: all 13 matching files under `work\translated_banks`
- Translation sources: all 13 matching files under `work\translations`
- Merged scenario documents: the matching files under `work\translated_scripts`
- Mixed-case pixel-font preview: `work\build\mixed_case_font_preview.png`
- Translation tooling: `work\time_twist`
- Tests: `work\tests`

## Superseded builds

`Time Twist Zenpen - forest and church wording fix test.fds` and `Time Twist Kouhen - complete English scenario test.fds` are superseded by the clean baseline-rebuilt `complete English playtest` pair. Their payloads were already identical; the new names establish the two files to use for full-game playtesting.

`Time Twist Zenpen - museum directions and accent fix test.fds` is superseded by `Time Twist Zenpen - forest and church wording fix test.fds`; it still contained the literal sky line, the `AREA / GND` forest labels, and the clipped `BELIEV` church target.

Every earlier Zenpen milestone ROM, including `Time Twist Zenpen - dialogue line restore test.fds`, `Time Twist Zenpen - clock and time machine fix test.fds`, `Time Twist Zenpen - reference clock test.fds`, `Time Twist Zenpen - clean aligned title test.fds`, `Time Twist Zenpen - aligned reference title test.fds`, `Time Twist Zenpen - polished centered reference title test.fds`, `Time Twist Zenpen - centered reference clock test.fds`, `Time Twist Zenpen - exact-reference title test.fds`, `Time Twist Zenpen - atomic mockup title test.fds`, `Time Twist Zenpen - mockup-accurate title test.fds`, `Time Twist Zenpen - polished English title card test.fds`, `Time Twist Zenpen - corrected English title card test.fds`, `Time Twist Zenpen - English title card test.fds`, and `Time Twist Zenpen - complete English menus test.fds`, is superseded by the museum-direction-and-accent build. The dialogue-line-restoration build still placed the accented `e` one pixel too low and abbreviated the museum directions to isolated `E` and `W`. The immediately preceding clock-and-time-machine build blanked a live dialogue row during scroll upload, deleting complete sentences. The reference-clock build still treated the 20 live hand tiles as assignable background patterns, causing runtime substitutions in the wordmark and lower graphic. The clean aligned-title build used oversized generic 5x7 clock numerals and left the hands' shared elbow slightly above and left of the face center. The aligned-reference build overcorrected the clock position, retained resampled numerals, and still permitted white-to-pink tile substitutions. The first centered-reference attempt compensated only for the title's background scroll; it did not account for the original metasprites' visible elbow being offset inside their object boxes. The first exact-reference build used the correct source art but left the sprite hands in unscrolled screen coordinates and prioritized the lower belt over some large-logo patterns. The atomic mockup build fixed corruption but used a separately reconstructed title and oversized clock rather than the user's final exact logo source. The immediately preceding mockup build restored CHR while rendering and NMI activity were live, tearing the PPU address state into repeated vertical columns. The previous polished build attempted to select a second background pattern table, but the game's NMI forces table 1 while Nintendo is displayed; that produced English-title debris inside the Nintendo logo. The corrected-but-unpolished build instead forced both phases into one aggressively approximated static table, leaving rough logo edges. The first English-title-card build also used illegal `$FF` run prefixes, corrupting both title nametables at runtime. The fixed-record-menus build still left TT1B's 53-record museum table in Japanese. The older complete-English-scenario build preserved each previously known fixed table's total size but not each record address, causing submenu corruption and risking equivalent failures in later chapters. The `proper-question polish` build used unaccented `consomme`, offered `or miso soup?` despite the yes/no response, and paced its opaque dialogue-tail blanks as invisible typed characters. The `question polish` build still rendered the personality entries as terse statements rather than proper questions. The `24-column polish` build over-shortened them and lost distinctions from the Japanese. The `text-layout fix` contained 59 chunks wider than the dialogue row, while `menu-clear fix` used visible `$B5` accent tiles as line padding. The blood-type fix still had a Japanese month table and a wrapped birth-month question. The older `disk-prompt fix` and `flat-dictionary fix` builds contain the oversized 2,779-byte `TT1A` overlay that can corrupt the television sequence; `static-menu`, the original milestone, and `v2` also contain earlier menu or nested-dictionary defects.

The earlier Kouhen `TT4 English`, `TT4-TT5 English`, and `TT4-TT5-T25 English` milestone images are superseded by `Time Twist Kouhen - complete English scenario test.fds`.

This is a development checkpoint, not a finished English release.
