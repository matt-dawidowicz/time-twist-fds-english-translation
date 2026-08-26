# Documentation index

The project serves translators, reverse engineers, and release maintainers.
Choose the shortest path for your task.

## First visit

- **I want to play a candidate:** [Playtesting guide](../PLAYTESTING.md)
- **I want to improve English text:** [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md)
- **I want to change Python tooling or tests:** [Code contributor guide](../CONTRIBUTING_CODE.md)
- **I want a guided explanation of the code:** [Code tour](CODE_TOUR.md)
- **I want to understand the full technical design:** continue below

The public repository is source-only. Candidate images, original FDS images,
BIOS files, extracted retail data, and emulator state belong in a private
maintainer overlay, never in a pull request.

## Understand how the project was solved

Read [the project retrospective](PROJECT_RETROSPECTIVE.md) for a connected
explanation of the packed-text translation, historical difficulty, English
title reconstruction, validation evidence, and remaining release work.

For the recovered addresses, source-byte guards, 6502 patch records, title
asset budgets, appended NOV4 layout, and regression evidence, use the
[bug-fix and title-screen implementation guide](BUG_FIXES_AND_TITLE_IMPLEMENTATION.md).
For the recovered boundary between post-title direct 2bpp source graphics and
the writable 1bpp English font source, including the historical `$AC` alias,
read [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md).

## Audit a bug fix

Read:

1. [Bug-fix and title-screen implementation guide](BUG_FIXES_AND_TITLE_IMPLEMENTATION.md)
2. [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md)
3. [Patch layers](ARCHITECTURE.md#patch-layers)
4. [Adding a binary patch](DEVELOPMENT.md#adding-or-changing-a-binary-patch)
5. [Runtime playtest matrix](PLAYTEST_MATRIX.md)

The guide distinguishes a proven original-engine defect from localization
completeness fixes, translation regressions, presentation corrections, and
build/publication repairs. Preserve that distinction when documenting new
findings.

## Change dialogue

Read:

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [Workbook pipeline](WORKBOOK_PIPELINE.md)
3. [Scenario-bank format](FORMATS.md#scenario-bank-layout)

Playable scenario text lives in `work/translations/*.json`. The workbook's
patch-safe field mirrors it; the natural field can retain a more expansive
editorial translation.

That natural field is intentionally retained for future renderer expansion,
bank optimization, or relocation work. Read
[Preserving the full translation](WORKBOOK_PIPELINE.md#preserving-the-full-translation)
before attempting to install it; natural text is an editorial target, not
proof that it fits the current ROM.

## Change a menu, item, or quiz label

Read:

1. [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)
2. [Fixed-address text](FORMATS.md#fixed-address-packed-text)
3. [Patch layers](ARCHITECTURE.md#patch-layers)
4. [Adding a binary patch](DEVELOPMENT.md#adding-or-changing-a-binary-patch)

The 11 scenario menu tables use a recovered base-plus-page-pointer model and
are repacked by the canonical release. Other fixed records may still require
their individual packed boundaries to remain unchanged. Do not infer one
layout from the other.

## Understand the binary format

Read:

1. [Architecture](ARCHITECTURE.md)
2. [Formats](FORMATS.md)
3. `fds.py`, `textcodec.py`, `scenario.py`, `english.py`, then `compression.py`

## Work on the title or font

Read:

1. [Bug-fix and title-screen implementation guide](BUG_FIXES_AND_TITLE_IMPLEMENTATION.md#english-title-screen-reconstruction)
2. [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md)
3. [Font/title formats](FORMATS.md#font-and-title-assets)
4. [Title sequence architecture](TITLE_SEQUENCE.md)
5. [Patch layers](ARCHITECTURE.md#patch-layers)
6. `work/time_twist/font.py`
7. `work/time_twist/title.py`
8. `work/integration_tests/test_title.py`

The title conversion reuses the existing pattern-table split and animated
clock sprites and is guarded by source hashes and size checks.

## Audit scenario translation safeguards

Read [scenario translation pipeline hardening](SCENARIO_VALIDATION_HARDENING.md)
for stable-ID refresh, shared English validation, direct-insert structure
checks, fixed-UI dictionary boundaries, capacity-aware compressor fallback, and
the fixture-free regression coverage added after code review.

## Add code or tests

Read:

1. [Development guide](DEVELOPMENT.md)
2. [Private fixtures](PRIVATE_FIXTURES.md)
3. [Contributing](../CONTRIBUTING.md)
4. [CLI reference](CLI_REFERENCE.md)

Run `python work/run_tests.py unit` for public work and the integration/all
suite when the private overlay is available. Supported suites allow no skips.

For the Python entry points, companion modules, and matching test files, read
the [module map](MODULE_MAP.md).

## Build or promote a release

Read:

1. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)
2. [Release lifecycle](DEVELOPMENT.md#release-lifecycle)
3. [Release risk assessment](RELEASE_RISK_ASSESSMENT.md)
4. [Release commands](CLI_REFERENCE.md#release-commands)
5. [Translation workflow](TRANSLATION_WORKFLOW.md)

A source-lock refresh approves inputs; a candidate build exposes new outputs;
promotion approves the exact reviewed hashes; a strict build reproduces them.

## Authority map

| Representation | Purpose |
| --- | --- |
| `work/translations/*.json` | Playable scenario source |
| `work/time_twist/ui.py` | Playable fixed/interface source |
| `work/title_assets/Time Twist approved native title.png` | Native ROM-bound final title geometry |
| `work/title_assets/Time Twist approved native slide.png` | Native ROM-bound monochrome swipe geometry |
| `work/release_sources.json` | Approved non-code input hashes |
| `work/release_target.json` | Absent until a reviewed candidate is promoted |
| `work/translated_scripts/*.json` | Decoded/review scenario records |
| `work/translation_workbook_banks/*.json` | Detailed per-bank review |
| `outputs/Time_Twist_complete_translation_workbook.*` | Aggregate review artifacts |
| User-supplied FDS bytes | Authoritative original binary layout |

Never replace exact Japanese evidence with reconstructed kanji. Reconstruction
is editorial context, not recovered ROM data.
