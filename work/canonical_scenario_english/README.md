# Canonical scenario English

This directory is the sole intended playable-English source for scenario text after the v17 cleanup migration.

## Invariant

Build/release code must consume the canonical scenario-English bank files from this directory and must not obtain playable English from legacy translation, review, workbook, or override layers.

The canonical corpus is anchored to ROM SHA-256:

`f269d129ca1ad0db6595566476877840a37275bfa9407e6dad62b1435fe93f0d`

It contains 1,299 scenario records across 13 banks. See `MANIFEST.json` for per-bank record counts and SHA-256 values.

## Legacy material

Older English wording may be mentioned only in historical/audit documentation. It must not be imported by build code or stored as an alternate playable source.

During the migration, the following active paths are considered legacy and are scheduled for removal or conversion to source/control metadata only:

- `work/translations/*.json`
- `work/production_overrides/*.json`
- `review/production_retranslation/*.json` as build inputs
- `current_english` and `patch_safe_english_translation` fields in generated workbook data
- manual/alternate English literals embedded in workbook-generation code

No destructive deletion should occur until the complete canonical bank set is committed and a rebuild proves equivalence to the v17 scenario corpus.
