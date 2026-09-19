# Contributing translation

This guide is for editors and reviewers changing scenario English without
editing ROM bytes directly.

## One scenario-English source

Every playable scenario record has exactly one current English source:

```text
work/translations/<BANK>.json
```

Edit that record directly. There is no secondary English layer that can replace
it later.

Use `work/source_records/<BANK>.json` to inspect the decoded Japanese and
stable record ID. Source records are evidence; they are not an alternate
English translation source.

Fixed menus and other non-scenario UI use
`work/time_twist/ui_fixed_tables.py` and `work/time_twist/ui.py`.

## Required translation standard

For every edit:

1. Preserve the Japanese meaning, referents, speaker identity, and scene logic.
2. Prefer natural contemporary English over literal or compressed fragments.
3. Do not weaken, embellish, or sanitize source content.
4. Keep established names and terminology consistent.
5. Do not silently shorten a line merely to make it easier to pack. If the
   preferred wording cannot be represented safely, document the exact engine
   limitation and address that limitation deliberately.

## Dialogue layout

The canonical JSON stores the approved control layout together with the words.

- Every recognized new speaker heading starts on a **fresh row**.
- Fill ordinary rows greedily to the 24-column limit within that speaker turn.
- Never split a speaker heading.
- Do not add short aesthetic lines when the next word still fits.
- Preserve intentional waits, reveals, and re-entry controls.
- Quiz prompts and identity/info cards are structural UI and may intentionally
  retain non-prose row geometry.

See [docs/ENGLISH_PAGINATION_POLICY.md](docs/ENGLISH_PAGINATION_POLICY.md).

## Safe edit workflow

1. Locate the record ID in `work/source_records/<BANK>.json`.
2. Read the Japanese source and surrounding records.
3. Edit only the corresponding entry in `work/translations/<BANK>.json`.
4. If control placement must change, verify why the control is presentation
   geometry versus a semantic/timing boundary.
5. Run:

   ```powershell
   python -m pip install -e ".[dev]"
   python work/tools/materialize_production_translations.py \
     --repo-root . --output work/build/production_translations
   python work/run_tests.py unit
   ```

6. Build a candidate and playtest the changed scene before promotion.

In a pull request, name every changed record ID and explain the source meaning,
wording choice, control/layout change, and tests performed.

## Do not do these things

- Do not edit generated FDS images, rebuilt banks, save states, or emulator
  memory as translation source.
- Do not introduce another English fallback, review, or override directory.
- Do not copy an older English string from Git history into the canonical map
  merely because it once fit.
- Do not change decoded Japanese to make an English decision look correct.
- Do not move a semantic control across a speaker turn just to gain space.
- Do not expand into unknown RAM or storage without proving the relevant engine
  boundary.
- Do not commit retail images or private fixtures.

Historical engineering records are for explanation only. Current accepted
English always lives in `work/translations/<BANK>.json`.

## More context

- [Translation workflow](docs/TRANSLATION_WORKFLOW.md)
- [English pagination policy](docs/ENGLISH_PAGINATION_POLICY.md)
- [Scenario-bank format](docs/FORMATS.md#scenario-bank-layout)
- [Project architecture](docs/ARCHITECTURE.md)
- [General contribution rules](CONTRIBUTING.md)
