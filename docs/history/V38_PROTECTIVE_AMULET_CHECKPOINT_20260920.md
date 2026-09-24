# v38 Gypsy Amulet checkpoint — 2026-09-20

This checkpoint records the user-approved Time Twist translation build that is now the baseline for subsequent work.

## Canonical binary

- Uploaded filename: `Time-Twist-v38-PROTECTIVE-AMULET-CANDIDATE(1).fds`
- Size: 262000 bytes
- SHA-256: `62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400`
- FDS disk label observed from the image header: `FMC-TT1`

The ROM/FDS image itself is not committed to this repository. The hash above is the identity of the approved checkpoint.

## Translation decisions carried into this checkpoint

These decisions supersede stale/legacy English layers and should be preserved unless explicitly revised later:

- Treat the newest organic retranslation as authoritative; do not allow older translation layers to leak back into production.
- Speaker headings begin on a new line.
- Fill dialogue lines naturally within the expanded text-window capacity instead of preserving obsolete tight-space compromises.
- American punctuation is the default; punctuation around quotation marks follows the approved context-specific wording from the v38 pass.
- Preserve `Maradul Barao Garadura` as the approved incantation wording where that source variant is intended.
- The museum item had previously been modernized to `Romani Talisman`, but the v37 source-fidelity pass deliberately restored the source-explicit ethnonym as **Gypsy Talisman**. The v38 terminology pass changed only `Talisman` to the more accurate **Amulet**, producing the approved **Gypsy Amulet** wording. Frankie's later reference is correspondingly **Gypsy amulet**.
- The Jeanne/Joan naming pass and the broader dialogue/menu/disc audit from the September 20 review are part of the v38 baseline; source text should be reconciled to the binary rather than regenerated from pre-v38 review tables.
- Continue to exclude obsolete translation artifacts from production. Historical references may remain only in history/documentation.

## Source-reconciliation rule

Until every v38 string has been re-materialized into the canonical source tree, the binary hash above is the tie-breaker for disputes about whether a later source change is a regression.

Do not rebuild from an older review workbook, production override, or legacy translation layer and call it v38-equivalent unless its output is verified against this checkpoint.
