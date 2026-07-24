# CLI reference

Run commands from `work/`:

```powershell
python -m time_twist.cli --help
python -m time_twist.cli COMMAND --help
```

## FDS container commands

### `manifest IMAGE [--output PATH]`

Parses an FDS image and emits JSON containing:

- header convention and side count;
- disk identifiers;
- used/padding bytes;
- every file's number, ID, name, load address, size, kind, and offsets.

Use it before and after a build to review layout changes.

### `extract IMAGE OUTPUT_DIR`

Writes each FDS file payload to a descriptive `.bin` filename. Extraction does
not modify the image.

### `roundtrip IMAGE OUTPUT`

Parses and serializes the image, prints source/rebuilt SHA-256 values, and
fails unless every byte matches.

### `combine IMAGE [IMAGE ...] --output PATH`

Combines all sides from multiple images in argument order. The first image
determines whether the output has a 16-byte FDS header.

### `replace-file IMAGE SIDE NAME DATA OUTPUT`

Replaces one named file on a zero-based side and rebuilds the image. The file
header size is updated; the side must still fit 65,500 bytes.

## Scenario commands

### `scenario-extract BANK OUTPUT`

Decodes group pointers, packed records, dictionary references, and Japanese
text into a JSON scenario document. Existing English at matching group/record
coordinates is retained.

### `scenario-merge SCENARIO TRANSLATIONS [--output PATH] [--allow-partial]`

Merges an ID-keyed English JSON object into an extracted scenario document.
Without `--allow-partial`, every record ID is required. It validates controls,
font support, and display width.

### `scenario-footprint BANK [--translations PATH]`

Reports the bank's fixed text reservation and tail. With a complete
translation map it performs dictionary compression and reports remaining
bytes.

### `scenario-insert BANK TRANSLATION OUTPUT [--no-compress]`

Rebuilds scenario groups and pointers. A fully translated bank receives a new
English dictionary unless `--no-compress` is supplied. A partial bank
preserves the Japanese dictionary.

`--no-compress` is a diagnostic option, not a way around the fixed memory
limit.

## Asset and UI commands

### `font-patch NOV4 OUTPUT`

Installs every common and extended English glyph into the recovered NOV4 font
table. The patch is size-neutral.

### `title-patch NOV4 TARGET OUTPUT [--subtitle TEXT]`

Builds the translated title assets from an image, preserves the moving clock
sprites, relocates the compressed nametable stream/helpers, and appends data
without overlapping resident NOV3.

The default subtitle is `On the Outskirts of History...`.

### `ui-patch SOURCE OUTPUT [--component NAME]`

Applies one source-verified UI/fixed-table patch.

Supported components:

| Component | Content |
| --- | --- |
| `SON-KOUH` | Kouhen direct-boot warning |
| `NOV2` | Shared start/disk/wait/wrong-disk text and one-choice B guard |
| `NOV4` | Live START prompt |
| `TT1A` | Blood type, month, and confirmation choices |
| `TT1B` | Museum commands, objects, and interactions |
| `TT2` | Commands, objects, and quiz labels |
| `T22` | Commands and objects |
| `TT3A` | Commands, objects, and quiz labels |
| `TT3B` | Commands, objects, and battle actions |
| `TT4` | Commands, treatment, and quiz labels |
| `TT5` | Commands, puzzle, and quiz labels |
| `T25` | Mansion and flooded-island actions |
| `TT6A` | Donkey actions and Nazareth objects |
| `TT6B` | Travel, quiz, and animal actions |
| `TT6C` | Finale actions and retrospective quiz |

The command fails if the source bytes, record count, table hash, dictionary, or
exact slot sizes do not match expectations.

## Failure interpretation

| Error class/message | Meaning |
| --- | --- |
| `FdsFormatError` | Container/block/side layout is invalid |
| `PackedTextError` | Bitstream ended early or a symbol is out of range |
| `ScenarioError` | Pointer, group, dictionary, or RAM footprint is invalid |
| `EnglishTextError` | Unsupported glyph/control tag or unsafe row width |
| `UiPatchError` | Fixed source bytes/table/slot constraints did not match |
| `FontPatchError` | Font table/glyph/tile mapping is invalid |
| `TitlePatchError` | NOV4 source assets, capacity, tile counts, or verification failed |

Treat these as evidence that an invariant was violated. Do not catch and ignore
them in a production build.
