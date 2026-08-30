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
| Command line | `work/time_twist/cli.py` | `cli_commands.py`, `cli_parser.py` | `work/tests/test_release_unit.py` |
| Release build and promotion | `work/time_twist/release.py` | `release_metadata.py` | `work/tests/test_release_unit.py`, `test_release_integrity_polish.py` |
| Fixed UI and input behavior | `work/time_twist/ui.py` | `ui_fixed_tables.py` | `work/tests/test_ui_unit.py`, `test_ui_fixed_tables.py` |
| English title | `work/time_twist/title.py` | `title_layout.py`, `title_assets.py`, `title_patch.py` | `work/tests/test_title_unit.py` and private title integration tests |
| Packed scenario text | `work/time_twist/scenario.py` | `textcodec.py`, `compression.py`, `scenario_validation.py` | `work/tests/test_textcodec.py`, `test_scenario_validation_hardening.py` |
| Private three-way translation audit | `work/generate_three_way_comparison.py` | `work/time_twist/three_way.py` | `work/tests/test_three_way.py` |
| FDS container | `work/time_twist/fds.py` | — | `work/tests/test_fds_synthetic.py`, `test_binary_properties.py` |

`work/tests/test_modern_module_layout.py` protects the public facades and the
generic private runtime-capture layout after module moves.

## Facade rule

Import from `cli.py`, `release.py`, `ui.py`, or `title.py` when writing a tool,
test, or integration. Those files preserve the stable public API. Use their
companion modules when changing a specific implementation concern.

## Refactor safety

Module moves are source changes even when they preserve behavior. Run the full
public suite after a refactor. For release, UI, font, or title work, also build
a fresh private candidate from legal local inputs and replay the affected
emulator route before treating the change as runtime-safe.
