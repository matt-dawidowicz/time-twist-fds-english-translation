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

Developer-facing commands live under the top-level `tools/` package, grouped
by responsibility (`analysis`, `audit`, `generation`, `maintenance`, and
`preview`). Core binary behavior remains in `work/time_twist/`; tools may
orchestrate or inspect that package but must not become hidden runtime layers.

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
2. `compress_english_groups()` selects useful repeated literal sequences for
   31 native slots or 68 slots in a patched English release bank.
3. For the 11 menu-bearing banks, the release compressor treats the full-word
   menu table as an additional group and shares its byte budget with dialogue.
4. `rebuild_scenario_bank()` repacks groups, writes new pointers, and preserves
   the original fixed tail address.
5. The release layer regenerates the fixed-menu page index and shifts only the
   recovered pointer-addressed prefix data.
5. `replace-file` writes the rebuilt overlay back into an FDS image.

## Patch layers

Patches are intentionally separated by the kind of address stability they
need.

### Scenario rebuild

Scenario group starts and the dictionary may move inside their reserved region.
The region must not extend past `dictionary_end_offset` when
`preserve_memory_footprint=True`.

### Fixed-record table patch

Legacy standalone UI patching retains every source record boundary.
`_encode_at_exact_record_size()` uses dictionary references and invisible
trailing common-space tiles to fill each original slot exactly.

The canonical release uses the more precise recovered menu addressing model:
one base pointer plus page pointers for records 32, 64, and 96. It repacks
those records at variable lengths, regenerates the page index, updates the
verified secondary-table pointers, and shares the recovered bytes with the
scenario region. No fixed suffix or overlay size moves.

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
- Dictionary references are one-based and limited to 31 in native data or 68
  in guarded English release data.
- Control-code order must match the Japanese record.
- All visible English glyphs must exist in the installed font.
- Ordinary dialogue segments must fit the 24-column renderer unless a
  specifically tested record uses safe wrapping.
- Fixed-address tables must preserve every record boundary unless their
  complete runtime addressing model is recovered and every affected pointer
  is regenerated.
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
   Schema v2 declares LF-normalized identity for translation JSON and raw-byte
   identity for FDS/PNG inputs. The lock document is itself hashed after LF
   normalization, so Windows checkout policy cannot change its release
   identity.
2. Code provenance records the checkout Git commit/dirty state when available.
   It computes the same authoritative digest for the imported/executing
   `time_twist` package and the checkout's `work/time_twist/**/*.py`, using
   checkout-equivalent logical paths, and fails unless those trees match.
3. `release-build --candidate` deterministically composes an unapproved build
   and records scenario capacities, component hashes, final image hashes, and
   the active code provenance.
4. `release-promote` revalidates the exact candidate files and code tree, then writes
   `work/release_target.json`, tying output hashes to the active source-lock
   SHA-256 and release-critical implementation.

A strict `release-build` requires both ties and reproduces the promoted sizes
and hashes. No target is checked in while the current candidate awaits
playtesting; strict mode fails closed until that exact candidate is promoted.
Build files are prepared in a sibling staging directory and are not published
when source, code, or target validation fails. Verified files are copied to
destination-local temporary files before atomic replacement so Windows outputs
inherit the emulator user's directory permissions rather than the staging
directory's private ACL.

The code-tree digest sorts normalized POSIX-relative logical paths, normalizes
Python line endings to LF, and hashes length-prefixed path/content records
under a versioned domain marker. Physical install paths never enter the hash.
This is unambiguous and stable across Windows and Unix checkouts. Git metadata
is informational: Git may be missing in an installed-tool environment, while
the code-tree digest remains available and authoritative.

Source normalization is narrower than code normalization. Only the 13
translation JSON files may use `lf`; executable game images and title artwork
must use `raw`. Metadata validation enforces that path-to-policy mapping so a
binary record cannot opt into lossy text treatment.

Release commands operate on a project checkout rather than package data. This
keeps the wheel free of translation project artifacts and all proprietary ROM
material. Checkout discovery searches the current directory and parents;
`--project-root` makes the dependency explicit for an installed command run
elsewhere.

## Public/private test boundary

Fixture-free tests use synthetic FDS data and generated workbook inputs and run
in public CI. Exact tests against original or derived game bytes live under
`tests/integration/`. Their local inputs are described only by hashes in
`tests/fixtures/integration_fixtures.json` and are validated before discovery. This
prevents a missing private fixture from turning a critical exact-output test
into an unnoticed skip.
