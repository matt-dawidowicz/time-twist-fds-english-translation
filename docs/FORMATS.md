# Binary and text formats

All hexadecimal offsets in the source are file-relative unless a name
explicitly says `address` or the documentation uses a dollar-prefixed CPU/PPU
address such as `$A200` or `$2000`.

## Archival FDS image

The parser supports both common forms:

- **headered**: a 16-byte `FDS\x1A` header followed by one or more sides;
- **raw**: one or more sides with no outer header.

Each archival side is exactly 65,500 bytes. Physical disk gaps and CRCs are
not present in this representation.

### Side block layout

| Block | Marker | Contents |
| --- | --- | --- |
| Disk info | `$01` | 56-byte disk metadata block |
| File count | `$02` | Marker plus one-byte file count |
| File header | `$03` | 16-byte header including name, load address, size, and kind |
| File data | `$04` | Marker followed by the declared payload |

`FdsSide.to_bytes()` rebuilds the used area, consumes original padding as
files grow, and pads the result back to exactly 65,500 bytes. It fails before
writing if the rebuilt side exceeds that capacity.

### FDS file header fields used by the tools

| Header bytes | Meaning |
| --- | --- |
| `1` | File number |
| `2` | File ID |
| `3:11` | Eight-byte FDS filename |
| `11:13` | Little-endian CPU/PPU load address |
| `13:15` | Little-endian payload size |
| `15` | File kind |

The parser retains the complete original header and updates only the payload
size during serialization.

## Scenario bank layout

Most scenario overlays are loaded at `$A200`. Three little-endian pointers in
the overlay header describe the variable text region:

| File offset | Meaning |
| --- | --- |
| `$0016` | Dictionary address |
| `$0024` | Additional group-pointer table address |
| `$0026` | Group-zero address |

Group zero starts the packed record region. Additional group addresses are
stored consecutively in the pointer table. The dictionary follows that table.
The first byte after the referenced dictionary is
`ScenarioBank.dictionary_end_offset`, the fixed boundary used when preserving
the bank's RAM footprint.

```text
overlay prefix / code
group 0 packed records
group 1 packed records
...
group pointer table (groups 1..n)
dictionary packed records
fixed tail / code / data
```

The group streams and dictionary may shrink or grow inside the reservation,
but the fixed tail cannot move.

## Packed symbol prefix tree

Bits are read most-significant bit first. A symbol's prefix determines its
kind and total encoded width:

| Prefix | Total bits | Kind | Value range |
| --- | ---: | --- | --- |
| `0xxxxx` or `10xxxx` | 6 | Common glyph | `0..47` |
| `110xxxxxx` | 9 | Extended glyph | `0..63` |
| `1110xxxxx` | 9 | Dictionary reference | `1..31` in valid text |
| `1111xxx` | 7 | Control | `0..7` |

Control value `5` is reserved as the record separator. After it is decoded,
the engine discards the rest of that byte and starts the next record at a byte
boundary. `pack_records()` and `split_records()` reproduce that behavior.

`PackedSymbol.start_bit` and `end_bit` record the original bit positions during
decoding. Newly encoded symbols use zeroes for those fields because positions
are assigned only when the final stream is written.

## Dictionary

Dictionary references are one-based: value `1` selects the first entry. A
bank may use no dictionary, a flat dictionary, or references that require
recursive expansion while analyzing Japanese source data.

The English compressor deliberately creates a **flat** dictionary:

- entries contain only common or extended literal glyphs;
- controls and existing references form candidate boundaries;
- required bank-specific entries are reserved first;
- a maximum of 31 entries is enforced;
- a candidate is accepted only if the complete packed size decreases.

Some fixed-address tables depend on required dictionary words such as command,
object, or speaker labels. Changing those words may change both the scenario
compression and the exact-size table encoding.

## English character map

The English map is optimized for packed size:

- common codes cost 6 bits and contain space, all lowercase letters, common
  uppercase letters, comma, and period;
- extended codes cost 9 bits and contain the remaining uppercase letters,
  digits, punctuation, and `é`;
- visible control tags use the textual form `{CTRL:n}` in patch-oriented JSON.

Code `44` in the extended table was reassigned to `é` for `consommé`. The font
patch writes a matching tile into NOV4.

The renderer has 24 visible columns. `validate_display_width()` checks the text
between control tags rather than the raw string including `{CTRL:n}` markup.

## Control codes

The tools intentionally treat controls as structural tokens instead of
guessing a universal linguistic meaning for every value. Their effect can
depend on the calling routine and scene.

The safe editing rule is:

- preserve the ordered control values from the Japanese record;
- do not translate, remove, duplicate, or reorder them;
- preserve intended page/line/pause timing when rewriting the visible text.

The detailed workbook uses `⟦CTRL:n⟧` for editorial display in some fields;
patch-oriented scenario JSON uses `{CTRL:n}`. Conversion code must keep the
numeric sequence identical.

## Fixed-address packed text

Many menus, command names, objects, quiz answers, and disk messages are packed
records outside the normal scenario group area.

Two constraints appear:

1. **table-size fixed**: the whole table must have the original byte size;
2. **record-boundary fixed**: every individual record must retain its byte
   length because code points directly to later records.

The UI patcher verifies a SHA-256 hash or exact source bytes before changing a
table. It decodes the original record boundaries, chooses a dictionary-aware
encoding, and appends invisible common-space symbols until each record consumes
its exact original slot.

## Font and title assets

### Dialogue font

NOV4 stores inverse one-bit glyph rows at:

```text
NOV4 file offset $1B7D + tile_id * 8
```

`font.py` uses a deterministic 5x7 design inside each 8x8 tile. A set pixel in
the source pattern clears a bit in the inverse stored row. Uppercase and
lowercase have separate glyphs.

### NES CHR

NES background/sprite patterns are 16-byte 2bpp tiles:

- first 8 bytes: low bitplane, one byte per row;
- next 8 bytes: high bitplane;
- palette index: low bit plus high bit shifted left.

### Title nametable RLE

The title's nametable stream uses:

- literal bytes below `$C0`;
- `$C0 + count`, followed by a byte to repeat;
- `$FF` as the complete stream terminator.

Because `$FF` is reserved, the largest legal run prefix is `$FE`, representing
62 copies. The final relocated title stream contains two decoded 1 KiB
nametables followed by one `$FF`.

### Native title authority

The production title image is a 256x240 indexed PNG with values 0-3. Only
rows 0-95 may contain pixels. No production crop, scale, or palette search is
performed: those indices become exact 2bpp tile pixels. The first twelve rows
of the second nametable are generated from all 32 columns of those same final
pixels, making completed-slide geometry identical to the final title.

### Title split and animated clock

The translated final title uses different CHR sources above and below tile row
16. The split occurs in a visually blank band. The original clock face is part
of the background, while the moving blue hands remain the game's original
sprites. The patch may adjust metasprite origins but must not alter the source
hand tiles, frame layouts, or animation timing.

Background IDs `$00-$EB` belong to the title; `$EC-$FF` remain the original
hand source. Nintendo temporarily owns `$B0-$D5`, which are restored from base
CHR immediately before the swipe.

## Source guards

Patch functions use one or more of:

- exact file size;
- exact bytes at a recovered offset;
- uniqueness of a source sequence;
- SHA-256 of a recovered region;
- decoded stream boundaries;
- post-patch re-decoding and equality checks.

These checks make the patch revision-specific by design. If a source guard
fails, first determine whether the input is the expected Japanese revision.
Do not weaken the guard merely to make the patch run.
