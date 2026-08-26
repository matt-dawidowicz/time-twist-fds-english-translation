# Scenario translation pipeline hardening

This note records the defensive changes added after the August 2026 code
review. The objective is to make low-level scenario commands enforce the same
translation invariants as the release builder and to make the scenario/UI
shared-dictionary boundary explicit without guessing dictionary lengths.

## Stable identity during extraction

`scenario-extract` now carries existing English forward only when the previous
record has the same stable ID (`BANK/gN/rN`). Group/record coordinates alone
are not sufficient. Reusing one output path for another bank therefore cannot
silently copy English into an unrelated record at the same coordinates.

## One translation validation policy

`work/time_twist/scenario_validation.py` is the shared policy layer for
scenario-facing English. It checks:

- a nonempty string value;
- exact control-tag order relative to decoded Japanese source text;
- the 24-column renderer limit;
- the documented wrapping exception for TT1A personality questions; and
- native English glyph encodability.

`scenario-merge`, `scenario-footprint`, `scenario-insert`, and the release
builder all call the same validator. Command-specific code only adds useful
error context.

## Direct insertion is structurally guarded

`scenario-insert` now rejects a merged JSON document when any group index,
record index, or stable record ID differs from the source bank. It also applies
the shared English validator before packing. A reordered or hand-edited JSON
file therefore cannot redirect otherwise valid text into the wrong record, and
an overwide line cannot bypass `scenario-merge` by invoking insertion directly.

The lower-level `rebuild_scenario_bank()` API now independently enforces the
source bank's per-group record counts and an explicit decoder-specific
dictionary limit. Native callers default to 31; the guarded English release
path explicitly requests 68. Callers outside the CLI therefore cannot
accidentally serialize a structurally shifted record layout or a dictionary
unsupported by their decoder merely because the outer group count still
matches.

## Dictionary reservation boundary

Ordinary scenario records are not necessarily the only users of a source
bank's dictionary. Fixed-address command, object, and quiz tables can reference
dictionary entries while living outside the scenario group streams.

`source_dictionary_reference_floor()` decodes each verified source fixed table
and finds its highest one-based dictionary reference. Scenario parsing accepts
that reference as an explicit minimum and then follows nested dictionary
references transitively. `dictionary_end_offset` therefore covers entries
proven reachable from either dialogue or the source fixed UI, without assuming
that every bank has 31 source entries.

The standalone `scenario-insert`/`ui-patch` workflow is a separate legacy
case: its exact-slot patcher indexes a complete 31-slot English dictionary.
`required_dictionary_entries()` marks those banks as full-dictionary consumers.
The compressor therefore accepts a fast result only when it contains all 31
entries, retries with candidate pruning disabled when necessary, and fails
closed if the exhaustive positive-saving search still cannot produce a
complete dictionary.

The canonical release uses the fully recovered menu layout instead. It packs
each bank's complete menu strings as another compression group, permits 68
English dictionary entries through the source-verified NOV2 decoder patch,
regenerates record-page pointers 32/64/96, and moves only the two intervening
tables whose base pointers are present in the header. The fixed scenario suffix
and total overlay size do not move. This is the path that removes menu
abbreviations.

A fully translated fixed-UI bank also rejects `scenario-insert --no-compress`.
That diagnostic mode deliberately preserves the Japanese dictionary, so it
cannot be a safe input to the English fixed-table `ui-patch` step. The command
now fails before writing an output rather than allowing that unsafe workflow.

The hardening is folded into the canonical CLI, parser, compressor, and release
modules rather than hidden behind compatibility facades. The recovered binary
logic remains structurally unchanged except where this note documents a new
validation or capacity boundary.

## Capacity and dictionary-completeness fallback

The normal compressor still evaluates the top 200 estimated candidates per
greedy iteration for speed. Callers that know a fixed packed-byte reservation
pass it as `max_bytes`. If the fast result misses that reservation, the
compressor reruns the same deterministic greedy search with candidate pruning
disabled and keeps the smaller result.

Fixed-UI banks also trigger that exhaustive retry if the fast pass stops before
all 31 dictionary slots are populated. A result with fewer than 31 entries is
rejected for those banks rather than allowing the later fixed-table encoder to
scan beyond the generated dictionary.

Complete scenario insertion and footprint reporting add a second deterministic
optimization stage. They compare the valid greedy result with a bounded beam
search and a hill climb over optional dictionary-entry order. Required legacy
fixed-UI entries remain an immutable prefix, and tight banks receive a wider
beam. The smallest exact result wins, so optimization cannot make a bank larger
than the established greedy output. The release's joint 68-entry menu/dialogue
path uses exact greedy accounting because it already fits every bank and avoids
the much larger bounded-search cost at that dictionary width.

This remains bounded search, not a claim of globally optimal compression.
Direct compressor and property-test callers retain the fast greedy default;
the extra search cost is explicit in the complete build paths where recovered
bytes can improve the release candidate.

## Regression coverage

`work/tests/test_scenario_validation_hardening.py` uses synthetic banks and no
private ROM bytes. It verifies:

- cross-bank extraction does not carry English by coordinates;
- direct insertion rejects mismatched stable IDs;
- direct insertion rejects overwide English;
- an explicit fixed-UI dictionary floor extends the preserved tail boundary;
- fixed-UI dictionary generation fails closed before an incomplete dictionary
  can reach the UI patcher;
- fully translated fixed-UI insertion rejects `--no-compress` without writing
  an unsafe intermediate bank;
- direct scenario rebuilding rejects changed per-group record counts;
- direct scenario rebuilding rejects dictionaries larger than the selected
  decoder limit;
- the personality-question wrapping exception remains intact;
- a capacity miss triggers an unpruned compressor retry;
- beam search can beat a locally optimal greedy dictionary;
- dictionary reordering can reduce overlapping optional entries;
- optimized results expand exactly and preserve fixed-UI dictionary indices;
- raw and headered zero-side FDS images are rejected;
- negative packed-record decode limits are rejected; and
- the release dependency metadata keeps Pillow pinned to the approved version.

The existing public CI matrix continues to run Black, Ruff, pydocstyle, mypy,
public-tree validation, the fixture-free unit suite on Python 3.11/3.12, and
the Python 3.12 package/wheel smoke tests. Private integration tests remain a
separate local release gate because original ROM-derived fixtures are
intentionally absent from the repository.
