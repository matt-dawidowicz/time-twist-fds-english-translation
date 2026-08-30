# Python module map

Start with the row that matches the behavior you want to understand. Public
facade modules retain the established import paths; their focused companion
modules hold the implementation details.

For the project objective, binary safety model, data flow, and a plain-language
explanation of each module's responsibility, read the [code tour](CODE_TOUR.md)
first. This page is the compact lookup table to use once you know the area you
need to change.

| Area | Start here | Companion modules | Main tests |
| --- | --- | --- | --- |
| Command line | `src/time_twist/cli.py` | `cli_commands.py`, `cli_parser.py` | `tests/unit/test_release_unit.py`, `test_public_api.py` |
| Release build and promotion | `src/time_twist/release.py` | `release_metadata.py` | `tests/unit/test_release_unit.py`, `test_release_integrity.py` |
| Fixed UI and input behavior | `src/time_twist/ui.py` | `ui_fixed_tables.py` | `tests/unit/test_ui_unit.py`, `test_ui_fixed_tables.py` |
| English title | `src/time_twist/title.py` | `title_layout.py`, `title_assets.py`, `title_patch.py` | `tests/unit/test_title_unit.py` and private title integration tests |
| Packed scenario text | `src/time_twist/scenario.py` | `textcodec.py`, `compression.py`, `scenario_validation.py` | `tests/unit/test_textcodec.py`, `test_scenario_validation.py` |
| FDS container | `src/time_twist/fds.py` | — | `tests/unit/test_fds_synthetic.py`, `test_binary_properties.py` |

`tests/unit/test_public_api.py` protects the stable facade contract.
`tests/unit/test_private_fixture_manifest.py` protects the public metadata for
private runtime-capture evidence. Repository discovery and relocatability are
covered separately by `tests/unit/test_repository_paths.py`.

## Facade rule

Import from `cli.py`, `release.py`, `ui.py`, or `title.py` when writing a tool,
test, or integration. Those files preserve the stable public API. Use their
companion modules when changing a specific implementation concern.

## Repository rule

Release-critical executable code lives under `src/time_twist/`. Developer-only
analysis, audit, generation, maintenance, and preview code lives under `tools/`.
`work/` contains project data and evidence and must not become an import root
again.

## Refactor safety

Module moves are source changes even when they preserve behavior. Run the full
public suite after a refactor. For release, UI, font, or title work, also build
a fresh private candidate from legal local inputs and replay the affected
emulator route before treating the change as runtime-safe.
