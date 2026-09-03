# English dialogue layout

Time Twist's English script must satisfy two independent constraints:

1. the sentence must be faithful, natural English with the intended character
   voice;
2. the rendered text must remain safe inside the game's 24-tile dialogue row.

Historically the project often solved the second problem by shortening prose.
The editorial-compression work instead treats layout and compression as
engineering problems so the natural sentence remains the authority whenever the
fixed bank can encode it.

## 24-column row

`work/time_twist/english.py` defines `DISPLAY_COLUMNS = 24` and validates every
control-delimited visible segment against that width.

The renderer can automatically wrap some long text, but a following control may
reuse the wrapped row and overwrite characters. The release tooling therefore
does not assume that arbitrary automatic wrapping is safe.

## Semantic controls versus presentation controls

Not every `{CTRL:n}` is interchangeable. Controls may affect row position,
paging, waits, timing, or game state. Source controls are therefore preserved by
default.

The shared scenario validator historically required:

```text
English control sequence == Japanese control sequence
```

That remains the default rule.

English sometimes needs an additional visual row because its syntax or word
length differs from Japanese. The project now provides a narrow exception for a
**verified presentation row advance**, currently `CTRL:0` in explicitly audited
records.

The exception has three safeguards:

- the record ID must be allowlisted;
- every source control must still appear in original order;
- any additional control must be `CTRL:0`.

An allowlisted record cannot insert `CTRL:4`, reorder a source wait, or otherwise
use the presentation rule to change script semantics. The shared
`scenario_controls_match_policy()` predicate is used by scenario validation and
review tooling so the ROM builder, comparison corpus, and workbook do not carry
separate definitions of a safe control sequence.

The bilingual corpus still records `source_controls` and `english_controls`
separately. Its `control_match` result means that the English sequence is valid
under the reviewed policy; it does not hide an English-only presentation break.

## Why English-only breaks are cheap

In the packed format:

- a common space costs six bits;
- a control token costs seven bits.

When a line break replaces an existing inter-word space, its direct raw cost is
therefore only one bit. Because records are byte-aligned after their separator,
that extra bit may produce no increase in the final byte count at all.

Dictionary effects can be larger than the direct one-bit difference because a
control splits literal candidate regions. That is why layout should be measured
against the whole bank rather than judged from visible character count.

## Blue-sky pilot

Japanese:

```text
さいごにあおぞらをみたのは いつだっけ
```

Natural English:

```text
When was the last time I saw a blue sky?
```

The earlier playable draft shortened this to telegraphic English to remain under
the row width. The accepted source layout is:

```text
When was the last time{CTRL:0}I saw a blue sky?
```

Visible rows:

```text
When was the last time
I saw a blue sky?
```

Both rows are below 24 columns. The prose itself is not rewritten to satisfy the
renderer.

## Deterministic minimum-row layout generation

`work/time_twist/editorial_layout.py` implements
`presentation_break_variants()`.

For control-free natural English it:

1. validates single internal spaces and legal word widths;
2. returns the unmodified sentence alone if it already fits one row;
3. computes the minimum number of renderer rows required to preserve every word;
4. enumerates only word-boundary layouts that use that minimum row count and
   keep every row at or below 24 visible characters;
5. replaces selected spaces with the verified presentation control;
6. validates every resulting layout through the normal display-width checker;
7. returns variants in deterministic order.

It never changes a letter, word, punctuation mark, or word order. Existing
controls are rejected by this narrow helper so semantic-control composition
cannot be moved accidentally.

Layouts that use more rows than necessary are intentionally excluded. Once the
sentence safely fits in *N* rows, an *N+1*-row version adds another control and
another dictionary boundary without solving a display requirement. This
minimum-row rule prevents combinatorial runaway and keeps compression scoring
focused on editorially meaningful alternatives. A variant-count guard still
bounds pathological sets of equally minimal layouts.

## Whole-bank layout scoring

A line break changes the compression problem because dictionary candidates do
not cross controls. The cheapest-looking wrap locally may therefore produce a
larger bank globally.

`work/tools/editorial_layout_audit.py` addresses this by:

1. loading the real Japanese source bank and reviewed translation map;
2. generating every minimum-row presentation layout for the supplied natural
   prose;
3. substituting one layout into a temporary translation map;
4. rebuilding the complete bank with maximize-headroom compression;
5. measuring exact packed bytes, remaining capacity, dictionary count, and
   elapsed time;
6. ranking the layouts by complete-bank packed size.

The tool is an audit, not an automatic source editor. Its result tells the editor
which natural layouts are technically cheapest; the final wording and
presentation remain a reviewed translation decision.

## Editorial priority

The intended order of decisions is:

1. exact Japanese meaning and implication;
2. emotional valence and sentiment;
3. speaker stance, register, characterization, and subtext;
4. natural English and dramatic rhythm;
5. safe on-screen layout;
6. fixed-bank compressed fit.

When a natural sentence does not initially fit, the first response should be to
measure wrapping and compression options. Deleting articles, pronouns,
conjunctions, humor, hesitation, emphasis, or emotional rhythm is a last resort
after the engineering options have been exhausted.

## Expanding the presentation-break allowlist

The current allowlist is deliberately small. A new record should be added only
after its runtime context has established that an additional `CTRL:0` is a pure
row-layout operation there.

For each new allowlisted record:

- preserve the natural English source in the editorial record/workbook;
- document why an extra row is required;
- add a validator regression showing the intended extra `CTRL:0` is accepted;
- add a negative test proving non-presentation controls remain rejected;
- run the whole-bank layout/compression audit;
- runtime-test representative transitions if the control context differs from
  already proven cases.

This keeps the exception auditable instead of gradually turning control
validation into an unrestricted rewrite facility.

## Intent and sentiment are editorial constraints

Line layout is not allowed to flatten the source. The preferred English must be
chosen from the translation review evidence first: exact Japanese, literal
meaning, speaker identity, linguistic/register notes, established character
voice, scene context, emotional/sentiment analysis, and the reviewed natural
English reading. Compression is evaluated only after that target exists.

This means a layout that saves a few bytes does not automatically win. For the
blue-sky pilot, whole-bank optimization measured all three minimum-row layouts:

| Layout | Packed TT1B | Free bytes |
| --- | ---: | ---: |
| `When was the last` / `time I saw a blue sky?` | 3898 | 336 |
| `When was the last time I` / `saw a blue sky?` | 3900 | 334 |
| `When was the last time` / `I saw a blue sky?` | 3902 | 332 |

The project deliberately selects `When was the last time` / `I saw a blue sky?`.
It is four bytes larger than the compressor-optimal break but better preserves
English phrasing and reflective rhythm, while still leaving 332 bytes free in
the deep-audit result. Editorial quality therefore dominates byte minimization
once the hard ROM constraints are satisfied.

## Python-Rust editorial path

Compression-aware layout scoring may use the optional Rust optimizer because a
real TT1A benchmark reduced deep-search time from about 17.3 seconds in Python
to about 0.43 seconds in Rust while producing the same 1,594-byte result and the
same 26-entry dictionary. The speedup makes it practical to evaluate natural
prose and multiple legal layouts rather than pre-shortening text to avoid search
cost.

Rust is not allowed to define what the ROM means or accepts. Python supplies the
canonical symbols, independently expands every native result, repacks it through
the canonical codec, rechecks the exact byte count, and rejects any structural,
semantic, dictionary, or capacity disagreement. See
[`NATIVE_ACCELERATOR.md`](NATIVE_ACCELERATOR.md) for the complete boundary and
build protocol.