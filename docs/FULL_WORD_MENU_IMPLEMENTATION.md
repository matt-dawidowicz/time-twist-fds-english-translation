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
replacement: A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82
```

Values below 37 add 32 and enter the existing dictionary expander at `$82C5`, after the native five-bit dictionary-index reader.
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
writing. The standalone `scenario-insert` plus `ui-patch` workflow remains a
31-entry, exact-slot diagnostic path and may still use declared compact
fallbacks. It is not the canonical full-word build path.

## Verified candidate result

The August 25, 2026 candidate produced these exact bank results:

| Bank | Dictionary entries | Used bytes | Capacity | Remaining |
| --- | ---: | ---: | ---: | ---: |
| TT3A | 68 | 4,013 | 4,169 | 156 |
| TT3B | 37 | 1,901 | 1,927 | 26 |
| TT1B | 68 | 3,777 | 4,234 | 457 |
| TT1A | 31 | 1,656 | 1,669 | 13 |
| TT2 | 68 | 3,984 | 4,141 | 157 |
| T22 | 50 | 1,894 | 1,939 | 45 |
| TT6C | 68 | 3,852 | 3,947 | 95 |
| TT6B | 54 | 2,542 | 2,601 | 59 |
| TT6A | 68 | 2,800 | 3,000 | 200 |
| TT6D | 6 | 323 | 332 | 9 |
| TT4 | 68 | 5,146 | 5,187 | 41 |
| TT5 | 68 | 4,141 | 4,201 | 60 |
| T25 | 53 | 2,440 | 2,561 | 121 |

The fixed-menu audit decoded 721 installed labels from the finished four-side
image against their canonical source strings:

- 721 full-word matches;
- 0 fallback/abbreviated labels;
- 0 mismatches or width failures;
- 443 records using at least one dictionary reference; and
- 278 literal-only records.

The candidate output identities are:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| Zenpen | 131,000 | `19A3ABDAFCCC4A15D3082D7EBE653C996EC0C65BDF331F0E885B1CFF7AA49D17` |
| Kouhen | 131,000 | `5BF9FA9B773DA2E9B503761CC0843AE39BCD61B9B8D1BDF1EEAF166037A1AC50` |
| Four-side | 262,000 | `E8FBF9B39278170278F22D2A1C6558DE04DD0F7711570737E584A7A37DA149F3` |

These are candidate identities, not a promoted release target. The repository
remains source-only and does not contain the generated images.

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
