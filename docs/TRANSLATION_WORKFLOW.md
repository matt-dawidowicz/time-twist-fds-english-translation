# Translation workflow

This document defines the editing workflow for scenario English. The current
release is frozen to v38: see [V38_CANONICAL_BUILD.md](V38_CANONICAL_BUILD.md).
New edits need a separately reviewed checkpoint; refreshing the lock cannot
bypass the 1,299-record regression gate.

## Canonical data model

Each scenario record has:

- a stable ID such as `TT3A/g2/r30`;
- decoded Japanese/source structure in `work/source_records/<BANK>.json`;
- exactly one current playable English entry in
  `work/translations/<BANK>.json`.

The canonical English entry includes both visible English and approved
`{CTRL:n}` tokens. There is no additional English source-selection step during
release construction.

## Editing a record

### 1. Establish the source meaning

Start from `work/source_records/<BANK>.json`. Confirm:

- the exact Japanese;
- speaker identity;
- surrounding records and scene context;
- any source control sequence;
- puzzle/UI role, if applicable.

Do not infer a speaker or referent from an older English rendering when the
Japanese or runtime context provides stronger evidence.

### 2. Write the natural English

Prefer the most natural source-faithful wording that the current engine can
actually present.

Do not intentionally preserve compressed, telegraphic English simply because a
shorter form was once convenient. If natural wording fails a real renderer,
control, or bank-capacity constraint, document that constraint explicitly.

### 3. Lay it out for the renderer

The dialogue box has four physical 24-column rows.

For ordinary dialogue:

- every recognized new speaker heading starts on a fresh row;
- each row within the same speaker turn is filled greedily;
- a line breaks only when the next complete word cannot fit;
- a speaker label is never split;
- semantic waits/re-entry controls remain at their approved dramatic boundary.

Structural exceptions:

- scenario quiz prompts share space with answer-selection UI;
- identity/info cards use row placement as field structure.

These records keep their audited structural geometry.

### 4. Validate

Run:

```powershell
python work/tools/materialize_production_translations.py \
  --repo-root . --output work/build/production_translations
python work/run_tests.py unit
```

The materializer does **not** rewrite or choose wording. It validates the
canonical maps and copies them into a deterministic staging directory.

For a release candidate:

```powershell
time-twist release-lock --update
time-twist release-build --candidate --output-dir build/candidate
```

For v38 these commands reject any changed record. For a future candidate,
review and update the checkpoint/compiler contract explicitly, then playtest
the affected scene.

## Control-code policy

`CTRL:0` and `CTRL:4` are commonly row/scroll geometry. Their placement in
the canonical maps represents the current approved English layout.

`CTRL:1`, `CTRL:2`, `CTRL:3`, and `CTRL:6` may carry timing, page,
re-entry, reveal, or speaker-transition semantics. Do not move them solely to
make text fit. Use runtime evidence when a semantic boundary is uncertain.

`CTRL:5` is the packed record separator and is not translated text.

See [ENGLISH_PAGINATION_POLICY.md](ENGLISH_PAGINATION_POLICY.md) and
[REVERSE_ENGINEERING_GUIDE.md](REVERSE_ENGINEERING_GUIDE.md).

## Fixed-address English

Scenario maps do not own every English string in the game. In the current v38
release, fixed menu and runtime changes come from the frozen compiler bundle,
and font/title payloads come from the hash-locked v25 baseline. The following
modules are historical engineering tools, not active v38 release inputs.

- fixed menu/table wording: `work/time_twist/ui_fixed_tables.py`
- fixed interface patches: `work/time_twist/ui.py`
- font transformations: `work/time_twist/font.py`
- title transformations: `work/time_twist/title.py`

Changes there must satisfy the corresponding fixed-slot/runtime tests.

## Review checklist

Before accepting a scenario change, verify:

- [ ] Japanese meaning preserved
- [ ] speaker/referent verified
- [ ] terminology consistent
- [ ] no unnecessary compression of English
- [ ] every new speaker starts on a fresh row
- [ ] ordinary rows are maximally filled
- [ ] no speaker label is split
- [ ] semantic controls remain defensible
- [ ] quiz/info-card geometry preserved where applicable
- [ ] bank/runtime validators pass
- [ ] changed scene playtested

## Historical material

Historical engineering records may explain why an older design or wording once
existed, but they are not translation source. Any accepted change is made
directly to the current canonical bank map.
