# Bug-fix and title-screen implementation guide

> **Advanced implementation reference.** This document preserves recovered
> offsets and runtime evidence. Begin with [Architecture](ARCHITECTURE.md) or
> [Contributing code](../CONTRIBUTING_CODE.md) unless you are working directly
> on a guarded UI, font, title, or engine patch.

This guide documents the parts of the translation patch that repair runtime
problems or replace the title screen. It is intentionally tied to the current
source code rather than to a finished `.fds` file. The authoritative
implementations are:

- `work/time_twist/ui.py` for fixed-address prompts, renderer corrections,
  and the NOV2 input fix;
- `work/time_twist/font.py` for deterministic dialogue glyphs;
- `work/time_twist/title.py` for the English title, native swipe, clock, and
  title-state helpers;
- `work/time_twist/release.py` for patch ordering, FDS replacement, output
  validation, and safe publication;
- `work/integration_tests/test_ui.py` and
  `work/integration_tests/test_title.py` for exact ROM-derived regression
  coverage.

The documentation uses three address spaces. A **file offset** is relative to
an extracted FDS file payload. A **CPU address** is the address after that file
has been loaded by the game. A **PPU address** identifies NES video memory.
These values are not interchangeable. For example, NOV2 file offset `$39E1`
is CPU `$99E1` because NOV2 loads at `$6000`.

## Defect classification

Not every repaired symptom is a bug in Nintendo's original game. Keeping the
categories separate matters when deciding whether a change belongs in a
faithful translation.

| Class | Meaning | Examples in this project |
| --- | --- | --- |
| Proven original-engine defect | Reproduced behavior caused by original program logic | B on a one-choice menu can redraw the same menu and move its border through START |
| Localization completeness defect | Japanese-only fixed content was left behind by an earlier translation layer | Wrong-disk warning, normal disk prompts, wait prompt, Kouhen direct-boot warning |
| Translation-patch regression | A localization change broke behavior the original game handled correctly | A broad dialogue-clear change deleted complete lines; an incorrect title exit call crashed after START |
| Presentation correction | The game still ran, but translated graphics or glyphs were visibly wrong | Mirrored apostrophe, accented `é`, lowercase `p`, incomplete slide geometry, misplaced clock hands |
| Build/publication defect | Generated ROM bytes were correct, but tooling made the output unreliable or inaccessible | Windows output inherited a private temporary-directory ACL |

Only the one-choice B issue is presently proven as an original-engine bug.
Other suspected gameplay issues must be reproduced from equivalent Japanese
and English save states before they are attributed to the original engine.
The direct Kouhen warning, the disk-request waiting screen, and the original
eight-pixel black strip at the left edge are intentional behavior.

### Why the leftmost eight pixels remain black

The NES PPU can suppress background and sprite rendering in the leftmost
eight-pixel column through PPUMASK. Time Twist uses that native clipping region
throughout ordinary scenes; the Japanese game shows the same strip. It hides
partially updated tiles and horizontal-scroll seams at the edge of the
nametable. The translation therefore does not force those pixels on globally:
doing so would exchange one stable black column for scene-dependent garbage or
sprite fragments.

This is independent of display aspect ratio. Stretching the 256x240 signal to
4:3 changes pixel shape but cannot create or remove the source-side clipping
column. A player who does not want to see it should crop eight source pixels
from the left in the emulator's overscan settings; that presentation-only crop
does not alter the ROM or expose hidden edge data.

## Safety model shared by every patch

The patching code follows a fail-closed contract:

1. Identify the owning FDS file and its load address.
2. Validate exact source bytes, a source-region hash, or a whole-component
   SHA-256 before mutation.
3. Encode text through the native packed-text codec. Never search and replace
   display strings in the combined disk image.
4. Preserve fixed record sizes, control ordering, pointers, table ends, and
   component footprints unless a separately proven free region is used.
5. Return a new `bytes` object; do not modify the supplied source object.
6. Decode or inspect the result and verify every critical invariant again.
7. Replace the named FDS file through `FdsImage`, allowing the container layer
   to update file sizes and side padding safely.

`SourceVerifiedPatch` in `ui.py` makes the instruction-patch form of this
contract declarative. Each immutable record names the component, file offset,
CPU address, expected source bytes, same-size replacement bytes, and purpose.
For components with a proven linear load mapping, the constructor also checks
`cpu_address == component_load_address + file_offset`; currently this is
established for NOV2 at `$6000`. Unknown mappings are rejected instead of being
hidden behind a guessed generic rule. It refuses an address inconsistency,
size change, or source mismatch before writing anything.

## NOV2 extended English dictionary decoder

The native nine-bit dictionary form can name entries 1-31. English does not
use extended-glyph values 0-36: its remaining uppercase letters, digits,
punctuation, and `é` occupy values 37-62. The release reinterprets that unused
range as dictionary entries 32-68. Both forms remain nine bits, and native
Japanese source parsing remains unchanged.

The complete decoder change is one exact-size, source-verified replacement:

| File | CPU | Expected bytes | Replacement bytes | Purpose |
| ---: | ---: | --- | --- | --- |
| `$21D3` | `$81D3` | `A5 3A C9 04 90 07 C9 20 B0 09 4C ED 81` | `A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82` | Route values 0-36 to dictionary entries 32-68; retain values 37-63 as extended glyphs |

The replacement is 13 bytes, exactly the size of NOV2's original extended
glyph branch. Values below `$25` reach the existing dictionary expander at
`$82BE` after adding 32; values `$25` and above branch to the existing glyph
path at `$8226`. `CMP #$25` clears carry for the add path, so the compact
sequence does not require a separate `CLC`.

## NOV2 one-choice B-button engine fix

### Symptom

After the title, START is presented as a one-choice menu. Pressing B could
close and immediately redraw that same menu. The top border then slid through
the START label. Normal Back/Cancel behavior on larger menus was desirable and
could not simply be disabled globally.

### Root cause

The B-button dispatcher begins at CPU `$99DC`. Its original five-byte guard is
correct:

```text
$99DC  A5 9C       LDA $9C
$99DE  D0 01       BNE $99E1
$99E0  60          RTS
```

`$9C` holds a saved Back destination. A one-choice menu can save its own
destination, so a nonzero pointer does not prove that going Back will leave the
menu. The old action path therefore re-entered the menu it had just closed.

### Why the fix needed code-space recovery

NOV2 occupies CPU `$6000-$A1FF`; NOV4 begins immediately above it. Growing
NOV2 would move or overlap another resident component. The patch instead
recovers twelve bytes at `$6A2E-$6A39` by redirecting duplicate state-table
entries to identical handlers that already exist elsewhere.

The complete source-verified patch table is:

| File | CPU | Expected bytes | Replacement bytes | Purpose |
| ---: | ---: | --- | --- | --- |
| `$0A0D` | `$6A0D` | `31 6A 34 6A` | `40 6A 40 6A` | Reuse the existing handlers for states 1 and 2 |
| `$0A13` | `$6A13` | `34 6A` | `40 6A` | Reuse the existing handler for state 4 |
| `$0A17` | `$6A17` | `37 6A` | `73 6B` | Reuse the existing handler for state 6 |
| `$0A25` | `$6A25` | `F0 07` | `F0 19` | Retarget the shared state-return branch |
| `$0A2E` | `$6A2E` | `4C 01 61 4C 01 61 4C 01 61 4C DB 89` | `A4 98 88 F0 60 A9 04 85 A1 4C B8 7D` | Install the one-choice guard helper in reclaimed space |
| `$39E1` | `$99E1` | `A9 04 85 A1 A9 22 4C 09 61` | `4C 2E 6A EA EA EA EA EA EA` | Detour the nonzero saved-destination path to the helper |

The helper at `$6A2E` is:

```text
$6A2E  A4 98       LDY $98       ; visible choice count
$6A30  88          DEY
$6A31  F0 60       BEQ $6A93     ; one choice: use an existing RTS
$6A33  A9 04       LDA #$04      ; larger menu: retain action 4
$6A35  85 A1       STA $A1
$6A37  4C B8 7D    JMP $7DB8     ; retain the original state-$22 path
```

`DEY` is used only for comparison; the stored choice count at `$98` is not
changed. One choice returns without acting on B. Two or more choices follow
the original Back/Cancel behavior through `$7DB8`. The original `$9C=0`
guard at `$99DC-$99E0` remains byte-identical.

### Regression evidence

`test_zenpen_nov2_b_ignores_one_choice_but_keeps_normal_back` verifies every
source and replacement sequence, the branch target `$6A93`, the detour at
`$99E1`, and the retained action/state path. The public
`test_ui_unit.py` also proves that declarative patches reject source and size
mismatches without partially mutating the component.

## Menu clearing without deleting dialogue

### Original visible problem

Shorter English menu choices could leave pixels from a previous, longer line.
NOV2 filled unused cells with tile `$AC`, which its menu renderer treats as
transparent. Transparent cells do not overwrite old nametable content.

### Narrow correction

At NOV2 file offset `$345B` / CPU `$945B`, the menu-choice clear operand is
changed from transparent `$AC` to opaque blank tile `$C0`. Only that verified
operand changes:

| Component | File | CPU | Source | Replacement |
| --- | ---: | ---: | --- | --- |
| NOV2 menu-choice clear | `$345B` | `$945B` | `$AC` | `$C0` |

### Why dialogue is deliberately different

An earlier broad clear attempt changed the dialogue scroll uploader at file
offset `$2571` / CPU `$8571` from indexed row data to an immediate blank. It
removed complete sentences at `{CTRL:3}` and `{CTRL:4}` transitions, including
a chant and the narration following it.

The current patch therefore treats these as protected source bytes, not a
patch target:

```text
file $2571 / CPU $8571: B9 D7 87
```

That indexed load copies the valid bottom dialogue row before the buffer
shifts. Dialogue tail cells also remain transparent `$AC`—including the
fixture byte at file `$245F`—so the typewriter does not process a full row of
silent spaces. The integration test locks both the one-byte menu correction
and the unchanged dialogue path.

## Disk switching and fixed prompts

The FDS logic itself was not rewritten. These patches complete the English
presentation at the exact packed-record slots already used by NOV2.

| Purpose | File offset | Packed bytes | English source |
| --- | ---: | ---: | --- |
| Wait prompt | `$25D9` | 13 | `Please wait... ` |
| Part 1 label | `$260D` | 6 | `Part 1` |
| Part 2 label | `$2613` | 5 | `Part2` |
| Side A line | `$2618` | 6 | `{CTRL:0}SideA` |
| Side B line | `$261E` | 7 | `{CTRL:0}Side B` |
| Insert instruction | `$2625` | 11 | `{CTRL:0}{CTRL:0}Insert now.` |
| Live Start prompt | `$2651` | 6 | `Start ` |
| Saved-game label | `$2657` | 4 | `Load` |
| Saved-game disk-status line | `$269A` | 8 | `Bad side.` |
| Alternate side-heading record | `$26CC` | 8 | `Bad side.` |
| Visible same-side retry heading | `$26D4` | 10 | `Wrong side.` |
| Same-side retry instruction | `$26DE` | 10 | `{CTRL:0}Try again.` |
| Wrong-disk heading | `$26E8` | 11 | `Wrong disk! ` |
| Wrong-disk instruction | `$26F3` | 14 | `{CTRL:0}Try another side` |

The saved-game label is a separate record immediately after the live START
prompt. Its original Japanese loanword means “load”; with the English font it
appeared as gibberish after a save was present. The native source has `A-B side
/ disk number / error` records. The disk-swap save-state comparison shows that
the same-side retry draws the `disk number` record at `$26D4`, followed by
`$26DE`; it previously rendered as English-font garbage. `$26D4` has room for
ordinary packed `Wrong side.`. The alternate eight-byte `$26CC` record instead
uses ordinary-glyph `Bad side.` so no private compact suffix is required. This
path does not reuse the later two-record `Wrong disk! / Try another side`
recovery text.

The saved-game loader has one additional status record. Runtime save-state
evidence superseded an earlier bit-aligned interpretation: the visible renderer
starts at NOV2 file `$269A`, so the complete eight-byte source record is
replaced in place with ordinary-glyph `Bad side.`. The patch changes no next
record, pointer, disk-state branch, requested-side variable, decoder limit, or
FDS BIOS call.

Each record is encoded independently with `encode_english()` and
`pack_records()`. The two short labels use the intentional compact spellings
`Part2` and `SideA`, which fit their immutable direct packed records with
ordinary glyphs. This avoids repurposing NOV4 tile `$AC`: the title nametable
uses that tile for its background pattern. Both byte lengths and exact Japanese
source records remain guarded. No disk-state branch, requested-side variable,
polling loop, or FDS BIOS call is altered.

NOV4 owns another copy of the live Start prompt at file offset `$0095`. It is
patched separately because changing the NOV2 copy cannot affect text embedded
inside NOV4. Both Japanese source records and `Start ` occupy six packed
bytes.

## Kouhen direct-boot warning

Booting Kouhen directly is intentionally unsupported because the second half
expects live state inherited from Zenpen. `SON-KOUH` is a 739-byte (`$02E3`)
startup program that shows the warning. It does not use the scenario codec or
the NOV4 dialogue font.

The patch leaves all program code, vectors, addresses, and file size intact.
It replaces only:

- the RLE nametable stream at file `$01EC-$0226`;
- the private 1bpp glyph rows beginning at file `$0233`.

The decoded tilemap contains 414 tile IDs beginning at PPU `$20D0`. The two
centered lines are `Please start with` on row 11 and `Part 1` on row 13.
Eleven distinct visible characters are assigned private tile IDs; tile `$14`
is the blank. Twenty-one eight-byte tile allocations remain reserved exactly
as in the source.

Runs are encoded with the component's native count-prefix format. `$FF`
terminates the stream, so runs are split at 62 copies (`$FE`) and the remaining
allocation is padded with additional terminators. The direct-upload glyphs
invert the dialogue font's stored bits because SON-KOUH uploads its 1bpp rows
directly, whereas NOV4 expands inverse font data.

Before either asset is written, `patched_kouhen_boot_guard()` requires the
exact component size and whole-file SHA-256
`EE32CD2462B224A55B875694D8C34A362754A92630DCDB1A40451AA331C43847`.

## Dialogue-font presentation corrections

`font.py` replaces desktop-font rasterization with a deterministic 5x7 pixel
font. Every glyph is placed inside an 8x8 cell at x=1, uses rows 0-6, and keeps
the final row blank. The stored rows are inverse 1bpp because NOV4 expands
zero bits into ink pixels.

This directly fixes several screenshot-driven defects:

- the apostrophe is a closing mark, with its lower pixel leaning left rather
  than looking like an opening quote;
- accented `é` has a separately designed acute accent aligned over the
  lowercase body, used by `consommé`;
- lowercase `p` uses the lowercase x-height and stem rather than appearing as
  an oversized capital-like glyph;
- uppercase and lowercase letters remain visibly distinct.

The human-readable glyph rows in `PIXEL_FONT_5X7` are the authority. Font
generation does not depend on an installed desktop font, antialiasing, or host
rendering differences. `patched_nov4_font()` accepts only the clean NOV4 or the
same component after the size-neutral NOV4 UI patch, then writes only recovered
font-table rows starting at file `$1B7D`.

## English title-screen reconstruction

### Recovered NOV4 ownership

NOV4 loads at CPU `$A200`. The Japanese source payload is `$2375` bytes. It
owns the title-state 6502 code, two compressed nametables, background CHR, and
the source graphics and metasprite tables for the animated clock hands.
Resident NOV3 begins at `$D7B5`, which is the hard upper bound for an expanded
NOV4.

Important recovered regions are:

| Region | File range or offset | Loaded CPU address | Contract |
| --- | --- | --- | --- |
| Final nametable RLE | `$065E-$0808` | `$A85E` | Decodes to exactly 1,024 bytes |
| Second nametable RLE | `$0809-$094B` | `$AA09` | Decodes to exactly 1,024 bytes |
| Slide palette byte | `$0995` | `$AB95` | Source `$0F`, patched `$30` |
| Background CHR | `$09D2-$19D1` | `$ABD2` | Exactly 4 KiB |
| Clock-source tail | tile IDs `$EC-$FF` | Inside background CHR | Must remain byte-identical |
| Clock metasprites | `$047A-$0599` | `$A67A` | Graphics sequence and timing remain unchanged |
| Clock origins | `$03CA` | `$A5CA` | Position only; frame data is preserved |

### Source-revision guards

`_validate_source()` runs before asset generation or mutation. It checks:

- exact source size `$2375`;
- the title pointer instruction at `$01BC`;
- PPUCTRL setup at `$0176`;
- title exit at `$022F`;
- the background-tail and phase-zero upload calls at `$0296` and `$02AC`;
- the pre-slide call at `$02E4`;
- the state-transition call at `$038E`;
- the palette byte at `$0995`;
- the clock-hand origin bytes at `$03CA`;
- the combined two-nametable RLE framing and single terminator;
- SHA-256 fingerprints of both original compressed nametables, the 4 KiB CHR,
  the clock-source tail, and the metasprite animation table.

This prevents absolute addresses or injected 6502 helpers from being applied
to another game revision or to an already modified, incompatible NOV4.

### The production artwork contract

The approved opening GIF is retained as regeneration provenance. Production
consumes two exact 256x240 indexed (`L` or `P`) authorities:

- `Time Twist approved native title.png` uses indices 0-3 and may own rows
  0-96;
- `Time Twist approved native slide.png` uses indices 0-1 and may own rows
  0-95.

The final palette indices mean:

| Index | Meaning |
| ---: | --- |
| 0 | Black/background |
| 1 | White outline |
| 2 | Pink fill |
| 3 | Purple bevel/shadow |

Production does not crop, resize, resample, or quantize either PNG. The
regeneration tool validates the GIF hash, dimensions, loop flag, frame count,
and delays; inverts its display cells by majority vote; selects the completed
white swipe; and uses temporal consensus to remove only the moving blue hand
sprites from the colored phase. It then applies the reviewed native-pixel
cleanup to the lower T bevel, reference-traced clock rim, W/I/S outlines, and
balanced TM. The first T's upper-right cap uses a reviewed four-pixel correction to restore the white cap and dark inner bevel. The clock rim also preserves the GIF's one-native-pixel black outer boundary instead of bridging those cells with pink.
The lower screen, time machine, copyright line, PUSH START, and live hand
sprites remain derived from native game assets.

The subtitle is not baked into either authority PNG. `build_title_assets()`
clears rows 97-111 and redraws `On the Outskirts of History...` at `(42,102)`
with the deterministic pixel font. This keeps subtitle wording and glyph
rendering reviewable in code.

### Fitting exact artwork into the NES pattern budget

Each upper phase fits individually in the 236 IDs `$00-$EB`, but their union
needs 291 patterns. The allocator reuses 55 contiguous IDs across time. They
hold exact swipe patterns in the base CHR and exact final patterns after a
880-byte transition upload. All remaining phase patterns have fixed IDs. No
tile is clustered, merged, approximated, or substituted.

Rows 16-29 still use the independent exact 55-pattern lower table through the
native split at row 16. IDs `$EC-$FF` remain reserved for original clock-hand
source tiles. All assignments are deterministic, and applying the stored
delta to the base slide table must reproduce the final table byte-for-byte.

### Building the final and sliding nametables from two exact phases

The final nametable begins as the original decoded map. Rows 0-96 are replaced
by the approved colored authority; the exact subtitle is drawn below it; and
the original composition resumes at row 112. Tile IDs are assigned from the
final upper or exact lower pattern set according to the split row.

The defective earlier slide treated the Japanese title's tile occupancy as a
mask for an English wordmark. Because the letter shapes differ, it assembled
unrelated fragments, omitted the final columns, and jumped to another geometry
when the colored title appeared.

The corrected second nametable copies all 32 columns of the first twelve tile
rows from the separate monochrome authority. The original nametable attribute
bytes remain responsible for deciding which pieces are visible during the
swipe. Pixel and file hashes lock both authorities against drift.

### Preserving the original dramatic swipe

NOV4 states 3-5 retain all 21 original nine-bit horizontal origins:

```text
1F0 01C 1D8 034 1C0 04C 1A8 064 190 07C 178
094 160 0AC 148 0C4 130 0DC 118 0F4 100
```

`$57` provides the low eight scroll bits and bit zero of `$58` selects the
neighboring horizontal nametable. NT0 and NT1 form one 512-pixel world. The
origins alternate across that world with damped movement toward `$0100`.

The animation is not a simple whole-logo slide. Its attribute tables select
different background palettes for 16x16 regions. During state 3, three
palettes are entirely black while palette 1 is visible. The combination of
horizontal wrap and attribute masking produces the native sequence: blank,
alternating pieces from each side, nearly complete, and settled.

`render_slide_logo_frame()` reconstructs this exact 512-pixel world, applies
each physical nametable's attribute table before scrolling, and returns the
same twelve moving tile rows the PPU would show. This corrected an early static
model that mistakenly treated the effect as an unmasked whole-logo movement.

### Sharing tile IDs with the Nintendo phase safely

The opening Nintendo graphic needs 38 patterns and temporarily occupies tile
IDs `$B0-$D5`. The full English title also needs those IDs. Preventing the
English slide from using them caused missing columns; using them without a
restore caused Nintendo fragments to appear inside the wordmark.

The patch uses temporal ownership:

1. The initial helper uploads the 38 Nintendo patterns to `$B0-$D5` for the
   Nintendo phase.
2. At the original state-3 call site, a 59-byte helper preserves the native
   monochrome-palette call.
3. The helper saves and clears the `$1C` PPUMASK mirror, blanks `$2001`, and
   disables NMI.
4. The English base patterns for `$B0-$D5` are uploaded from the patched CHR.
5. The helper installs the first `$01F0` origin while still blank, then
   restores PPUCTRL/NMI and the `$1C` PPUMASK mirror only. It deliberately
   leaves `$2001` blank so the next NMI can apply the new scroll/nametable
   registers before rendering becomes visible again.

The original timing and 12-pixel movement remain native. The helper reads the
authoritative base slide CHR directly, so no duplicate restore payload is
serialized. The space that previously served as a zero/restore workspace now
stores the 880-byte final-phase delta.

### Rendering the completed monochrome phase faithfully

The original state-3 palette hid some nonzero 2bpp indices. On the English
art, that made the settled white logo lose parts of its outline even though
the later colored title contained them.

A one-byte, source-guarded patch changes file `$0995` / CPU `$AB95` from `$0F`
to `$30`. Runtime palette 1 becomes:

```text
$0F, $30, $30, $30
```

Every nontransparent pattern index is now white. The attribute mask still
makes unrevealed regions black, so the dramatic assembly is preserved. At
origin `$0100`, the viewport reproduces the separate approved monochrome
authority. The following phase safely replaces 60 CHR patterns before the
colored final nametable becomes visible.

### Preserving and aligning the animated clock hands

Tile IDs `$EC-$FF`, the metasprite frame data, tile order, and animation timing
remain byte-identical. The approved clock face moved relative to the original
Japanese wordmark, so only the two metasprite origins change:

```text
source: 78 00 37 04 80 00 3F
patch:  6A 00 3A 04 72 00 42
```

This moves both origins 14 pixels left and 3 pixels down, placing their shared
elbow near native coordinate `(127, 78)`. Post-build checks separately compare
the clock-source CHR and full metasprite table against the input NOV4.

## Appended NOV4 layout and helper code

The Japanese NOV4 ends at file offset `$2375`; new data is appended instead of
overwriting unknown code. With the approved title, the layout is:

| Appended region | File range | CPU range | Size |
| --- | --- | --- | ---: |
| Exact lower CHR | `$2375-$26E4` | `$C575-$C8E4` | `$0370` |
| Nintendo temporary CHR | `$26E5-$2944` | `$C8E5-$CB44` | `$0260` |
| Final-phase CHR delta | `$2945-$2D04` | `$CB45-$CF04` | `$03C0` |
| Initial Nintendo loader | `$2D05-$2D10` | `$CF05-$CF10` | 12 bytes |
| Pre-slide restore helper | `$2D11-$2D4B` | `$CF11-$CF4B` | 59 bytes |
| Final-title transition helper | `$2D4C-$2DAC` | `$CF4C-$CFAC` | 97 bytes |
| Title exit helper | `$2DAD-$2DCC` | `$CFAD-$CFCC` | 32 bytes |
| Relocated nametable stream | starts `$2DCD` | starts `$CFCD` | Data-dependent RLE |

The builder calculates the final RLE size and rejects the patch unless the
expanded payload ends below resident NOV3 at CPU `$D7B5`.

### Patch sites that enter the appended regions

| File | CPU | Change |
| ---: | ---: | --- |
| `$01BC` | `$A3BC` | Point the native title decoder at relocated stream `$CFCD` |
| `$0296` | `$A496` | Call the appended 12-byte Nintendo loader and NOP the remainder of the old upload sequence |
| `$02E4` | `$A4E4` | Replace `JSR $AB74` with `JSR` to the 59-byte pre-slide restore helper |
| `$038E` | `$A58E` | Call the final-title transition helper and NOP the unused source bytes |
| `$022F` | `$A42F` | Tail-jump to the title exit helper |
| `$03CA` | `$A5CA` | Install corrected clock-hand origins |
| `$0995` | `$AB95` | Make all nonzero slide indices white |
| `$09D2-$19D1` | `$ABD2-$BBD1` | Install the deterministic upper-title CHR while preserving `$EC-$FF` |

### Initial loader

The 12-byte loader calls the game's recovered CHR upload routine to place the
Nintendo-phase patterns at IDs `$B0-$D5`, then returns. It replaces an original
upload sequence at `$A496`; the patch fills the now-unused source bytes with
NOPs so instruction boundaries remain explicit.

### Pre-slide helper

The 59-byte helper saves the PPUMASK mirror, clears `$1C`, blanks `$2001`,
disables NMI, restores the 38 English title patterns, and sets the original
first swipe origin (`$58:$57 = $01F0` and `$4D = $F0`). Only then does it
execute the original `JSR $AB74` palette behavior. The ordering is required
because the FDS BIOS CHR upload can overwrite the palette staging buffer and
update flag; queuing the palette first made normally masked regions appear as
white and blue garbage during the swipe. The helper then restores the saved
PPU control state, restores only the `$1C` mirror, and returns with `$2001`
still blank. The unchanged code immediately repeats those origin writes. The
following NMI copies the palette and `$57/$58` into the real PPU state before
copying `$1C` back to `$2001`. Restoring `$2001` inside the helper can reveal
one frame of the old Nintendo nametable with the restored English-title CHR.

### Final-title transition helper

The 97-byte helper preserves the original state transition, uploads the exact
55-tile final-phase delta, uploads the independent 55-tile lower set, and
enables NOV4's existing raster split at tile row 16. It resets the recovered
scroll, split, and timer variables to explicit known values before rendering
resumes.

### Exit helper, post-START crash fix, and clean visual teardown

The title-only raster split must be disabled before gameplay. The 32-byte exit
helper first clears the PPUMASK mirror at `$1C` and writes zero to `$2001`,
blanking the screen before the split and pattern-table state change. It then
disables the FDS timer IRQ through `$4022`, clears split state, clears the saved
menu-cancel pointer `$9C`, restores the expected PPUCTRL state, and performs the
original game-state change.

The ordering is visible correctness, not cosmetic bookkeeping. The lower title
rows use their own CHR table for the time-machine graphic. An earlier helper
selected the upper logo table while those rows were still rendered, so pressing
START briefly reinterpreted the machine's tile IDs as unrelated logo fragments.
Clearing the `$1C` mirror before `$2001` also prevents an intervening NMI from
restoring the old mask during teardown. The next game state owns and restores
its normal display setup.

The call form is critical. The original title exit tail-jumps to `$6119`, whose
`RTS` returns directly to the main engine. A historical patch used `JSR` for
the detour, leaving an extra return address on the stack. `$6119` then returned
into the middle of NOV4 and crashed immediately after START. The current site
at file `$022F` uses `JMP` to the helper; the helper ends in the original tail
transition and does not return to the replaced branch.

## Native title RLE

NOV4 uses a count-prefix stream:

- bytes below `$C0` are literals;
- `$C0+n, value` emits `n` copies of `value`;
- `$FF` terminates the combined stream;
- `$FF` cannot be a run prefix, so the largest run is 62 bytes (`$FE`).

`encode_title_rle()` emits runs of three or more bytes and must also encode
literal values at or above `$C0` as runs. `decode_title_rle()` requires an
exact 1,024-byte nametable and rejects early termination or overflow.
`decode_title_stream()` verifies the concatenated final and second nametables
and the single final terminator.

Both new nametables are relocated together instead of being forced into the
smaller original compressed allocations. The pointer at `$A3BC` is updated to
their new address only after the final append layout is known.

## Post-build verification

`patched_nov4_title()` does not trust its own writes. Before returning bytes it
checks that:

- both relocated streams decode to the generated nametables;
- the combined stream ends exactly at the end of NOV4;
- one `$FF` terminator follows the two 1,024-byte maps;
- lower CHR, Nintendo CHR, and the final-phase CHR delta occupy their computed
  ranges;
- the palette byte and clock origins contain their replacements;
- clock-source tiles and metasprite animation bytes still equal the input;
- the expanded address stays strictly below NOV3 at `$D7B5`.

`TitlePatchError` is raised instead of returning a partial or approximate
patch whenever any check fails.

## Build order

The order in `release.py` is intentional:

1. Rebuild and fixed-UI-patch every scenario bank.
2. Apply the NOV2 UI/input patch.
3. Apply the size-neutral NOV4 START-prompt patch.
4. Install the deterministic English font into NOV4.
5. Build and append the English title assets and helpers to that same NOV4.
6. Patch the Kouhen direct-boot component.
7. Replace named files through the parsed FDS containers.
8. Serialize Zenpen, Kouhen, and the combined four-side image.
9. Record component/output hashes and validate candidate or promoted release
   provenance.

The font patch accepts the clean NOV4 and the known post-UI NOV4. The title
patch validates only source regions it owns, so the earlier prompt/font stages
can coexist without weakening title guards.

For maintainers with legal private inputs, the preferred end-to-end command is:

```powershell
time-twist release-build --candidate --output-dir build/candidate
```

Individual diagnostic stages are also available:

```powershell
time-twist ui-patch NOV2.bin NOV2-ui.bin --component NOV2
time-twist ui-patch NOV4.bin NOV4-ui.bin --component NOV4
time-twist font-patch NOV4-ui.bin NOV4-font.bin
time-twist title-patch NOV4-font.bin `
  "work/title_assets/Time Twist approved native title.png" NOV4-title.bin `
  --slide-target "work/title_assets/Time Twist approved native slide.png"
```

Do not use individually patched banks as release authority. The release command
also validates approved inputs, file ownership, component order, FDS capacity,
output hashes, and release-code provenance. Provenance hashes the actual
imported package and the supplied checkout under identical logical paths and
fails before generation if they differ.

## Test and evidence map

| Behavior | Primary automated evidence |
| --- | --- |
| One-choice B is ignored and larger-menu Back survives | `test_zenpen_nov2_b_ignores_one_choice_but_keeps_normal_back` |
| Declarative patches reject wrong source/size | `work/tests/test_ui_unit.py` |
| Menu tails clear while dialogue rows remain intact | `test_zenpen_nov2_preserves_dialogue_rows_and_transparent_tails` |
| Disk, wrong-disk, wait, and START slots remain fixed | `work/integration_tests/test_ui.py` |
| Kouhen warning changes only its fixed assets | `test_kouhen_direct_boot_guard_is_horizontal_english` |
| Apostrophe uses the corrected closing shape | `work/tests/test_font.py` |
| Source NOV4 layout and hashes are exact | `test_recovered_title_boundaries_and_source_hashes` |
| Approved native title regenerates exactly | `test_native_authority_regenerates_exactly_and_has_locked_geometry` |
| Tile budgets and exact phase delta reconstruct | `test_exact_tile_budgets_phase_delta_and_completed_origin` |
| Nintendo patterns are restored before the swipe | `test_nintendo_overlay_and_pre_slide_restore_have_no_stale_logo_pixels` |
| All 21 origins match an independent viewport model | `test_native_slide_origins_wrap_and_representative_frames_are_locked` |
| Attribute-mask and palette behavior are native | `test_attribute_tables_and_runtime_palette_are_locked` |
| RLE framing is legal and exact | `test_rle_fragments_are_legal_exact_and_singly_terminated` |
| Appended helpers fit and are deterministic | `test_patch_layout_helpers_scope_memory_and_determinism` |
| START blanks rendering before changing title CHR/split state | `test_exit_helper_blanks_rendering_before_split_teardown` |
| Clock CHR/metasprites remain native | `test_clock_chr_metasprites_and_timing_stay_native_with_new_origin` |
| Unknown source or malformed title authority fails closed | `test_source_and_native_asset_guards_fail_closed` |

The title preview script uses the same production asset builder. With the
private NOV4 and emulator capture inputs present, it generates all 21 swipe
frames, a contact sheet, and the final title with captured clock sprites:

```powershell
python work/render_title_preview.py
```

Static evidence is necessary but not sufficient. This two-authority title
revision requires a fresh compatible FDS-emulator capture before promotion,
followed by a complete Zenpen and Kouhen playthrough for release certification.

### Auditing an expanded NOV4 correctly

The source NOV4 is 9,077 bytes; the patched title component is larger and its
exact size depends on the two new RLE streams. An allowed-difference audit must
therefore compare the source against exactly the same-length prefix of the
patched component. Strictly zipping the two full byte strings is itself an
error because the appended helper/data region has no source counterpart.

The integration test audits `patched[:len(source)]` against the documented
mutable ranges. The append is not exempt from verification: separate
assertions lock the helper layout, title pointer, exact 880-byte delta, two
decoded 1,024-byte nametables, exact stream termination, and the positive gap
before resident NOV3 at `$D7B5`. This division makes the test match the binary
layout rather than weakening it.

## Build-publication access fix

The release pipeline also fixes a Windows-specific failure that looked like a
bad ROM: an emulator reported access denied when opening a newly generated `.fds`.
The bytes were valid, but moving a file directly out of a private temporary
directory retained an ACL the interactive emulator account could not read.

`_atomic_publish_file()` now creates a temporary file inside the final output
directory, copies and flushes the staged bytes, applies the intended mode, and
atomically replaces the destination. The temporary file inherits the output
directory's access rules. This is a tooling/publication fix, not a game-engine
change.

## Rules for future maintenance

- Do not describe a translation regression as an original-game bug without a
  matching Japanese-build reproduction.
- Do not raw-hex-edit the combined `.fds`; patch the owning named component.
- Do not remove source guards to make a new revision “work.” Recover and
  document that revision's layout instead.
- Do not grow NOV2. It has no proven expandable space below NOV4.
- Do not place title data at or above `$D7B5` while NOV3 is resident.
- Do not use `$EC-$FF` for upper-title art; those tiles feed the live clock.
- Do not change the 21 scroll origins merely to make a static frame look good.
- Do not replace the title exit `JMP` with `JSR`.
- Do not make dialogue tail cells opaque; preserve the indexed row-copy path.
- Do not update `release_sources.json` or `release_target.json` as a side effect
  of documentation or experimentation.
- Preserve deterministic asset generation: exact indexed input, stable tile
  ordering, native RLE, and no host-font dependencies.
- Run the fixture-free suite for public changes and the complete private
  integration suite when the legal fixture overlay is available.
- Finish the manual playtest matrix before describing a candidate as a final
  release.

## Related documentation

- [Title sequence architecture](TITLE_SEQUENCE.md)
- [Architecture and patch layers](ARCHITECTURE.md#ui-font-and-title-patches)
- [Binary formats](FORMATS.md)
- [Development guide](DEVELOPMENT.md#adding-or-changing-a-binary-patch)
- [Runtime playtest matrix](PLAYTEST_MATRIX.md)
- [Project retrospective](PROJECT_RETROSPECTIVE.md)
