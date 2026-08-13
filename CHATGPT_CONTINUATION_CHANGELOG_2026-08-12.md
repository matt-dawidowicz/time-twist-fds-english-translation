# ChatGPT continuation changelog — 2026-08-12

## Scope

This continuation starts from `Time-Twist-source-for-regular-ChatGPT-2026-08-12.zip` and preserves the existing translation, menu/full-word, disk-retry, camel dialect, and title artwork work. It does not commit, push, publish, delete source work, or replace older candidates.

## Source changes

- `work/time_twist/title.py`
  - Added `_pre_slide_restore_helper()` so the pre-slide 6502 helper is directly unit-testable.
  - Changed the Nintendo-logo-to-title helper from 53 to 59 bytes.
  - The helper now saves `$1C`, clears `$1C`, blanks `$2001`, disables NMI, restores CHR `$B0-$D5`, writes `$58:$57 = $01F0` and `$4D = $F0` while still blank, then restores PPUCTRL and PPUMASK last.
  - Reduced the unused restore workspace from `$0256` to `$0250`, keeping the final NOV4 payload exactly 12,214 bytes.
- `work/tests/test_title_unit.py`
  - Added a fixture-free unit test that locks the safer helper ordering.
- `work/integration_tests/test_title.py`
  - Reused `_pre_slide_restore_helper()` in the private layout assertion to avoid duplicated expected bytes.
- `docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md`, `docs/TITLE_SEQUENCE.md`, and `docs/FUTURE_POLISH_AND_FIXES.md`
  - Updated the helper size, layout offsets, helper behavior, and remaining emulator-proof requirement.
- `work/release_sources.json`
  - Updated the source lock for the current `TT6B.json` camel dialect text already present in the supplied source tree.

## Candidate built

Built fresh from the supplied original Japanese FDS inputs copied locally to `work/baseline/` during the build only. The source zip does not include those private FDS inputs.

| Output | SHA-256 |
| --- | --- |
| `Time Twist - reproducible English four-side playtest.fds` | `11746B682F891D350FD57EA04E7E633A7085833F5ABBBA11E39B5D732DD5B843` |
| `Time Twist Zenpen - reproducible English playtest.fds` | `1EAA7BC923D0ED7BDD61FC3A3D37FE4966486D2B94A0BC2CC617E46C471C9DF9` |
| `Time Twist Kouhen - reproducible English playtest.fds` | `E8B4F40ECC021BB3C31A896C899C1BCA4A88831B17A3A20A26C8DCC316F15368` |

NOV4 remains exactly `12,214` bytes. The four-side candidate parses as four raw FDS sides: two Zenpen sides followed by two Kouhen sides.

## Tests and checks run

- `python -m pip install 'hypothesis>=6.100,<7'`
  - Failed because the environment cannot reach PyPI.
- `python work/run_tests.py unit`
  - Ran 99 discovered tests.
  - Failed only because `hypothesis` is missing and the source-only archive lacks generated comparison/workbook outputs.
- `PYTHONPATH=work python -m unittest work.tests.test_title_unit work.tests.test_ui_unit -v`
  - Passed: 27 tests.
- `python -m compileall -q work/time_twist work/tests/test_title_unit.py work/tests/test_ui_unit.py work/tools`
  - Passed.
- `PYTHONPATH=work python -m time_twist.cli release-lock --project-root . --update`
  - Passed; updated `work/release_sources.json` for current source inputs.
- `PYTHONPATH=work python -m time_twist.cli release-build --project-root . --candidate --output-dir /mnt/data/tt_continue_release`
  - Passed.
- `PYTHONPATH=work python work/tools/audit_full_word_menu_targets.py --output-csv ...`
  - Passed: 721 full-word targets audited, 0 failures.
- `PYTHONPATH=work python work/tools/audit_fixed_menu_labels.py --candidate-fds ... --targets-csv docs/full_word_menu_targets_all_records.csv --output-csv ...`
  - Passed: 721 fixed labels audited, 374 rendered as full words, 347 documented blockers, 0 failures.
- Static NOV2 disk-prompt audit of the rebuilt Zenpen NOV2 payload.
  - Passed for normal prompts, same-side retry records, wrong-disk records, and the bit-aligned saved-game disk-status stream.
- Static NOV4 helper audit of the rebuilt Zenpen NOV4 payload.
  - Confirmed helper byte order and hooks at `$A496`, `$A4E4`, `$A58E`, and `$A42F`.
- `PYTHONPATH=work python work/tools/check_public_tree.py`
  - Passed after removing local private FDS baselines and Python cache files.

## Remaining manual proof gates

- Mesen is not installed in this environment, so no emulator cold-boot evidence was captured here.
- The Nintendo-logo-to-English-title glitch must still be verified by cold boot in Mesen with screenshots/video around the logo disappearance.
- Disk-swap retry paths still need manual runtime confirmation across Load, New Game/opening side prompts, and later-disc save/swap flows. Static records decode correctly, but static decoding is not proof of the exact runtime branch drawn on every path.
- Do not call the title glitch fixed until runtime evidence confirms it.

## Nintendo-logo transition save-state analysis fix

New Mesen save states showed that the remaining title glitch was not caused by
logo artwork or NOV4 size.  Rendering the before-transition state with the
Nintendo temporary tile IDs restored to the English title CHR reproduces the
reported corrupt frame: the PPU was still displaying the old Nintendo nametable
origin when the restored CHR became visible.

The pre-slide helper now still blanks `$1C` and `$2001`, disables NMI, restores
the `$B0-$D5` title CHR, installs `$58:$57 = $01F0`, restores PPUCTRL/NMI, and
restores the `$1C` mirror, but deliberately does **not** write `$1C` back to
`$2001` itself.  The next NMI performs the normal scroll/nametable copy before
rendering is restored from the mirror.  The helper remains 59 bytes by replacing
the former `STA $2001` with three NOPs, and NOV4 remains exactly 12,214 bytes.

This is still a candidate requiring a cold-boot Mesen check; static save-state
analysis explains the corrupt frame and verifies the injected helper flow, but
it is not final runtime proof.
