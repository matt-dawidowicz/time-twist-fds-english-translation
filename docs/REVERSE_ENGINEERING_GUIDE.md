# Reverse-engineering guide: text, graphics, and runtime behavior

This document is the maintainer reference for understanding **how Time Twist actually
moves text and graphics from FDS files into RAM and onto the NES screen**. It is
intended to make future fixes incremental: a maintainer should be able to identify
which engine owns a symptom, find the relevant pointer or runtime state, prove the
constraint, patch the narrowest layer, and add the right regression test without
rediscovering the game from scratch.

Read this with [Architecture](ARCHITECTURE.md), [Formats](FORMATS.md), and the
[Code tour](CODE_TOUR.md). The specialized title, menu, and font documents remain
authoritative for their subjects; this guide connects them into one runtime model.

## Evidence labels

Reverse engineering becomes dangerous when a working hypothesis gets promoted into
an architectural fact. Use these labels in future notes, issues, and code comments:

- **VERIFIED** - established from exact source bytes, pointer structure, a guarded
  patch, a deterministic round trip, or a test against the supported source.
- **OBSERVED** - established in emulator runtime state, trace, VRAM/CHR viewer, or a
  repeatable playtest route, but not yet completely explained statically.
- **DERIVED** - follows mechanically from verified facts, such as
  `CPU address = load address + file offset`.
- **INFERRED** - best current explanation but not safe enough to become a generic
  patch rule.
- **UNKNOWN** - deliberately not modeled yet.

A future fix should turn the minimum required **OBSERVED/INFERRED** facts into
**VERIFIED** facts before broadening a transform.

---

## 1. Runtime memory model

The most important fact is that this is an overlay-driven FDS game. File-relative
addresses, loaded CPU addresses, and PPU addresses are different coordinate systems.
Do not mix them.

### CPU map used by the translation

| Range | Owner | Status |
| --- | --- | --- |
| `$6000-$A1FF` | `NOV2` shared UI/text/input runtime | VERIFIED; `NOV2` is exactly `$4200` bytes |
| `$A200-$D7B4` | Current `$A200` overlay: `NOV4`, `TT*`, `T22`, `T25`, etc. | VERIFIED overlay space |
| `$D7B5...` | Resident `NOV3` | VERIFIED exclusive boundary; translated overlays must not cross it |

`NOV4` and the scenario banks are not one giant continuous program. They reuse the
same `$A200` overlay window at different times. That is why a scenario bank may grow
past its original FDS-file length while still being safe, provided its **loaded end**
stays below `$D7B5` and its source-owned fixed tail remains at the recovered address.

`NOV2`, by contrast, has no adjacent expansion room. It already occupies
`$6000-$A1FF`, directly below the `$A200` overlay window. Runtime changes in `NOV2`
therefore reuse verified internal regions and remain size-neutral.

### FDS coordinates

An archival FDS side is 65,500 bytes. Each file has its own load address in the FDS
file header. The central conversion rule is:

```text
CPU address = component load address + component file offset
component file offset = CPU address - component load address
```

Examples:

```text
NOV2 file $21D3 -> CPU $81D3   ($6000 + $21D3)
NOV2 file $2571 -> CPU $8571
NOV4 file $09D2 -> CPU $ABD2   ($A200 + $09D2)
scenario header file $0016 -> CPU $A216 when the bank loads at $A200
```

PPU addresses such as `$2000`, `$2400`, `$1000`, and `$1FFF` are **not** CPU
addresses. They describe nametable or pattern-table destinations and must be traced
through the code that writes `$2000/$2001/$2006/$2007` or through FDS BIOS upload
calls.

### Overlay ownership rule

Before patching a byte, answer all four questions:

1. Which FDS file owns it?
2. What is that file's load address?
3. Is the byte data, a pointer, packed text, CHR, a nametable stream, or executable
   6502 code?
4. What else reads the same physical bytes at another phase of the game?

The fourth question matters. The historical `$AC` font regression happened because
bytes that looked like font storage were also consumed as post-title 2bpp graphics.

---

## 2. Text-engine architecture at a glance

There are two binary text representations in the project but one semantic engine:

```text
Japanese source
  native packed grammar
  byte-aligned record separators
       |
       v
stable semantic tokens
(common / extended / dictionary / control / separator)
       |
       +--> workbook and source analysis
       |
       v
English production layout
24-column/four-row renderer geometry
       |
       v
frozen entropy grammar
bit-contiguous records inside each independently addressed stream
       |
       v
patched NOV2 decoder
       |
       v
original semantic glyph/control/dictionary handlers
```

The production entropy runtime **does not replace the whole text engine**. It changes
how a semantic token is read from bits, then dispatches into the recovered native
handlers for common glyphs, extended glyphs, controls, and dictionary expansion.
That design is why source semantics and runtime rendering behavior can remain stable
while the binary packing becomes much denser.

---

## 3. Native packed text

The Japanese source grammar is MSB-first and recovered in `textcodec.py`.

| Prefix | Total bits | Meaning | Value range |
| --- | ---: | --- | ---: |
| `0xxxxx` or `10xxxx` | 6 | common glyph | `0-47` |
| `110xxxxxx` | 9 | extended glyph | `0-63` |
| `1110xxxxx` | 9 | dictionary reference | `1-31` in native text |
| `1111xxx` | 7 | control | `0-7` |

Control value `5` is special: it is the **record separator**, not ordinary visible
control markup. In the native representation the decoder discards the remaining bits
of that byte after separator 5 and the next record begins on a fresh byte.

That byte-alignment behavior is source-format behavior. It must not be projected
onto the production entropy format.

### Scenario-bank pointer structure

Most story overlays load at `$A200`. Three header words describe the scenario text
region:

| File offset | Loaded address | Meaning |
| ---: | ---: | --- |
| `$0016` | `$A216` | dictionary pointer |
| `$0024` | `$A224` | table of group pointers 1..n |
| `$0026` | `$A226` | group-zero pointer |

The actual pointed-to addresses vary by bank. The physical order is:

```text
prefix / program / local tables
scenario group 0
scenario group 1
...
group pointer table
dictionary
fixed tail: code and/or data whose loaded address must remain stable
```

`parse_scenario_bank()` proves that group pointers are strictly ordered, every group
ends exactly at the next group/table boundary, and the dictionary is decoded far
enough to include the transitive closure of dictionary references.

### Dictionary reachability is wider than dialogue

Do not determine the source dictionary size from story records alone. Fixed-address
menu/quiz/object tables can reference dictionary entries that ordinary scenario
records never use. `source_dictionary_reference_floor()` decodes those verified
external tables and forces scenario parsing to include the highest referenced source
entry.

This detail is critical when identifying the fixed tail. Under-decoding the source
dictionary makes code/data after it appear to be free text space.

---

## 4. Production entropy grammar

The release codec is a frozen ABI. Reordering these categories changes the NOV2
runtime format and is not a harmless compressor tweak.

| Category | Prefix | Payload bits | Semantic range |
| ---: | --- | ---: | --- |
| 0 | `0111` | 0 | separator 5 |
| 1 | `11000` | 3 | controls 0-7 |
| 2 | `111` | 2 | common 0-3 |
| 3 | `001` | 2 | common 4-7 |
| 4 | `101` | 3 | common 8-15 |
| 5 | `1101` | 3 | common 16-23 |
| 6 | `00001` | 3 | common 24-31 |
| 7 | `1001` | 4 | common 32-47 |
| 8 | `0110` | 3 | dictionary 1-8 |
| 9 | `0001` | 3 | dictionary 9-16 |
| 10 | `1000` | 4 | dictionary 17-32 |
| 11 | `010` | 5 | dictionary 33-64 |
| 12 | `000001` | 5 | dictionary 65-96 |
| 13 | `0000001` | 5 | dictionary 97-128 |
| 14 | `0000000` | 7 | dictionary 129-255 |
| 15 | `11001` | 5 | extended 37-63 |

The runtime ABI can address dictionary entries through 255. The current production
optimizer is deliberately tighter: normal banks search up to 128 entries, `TT2` is
capped at 96, dictionary phrases are capped at 12 grammar tokens, and nesting depth
is capped at 4.

### The framing rule that caused several historical failures

Production records are **bit-contiguous within one independently addressed stream**.
Separator 5 does not align to the next byte. Padding occurs only at the end of the
stream.

Independent streams do start on byte boundaries because native code stores byte
addresses for them. Current independently addressed units include:

- each scenario group;
- the entropy dictionary;
- each 32-record page of a large scenario menu table;
- individually addressed TT1A selector records;
- fixed decoder-visible streams converted by the release builder.

A bug that resets the bit mask after every record can work on the first record and
then decode garbage. A bug that fails to reset at a genuinely new byte-addressed
stream can do the opposite.

---

## 5. NOV2 production decoder: execution map

The important production decoder addresses are intentionally stable and guarded.
They are excellent debugger breakpoints.

| CPU address / region | Role |
| --- | --- |
| `$80A9` | detour that initializes a fresh byte-addressed entropy stream |
| `$80B1` | resumable record scanner; region budget `$A3` bytes |
| `$815E` | semantic frontend; region budget 69 bytes |
| `$81E0` | prefix-category decoder/trie; region budget 70 bytes |
| `$8328` | recovered native single-bit reader called by the entropy code |
| `$81A6` | native common-glyph handler |
| `$8226` | native extended-glyph handler |
| `$8242` | native control handler |
| `$82C5` | native dictionary handler / expansion entry |
| `$85D9` | entropy-converted internal fixed 51-record table |
| `$9402` | menu entropy-page initialization call site |
| `$946B` | menu label-width capture call site |
| `$989F` | dynamic selection-bracket span call site |
| `$8757` | base of menu-width scratch table; effective entries use `$8758-$875F` |

### Scanner state

The production scanner deliberately preserves the current stream bit state across
record separators and across frame-budget returns.

Recovered/used scratch state includes:

- `$6A/$6B` - stream pointer state retained while scanning;
- `$6C` - current bit mask, initialized to `$80` only for a genuinely fresh
  byte-addressed stream;
- `$3A` - token payload accumulator used before semantic dispatch;
- `$C2` - remaining record count for scanner work;
- `$7F79` - scanner work budget;
- `$7F78` - scanner/initialization flag used by the patched path;
- `$71` - dictionary nesting depth counter in the production patch.

Do not borrow an apparently unused zero-page byte without proving its lifetime. A
previous runtime iteration attempted to use `$74`; tracing showed it belonged to
unrelated live native state, so the current decoder keeps temporary category state on
the CPU stack instead.

### Nested dictionary expansion

The native dictionary expander already saves the text-pointer triplet on the CPU
stack. Production only needed two source-verified changes:

```text
NOV2 file $22C5 / CPU $82C5: increment dictionary depth
NOV2 file $2311 / CPU $8311: decrement dictionary depth
```

The production dictionary is backward-only: an entry can reference earlier entries,
never itself or a later entry. Combined with the build-time nesting cap, this makes
expansion acyclic and bounded.

### NOV3 boundary is enforced by the scanner too

`$D7B5` is not merely a build-time capacity number. The patched scanner checks the
stream pointer against the exclusive NOV3 boundary and stops instead of walking into
resident code/data. A build that only “seems to fit” in the FDS file but loads beyond
`$D7B4` is invalid.

---

## 6. Scenario placement: resident data, spill data, and fixed tails

Scenario packing has two independent constraints:

1. preserve source-owned code/data beginning at the recovered fixed tail; and
2. keep the complete loaded overlay below `$D7B5`.

`build_entropy_scenario_bank()` therefore treats the original text reservation as a
hole that can hold some complete group streams plus the group-pointer table and
dictionary. It chooses whole resident groups that consume the most old reservation
space. Groups that do not fit are appended after the original bank and their pointers
are changed to the appended addresses.

The source suffix beginning at `dictionary_end_offset` is compared byte-for-byte
against the output. If it moved or changed, the layout is rejected.

This is why “there are free bytes before the end of the FDS file” is not a sufficient
capacity argument. The relevant limits are ownership, loaded addresses, and the
resident NOV3 boundary.

---

## 7. Large scenario menus: the recovered 32-record page model

Eleven scenario banks have large menu/object/quiz tables. They are not one-pointer-
per-label tables.

| Header file offset | Loaded address | Meaning |
| ---: | ---: | --- |
| `$0010` | `$A210` | first secondary-table base |
| `$0012` | `$A212` | second secondary-table base |
| `$0014` | `$A214` | record-zero menu base |
| `$001A` | `$A21A` | page-pointer-table base |

Records 0-31 are reached from the record-zero base. Records 32, 64, and 96 begin at
addresses stored in the page index when those pages exist. The decoder then walks
separator-delimited records within the selected page.

Therefore records can change byte length **inside a page** if the builder also:

1. entropy-packs each 32-record page as an independent byte-addressed stream;
2. regenerates the page pointers;
3. shifts the two recovered secondary tables by the same delta;
4. updates their `$A210/$A212` pointers;
5. shifts scenario group zero accordingly; and
6. preserves the fixed tail and NOV3 boundary.

Relocation fails if the secondary prefix appears to contain another absolute pointer
into the relocated block. That is intentional: an unknown relocation rule is not
safe to guess.

### Menu renderer width behavior

The recovered visible menu surface supports eight glyphs. The production runtime
patches two native six-glyph row limits to eight and replaces the fixed selection
bracket width with a dynamic width:

- when a label finishes decoding, X is exactly twice its visible glyph count;
- the runtime stores that width in the existing `$8758-$875F` staging area;
- the selection helper uses the selected visual slot to derive the right bracket.

Do not store scratch data in `$9390-$93AF`; that region is live palette state.

---

## 8. TT1A is a dual-addressing exception

TT1A selector text is reached in two incompatible ways:

- native code can jump directly to individual selector records by byte address;
- the generic NOV2 renderer also expects a sequentially traversable copy.

The release therefore keeps **address-stable one-record entropy mirrors** for direct
entry points and appends a separate contiguous renderer copy used by the sequential
scanner through the `$A214` contract.

If a TT1A selector works when chosen directly but fails when reached through generic
rendering, or vice versa, inspect both copies before changing the decoder.

---

## 9. Dialogue renderer geometry

Production layout models the recovered NOV2 staging buffer rather than merely counting
characters in a string.

```text
24 visible columns
2 staging bytes per visible glyph
48 bytes per row ($30)
4 rows
192-byte logical staging span ($C0)
row starts: X=$00, $30, $60, $90
```

A visible segment may not cross a physical row without an explicit control. The
validator simulates X and rejects implicit crossing or writes beyond `$C0`.

### Recovered control geometry

Control values are context-sensitive native operations, so this table documents only
behavior the production layout is allowed to rely on.

| Control | Production treatment | Re-entry geometry / known effect |
| ---: | --- | --- |
| `0` | layout control; regenerated | rounds X to the next `$30` row start until row four |
| `1` | semantic by default | re-enters at X=`$30`; can overwrite staged text if used too late |
| `2` | mixed semantic/page control | re-enters at X=`$60`; may be demoted only under strict continuity rules |
| `3` | mandatory semantic control | continues at X=`$90` |
| `4` | layout scroll control; regenerated | scrolls dialogue rows and continues at X=`$90` |
| `5` | record separator | structural only; never ordinary translated markup |
| `6` | mandatory semantic control | continues at X=`$90` |
| `7` | decoder-supported, not generalized by production layout | treat as unrecovered for editing unless a call site is proved |

The overwrite guards are especially important for controls that re-enter earlier
rows. Current validation rejects a `CTRL:1` after staged bytes have passed `$30`, a
`CTRL:2` after `$60`, and a `CTRL:6` after `$90`.

### What production layout is allowed to regenerate

Interior Japanese `CTRL:0` and `CTRL:4` values are presentation geometry. The layout
engine removes them and greedily reflows reviewed English into 24-column rows,
inserting `CTRL:0` until the fourth row and `CTRL:4` when another row requires a
scroll.

Leading/trailing layout controls are retained because they can affect entry or exit
position even without visible text on both sides.

Speaker labels are recognized as layout units. A recognized `Name:` label starts a
fresh turn and may not be stranded on a row without its first spoken word.

### Semantic controls and the two audited demotion classes

Controls `1`, `3`, and `6` are normally mandatory and remain in source order.
`CTRL:2` is mixed: production may omit a source `CTRL:2` when it is only page geometry
inside continuous English, but it may never invent a new `CTRL:2` or move a source
speaker-changing `CTRL:2` away from that speaker turn.

Playtesting exposed a second, narrower exception: ten exact source `CTRL:1` waits are
presentation-only for the English layout. They are keyed by stable record ID and
locked to the exact certified base template in `production_translation.py`. The base
maps remain unchanged. If any locked template changes, the build fails and requires a
fresh audit instead of silently carrying the exception forward.

This is the safe pattern for future control exceptions: **record-scoped, source-
locked, and fail-closed**, never “change every control N.”

---

## 10. The scroll-copy and transparency traps

Two renderer details have already caused regressions and should be treated as engine
invariants.

### Dialogue scroll row copy

NOV2 file `$2571` / CPU `$8571` contains:

```text
B9 D7 87    LDA $87D7,Y
```

That indexed load copies the valid bottom dialogue row to the nametable before the
text buffer shifts during `CTRL:3/CTRL:4` behavior. Replacing it with a constant blank
load erased complete sentences at transitions. It is guarded as a **must remain
unchanged** sequence.

### `$AC` is useful for dialogue tails but wrong for menu clearing

The menu renderer treats tile `$AC` as transparent. Leaving menu-tail cells as `$AC`
can expose stale pixels, so the menu clear path uses opaque common-space tile `$C0`.

Dialogue tails are different. Making all unused dialogue cells opaque caused the
native typewriter cadence to process them as silent characters. Dialogue tails
therefore remain transparent `$AC` so they can be skipped without adding invisible
character timing/sounds.

Do not generalize a “blank tile fix” across menu and dialogue paths.

---

## 11. Fixed text outside scenario groups

Not every visible string passes through the scenario group parser. Three broad classes
exist:

1. **size-neutral direct records** beside code, such as NOV2 disk/save/load prompts;
2. **fixed tables** whose record/table boundaries are part of an addressing contract;
3. **special-purpose graphics text**, such as the Kouhen direct-boot warning.

A fixed-record patch must prove the source bytes or region hash before writing. If the
replacement changes the size, either recover the complete relocation model or choose
text that fits. Never shift adjacent executable code because a human-readable string
“looks like it should have room.”

The current release builder also converts every fixed stream that can reach the
patched entropy decoder. Mixing a byte-aligned native record into an entropy-only
runtime is invalid even if the English bytes themselves are correct.

### Canonical component patch order

Patch order is part of the architecture:

```text
all scenario banks
  -> production entropy placement

NOV2
  -> patched_nov2_ui()
  -> patch_entropy_nov2()

NOV4
  -> patched_nov4_font()
  -> patched_nov4_entropy_text()
  -> patched_nov4_entropy_title()

Kouhen
  -> patched_kouhen_boot_guard(SON-KOUH)
```

The order is intentionally non-commutative. For example, the font patch accepts a
small whitelist of known NOV4 states, and the entropy title path expects the
entropy-converted fixed text, not the retired native fixed-text patch.

---

## 12. Font engine and CHR ownership

### Dialogue font format

NOV4 stores inverse one-bit source rows at:

```text
NOV4 file offset = $1B7D + tile_id * 8
```

Each translated glyph is an 8x8 cell generated from deterministic five-pixel-wide
patterns. Lowercase descenders can use the eighth row, so the maintained font model is
5x8-in-an-8x8-cell rather than a strict seven-row font.

A set pixel in the logical glyph clears a bit in the inverse stored row because NOV4
expands these source rows into runtime tiles.

### The font table is not uniformly writable

This is one of the most important graphics discoveries:

- relative source slots `$98-$AF` alias a normal 2bpp graphics block used by the
  post-title graphics loader;
- the safely writable English 1bpp font-source range begins at slot `$B0`, NOV4 file
  `$20FD`;
- the active English font-source range ends after slot `$FE`, at NOV4 file `$2375`.

An English glyph must not be assigned to `$98-$AF` without first redesigning that
shared graphics ownership.

The historical extended-code-63 mapping pointed to tile `$AC`. Installing a glyph
there produced a repeated glyph-shaped post-title background. Production redirects
extended code 63 to recovered font tile `$B0` instead.

This is why “unused glyph code” and “unused CHR/font storage” are separate questions.

### NES 2bpp CHR refresher

Ordinary NES CHR patterns are 16 bytes per 8x8 tile:

```text
bytes 0-7   = low bitplane
bytes 8-15  = high bitplane
pixel palette index = low | (high << 1)
```

The inverse 1bpp dialogue-font source is therefore a game-specific intermediate
format, not generic NES CHR. `SON-KOUH` is another special case: it uploads private
1bpp patterns directly and flips the inverse dialogue glyph rows when generating its
message.

---

## 13. Title graphics engine

The title sequence is the most timing-sensitive graphics path. See
[Title sequence architecture](TITLE_SEQUENCE.md) for asset provenance; the runtime
facts most useful for debugging are summarized here.

### Recovered NOV4 layout

| NOV4 file region / offset | Purpose |
| --- | --- |
| `$065E-$0808` | source final-title RLE stream |
| `$0809-$094B` | source second/slide nametable RLE stream |
| `$09D2-$19D1` | 4 KiB title CHR |
| `$047A-$0599` | clock metasprite animation data - must remain byte-identical |
| `$03CA` | two clock-hand origins - the only intentionally adjusted hand geometry |
| `$1B7D + tile*8` | inverse dialogue-font source geometry |

`NOV4` loads at `$A200`. Appended English title helpers/assets are valid only while
their final loaded end remains below `$D7B5`.

### Two nametables and the swipe

The resident decoder writes:

- final title map to nametable 0 at PPU `$2000`;
- slide/Nintendo map to nametable 1 at PPU `$2400`.

States 3-5 use 21 recovered horizontal origins:

```text
$01F0, $001C, $01D8, $0034, $01C0, $004C, $01A8,
$0064, $0190, $007C, $0178, $0094, $0160, $00AC,
$0148, $00C4, $0130, $00DC, $0118, $00F4, $0100
```

The physical attribute tables hide/reveal sections of the 512-pixel-wide NT0/NT1
world while those origins alternate.

### Pattern-table ownership and temporal reuse

The upper title background owns tile IDs `$00-$EB`. IDs `$EC-$FF` remain the original
clock-hand source and are protected.

The Nintendo phase temporarily overlays 38 IDs `$B0-$D5`. Before the monochrome swipe
becomes visible, a helper restores those IDs from the authoritative base slide CHR.

The exact slide and exact final upper tables cannot coexist in the available upper
background IDs. The current build therefore temporally reuses **53** tile IDs:

1. those IDs initially contain the exact monochrome slide patterns;
2. the final transition uploads a 53-tile / 848-byte delta into the same IDs;
3. applying that delta reconstructs the exact colored final upper table.

The lower title uses an independent 55-pattern set in pattern table 0. NOV4's existing
raster split switches pattern-table behavior at tile row 16, inside a visually blank
band below `PUSH START`.

### RLE nametable format

The native title/SON-KOUH family uses a small count-prefix RLE:

- bytes below `$C0` are literals;
- `$C0 + count`, followed by one byte, repeats that value;
- `$FF` terminates the stream;
- because `$FF` is reserved, the largest legal run prefix is `$FE` = 62 copies.

The relocated title payload contains two decoded 1 KiB nametables followed by one
final `$FF` terminator.

### PPU/NMI ordering is functional behavior

The title helpers intentionally blank rendering and sometimes disable NMI while CHR
or title-only split state changes.

Important state:

- `$1C` - PPUMASK mirror used by the game;
- `$FF` - PPUCTRL/NMI-related mirror used by the title code;
- `$57/$58` - recovered horizontal scroll/nametable origin state;
- `$2000` - PPUCTRL register;
- `$2001` - PPUMASK register.

The pre-slide helper clears the `$1C` mirror **before** blanking `$2001`, then disables
NMI, restores Nintendo-overlaid CHR, installs the first scroll origin, and queues the
monochrome palette. The palette must be queued **after** the FDS BIOS CHR upload,
because that BIOS operation can overwrite palette staging state and its update flag.

The helper deliberately does not restore `$2001` immediately. The next NMI must apply
the new scroll/palette/nametable state first, then restore rendering from `$1C`. If
rendering is restored too early, one frame of the old Nintendo nametable appears
through the restored English title CHR.

The final transition similarly blanks rendering/NMI while uploading the 53-tile upper
delta and 55 lower patterns, then restores the split and render state.

### START exit stack trap

The source title-exit branch is a tail call. It ultimately jumps to `$6119`, whose
`RTS` is supposed to return directly to the main engine. A detour implemented with
`JSR` leaves an extra return address on the stack; `$6119` then returns into the
middle of NOV4 and crashes after START.

The production detour therefore uses `JMP` to the appended exit helper and ends with
the original state-change/tail-call behavior.

This is a good example of why a visually correct patch still needs control-flow
recovery.

---

## 14. Kouhen direct-boot warning is a separate graphics engine path

`SON-KOUH` does **not** render its warning through the normal scenario decoder.
It owns a small private graphics path:

- component size: 739 bytes;
- 21 private one-bit tiles;
- blank tile ID `$14`;
- RLE nametable fragment starts at PPU `$20D0`;
- decoded fragment size: 414 bytes.

The English patch regenerates only the private glyph rows and RLE tilemap while
preserving the program and component size. The generated glyph bits are inverted from
the NOV4 dialogue-source representation because `SON-KOUH` uploads them directly.

If the normal English font and dialogue are correct but the direct-Kouhen warning is
Japanese or garbled, the fix belongs here, not in the shared text decoder.

---

## 15. Graphics files not yet modeled as a generic editable engine

The game also contains `OB*`, `OBJ*`, and `BG*` graphics components. Their existence
and FDS identities are known, but the public translation architecture does not yet
claim one universal decoded object/background format or relocation model for all of
them.

Treat these as **UNKNOWN unless a specific component has been recovered**. Before a
future graphics edit becomes production code, document:

- file load address and FDS file kind;
- CHR/nametable/sprite/palette destination;
- compression or transfer routine;
- pointer/caller structure;
- lifetime relative to other overlays;
- any tile IDs shared temporally with another scene;
- exact free-space/relocation proof;
- emulator evidence and a regression test.

Do not extrapolate the title allocator or `SON-KOUH` RLE format to unrelated graphics
without evidence.

---

## 16. Debugger cookbook

These are the fastest first checks for recurring symptom classes.

### First record is correct, following text becomes garbage

Suspect entropy stream framing.

- Break at `$80B1` and `$81E0`.
- Watch `$6A/$6B/$6C` across separator 5.
- `$6C` must **not** reset after an ordinary record separator.
- Confirm that the current stream is not a genuinely new byte-addressed page/group.

### A menu page works until record 32/64/96

Suspect page-pointer regeneration or page alignment.

- Inspect header pointer `$A21A` (file `$001A`).
- Verify each stored page address lands on the first byte of a separately packed
  32-record entropy stream.
- Confirm the secondary tables moved by the same relocation delta.

### Text overwrites an earlier line or an unexpected A press is required

Suspect control geometry, not encoding.

- Inspect the record's certified control topology.
- Simulate X using row starts `$00/$30/$60/$90`.
- Check whether `CTRL:1`, `CTRL:2`, or `CTRL:6` re-enters before already staged text.
- Decide whether the source control is semantic, mixed, or a narrowly auditable
  presentation-only exception. Do not globally demote the control value.

### Dialogue vanishes during a scroll/pause transition

Check NOV2 file `$2571` / CPU `$8571` first. The `B9 D7 87` indexed row-copy load must
remain intact.

### Menu text leaves stale garbage at the right edge

Check menu clear tile `$C0` and the eight-glyph renderer. Do not apply the same opaque
clear to dialogue tails.

### Selection brackets fit short labels but not long labels

Break at `$946B` and `$989F`; inspect the captured width table at `$8758-$875F`.

### A repeating letter/pattern appears in the post-title background

Suspect font/graphics aliasing. Verify that no active English glyph source was written
into relative slots `$98-$AF`; active font storage begins at `$B0`.

### The title flashes mixed graphics for one frame

Suspect PPUMASK/NMI ordering. Inspect `$1C`, `$FF`, `$2000`, `$2001`, `$57`, and `$58`
through the pre-slide/final transition. Confirm palette staging occurs after the BIOS
CHR upload.

### Game crashes immediately after START

Inspect the title-exit detour. The handoff must preserve the source tail-call stack
shape; a `JSR` substituted for the production `JMP` is a prime suspect.

### Only the Kouhen direct-boot warning is wrong

Inspect `SON-KOUH`; it is a private tile/RLE path, not the scenario text engine.

---

## 17. A repeatable workflow for future fixes

For each new bug, create a small evidence packet before changing code.

### Step 1: identify the owning surface

Record:

```text
visible symptom:
FDS component:
side / phase:
component load address:
file offset(s):
CPU address(es):
PPU destination if relevant:
```

If the component is unknown, stop and locate the FDS file load first.

### Step 2: capture source authority

Record one or more of:

- exact source byte sequence;
- region SHA-256;
- pointer chain from known header/caller;
- decoded record ID and control sequence;
- source CHR/tile range;
- source routine/disassembly range.

A future patch should reject different bytes rather than “find something similar.”

### Step 3: recover all consumers before relocating

Search for:

- direct absolute pointers;
- page/base pointers;
- sequential scanners;
- secondary tables;
- duplicated renderer copies;
- code that assumes a fixed end address;
- another phase that reads the same physical bytes.

A string/table is movable only after all address contracts that reach it are modeled.

### Step 4: reproduce the runtime state

Use Mesen or equivalent to capture:

- PC at the relevant handler;
- A/X/Y and stack if control flow matters;
- zero-page scratch used by the routine;
- source pointer and current bit mask for text;
- PPUCTRL/PPUMASK/scroll state for graphics;
- nametable and pattern-table view for rendering bugs.

Label the result **OBSERVED** until static code explains it.

### Step 5: choose the narrowest patch layer

Prefer, in order:

1. translation/review data;
2. production layout policy;
3. entropy packing/placement;
4. fixed-table declarative data;
5. source-verified size-neutral instruction patch;
6. verified relocation with all pointers regenerated;
7. new runtime helper in proven free/reclaimed space.

Do not start with a global decoder rewrite when one record/table policy is wrong.

### Step 6: define postconditions before implementation

Examples:

```text
record IDs unchanged
semantic controls preserved
scenario fixed tail byte-identical
loaded end < $D7B5
menu page pointers decode every label
clock CHR/metasprite bytes unchanged
palette region $9390-$93AF unchanged
NOV2/NOV4 size invariant preserved where required
```

### Step 7: test at three levels

- **unit** - synthetic structure and policy behavior;
- **integration** - exact source guards and rebuilt component identity;
- **runtime** - emulator route that proves the player-visible behavior.

A static round trip cannot prove NMI timing, disk swapping, save/load behavior, or one-
frame graphics corruption.

---

## 18. What to document when a new engine fact is discovered

Every newly recovered fact should be written where the next maintainer will find it.
Use this compact template:

```text
Component:
Source revision / guard:
File offset:
Loaded CPU address:
PPU address, if any:
Callers / pointer chain:
Runtime state used:
Observed behavior:
Verified interpretation:
Bytes/addresses that may change:
Bytes/addresses that must not change:
Test protecting the fact:
Playtest route protecting the behavior:
Remaining unknowns:
```

If the fact changes a general mental model - for example, discovering that an
apparently fixed table is actually page-indexed - update this guide as well as the
specific module comments.

---

## 19. Known unknowns and non-generalizable behavior

The following should remain explicit so future work does not silently invent rules:

- Control codes are not assigned one universal narrative meaning. Production relies
  only on recovered geometry and record-specific semantic evidence.
- `CTRL:7` is decoder-representable but has no generic production-layout rule.
- `OB*`, `OBJ*`, and `BG*` files are not one proven universal graphics format.
- Hardware-visible title behavior depends on NMI/PPU ordering that static asset tests
  cannot fully prove.
- FDS BIOS calls can mutate staging state outside the immediate source buffer; title
  palette ordering is one known example.
- An emulator save state can preserve candidate-specific disk-write overlays or stale
  loaded code. Reproduce release-critical bugs from clean candidate state.

Unknown is a valid status. It is safer than encoding an attractive guess into the
release builder.

---

## 20. High-value source files for deeper study

| Question | Primary source |
| --- | --- |
| Native packed bits and separator alignment | `work/time_twist/textcodec.py` |
| English glyph/token mapping | `work/time_twist/english.py`, `charmap.py` |
| Scenario pointer layout and fixed-tail recovery | `work/time_twist/scenario.py` |
| Frozen production grammar | `work/time_twist/entropy_codec.py` |
| Dictionary search/constraints | `work/time_twist/entropy_compression.py` |
| Resident/spill placement and page relocation | `work/time_twist/entropy_scenario.py` |
| NOV2 patched decoder/runtime | `work/time_twist/entropy_runtime.py` |
| Four-row English layout/control policy | `work/time_twist/production_translation_core.py` |
| Record-scoped production exceptions | `work/time_twist/production_translation.py` |
| Fixed prompts, special UI, Kouhen guard | `work/time_twist/ui.py`, `ui_fixed_tables.py` |
| Dialogue font and tile ownership | `work/time_twist/font.py` |
| NOV4 title memory map | `work/time_twist/title_layout.py` |
| Exact title asset allocation | `work/time_twist/title_assets.py` |
| PPU/NMI helper installation | `work/time_twist/title_patch.py`, `entropy_title.py` |
| Final component patch order | `work/time_twist/release_build.py` |

The goal is that a future maintainer starts from a known runtime model, not a hex
editor and a blank notebook.
