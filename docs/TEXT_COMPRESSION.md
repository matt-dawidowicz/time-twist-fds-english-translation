# Time Twist packed-text compression

This document describes the packed scenario-text format recovered from the FDS
runtime, the English character map, and the 68-entry English dictionary
extension. It separates **runtime facts** from **build-side optimization
policy**. The decoder determines which bitstreams are legal; the optimizer only
chooses among legal encodings.

## Runtime prefix tree

Scenario text is read most-significant bit first. The maintained Python model is
`work/time_twist/textcodec.py` and must remain bit-for-bit compatible with the
6502 reader in NOV2.

| Form | Meaning | Total bits |
| --- | --- | ---: |
| `0xxxxx` / `10xxxx` | common glyph | 6 |
| `110xxxxxx` | extended glyph, or English dictionary 32-68 | 9 |
| `1110xxxxx` | dictionary 1-31 | 9 |
| `1111xxx` | control | 7 |

Control value 5 is reserved as the record separator. After a separator the
reader advances to the next byte boundary. That alignment is why exact packed
size cannot be inferred from visible character count alone.

## English character costs

The English map deliberately assigns the most common letters, space, and common
punctuation to six-bit symbols. Less common uppercase letters, digits, and some
punctuation use nine-bit extended symbols. A dictionary reference is also nine
bits.

The practical consequence is important for prose layout: replacing an ordinary
six-bit space with a seven-bit presentation row advance has a raw cost of only
one bit. Depending on the record's final byte alignment, that may cost zero
additional bytes in the packed file.

## Native dictionary

The original format provides 31 one-based dictionary references through the
`1110xxxxx` branch. A dictionary entry is itself a record containing literal
common/extended glyph symbols. English build output keeps generated entries
flat: dictionary entries do not contain dictionary references or controls.

A reference is worthwhile only when repeated nine-bit references save more
space than storing the dictionary entry itself. The exact answer also depends
on byte-aligned record boundaries.

## English 68-entry extension

English does not need extended-glyph values 0 through 36. The translation
reclaims those otherwise-unused values as dictionary references 32 through 68:

```text
110000000 -> dictionary 32
110000001 -> dictionary 33
...
110100100 -> dictionary 68
```

The encoded width remains nine bits. No scenario token becomes wider merely
because it refers to an entry above 31.

Values 37 through 63 continue to use the normal extended-glyph path, preserving
digits, punctuation, and active uppercase letters.

## Correct NOV2 control flow

The English NOV2 patch reads the six-bit payload of an extended code and, when
that value is below 37, converts it to a one-based dictionary index by adding
32.

The critical instruction sequence is:

```asm
81D3: LDA $3A
81D5: CMP #$25
81D7: BCS $8226
81D9: ADC #$20
81DB: STA $3A
81DD: JMP $82C5
```

`$82C5` is intentional. It is the dictionary-expansion entry **after** the
native five-bit dictionary-index reader.

### Why `$82BE` is wrong

The earlier patch jumped to `$82BE`. That address is the beginning of the
native dictionary-reference path and immediately clears `$3A` and calls the
bit reader to consume another five-bit index. For an English extended
reference, the six-bit index has already been read. Jumping to `$82BE` therefore
throws away the correct 32-68 index, consumes five bits belonging to the next
symbol, and desynchronizes the remainder of the record.

The first TT1A narration exposed this immediately because `September` uses
extended dictionary references. The bad control flow produced a repeatable
mixed-garbage string while the packed TT1A bytes, dictionary, and font data were
all correct.

A semantic regression in
`work/tests/test_extended_dictionary_runtime_semantics.py` now constructs an
extended dictionary reference followed by another symbol and verifies that the
second symbol begins at the expected bit position. This is intentionally
stronger than a test that merely locks a machine-code byte string.

## Record packing

`pack_records()` writes every record as:

1. payload symbols;
2. one control-5 separator;
3. zero padding to the next byte boundary.

The complete packed footprint for one bank includes all scenario group streams
plus its generated dictionary stream. Pointer-table and relocated fixed-UI
bytes are accounted for separately by the scenario/release builder.

## Fixed capacity

The English release does not enlarge scenario-bank memory footprints. The
release builder recovers each bank's available packed region from the Japanese
source, compresses the English into that reservation, and rebuilds with
`preserve_memory_footprint=True`.

A natural-language revision is therefore acceptable only when the complete
rebuilt bank remains within its original capacity. That is an engineering
constraint, not a reason to prefer telegraphic English before compression has
been fully optimized.

## Reference implementation

The authoritative bitstream model remains Python:

- `work/time_twist/textcodec.py` -- prefix tree, bit I/O, separators, alignment;
- `work/time_twist/english.py` -- English character-to-symbol map and renderer
  width validation;
- `work/time_twist/compression.py` -- dictionary selection and exact packed-size
  measurement;
- `work/time_twist/ui.py` -- source-verified NOV2 runtime patch metadata.

Any future native accelerator must propose output that the Python model can
independently repack, expand, and verify. Runtime correctness must never depend
only on a faster implementation agreeing with itself.
