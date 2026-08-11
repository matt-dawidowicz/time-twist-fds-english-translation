# CLI reference

Install from the repository root:

```powershell
python -m pip install -e .
time-twist --help
time-twist COMMAND --help
```

Release commands auto-discover a checkout from the current directory and its
parents. From elsewhere, pass `--project-root PATH`.

## FDS container commands

### `manifest IMAGE [--output PATH]`

Emits JSON describing the header convention, side count, disk identifiers,
used/padding bytes, and every named FDS file.

### `extract IMAGE OUTPUT_DIR`

Writes each named FDS payload to a descriptive `.bin` file without modifying
the image.

### `roundtrip IMAGE OUTPUT`

Parses and serializes the image and fails unless every byte matches.

### `combine IMAGE [IMAGE ...] --output PATH`

Combines all sides in argument order. The first image determines whether the
result has a 16-byte FDS header.

### `replace-file IMAGE SIDE NAME DATA OUTPUT`

Replaces one named file on a zero-based side and rebuilds the image. The side
must still fit 65,500 bytes.

## Scenario commands

### `scenario-extract BANK OUTPUT`

Decodes group pointers, packed records, dictionary references, and Japanese
text to JSON. Existing English at matching group/record coordinates is kept.

### `scenario-merge SCENARIO TRANSLATIONS [--output PATH] [--allow-partial]`

Merges an ID-keyed English map. Without `--allow-partial`, every record ID is
required. It validates controls, glyph support, and display width.

### `scenario-footprint BANK [--translations PATH]`

Reports the fixed text reservation and, with a complete translation map,
compressed use and remaining bytes.

### `scenario-insert BANK TRANSLATION OUTPUT [--no-compress] [--bank-name NAME]`

Rebuilds scenario groups and pointers. Complete translations receive a new
English dictionary; partial work keeps the Japanese dictionary. `--bank-name`
is available when the input filename does not safely identify its bank.

## Asset and UI commands

### `font-patch NOV4 OUTPUT`

Installs the translated dialogue font after validating the supported NOV4
source revision.

### `title-patch NOV4 TARGET OUTPUT [--subtitle TEXT]`

Builds and installs the English title assets from an exact 256x240 indexed
native image while preserving the clock and recovered raster-split behavior.

### `ui-patch SOURCE OUTPUT [--component NAME]`

Applies one source-verified fixed UI/text-table patch. Supported components are
`SON-KOUH`, `NOV2`, `NOV4`, `TT1A`, `TT1B`, `TT2`, `T22`, `TT3A`, `TT3B`,
`TT4`, `TT5`, `T25`, `TT6A`, `TT6B`, and `TT6C`.

The command rejects source-byte, record-count, table-hash, dictionary, and
exact-slot mismatches.

## Release commands

All release commands accept `--project-root PATH`.

### `release-lock [--lock PATH] [--update]`

Without `--update`, verifies the Japanese baselines, all 13 playable scenario
maps, and the title asset against the source lock. The default is
`PROJECT/work/release_sources.json`.

`--update` rewrites the lock from the current project inputs. It approves input
changes only; it does not approve new output hashes.

### `release-build [--output-dir PATH] [--lock PATH] [--target PATH] [--candidate]`

Rebuilds all 13 scenario banks, applies fixed UI/font/title patches, produces
Zenpen and Kouhen, combines four sides, and writes `release_manifest.json`.

Default strict mode verifies `PROJECT/work/release_target.json`, including its
tie to the active source-lock SHA-256 and the active release-code provenance.
It stages output and does not publish a new build when target verification
fails.

`--candidate` skips target approval and publishes a candidate manifest for
review. Candidate mode is required after an intentional source/output change.

### `release-promote CANDIDATE_MANIFEST [--target PATH] [--release-id ID]`

Accepts only a candidate-mode manifest. It verifies the candidate's active
source lock, release-code tree, output paths, sizes, and SHA-256 hashes, then
atomically writes the versioned release target. A subsequent strict
`release-build` must reproduce that target.

Candidate and target manifests record an optional Git commit and dirty flag,
plus an authoritative SHA-256 over normalized `work/time_twist/**/*.py` paths
and contents. Git is not required. A legacy target without code provenance, or
a target made by a different active code tree, is rejected and must be
re-created through candidate review and promotion.

## Failure interpretation

| Error | Meaning |
| --- | --- |
| `FdsFormatError` | Container/block/side layout is invalid |
| `PackedTextError` | Bitstream ended early or a symbol is out of range |
| `ScenarioError` | Pointer, group, dictionary, or RAM footprint is invalid |
| `EnglishTextError` | Unsupported glyph/control tag or unsafe width |
| `UiPatchError` | Fixed source/table/slot constraints did not match |
| `FontPatchError` | Font source/layout/glyph constraint failed |
| `TitlePatchError` | NOV4 asset, capacity, tile-count, or verification failed |
| `ReleaseBuildError` | Checkout, lock, target, candidate, or output approval failed |

Known command errors are rendered as concise `time-twist: error: ...` messages
without a Python traceback. Treat them as violated invariants; do not suppress
them in a production build.
