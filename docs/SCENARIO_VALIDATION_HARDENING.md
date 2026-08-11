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

The large recovered parsers/builders remain semantically unchanged in private
`_core` modules. The copied release implementation received only the
repository-standard Black formatting required by CI. Small public facades add
the new policy checks around those cores, keeping the reverse-engineered binary
implementation easy to compare with its previous version.

## Capacity-only compressor fallback

The normal compressor still evaluates the top 200 estimated candidates per
greedy iteration for speed. Callers that know a fixed packed-byte reservation
now pass it as `max_bytes`. If the fast result misses that reservation, the
compressor reruns the same deterministic greedy search with candidate pruning
disabled and keeps the smaller result.

This is a bounded robustness fallback, not a claim of globally optimal
compression. Successful fast-path builds are unchanged, and the extra search
cost is paid only when the native reservation would otherwise be exceeded.

## Regression coverage

`work/tests/test_scenario_validation_hardening.py` uses synthetic banks and no
private ROM bytes. It verifies:

- cross-bank extraction does not carry English by coordinates;
- direct insertion rejects mismatched stable IDs;
- direct insertion rejects overwide English;
- an explicit fixed-UI dictionary floor extends the preserved tail boundary;
- the personality-question wrapping exception remains intact; and
- a capacity miss triggers an unpruned compressor retry.

The existing public CI matrix continues to run Black, Ruff, pydocstyle, mypy,
public-tree validation, unit tests on Python 3.11/3.12, and the Python 3.12
package/wheel smoke tests. Private integration tests remain a separate local
release gate because original ROM-derived fixtures are intentionally absent
from the repository.
