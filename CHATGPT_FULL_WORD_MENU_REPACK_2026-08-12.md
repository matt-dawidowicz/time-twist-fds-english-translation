# ChatGPT full-word menu repacking pass — 2026-08-12

This source tree follows the retry-message readability fix. It reserves additional bank dictionary entries in `work/time_twist/project.py` to fit more full menu/choice labels while preserving bank memory footprints and the native 31-entry dictionary format.

Result: 405 / 721 fixed menu labels render as full words in the rebuilt candidate, up from 374 / 721. There are no regressions and no label mismatches.

See `docs/FULL_WORD_MENU_REPACKING_RESULTS.md` for details and CSV report paths.
