# How the Time Twist translation and English title were built

This document explains the technical and editorial path behind the English
translation of *Time Twist: Rekishi no Katasumi de...*, why the game resisted
ordinary ROM-translation methods, and how the current title sequence was
changed.

It is a technical retrospective, not a claim that the game was solved from
nothing or that earlier researchers lacked ability. The current result depends
on the original game, earlier observations preserved in the project, legally
obtained local FDS images, the translation corpus and workbook, user-supplied
screenshots and playtest reports, and repeated emulator verification.

## Why this game was unusually difficult to translate

### The text is not stored as ordinary strings

Most story text is a packed bitstream. Symbols have variable-length prefixes:
common glyphs cost six bits, extended glyphs and dictionary references cost
nine bits, and controls cost seven bits. Records are separated by a structural
control and realign at byte boundaries.

As a result, searching the ROM for a visible Japanese or English sentence is
not a dependable editing method. Changing one symbol can move every later bit,
record boundary, pointer, and dictionary location in that packed region.

### Compression is part of the file format

Each scenario bank can use up to 31 one-based dictionary entries. Those entries
are referenced from the packed records, and some fixed UI tables expect
specific dictionary words. Translating a line therefore changes more than that
line: it can change the best dictionary, the size of every affected record,
and the placement of the pointer table and dictionary.

The English builder creates a flat native-compatible dictionary, reserves
required entries first, and accepts a candidate entry only when it reduces the
complete packed size. Dictionary reference zero is invalid and is rejected.

### The overlays have fixed memory boundaries

Time Twist is divided among FDS files loaded as overlays, commonly at CPU
address `$A200`. A variable text region is often followed by code or data whose
loaded address cannot move. The translated records, group pointers, and
dictionary may be repacked inside the reservation, but the fixed tail must
begin at exactly its original address.

This means that "the disk still has free bytes" is not enough. A translation
can fit the archival FDS side and still overwrite live code in RAM. Every bank
must satisfy both its storage limit and its loaded-memory footprint.

### Story text is only one of several text systems

Dialogue records, menus, command labels, objects, quiz answers, disk prompts,
the dialogue font, and title graphics are not all stored together. Some UI
tables preserve only their total size; others must preserve every individual
record boundary because 6502 code points directly to later entries.

Those records cannot safely be handled by the normal scenario rebuilder.
Source-verified fixed-table patches encode each replacement into its exact old
slot, using dictionary references and invisible trailing space symbols when
necessary.

### The display is narrower than normal English prose

The message renderer exposes 24 columns. Control codes can create line, page,
pause, or scene behavior depending on the caller. A linguistically accurate
translation may still wrap badly, leave stale text, clear at the wrong moment,
or exceed the safe packed footprint.

The playable text therefore has to preserve meaning, control order, width,
compression, and scene timing at once. The workbook keeps a natural editorial
translation separate from the constrained patch-safe wording so review prose
cannot silently enter a ROM build.

### Zenpen and Kouhen form one stateful FDS game

The two halves occupy four archival sides and depend on disk changes, prompts,
save data, and continuation state. A bank-level rebuild or a successful direct
boot does not prove the complete game. Progression, correct-side and wrong-side
disk handling, Zenpen-to-Kouhen continuity, saving, page clearing, and obscure
branches still require runtime playtesting.

### The title is a graphics and program problem, not a text replacement

The title lives in `NOV4` with program code, compressed nametables, two CHR
layouts, palettes, a raster split, Nintendo opening graphics, and animated
clock-hand sprites. The English wordmark needs more unique 8x8 patterns than a
naive replacement can allocate. A static final-screen edit can look correct
while the preceding slide exposes stale Nintendo patterns, wrong nametable
columns, or a different clock shape.

These interacting constraints explain why manual hex editing and simple string
insertion could make partial progress but could not safely produce a complete,
reproducible translation.

## The translation process used by this project

### 1. Parse the FDS container losslessly

`work/time_twist/fds.py` models the disk header, fixed 65,500-byte sides, FDS
file headers, payloads, and trailing padding. An untouched image must parse and
serialize byte-identically. This establishes trustworthy file names, load
addresses, sizes, and side order before game-specific interpretation begins.

### 2. Decode the native packed text

`textcodec.py`, `charmap.py`, and `scenario.py` read the actual prefix tree,
record separators, pointers, and dictionary. Extraction records raw symbols and
stable coordinates such as `TT1B/g2/r7`; it does not infer source text by
looking at visible byte fragments.

The exact decoded Japanese remains immutable evidence. Romaji, reconstructed
kanji, notes, and natural English are separate editorial layers.

### 3. Establish a stable translation authority

The complete workbook contains 2,052 extracted records. Of those, 1,299 are
playable scenario records across 13 banks. Scenario English lives in
`work/translations/*.json`; fixed UI English lives in `ui.py`; the workbook is
the review surface rather than an independent ROM source.

Generation verifies unique IDs, canonical order, exact Japanese retention,
control sequences, playable-source equality, and complete coverage. This makes
it possible to revise prose without losing track of which binary record it
owns.

### 4. Install an English font and encoding

The project defines a compact English symbol map and a deterministic 5x7 font
inside the game's 8x8 cells. Common letters receive the cheapest codes. The
extended table holds less frequent characters, digits, punctuation, and the
accented `é` used in `consommé`. Font tests lock case distinction, baseline
alignment, and corrected glyphs such as lowercase `p`.

### 5. Recompress each scenario bank inside its reservation

The builder encodes English, chooses a new flat dictionary, repacks every
record group, rewrites group pointers, and then checks that the original fixed
tail address is unchanged. Unknown IDs, missing IDs, reordered controls,
unsupported glyphs, unsafe widths, duplicate pointers, and footprint overruns
all fail before publication.

### 6. Patch fixed UI separately

Menus, labels, answers, prompts, and program bytes are handled by named patch
functions with exact source guards. Record-boundary-fixed tables retain every
old slot length. Program changes compare the expected bytes at a recovered
offset before writing the replacement.

This prevents a translation that happens to fit from being applied to the
wrong occurrence or an unsupported ROM revision.

### 7. Regenerate review artifacts from playable sources

The comparison corpus and HTML/CSV/JSON workbook are regenerated after changes.
Patch-safe scenario fields must equal the actual translation maps, while more
expansive natural wording stays editorial. The generated workbook is never
edited as the only source change.

### 8. Build, hash, test, and playtest exact candidates

The release layer locks approved non-code inputs, builds Zenpen, Kouhen, and a
combined four-side image, and records sizes and SHA-256 hashes. Candidate mode
does not imply approval. Promotion revalidates the reviewed files and binds the
release target to the active source lock.

Static tests prove parsing, encoding, boundaries, hashes, and deterministic
composition. Emulator work proves title timing and helps locate display faults.
A complete manual story playthrough remains the final authority for branches,
disk switching, saves, progression, wording, and presentation.

## How the English logo was changed

### Establishing one native artwork authority

The desired screenshot was converted deliberately to the NES's native
256x240 indexed format. The production image uses only four values:

- 0: black;
- 1: white outline;
- 2: pink fill;
- 3: purple bevel.

Only rows 0-95 contain the wordmark and retained `TM`. Subtitle, `PUSH START`,
time-machine art, copyright, and the live blue hand remain owned by the game.
Production does not resize or requantize a display screenshot.

`work/rebuild_native_title_asset.py` records the review decisions: inverse
display mapping, a `(-4,-4)` placement that preserves the lower composition,
removal of the frozen hand visible in the reference, preservation of the
existing `TM`, and ten pink/purple-only bevel edits.

Those ten pixels make eight patterns reusable, reducing the upper wordmark
from 244 to exactly 236 unique tiles without changing any black silhouette or
white-outline pixel.

### Preserving the CHR split and live clock

Tile IDs `$00-$EB` provide the 236 safe upper-title patterns. IDs `$EC-$FF`
remain the original clock-hand source and are byte-identical. The lower screen
continues to use exactly 55 patterns through the existing raster split.

The original hand graphics, frame layouts, and timing were retained. Only the
metasprite origin changed: 16 pixels left and 8 pixels up, centering the native
animation in the corrected clock face.

### Making the slide and final title share geometry

The old English slide populated approximately 27 columns and forced the final
five columns black. It eventually switched to a different complete nametable,
which made the logo jump and left the moving phase structurally incomplete.

The corrected second nametable is generated mechanically from all 32 columns
of the approved final title's first twelve tile rows. The final colored title
and the completed monochrome slide therefore cannot drift into separate art
versions.

The original 21 nine-bit scroll origins are preserved. They alternate across
the two horizontal nametables and settle at `$0100`. NT0's upper attributes
select a hidden black palette while NT1's upper attributes select the visible
palette, producing the original dramatic sequence: blank, alternating left and
right pieces, nearly complete, and settled.

### Restoring patterns reused by the Nintendo opening

The opening Nintendo phase temporarily owns 38 patterns at `$B0-$D5`. Those
IDs are also needed by the full English wordmark. Avoiding them caused the
missing-column workaround; using them without restoration caused corrupted
slide tiles.

The title patch hooks the original state-3 call at NOV4 file offset `$02E4`.
A 43-byte helper briefly blanks rendering, uploads the patched base patterns
back into `$B0-$D5`, restores PPU/NMI state, and returns before the original
scroll sequence begins.

### Making the completed white logo match the colored logo

The stock state-3 palette made only some nonzero pattern indices white, hiding
the final title's white outline in the settled monochrome frame. A guarded
one-byte patch changes NOV4 offset `$0995` (CPU `$AB95`) from `$0F` to `$30`.
Visible palette 1 becomes `$0F,$30,$30,$30`, so every nontransparent logo pixel
is white while unrevealed attribute regions remain black.

The completed slide now contains exactly the same 9,348 nontransparent pixels
as the approved final geometry. Colorization changes the palette and title
state rather than replacing visibly different artwork.

### Staying inside NOV4

The patched NOV4 is 12,209 bytes and ends at CPU `$D1B1`. Resident NOV3 begins
at `$D7B5`, leaving 1,540 bytes of verified headroom. Both nametables decode to
exactly 1,024 bytes, title RLE uses legal markers, and the clock-source tail
remains unchanged.

The final candidate was cold-booted twice in a headless FDS emulator for 1,150 frames.
The two runs produced 1,153 byte-identical comparison artifacts. The moving
slide occupies frames 896-915, the completed white logo remains through frame
979, the colored screen fades in at frames 1020-1027, and hand animation is
visible from frame 1029.

## Why the work moved faster than many earlier attempts

The main improvement was not a single hidden trick. It was the availability of
an end-to-end feedback system:

1. lossless parsing established trustworthy binary boundaries;
2. a real codec replaced raw-string assumptions;
3. stable IDs connected binary records to a reviewable workbook;
4. native recompression made English fit without moving fixed tails;
5. source guards prevented accidental application to the wrong bytes;
6. deterministic builds and hashes made revisions comparable;
7. screenshots and headless emulator captures exposed runtime behavior;
8. tests preserved each verified discovery.

Earlier work on a niche FDS title often had to solve these pieces manually,
with fewer debugging and automation tools and without a complete corpus tied to
rebuildable sources. Once this project assembled those pieces, later fixes
could take minutes because they operated inside a proven model. Building that
model was the difficult part.

## Reproducible evidence map

| Subject | Primary source |
| --- | --- |
| FDS layout | `work/time_twist/fds.py`, `docs/FORMATS.md` |
| Packed symbols | `textcodec.py`, `scenario.py`, `compression.py` |
| Playable dialogue | `work/translations/*.json` |
| Fixed UI | `work/time_twist/ui.py` |
| Workbook authority | `docs/WORKBOOK_PIPELINE.md` |
| Font | `work/time_twist/font.py` |
| Native title art | `work/title_assets/Time Twist approved native title.png` |
| Art reconstruction | `work/rebuild_native_title_asset.py` |
| Title patch | `work/time_twist/title.py` |
| Title architecture | `docs/TITLE_SEQUENCE.md` |
| Exact title tests | `work/integration_tests/test_title.py` |
| Release controls | `work/time_twist/release.py` |
| Playtest coverage | `docs/PLAYTEST_MATRIX.md` |

## What remains before a final release

The title candidate has deterministic build and targeted runtime evidence, but
that does not prove the whole adventure. A release still requires complete
human playthroughs of Zenpen and Kouhen, correct disk changes, save/load checks,
branch and ending coverage, and continued review of wrapping, clearing,
speaker attribution, terminology, and natural English.

Only the exact reviewed candidate should be promoted. Generated FDS images are
outputs; the translation maps, patch code, native title asset, source lock, and
tests remain the maintainable authority.
