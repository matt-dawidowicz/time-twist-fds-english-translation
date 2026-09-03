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
use the presentation rule to change script semantics.

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
the row width. The intended pilot layout is:

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

## Deterministic layout generation

`work/time_twist/editorial_layout.py` implements
`presentation_break_variants()`.

For control-free natural English it:

1. validates single internal spaces and legal word widths;
2. returns the unmodified sentence alone if it already fits one row;
3. otherwise enumerates all word-boundary layouts whose rows are at most 24
   visible characters;
4. replaces selected spaces with the verified presentation control;
5. validates every resulting layout through the normal display-width checker;
6. returns variants in deterministic order.

It never changes a letter, word, punctuation mark, or word order. Existing
controls are rejected by this narrow helper so semantic-control composition
cannot be moved accidentally.

A variant-count guard prevents pathological input from creating an unbounded
combinatorial search.

## Whole-bank layout scoring

A line break changes the compression problem because dictionary candidates do
not cross controls. The cheapest-looking wrap locally may therefore produce a
larger bank globally.

`work/tools/editorial_layout_audit.py` addresses this by:

1. loading the real Japanese source bank and reviewed translation map;
2. generating every legal presentation layout for the supplied natural prose;
3. substituting one layout into a temporary translation map;
4. rebuilding the complete bank with maximize-headroom compression;
5. measuring exact packed bytes, remaining capacity, dictionary count, and
   elapsed time;
6. ranking the layouts by complete-bank packed size.

The tool is an audit, not an automatic source editor. Its result tells the editor
which natural layouts are cheapest; the final wording and presentation remain a
reviewed translation decision.

## Editorial priority

The intended order of decisions is:

1. exact Japanese meaning;
2. natural English;
3. character voice and dramatic rhythm;
4. safe on-screen layout;
5. fixed-bank compressed fit.

When a natural sentence does not initially fit, the first response should be to
measure wrapping and compression options. Deleting articles, pronouns,
conjunctions, or emotional rhythm is a last resort after the engineering options
have been exhausted.

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
