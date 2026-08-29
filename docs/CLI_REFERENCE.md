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
text to JSON. Existing English is retained only when its stable `BANK/gN/rN`
record ID still matches the refreshed source.

### `scenario-merge SCENARIO TRANSLATIONS [--output PATH] [--allow-partial]`

Merges an ID-keyed English map. Without `--allow-partial`, every record ID is
required. It validates controls, glyph support, and display width.

### `scenario-footprint BANK [--translations PATH]`

Reports the source scenario reservation and, for standalone-layout banks with a
complete translation map, compressed use and remaining bytes. Source-only
inspection remains available for every bank. The 11 banks whose current English
menus are jointly repacked and relocated must use `release-build` for translated
capacity because their playable footprint spans both menu and scenario regions.

### `scenario-insert BANK TRANSLATION OUTPUT [--no-compress] [--bank-name NAME]`

Rebuilds scenario groups and pointers only after validating group indices,
record indices, stable IDs, control order, display width, and glyph support.
Complete translations receive a new English dictionary; partial work keeps the
Japanese dictionary. `--bank-name` is available when the input filename does
not safely identify its bank. The command is intentionally limited to banks
whose current English layout is self-contained in the scenario reservation
(currently TT1A and TT6D). The 11 relocated-menu banks fail closed and direct
maintainers to `release-build`, which owns their combined menu/scenario layout.

`--no-compress` remains a diagnostic option for supported standalone banks; it
preserves the original dictionary on a complete bank.

## Asset and UI commands

### `font-patch NOV4 OUTPUT`

Installs the translated dialogue font after validating the supported NOV4
source revision.

### `title-patch NOV4 TARGET OUTPUT [--slide-target PNG] [--subtitle TEXT]`

Builds and installs the English title assets from exact 256x240 indexed final
and monochrome-swipe images while preserving the clock and recovered
raster-split behavior. `--slide-target` defaults to `Time Twist approved
native slide.png` beside `TARGET`.

### `ui-patch SOURCE OUTPUT [--component NAME]`

Applies one source-verified standalone UI/program patch. Supported components
are `SON-KOUH`, `NOV2`, `NOV4`, and `TT1A`. The 11 scenario banks with
relocated full-word menu tables are not standalone patch targets; `release-build`
repacks those tables together with dialogue and regenerates their page pointers.

The command rejects source-byte and fixed-layout mismatches.

## Release commands

All release commands accept `--project-root PATH`.

### `release-lock [--lock PATH] [--update]`

Without `--update`, verifies the Japanese baselines, all 13 playable scenario
maps, and both title assets against the source lock. The default is
`PROJECT/work/release_sources.json`.

Source-lock schema v2 hashes translation JSON after CRLF/bare-CR to LF
normalization, while FDS baselines and PNG artwork remain byte-exact `raw`
inputs. The lock document's identity is also LF-normalized, so the same
approved checkout has one `source_lock_sha256` on Windows and Unix.

`--update` rewrites the lock from the current project inputs. It approves input
changes only; it does not approve new output hashes. Custom lock destinations
are rejected when they would overwrite an approved source, release-critical
Python file, project metadata, or the release target. The canonical
`PROJECT/work/release_sources.json` destination remains valid.

### `release-build [--output-dir PATH] [--lock PATH] [--target PATH] [--candidate]`

Rebuilds all 13 scenario banks, applies fixed UI/font/title patches, produces
Zenpen and Kouhen, combines four sides, and writes `release_manifest.json`.

For the 11 banks with scenario menu tables, this canonical path packs the
unabbreviated labels together with dialogue, uses the guarded 68-entry English
dictionary decoder, regenerates the menu page pointers, and preserves the
overlay's original fixed suffix. It is the only supported translated build path
for those banks; standalone scenario/UI commands fail closed rather than
reproducing the superseded 31-entry fixed-slot architecture.

Release manifest schema v4 is a complete audit record. It includes source-lock
and release-code provenance, Python/Pillow environment versions, all
scenario-bank capacity/hash reports, fixed-component hashes, target state, and
canonical final-output records. Generated manifests are structurally validated
before publication. Package metadata pins Pillow 12.3.0; the manifest records
the version that actually executed the build.

Default strict mode verifies `PROJECT/work/release_target.json`, including its
tie to the active source-lock SHA-256 and the active release-code provenance.
It stages output and does not publish a new build when target verification
fails.

The repository intentionally has no checked-in target while the current
candidate awaits playtesting. Strict mode therefore fails closed with a
missing-target error until that exact candidate is reviewed and promoted.

`--candidate` skips target approval and publishes a candidate manifest for
review. Candidate mode is required after an intentional source/output change.
Candidate manifests must be built with the current code before they can be
promoted.

### `release-promote CANDIDATE_MANIFEST [--target PATH] [--release-id ID]`

Accepts only a complete current-schema candidate manifest. It validates the
active source lock, requires the candidate subtitle to match that lock, proves
the executing package is identical to the checkout release-code tree, and
checks the reviewed candidate files against their manifest records.

Promotion then performs an **independent candidate-mode rebuild** from the
validated source lock and current release code. The fresh rebuild's complete
`scenario_banks`, `component_sha256`, and `outputs` records must exactly equal
the reviewed manifest. This means a hand-edited manifest cannot promote
arbitrary bytes merely by supplying matching hand-edited hashes.

After the reproduction proof, candidate outputs are checked again and the
candidate manifest is re-hashed immediately before the target is atomically
written. These checks are a strong trusted-local-process mitigation for
concurrent changes; they are not a claim of hostile-filesystem transactional
semantics across the candidate's multiple files.

Custom target destinations are rejected if they collide with the active source
lock, candidate manifest, candidate outputs, approved project inputs,
release-critical Python code, or project metadata. The canonical
`PROJECT/work/release_target.json` destination remains valid.

Candidate and target metadata record an optional checkout Git commit and dirty
flag, plus an authoritative SHA-256 over normalized logical
`work/time_twist/**/*.py` paths and contents. Git is not required. Candidate and
verified manifests also record Python implementation/version and the executing
Pillow version for diagnostics. The package-level Pillow pin narrows the
expected release environment; source, code, component, and output hashes remain
the release authority. A legacy target without code provenance, or a target
made by a different active code tree, is rejected and must be re-created through
candidate review and promotion.

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
