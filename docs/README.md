# Documentation index

The project serves translators, reverse engineers, and release maintainers.
Choose the shortest path for your task.

## Understand how the project was solved

Read [the project retrospective](PROJECT_RETROSPECTIVE.md) for a connected
explanation of the packed-text translation, historical difficulty, English
title reconstruction, AI-assisted workflow, validation evidence, and remaining
release work.

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

1. [Fixed-address text](FORMATS.md#fixed-address-packed-text)
2. [Patch layers](ARCHITECTURE.md#patch-layers)
3. [Adding a binary patch](DEVELOPMENT.md#adding-or-changing-a-binary-patch)

These records are often referenced directly by 6502 code, so individual packed
slot boundaries must remain fixed.

## Understand the binary format

Read:

1. [Architecture](ARCHITECTURE.md)
2. [Formats](FORMATS.md)
3. `fds.py`, `textcodec.py`, `scenario.py`, `english.py`, then `compression.py`

## Work on the title or font

Read:

1. [Font/title formats](FORMATS.md#font-and-title-assets)
2. [Title sequence architecture](TITLE_SEQUENCE.md)
3. [Patch layers](ARCHITECTURE.md#patch-layers)
4. `work/time_twist/font.py`
5. `work/time_twist/title.py`
6. `work/integration_tests/test_title.py`

The title conversion reuses the existing pattern-table split and animated
clock sprites and is guarded by source hashes and size checks.

## Add code or tests

Read:

1. [Development guide](DEVELOPMENT.md)
2. [Private fixtures](PRIVATE_FIXTURES.md)
3. [Contributing](../CONTRIBUTING.md)
4. [CLI reference](CLI_REFERENCE.md)

Run `python work/run_tests.py unit` for public work and the integration/all
suite when the private overlay is available. Supported suites allow no skips.

## Build or promote a release

Read:

1. [Release lifecycle](DEVELOPMENT.md#release-lifecycle)
2. [Release commands](CLI_REFERENCE.md#release-commands)
3. [Translation workflow](TRANSLATION_WORKFLOW.md)

A source-lock refresh approves inputs; a candidate build exposes new outputs;
promotion approves the exact reviewed hashes; a strict build reproduces them.

## Authority map

| Representation | Purpose |
| --- | --- |
| `work/translations/*.json` | Playable scenario source |
| `work/time_twist/ui.py` | Playable fixed/interface source |
| `work/title_assets/Time Twist approved native title.png` | Native ROM-bound title geometry |
| `work/release_sources.json` | Approved non-code input hashes |
| `work/release_target.json` | Promoted output hashes |
| `work/translated_scripts/*.json` | Decoded/review scenario records |
| `work/translation_workbook_banks/*.json` | Detailed per-bank review |
| `outputs/Time_Twist_complete_translation_workbook.*` | Aggregate review artifacts |
| User-supplied FDS bytes | Authoritative original binary layout |

Never replace exact Japanese evidence with reconstructed kanji. Reconstruction
is editorial context, not recovered ROM data.
