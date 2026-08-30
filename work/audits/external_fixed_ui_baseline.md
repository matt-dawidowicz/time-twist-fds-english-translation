# External fixed-UI baseline

This audit extends the scenario comparison into fixed-address command, object,
quiz, and selector text. The external patch remains a diagnostic target only:
its wording is not stored here and never supplies replacement prose. Japanese
source text remains authoritative for every editorial change.

## Recovered scope

The eleven major scenario-bank fixed tables reconstruct completely from the
external patch, even though many are physically relocated into roughly
32-record pages. TT1A's separate blood-type, month, and confirmation selector
records remain contiguous and are included as well.

| Bank | Records | Exact | Different | External logical segments |
| --- | ---: | ---: | ---: | --- |
| TT1A | 19 | 18 | 1 | `0x025B` × 19 |
| TT1B | 53 | 30 | 23 | `0x1AC8` × 32; `0x3542` × 21 |
| TT2 | 70 | 27 | 43 | `0x3500` × 32; `0x1BEE` × 32; `0x3596` × 6 |
| T22 | 33 | 17 | 16 | `0x0E14` × 33 |
| TT3A | 95 | 47 | 48 | `0x0A9E` × 64; `0x0A04` × 31 |
| TT3B | 21 | 13 | 8 | `0x0AF4` × 21 |
| TT4 | 97 | 53 | 44 | `0x21CE` × 32; `0x2141` × 32; `0x20A9` × 32; `0x0E81` × 1 |
| TT5 | 113 | 47 | 66 | `0x0B50` × 32; `0x0AA5` × 32; `0x0BDA` × 32; `0x1B63` × 17 |
| T25 | 42 | 24 | 18 | `0x098A` × 32; `0x1281` × 10 |
| TT6A | 41 | 24 | 17 | `0x0547` × 32; `0x0F28` × 9 |
| TT6B | 62 | 47 | 15 | `0x0580` × 32; `0x0D4E` × 30 |
| TT6C | 94 | 46 | 48 | `0x176A` × 32; `0x1643` × 32; `0x16DB` × 30 |
| **Total** | **740** | **393** | **347** | |

All 740 records decode without unresolved external tokens after reconstructing
the physical segments into source record order. TT1A exact-match counting strips
only invisible trailing slot-padding spaces; no visible wording is normalized.

The external layout is a comparison-format quirk, not a reason to relax the
production parser. `work/tools/external_translation_compare.py` records only
bank-relative offsets and record counts and provides a generic logical-segment
decoder. Unit tests lock the recovered record totals and reassembly behavior.

## Editorial meaning

A differing fixed label is not automatically wrong. Some differences are
ordinary independent localization choices or abbreviations forced by fixed
slots. Each candidate still has to be checked against the Japanese and against
its gameplay context before the current patch changes.

The comparison exposed a separate completeness issue in NOV2: six save/system
records in the English image were byte-for-byte identical to the Japanese ROM.
Those six records have now been independently decoded from Japanese, translated
in their exact fixed allocations, protected by source-drift tests, and added as
first-class rows to the 2,058-record review corpus. NOV2 is repacked differently
by the external patch, so it still remains outside the 740-record external
alignment until its system block is structurally reconstructed.

## Pending

- Recover and compare the external NOV2/NOV4 system-text blocks without
  assuming that source offsets survived the external repack.
- Review fixed-label differences against Japanese before making editorial
  changes.
- Keep competitor prose out of committed reports and change audits.
