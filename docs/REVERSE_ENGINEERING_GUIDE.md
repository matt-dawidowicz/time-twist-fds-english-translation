# Reverse-engineering guide: text, graphics, and runtime behavior

This document is the maintainer reference for understanding **how Time Twist actually
moves text and graphics from FDS files into RAM and onto the NES screen**. It is
intended to make future fixes incremental: a maintainer should be able to identify
which engine owns a symptom, find the relevant pointer or runtime state, prove the
constraint, patch the narrowest layer, and add the right regression test without
rediscovering the game from scratch.

Read this with [Architecture](ARCHITECTURE.md), [Formats](FORMATS.md), the
[Gameplay script engine](GAMEPLAY_SCRIPT_ENGINE.md), the
[Gameplay graphics engine](GAMEPLAY_GRAPHICS_ENGINE.md), and the
[Code tour](CODE_TOUR.md). The specialized title, menu, font, gameplay-VM, and
graphics documents remain authoritative for their subjects; this guide connects them
into one runtime model.

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
optimizer searches up to 128 entries for every scenario bank, caps dictionary phrases
at 12 grammar tokens, and caps nesting depth at 4. The former TT2-specific 96-entry
exception was removed after source-backed benchmarking showed the normal 128-entry
policy was safe and slightly smaller.

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

The native renderer used fixed six-glyph geometry. An early English patch raised two
loop counts to eight, but later reverse engineering and MesenCE testing proved that
eight was only a conservative implementation limit. The production renderer is now
variable-width:

- when a label finishes decoding, X is exactly twice its visible glyph count;
- a width recorder converts that to pixels and stores it at Work RAM
  `$042D+visual_index`;
- the first-row draw count comes from that metadata with a nonzero fallback;
- the paired row reuses the first-row count rather than a fixed literal;
- the second column is positioned from the corresponding first-column label width;
- leading and trailing selection cursors use the same width metadata; and
- the staging clear spans 36 bytes, supporting up to 18 glyphs at two staging bytes
  per glyph.

For two-column rows, validate actual use-site geometry rather than applying a global
eight-character rule. The conservative production model allows at most 20 combined
glyphs and keeps the trailing cursor at or before x=`$F8`. Do not store code or
scratch data in `$9390-$93AF`; that region is live palette state.

---

## 8. Renderer-aware menu QA

A menu label can be renderer-safe by itself and still fail in a two-column pairing.
The maintained menu-geometry audit therefore validates actual runtime geometry, not a
single global character-count limit.

For every source-visible descriptor combination it checks:

- the decoded English label width;
- 18-glyph per-label staging capacity;
- the conservative 20-glyph combined pair limit;
- the second-column position derived from the first label;
- the trailing selection cursor against x=`$F8`;
- all order-preserving compacted visible subsets that can arise when predicates hide
  entries; and
- entropy-decoded release-candidate labels rather than trusting source JSON alone.

The source-backed audit currently covers 721 labels, 367 descriptor records, and 162
distinct possible two-column pairs. Candidate auditing must decode all 721 labels from
the built image before a release can be promoted.

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

Playtesting exposed a second, narrower exception: eleven exact source `CTRL:1` waits
are presentation-only for the English layout. They are keyed by stable record ID and
locked to the exact certified base template in `production_translation.py`. The base
maps remain unchanged. `TT1A/g0/r30` joined this set during final playtesting after
its pause following `Time travel, huh...` proved to interrupt one continuous internal
thought; its later `CTRL:6` remains semantic. If any locked template changes, the
build fails and requires a fresh audit instead of silently carrying the exception
forward.

This is the safe pattern for future control exceptions: **record-scoped, source-
locked, and fail-closed**, never “change every control N.”

---
