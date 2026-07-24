# Documentation index

The project has two audiences:

1. translators who need to revise wording without corrupting the game; and
2. reverse engineers who need to understand or extend the binary patching
   code.

Use the shortest path below that matches your task.

## I want to change dialogue

Read:

1. [Translation workflow](TRANSLATION_WORKFLOW.md)
2. [Translation workbook pipeline](WORKBOOK_PIPELINE.md)
3. [Packed text and scenario banks](FORMATS.md#scenario-bank-layout)
4. [Translation constraints](../README.md#translation-constraints)

The important rule is that a translated scenario bank is not a list of
ordinary strings. It is a packed bitstream whose group pointers, dictionary,
control codes, fixed tail, and RAM reservation must remain valid.

## I want to change a menu, item, or quiz label

Read:

1. [Fixed-address text](FORMATS.md#fixed-address-packed-text)
2. [UI patch module](ARCHITECTURE.md#patch-layers)
3. [Adding or changing a binary patch](DEVELOPMENT.md#adding-or-changing-a-binary-patch)

Most of these labels live outside the normal scenario groups. Their individual
record addresses are referenced by 6502 code, so the project preserves each
record's original packed byte length.

## I want to understand the binary format

Read:

1. [Architecture](ARCHITECTURE.md)
2. [Formats](FORMATS.md)
3. The source modules in this order:
   `fds.py`, `textcodec.py`, `scenario.py`, `english.py`, `compression.py`

## I want to work on the title screen or font

Read:

1. [Font and title formats](FORMATS.md#font-and-title-assets)
2. [Patch layers](ARCHITECTURE.md#patch-layers)
3. `work/time_twist/font.py`
4. `work/time_twist/title.py`
5. `work/tests/test_title.py`

The title conversion reuses the game's existing pattern-table split and
animated clock sprites. It is intentionally guarded by source hashes and
exact-size checks.

## I want to add code

Read:

1. [Development guide](DEVELOPMENT.md)
2. [Contributing](../CONTRIBUTING.md)
3. [CLI reference](CLI_REFERENCE.md)

Run the entire regression suite before and after a change. A successful unit
test run is necessary but does not replace an end-to-end emulator playtest.

## Source of truth

The repository contains several related representations:

| Representation | Purpose |
| --- | --- |
| `work/translations/*.json` | Compact ID-to-English maps used for patching |
| `work/translated_scripts/*.json` | Extracted scenario records with Japanese, symbols, and English |
| `work/translation_workbook_banks/*.json` | Detailed linguistic review records |
| `outputs/Time_Twist_complete_translation_workbook.*` | Searchable and machine-readable full review |
| Original FDS/bank bytes | Authoritative binary layout; supplied locally and not committed |

Never replace the exact Japanese source in the workbook with reconstructed
kanji. Reconstructed Japanese is editorial context, not recovered ROM data.
