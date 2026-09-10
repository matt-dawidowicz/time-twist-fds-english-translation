# Full-word menu implementation

This document records how the canonical release eliminated the abbreviated
command, object, location, topic, answer, and quiz labels that remained in the
legacy exact-slot UI path. It describes recovered runtime behavior, not a
general license to move arbitrary packed text.

## The original limitation

The first English menu patch preserved every Japanese record's byte length.
That was safe, but many source slots were only two to six bytes long. The
native packed-text decoder also exposed only 31 one-based dictionary entries.
Even with better dictionary search, those two constraints could not encode all
full labels simultaneously. The readable fallback table therefore still
contained abbreviations such as `BOD`, `TRGH`, and `JORDN`.

Exact size modeling proved that a different search over the same 31-entry,
fixed-slot representation could recover bytes but could not remove every
abbreviation. The solution required using more of the format already present
in the game.

## Recovered menu addressing

The 11 scenario banks with large fixed menu tables do not contain one absolute
6502 address per record. Their header exposes this addressing model:

| Header offset | Loaded address in an `$A200` bank | Meaning |
| ---: | ---: | --- |
| `$0010` | `$A210` | First secondary table base |
| `$0012` | `$A212` | Second secondary table base |
| `$0014` | `$A214` | Menu record-zero base |
| `$001A` | `$A21A` | Menu page-pointer table |

The renderer starts records 0-31 from `$A214`. The table addressed by `$A21A`
contains the starts of records 32, 64, and 96 when those pages exist. The code
then scans byte-aligned record separators within the selected 32-record page.

This means individual records inside a page may change length. The release
builder can safely repack the table when it also:

1. regenerates every record-32/64/96 page pointer;
2. moves the two following secondary tables by the same delta;
3. updates their `$A210` and `$A212` base pointers;
4. shifts scenario group zero and all scenario pointers by that delta; and
5. leaves the original fixed suffix and complete overlay size unchanged.

Every source table is SHA-256 guarded. The relocation also rejects a bank if
the recovered secondary block contains an internal absolute pointer into
itself, because such a pointer would need an additional relocation rule.

## Extending the English dictionary to 68 entries

Native dictionary references use the nine-bit `1110xxxxx` form and name
entries 1-31. English extended literals use the nine-bit `110xxxxxx` form, but
the installed English character map needs only values 37-62. Values 0-36 are
otherwise unreachable in translated English.

The release reclaims those 37 values as dictionary entries 32-68:

| Encoded form | Native meaning | Patched English meaning |
| --- | --- | --- |
| `1110xxxxx` | Dictionary 1-31 | Dictionary 1-31 |
| `110000000` through `110100100` | Extended glyph 0-36 | Dictionary 32-68 |
| `110100101` through `110111111` | Extended glyph 37-63 | Extended glyph 37-63 |

NOV2's decoder change is an exact 13-byte replacement at file `$21D3`, loaded
at CPU `$81D3`:

```text
source:      A5 3A C9 04 90 07 C9 20 B0 09 4C ED 81
replacement: A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82
```

Values below 37 add 32 and enter the existing dictionary expander at `$82BE`.
Values 37 and above retain the existing extended-glyph path at `$8226`. The
patch does not grow or relocate NOV2. Native Japanese parsing remains the
default in the tools; patched interpretation is enabled only for rebuilt
English release data.

## Joint menu/dialogue packing

For a menu-bearing bank, `release-build` encodes the complete menu table as an
additional compression group beside the scenario groups. It gives the
compressor the combined recovered menu-plus-scenario reservation, subtracting
the scenario group-pointer and menu page-pointer bytes before compression.

The resulting dictionary is shared by dialogue and menu labels. The canonical
release permits up to 68 entries, then verifies the exact packed size before
writing. There is no abbreviated fallback in the release path.

## Current measurements

The [generated progress report](../outputs/Time_Twist_translation_progress.md)
recomputes conservative fits for the current text. Exact optimized sizes and
output SHA-256 identities belong to the freshly built candidate's
`release_manifest.json`, as described in the
[maintainer release process](MAINTAINER_RELEASE_PROCESS.md).

The source defines 721 menu labels. The candidate audit must decode every label
back to its canonical full text with no mismatches or width failures. A shortened
label is a mismatch; retired fallback labels are not accepted. Reports reject
nonmatching audits before writing candidate summaries.

## Verification and remaining gate

Regression coverage locks the native/patched token distinction, the exact
NOV2 patch bytes and address, deterministic release output, relocated menu
page pointers, and full-label decode equality. The audit tool is:

```powershell
python work/tools/audit_fixed_menu_labels.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --output-csv build/candidate/fixed_menu_label_audit.csv
```

Static and binary checks prove that the full labels fit and decode exactly.
They cannot prove every runtime call site. Manual playtesting must still open
menus on every page boundary, move the cursor through them, select entries,
use Back/Cancel, save/load, and complete the Zenpen-to-Kouhen disk flow before
promotion.
