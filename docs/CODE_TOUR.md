# Code tour

This is the quickest route from a reported in-game problem to the code that
can safely investigate it. The repository is a **source-only translation
project**: original FDS images, extracted retail banks, rebuilt candidates,
and emulator evidence stay in a private maintainer overlay. Public code must
therefore explain what it expects, what it is allowed to change, and what it
deliberately refuses to guess.

Read this alongside [the module map](MODULE_MAP.md). The map is a short index;
this guide explains why those modules exist and how they support a playable,
reproducible English translation.

## The project objective

The project has four inseparable goals:

1. Preserve the Japanese FDS release as the binary/source authority.
2. Build playable English text and fixed UI without moving unknown game data.
3. Make every binary edit fail closed when its expected source bytes, capacity,
   addresses, or packed-text controls do not match.
4. Produce candidates that can be identified by hash and independently rebuilt
   before they are promoted or offered for playtesting.

The tools are not a general ROM editor. They are a set of narrow transforms for
known Time Twist components and known records. A new feature should normally
add a recovered fact, a source guard, a focused transform, a unit test, and a
runtime playtest route—in that order.

## Read this first for a reported problem

| Player sees… | Read first | Why |
| --- | --- | --- |
| Dialogue or narration problem | `work/translations/<BANK>.json`, then `scenario.py` | Scenario text is dictionary-packed and must retain IDs, controls, and capacity. |
| Menu, quiz, disk prompt, Save/Load, or B-button problem | `ui.py`, then `ui_fixed_tables.py` | Shared UI records may sit beside 6502 code and have fixed byte footprints. |
| Missing/wrong glyph or spacing | `font.py`, then `charmap.py` | English characters must map to the game's deterministic 8x8 font tiles. |
| Title animation or title-menu problem | `title.py`, then `title_layout.py`, `title_assets.py`, and `title_patch.py` | NOV4 combines code, CHR, nametables, palettes, and timing-sensitive transitions. |
| Disk layout, a missing file, or side-order problem | `fds.py` | The FDS container preserves file headers, side order, padding, and checksums. |
| Build/reproducibility/hash problem | `release.py`, then `release_metadata.py` | Candidate and promotion code binds outputs to the current source lock and code tree. |

Do not start by hex-editing a generated image. Trace the symptom to an owned
component and update the transform that regenerates it.

## From source text to a playtest candidate

```text
Reviewed translation map / fixed UI table / title asset
                    |
                    v
  source-byte, control-order, glyph, width, and capacity validation
                    |
                    v
       packed scenario rebuild or size-neutral component patch
                    |
                    v
     FDS side replacement with original layout and file identities kept
                    |
                    v
  candidate manifest: source lock + code provenance + component/output hashes
                    |
                    v
     private runtime smoke test and community playtest evidence
```

Only the arrows above are automated. Static checks prove that a candidate was
built safely from known inputs; they do not prove title timing, disk swapping,
saves, or scene progression. Those require the routes in
[the runtime playtest matrix](PLAYTEST_MATRIX.md).

## Production package, module by module

### Text and scenario modules

| Module | Responsibility | Important boundary |
| --- | --- | --- |
| `charmap.py` | Defines the available English symbol values and visible widths. | Unsupported characters fail before any packed data is written. |
| `english.py` | Encodes English, validates controls, line widths, and word breaks. | Translation wording is not allowed to rearrange recovered control codes. |
| `textcodec.py` | Reads/writes the native bitstream records, dictionary symbols, controls, and alignment. | It is the only layer that should reason directly about packed symbol bits. |
| `compression.py` | Chooses a legal 31-entry dictionary and compresses scenario groups. | Compression must decompress to the exact intended symbol stream. |
| `scenario.py` | Parses recovered scenario-bank layout and rebuilds a bank. | Fixed record addresses and tails are preserved unless a recovered layout says otherwise. |
| `scenario_validation.py` | Shares the policy used by tools and release building. | A text change is rejected if it breaks ID, glyph, control, or display rules. |
| `project.py` | Stores named bank facts, component locations, and approved dictionary reservations. | Project constants express recovered Time Twist facts, not configurable defaults. |

When translating, start with the stable record ID. Japanese source text,
playable English, and the editor's natural English are intentionally separate:
the first proves authority, the second must fit the hardware, and the third
records the complete editorial intent for future renderer work.

### FDS, font, fixed UI, and title modules

| Module | Responsibility | Important boundary |
| --- | --- | --- |
| `fds.py` | Parses, validates, edits, and combines FDS images. | Preserves sides, file records, sizes, and padding; it never translates text. |
| `font.py` | Generates and installs deterministic English 8x8 glyph rows. | Font data is owned by NOV4; do not repurpose tiles used by title graphics. |
| `ui_fixed_tables.py` | Holds declarative fixed-menu labels and blocker facts. | Values are data only; each must fit its recovered slot. |
| `ui.py` | Applies fixed text, disk prompts, direct-boot copy, and guarded input patches. | Every binary patch checks the source bytes and stays size-neutral unless proven relocation exists. |
| `title_layout.py` | Names recovered NOV4 regions, addresses, and title memory budgets. | These constants protect the resident NOV3 boundary and PPU-sensitive regions. |
| `title_assets.py` | Converts approved indexed title art to native CHR/nametable-friendly assets. | Inputs are validated against known palette, size, and geometry rules. |
| `title_patch.py` | Installs title assets and small 6502 helpers in verified space. | Rendering is blanked during sensitive transitions so mixed old/new frames cannot flash. |
| `title.py` | Provides the stable public title API. | Import this facade from callers; companions may move internally. |

`NOV2` is the shared game UI/input overlay. `NOV4` is the title/font overlay.
Scenario overlays such as `TT1A`, `TT1B`, and `TT2` hold story and local menu
data. The ownership distinction tells you where an observed string or behavior
can actually be fixed.

### Release and command-line modules

| Module | Responsibility | Important boundary |
| --- | --- | --- |
| `release_metadata.py` | Defines source locks, code provenance, manifests, and strict validation. | Metadata records current facts only; unsupported schemas fail rather than being silently upgraded. |
| `release.py` | Builds scenario banks, patches components, creates candidate images, and promotes reviewed output. | A promotion rebuilds independently and compares hashes before it writes a target. |
| `cli_parser.py` | Defines commands and human-facing command help. | Parsing has no FDS-writing side effects. |
| `cli_commands.py` | Connects parsed arguments to the narrow project transforms. | Command handlers report known validation failures without misleading tracebacks. |
| `cli.py` | Provides the stable command-line public API. | Tools should import the facade, not depend on internal module placement. |

Candidate mode is intentionally different from promotion. A candidate is a
testable build with a manifest; it is not automatically approved. Promotion is
the maintainer action that binds reviewed files to the active source lock and
current release-code hash.

## Supporting command-line tools

`work/tools/` contains narrow audit and public-tree helpers rather than another
copy of the release pipeline:

| Tool | Use it for |
| --- | --- |
| `check_public_tree.py` | Rejecting ROMs, FDS candidates, retail extracts, captures, caches, and personal paths before a public commit. |
| `audit_fixed_menu_labels.py` | Comparing the playable fixed-menu copy with the canonical full-word targets. |
| `audit_full_word_menu_targets.py` | Reporting whether a label fits its current packed slot and display width. |
| `report_full_word_menu_candidate.py` | Binding a menu audit to an actual candidate manifest and scenario-bank hashes. |
| `validate_translation_patch_fragments.py` | Checking the small public patch fragments without requiring private full-bank maps. |
| `disassemble_6502.py` | Inspecting a recovered code range before declaring a native engine patch safe. |

Tools should explain an existing recovered constraint. They must not create new
binary authority by guessing at an unknown bank, pointer table, or renderer.

## Tests: what each layer proves

| Test location | What it proves | What it does **not** prove |
| --- | --- | --- |
| `work/tests/` | Public parser, codec, validation, source-tree, documentation, and facade behavior. | That a candidate has run in a game. |
| `work/integration_tests/` | Private-overlay source guards, recovered file layout, title/UI patch locations, and reproducible candidate data. | Full player progression. |
| `docs/PLAYTEST_MATRIX.md` | The runtime routes that a maintainer and playtesters must verify. | Static source correctness. |

The test name is the exact behavior under protection; its docstring says why it
matters to the current project contract. A test that checks original Japanese
bytes is not old-code compatibility baggage—it protects the current patch from
being applied to an unknown revision.

## Documentation standard

Every maintained Python module, class, and function has a purpose docstring.
Use comments for decisions that code cannot make obvious, especially:

- why a byte count, address, source sequence, or dictionary reservation is
  fixed;
- why a workaround is limited to one overlay or input state;
- which visual/runtime failure a title or rendering step prevents; and
- why a check fails closed instead of attempting automatic recovery.

Do not comment routine punctuation, imports, assignments, or straightforward
control flow. That kind of line-by-line noise hides the constraints a future
ROM hacker actually needs. The public unit suite includes
`test_documentation_contract.py`, which prevents undocumented definitions from
being added later.

## Safe contribution loop

1. Use this guide to identify the owner of the behavior.
2. Read the module docstring, the function contract, and its matching test.
3. Change source data or a guarded transform—not a generated FDS image.
4. Add/update a focused test and explain the recovered constraint in code.
5. Run `python work/tools/check_public_tree.py` and
   `python work/run_tests.py unit`.
6. For a binary-visible change, rebuild privately and replay the affected route
   before asking outside playtesters to verify broader behavior.
