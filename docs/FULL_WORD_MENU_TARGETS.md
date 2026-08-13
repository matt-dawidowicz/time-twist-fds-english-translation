# Full-word menu/choice target map

This experimental branch makes the target explicit: every fixed menu/choice
record should be a readable English word or phrase, not a compressed-looking
abbreviation.

The active constants in `work/time_twist/ui.py` now contain the full-word target
text for all fixed menu tables. This does **not** mean the current compression
and fixed-slot layout can already build a valid ROM with every target. It means
the compression/repacking branch has a complete destination to optimize toward.

## Scope

- Fixed menu/choice records covered: **721**
- Records changed from the previous experimental branch: **370**
- Previously context-sensitive records reviewed against the fixed-table source:
  **31**. See `docs/FULL_WORD_MENU_REVIEW_DECISIONS.md`.

See `docs/full_word_menu_targets_all_records.csv` for the complete per-record
map.

## Important build note

The target map is intentionally broader than a single FDS candidate. The
current candidate keeps original fixed-record addresses and uses dictionary
references where they fit; labels that cannot coexist with the bank's dialogue
compression remain explicit blockers rather than being called complete.

See `docs/FULL_WORD_MENU_CANDIDATE_RESULTS.md` for the verified candidate
counts, reports, and the next technical boundary.

## Policy

- Full words/phrases are the default.
- Abbreviations are not final polish targets unless they are true acronyms such
  as `VCR` or intentionally numeric puzzle controls.
- Context-sensitive targets are kept in the CSV with `needs human review` so
  they can be checked against screenshots or original Japanese context before
  final release.
