# Full-word menu implementation

This document records how the canonical release eliminated the abbreviated
command, object, location, topic, answer, and quiz labels that remained in the
legacy exact-slot UI path. It describes recovered runtime behavior, not a
general license to move arbitrary packed text.

## The original limitation

The first English menu patch preserved every Japanese record's byte length.
That was safe, but many source slots were only two to six bytes long. Later
flat-codec work reclaimed additional dictionary values, but that representation
was still a transitional implementation and is no longer a release path.

The current solution combines the recovered page-addressing model with the
single frozen entropy codec used by all text reachable through the patched NOV2
decoder.

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
contains the starts of records 32, 64, and 96 when those pages exist. Within a
page the decoder advances through separators rather than consulting one pointer
per label.

This means individual records inside a page may change length. The canonical
builder can safely repack the table when it also:

1. regenerates every record-32/64/96 page pointer;
2. moves the two following secondary tables by the same delta;
3. updates their `$A210` and `$A212` base pointers;
4. shifts scenario group zero and all scenario pointers by that delta; and
5. preserves every fixed tail and the bank's NOV3 load boundary.

Every source table is guarded. Relocation also rejects a bank if a recovered
secondary block contains an internal absolute pointer that would require an
unmodeled relocation rule.

## Canonical entropy packing

`release-build` encodes scenario dialogue and full-word menu labels through
`entropy_compression.py` and `entropy_scenario.py`. The generated dictionary may
contain up to 255 entries; dictionary definitions can reference earlier entries
only, keeping expansion acyclic and bounded.

Entropy records are **not** the byte-aligned native format. Records inside one
independently addressed stream are bit-contiguous and pad only at the stream
boundary. The large scenario menu tables therefore use one independently
addressed stream per 32-record page, because the recovered page index stores
byte addresses.

The NOV2 entropy runtime decodes the same semantic token classes as the native
engine but through the frozen prefix grammar. There is no second Adaptive255 or
68-entry release decoder to select at build time.

## Dynamic selection brackets

Menu labels can now have different visible widths. The entropy runtime records
the decoded width of each menu label in the existing staging area and derives
the selected label's right-bracket coordinate from that width. This replaces
the old fixed six/eight-glyph span without placing code or scratch state in the
live `$9390-$93AF` palette region.

The text blitter still caps visible menu labels at the recovered eight-glyph
surface. Full-word here means the complete configured label, not arbitrary
unbounded menu prose.

## Fixed decoder-visible text

The entropy-only runtime creates a global format contract: every packed-text
stream that can reach it must also be entropy encoded. The canonical builder
therefore owns more than the 11 large menu tables:

- NOV4 title/start-menu and internal fixed text;
- NOV4's local dictionary;
- TT1A's fixed blood-type/month/confirmation selector records; and
- the TT1A renderer copy required by the generic sequential scanner.

TT1A is special because native code can jump directly to individual selector
records. Those native byte addresses remain independently aligned entropy
streams; the separate renderer copy supplies the sequential traversal contract.

## Current measurements and audit

The public workbook still reports a conservative flat/native fit diagnostic for
editorial review. It is not the release codec. Exact entropy dictionary sizes,
spill placement, loaded-end addresses, NOV3 headroom, component hashes, and
final image SHA-256 identities belong to a fresh `release_manifest.json`.

The source defines 721 menu labels. The candidate audit must decode every label
back to its configured full text with no mismatches or width failures. A
shortened label is a mismatch; retired fallback labels are not accepted.

```powershell
python work/tools/audit_fixed_menu_labels.py `
  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `
  --output-csv build/candidate/fixed_menu_label_audit.csv
```

Static and binary checks prove that the labels encode and decode exactly. They
cannot prove every runtime call site. Manual playtesting must still open menus
across page boundaries, move the cursor through them, select entries, use
Back/Cancel, save/load, and complete the Zenpen-to-Kouhen disk flow before
promotion.
