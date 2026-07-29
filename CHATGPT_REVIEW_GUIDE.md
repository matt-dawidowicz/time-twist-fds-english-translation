# Time Twist FDS English Translation: Review Bundle

This is the cleaned public source bundle. It contains project code,
translation data, title reference art, documentation, fixture-free tests,
ROM-integration test code, and generated review workbooks. It does **not**
contain original/patched FDS images, extracted ROM banks, emulator packages,
settings, or memory dumps.

## Start here

1. Read `README.md` and `docs/DEVELOPMENT.md`.
2. Treat `work/translations/` plus the fixed UI/font/title code as the playable
   source authority.
3. Treat workbook natural translations as editorial context; its patch-safe
   field is generated from the playable sources.
4. Run `python work/run_tests.py unit` in the public bundle.
5. Maintainers may overlay separately held private fixtures and run
   `python work/run_tests.py all`.

## Reproducible release boundary

- `work/release_sources.json` locks approved baselines, playable translation
  maps, and the title asset.
- `work/release_target.json` records the promoted output sizes and hashes.
- `release-build --candidate` creates an unapproved review build.
- `release-promote` ties reviewed candidate outputs to the active source lock.
- strict `release-build` reproduces and verifies the promoted target.

The currently promoted playtest hashes are:

| Image | SHA-256 |
| --- | --- |
| Zenpen | `60F646296635B13391A8666BA99F8B025D4A75865BD25DFD830F540BBE51F3FE` |
| Kouhen | `18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421` |
| Four-side | `21A48E6F0B955E7E970E3AAF86F147B366BB5AC02AFCEB681169ADD17E7C657F` |

Static reproducibility is not runtime proof. Preserve packed-text controls,
record IDs/order, fixed addresses, bank footprints, and source guards, and
report visual/gameplay claims with screen or save-point evidence.
