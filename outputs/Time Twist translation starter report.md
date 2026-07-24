# Time Twist English translation: starter report

## Bottom line

Do **not** begin by translating screenshots or overwriting Japanese bytes in a hex editor. The first milestone should be a repeatable text pipeline:

1. identify and decode every text record;
2. export records with stable IDs and context;
3. reinsert an unchanged dump and reproduce the original disk images byte-for-byte;
4. replace one short command/menu string with English;
5. only then translate the full script.

This is a substantial ROM-hacking/localization project, but the supplied dumps are valid-looking standard FDS images and the game is structured enough to automate.

## Supplied dump baseline

| Part | Internal code | Size | SHA-256 |
|---|---:|---:|---|
| Zenpen / first half | `TT1` | 131,000 bytes | `B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916` |
| Kouhen / second half | `TT2` | 131,000 bytes | `F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A` |

Each image contains two 65,500-byte sides, so the complete game spans four sides. Preserve these two files unchanged and ultimately distribute patches, not modified ROM images.

## Four-side file map

### Zenpen side A

| File | Load | Size | Likely role |
|---|---:|---:|---|
| `KYODAKU-` | `$2800` | `$00E0` | Nintendo license data |
| `TT3A` | `$A200` | `$3490` | Scenario/program bank |
| `TT3B` | `$A200` | `$0BF0` | Scenario/program bank |
| `OB3` | `$0000` | `$0A40` | Object graphics |
| `BG3` | `$1100` | `$0EA0` | Background graphics |
| `NOV1` | `$0390` | `$0050` | Engine/support data |
| `NOV2` | `$6000` | `$4200` | Shared 6502 adventure engine |
| `NOV3` | `$D7B5` | `$084B` | Engine/support code and data |
| `NOV4` | `$A200` | `$2375` | Boot/UI program and graphics data |
| `SAVE` | `$0390` | `$0050` | Save data |

Unused side padding: `$3658` = 13,912 bytes.

### Zenpen side B

| File | Load | Size | Likely role |
|---|---:|---:|---|
| `TT1B` | `$A200` | `$3430` | Scenario/program bank |
| `TT1A` | `$A200` | `$0970` | Scenario/program bank |
| `TT2` | `$A200` | `$3500` | Scenario/program bank |
| `T22` | `$A200` | `$1000` | Scenario/support bank |
| `OB1B`, `OB1A`, `OBJ2` | varies | varies | Object graphics |
| `BG1B`, `BG1A`, `BG2` | varies | varies | Background graphics |

Unused side padding: `$4FA8` = 20,392 bytes.

### Kouhen side A

| File | Load | Size | Likely role |
|---|---:|---:|---|
| `KYODAKU-` | `$2800` | `$00E0` | Nintendo license data |
| `SON-KOUH` | `$DD1D` | `$02E3` | Second-part boot/handoff code |
| `TT6A`, `TT6B`, `TT6C`, `TT6D` | `$A200` | varies | Scenario/program banks |
| `OB6A`, `OB6B`, `OB6C`, `OBJ6D` | varies | varies | Object graphics |
| `BG6A`, `BG6B`, `BG6C`, `BG6D` | varies | varies | Background graphics |

Unused side padding: `$3941` = 14,657 bytes.

### Kouhen side B

| File | Load | Size | Likely role |
|---|---:|---:|---|
| `TT4` | `$A200` | `$35B0` | Scenario/program bank |
| `TT5` | `$A200` | `$3100` | Scenario/program bank |
| `T25` | `$A200` | `$2000` | Scenario/support bank |
| `OBJ4`, `OBJ5`, `OBJ52` | varies | varies | Object graphics |
| `BG4`, `BG5`, `BG52` | varies | varies | Background graphics |

Unused side padding: `$39E9` = 14,825 bytes.

Aggregate unused side space is 63,786 bytes (62.3 KiB). That is encouraging, but it is not automatically usable: the large scenario banks load at `$A200` and must remain below the FDS BIOS at `$E000`. The tightest observed bank, `TT4`, has only `$0850` (2,128 bytes) left in that RAM window. A full English script will probably require repacking, more efficient English rendering, or additional bank loads rather than simply enlarging every existing file.

## What static inspection already established

- `NOV2` is the common 6502 engine loaded at `$6000`.
- The `TT*` files are replaceable scenario/program banks loaded at `$A200`.
- Each scenario bank begins with a table of 16-bit pointers consumed by the common engine.
- At least one family of command/menu strings is stored as length-prefixed, one-byte character codes. In `TT1B`, the relevant table is reached through the bank-header pointer at `$A210` (which points to `$ACC7` in that bank).
- Other scenario records are custom packed/bytecoded and are not plain ASCII, Shift-JIS, or simple null-terminated kana.
- The Japanese glyph renderer is custom. Engine code around `$804C–$8358` reads bit-coded glyph data and reconstructs characters from tile fragments. This is why a generic tile editor or table-file scan will not expose a normal font sheet.
- Text selected for display is copied into RAM buffers around `$0422/$0423`; code around `$93F0` selects and renders glyphs. These are useful dynamic-debugging breakpoints.

The exact narrative record format and complete character mapping still need to be documented before translation begins.

## Recommended first technical milestone

Produce an English command-menu proof-of-concept with a round-trip-safe toolchain.

### 1. Set up a reproducible debugger session

Use the current community-maintained Mesen build (MesenCE) with a legally obtained FDS BIOS. Keep automatic disk actions disabled while tracing so side and disk changes remain explicit.

Useful first breakpoints/watchpoints:

- execute at `$9522`: copies length-prefixed character data into the `$0422` display buffer;
- writes to `$0423–$043F`: captures the actual character-code stream;
- execute near `$93F0`: character-to-glyph selection;
- execute at `$8328`: bit reader used by the custom glyph reconstruction path;
- reads from `$A200–$A231`: identifies which scenario-bank header pointers are active.

For every text box, log the loaded FDS filename, side, `TT*` bank, script address, record ID, bytes copied to `$0423`, and screenshot/context.

### 2. Build the extractor before translating

Export a durable script format such as TSV, CSV, or YAML with fields like:

```text
part, side, bank, record_id, cpu_address, original_bytes,
japanese, literal_english, polished_english, context,
max_lines, max_width, control_codes, status
```

The extractor must preserve unknown control codes symbolically rather than discarding them.

### 3. Prove round-trip insertion

An unchanged export/import must reconstruct both supplied FDS images byte-for-byte and reproduce their SHA-256 hashes. This catches pointer, record-length, file-size, and side-layout mistakes before any real translation work is at risk.

### 4. Translate one short command

Choose a command/menu label that fits the existing record length. Patch its character codes and glyph mapping, boot the game, and validate:

- correct English letters;
- no adjacent text corruption;
- clean cursor/highlight behavior;
- correct choice behavior;
- correct disk loading and save behavior.

That vertical slice proves the extractor, encoder, font strategy, patcher, and emulator workflow together.

## Font and layout decision

The major engineering decision comes after the proof-of-concept:

1. **Adapt the existing reconstructed-glyph system.** Least engine disruption, but authoring Latin glyph data may be awkward.
2. **Replace it with a compact fixed-width 8x8 Latin font.** More engine work, but English layout and tooling become much simpler.
3. **Use a proportional Latin font.** Best fit for a verbose English script, but substantially more code and testing.

A compact 8x8 font is the likely practical middle ground. Japanese gameplay text is almost entirely hiragana, so English strings will often be longer; gaining more characters per line matters as much as raw disk capacity.

## Translation workflow

Once extraction is stable:

1. literal Japanese transcription and translation;
2. context pass using screenshots and the full walkthrough path;
3. concise English adaptation respecting line and record budgets;
4. consistency glossary for names, places, commands, and historical/religious terms;
5. automated overflow and missing-record checks;
6. full playthrough of both halves, all mandatory disk swaps, save/handoff, quizzes, branches, and endings;
7. verification in at least two accurate emulators;
8. release as two BPS patches plus hashes, instructions, credits, and known limitations.

Because the original deliberately writes nearly all gameplay text in hiragana, readings can be ambiguous. Machine translation can help produce a rough draft, but a Japanese reader should make the final contextual decisions—especially for the historical, religious, racist, and Holocaust-related material.

## Current public-project check

No released English patch was found in a July 2026 search. Community posts in 2025 still described the game as awaiting translation, although one post said prior ROM-hacking discussion had apparently identified its compression. A current search also found an April 2026 player asking for real-time translation because no English patch was available. Existing compression research should be located before duplicating too much work, but it should be validated against these exact dump hashes.

Useful references:

- [Nintendo's official Time Twist page](https://www.nintendo.com/jp/famicom/software/fmc-ttw/index.html)
- [NESdev FDS disk format](https://www.nesdev.org/wiki/FDS_disk_format)
- [Mesen Community Edition](https://github.com/nesdev-org/MesenCE)
- [Japanese full-game walkthrough route](https://xneo.jp/time-twist/)
- [2025 community translation discussion](https://retrogametalk.com/threads/time-twist-rekishi-no-katasumi-de-what-a-sleeper-of-a-game.10598/)

## Best immediate next task

Reverse-engineer and document the complete text-record decoder for `TT1B`, then export the first chapter with numeric character codes and control tokens. Once its charset is mapped, replace one short menu string with English and verify it in MesenCE. Do not begin full prose translation until that round trip works.
