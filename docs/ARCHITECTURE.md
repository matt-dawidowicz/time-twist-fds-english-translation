# Architecture

## Design goal

The tools make controlled, verifiable changes to a game whose text and
graphics were not designed for an English localization. Every layer is
lossless by default: parsing and serializing an unmodified input must reproduce
the original bytes, and patch functions reject inputs that do not match the
recovered source layout.

The main pipeline is:

```text
FDS image
  -> FDS side
    -> named FDS file / loaded overlay
      -> scenario records or fixed assets
        -> English encoding and dictionary compression
      -> rebuilt overlay with original tail/address constraints
    -> replaced FDS file
  -> rebuilt two-side or combined four-side image
```

The playable ROM is an output of the pipeline, not a source file. Original and
patched `.fds` files are intentionally excluded from Git.

## Module map

| Module | Responsibility | Does not do |
| --- | --- | --- |
| `fds.py` | Parse and rebuild archival FDS images, sides, and named files | Interpret game-specific text |
| `textcodec.py` | Read and write native packed symbols at bit granularity | Map symbols to Japanese or English |
| `charmap.py` | Render recovered Japanese common/extended codes | Re-encode English |
| `english.py` | Map supported English glyphs and `{CTRL:n}` tags to symbols | Pack groups or modify ROM bytes |
| `compression.py` | Build a flat, native-compatible English dictionary | Move code or expand RAM |
| `scenario.py` | Parse group pointers/dictionary and rebuild scenario regions | Patch fixed-address UI tables |
| `font.py` | Generate/install the 8x8 translated dialogue font | Change text records |
| `ui.py` | Apply source-verified, size-neutral fixed text and code patches | Rebuild normal scenario groups |
| `title.py` | Convert, relocate, and verify the NOV4 English title assets | Translate story dialogue |
| `cli.py` | Compose the above layers into reproducible commands | Hide validation failures |

The standalone scripts under `work/` render CHR data, preview fonts and title
art, generate translation workbooks, and perform exploratory analysis. Core
binary behavior belongs in `work/time_twist/` so it can be tested.

## Runtime organization

Time Twist is split across small FDS files loaded as overlays:

- `NOV2` contains shared text/menu rendering and input behavior.
- `NOV4` contains the dialogue font, title program, title nametables, title CHR,
  and live title/start text.
- `TT1A`, `TT1B`, `TT2`, `T22`, `TT3A`, `TT3B`, `TT4`, `TT5`, `T25`,
  `TT6A`, `TT6B`, `TT6C`, and `TT6D` contain story/chapter data.
- `SON-KOUH` is Kouhen's direct-boot guard.
- `OB*`, `OBJ*`, and `BG*` files are object/background graphics.

Scenario overlays normally load at CPU address `$A200`. Their text region is
followed by data or code that must remain at its original CPU address.

## Scenario data flow

### Read

1. `FdsImage.read()` separates the image into fixed 65,500-byte sides.
2. `FdsSide.find_file()` locates an overlay by its FDS filename.
3. `parse_scenario_bank()` reads the overlay's pointers and record groups.
4. `decode_symbol()` walks the native prefix tree.
5. `render_symbols()` expands dictionary references and renders Japanese plus
   structural control tags.

### Edit

1. An extracted record receives a stable ID such as `TT1B/g2/r7`.
2. The ID-keyed translation map changes only the English field.
3. `merge_translation_document()` rejects unknown/missing IDs, changed control
   sequences, unsupported glyphs, and unsafe row widths.

### Rebuild

1. `encode_english()` converts visible text and control tags to packed symbols.
2. `compress_english_groups()` greedily selects useful repeated literal
   sequences for at most 31 dictionary slots.
3. `rebuild_scenario_bank()` repacks groups, writes new pointers, and preserves
   the original fixed tail address.
4. A bank-specific UI patch updates packed labels that are outside the normal
   scenario groups.
5. `replace-file` writes the rebuilt overlay back into an FDS image.

## Patch layers

Patches are intentionally separated by the kind of address stability they
need.

### Scenario rebuild

Scenario group starts and the dictionary may move inside their reserved region.
The region must not extend past `dictionary_end_offset` when
`preserve_memory_footprint=True`.

### Fixed-record table patch

6502 code often points directly to individual command or object labels. The
table and every record boundary remain fixed. `_encode_at_exact_record_size()`
uses dictionary references and invisible trailing common-space tiles to fill
the original slot exactly.

### Byte-exact program/UI patch

Small NOV2/NOV4 patches compare the bytes at a recovered offset before writing
the replacement. These patches must be size-neutral unless they deliberately
relocate code into proven free space.

### Title relocation

The English title needs more exact tile patterns than the original layout
provides. `title.py`:

- validates the original NOV4 layout and recovered asset hashes;
- builds separate exact upper and lower CHR sets;
- reuses NOV4's existing raster split;
- preserves the original clock-hand source tiles and animation data;
- overlays and restores the Nintendo-phase tiles;
- appends relocated helpers and compressed nametables without crossing the
  resident NOV3 load address.

## Safety invariants

The following are architectural requirements, not optional style preferences:

- An unmodified FDS image must round-trip byte-identically.
- Packed record separator control `5` is structural and cannot appear as an
  ordinary translated control code.
- Dictionary references are one-based and limited to 31 entries.
- Control-code order must match the Japanese record.
- All visible English glyphs must exist in the installed font.
- Ordinary dialogue segments must fit the 24-column renderer unless a
  specifically tested record uses safe wrapping.
- Fixed-address tables must preserve every record boundary.
- Fixed scenario tails must remain at their original loaded addresses.
- A patch must reject an unknown source rather than applying by coincidence.
- Title clock animation bytes must remain untouched.
- Unit tests and manual playtesting are both release gates.

## Why the code has many constants

Offsets, source byte strings, load addresses, sizes, and hashes are evidence
from a specific recovered game revision. Naming them in one place makes the
patch reviewable and prevents broad pattern searches from modifying the wrong
copy of a string or instruction.

When adding a constant, document:

- which FDS file it belongs to;
- whether it is a file offset or CPU address;
- how the source bytes were established;
- what must remain fixed after the patch; and
- which test detects a mismatch.

## Release-control architecture

The release layer separates four approvals that were previously conflated:

1. `work/release_sources.json` approves non-code inputs: both Japanese
   baselines, all playable scenario maps, and the title reference asset.
2. Code provenance records the active Git commit/dirty state when available and
   always computes an authoritative digest over `work/time_twist/**/*.py`.
3. `release-build --candidate` deterministically composes an unapproved build
   and records scenario capacities, component hashes, final image hashes, and
   the active code provenance.
4. `release-promote` revalidates the exact candidate files and code tree, then writes
   `work/release_target.json`, tying output hashes to the active source-lock
   SHA-256 and release-critical implementation.

A strict `release-build` requires both ties and reproduces the promoted sizes
and hashes. Legacy targets without code provenance fail closed and must be
re-promoted from a reviewed candidate. Build files are prepared in a sibling
staging directory and are not published when source, code, or target validation
fails. Verified files are copied to destination-local temporary files before
atomic replacement so Windows outputs inherit the emulator user's directory
permissions rather than the staging directory's private ACL.

The code-tree digest sorts normalized POSIX-relative paths, normalizes Python
line endings to LF, and hashes length-prefixed path/content records. This is
unambiguous and stable across Windows and Unix checkouts. Git metadata is
informational: Git may be missing in an installed-tool environment, while the
code-tree digest remains available and authoritative.

Release commands operate on a project checkout rather than package data. This
keeps the wheel free of translation project artifacts and all proprietary ROM
material. Checkout discovery searches the current directory and parents;
`--project-root` makes the dependency explicit for an installed command run
elsewhere.

## Public/private test boundary

Fixture-free tests use synthetic FDS data and generated workbook inputs and run
in public CI. Exact tests against original or derived game bytes live under
`work/integration_tests/`. Their local inputs are described only by hashes in
`work/integration_fixtures.json` and are validated before discovery. This
prevents a missing private fixture from turning a critical exact-output test
into an unnoticed skip.
