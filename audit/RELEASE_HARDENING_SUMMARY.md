# Time Twist release hardening — final summary

## Result

The translation project is now split into a clean public source package and a
separate private ROM-derived fixture overlay. The packaged public source plus
the packaged private overlay passes the complete supported test matrix:

- **38 public fixture-free tests passed**
- **67 private integration/release tests passed**
- **105 total tests passed**
- **0 skipped tests**

The final verification extracted the actual public ZIP, overlaid the actual
private fixture ZIP, and ran all tests from those packaged files.

## Problems fixed

### Public/private distribution

- Removed FDS images, extracted/rebuilt banks, dumps, emulator archives,
  machine-local settings, caches, and generated build directories from the
  public tree.
- Created a separate, hash-validated private fixture overlay.
- Added `work/tools/check_public_tree.py` and CI coverage to reject prohibited
  files, build debris, and personal absolute paths.
- Added unit tests for the public-tree policy.
- Verified the public source ZIP contains **146 files** and **zero forbidden ROM,
  bank, dump, or cache members**.

### Release workflow

- Added project-root discovery and `--project-root` support so an installed
  code-only wheel can drive an external checkout.
- Fixed defaults so release commands work from the repository root or `work/`.
- Added source locking for both Japanese baselines, the title asset, and all 13
  playable scenario maps.
- Replaced hardcoded output hashes with a versioned release target.
- Added candidate builds and explicit promotion:
  - `release-build --candidate`
  - `release-promote`
  - strict verified `release-build`
- Proved an intentional real translation edit can refresh the source lock,
  produce different hashes, be promoted, and then pass a strict rebuild.
- Made release publication transactional: target failure does not leave new ROM
  files in the requested output directory.
- Fixed external lock handling.
- Converted expected CLI failures to concise `time-twist: error:` messages with
  no traceback.

### Tests and clean-room behavior

- Split public unit tests from private ROM-derived integration tests.
- Removed the four obsolete skipped historical tests.
- Made the test runner reject all skips.
- Added a private fixture manifest and validate every fixture before discovery.
- Fixed a final clean-room issue where launching tests from another checkout's
  working directory could select the wrong release root.
- Removed remaining test paths that depended on the caller's current directory.

### Binary and translation safeguards

- Reject duplicate scenario group pointers.
- Reject dictionary reference zero.
- Verify the supported NOV4 source before applying the font patch.
- Replace production `assert` statements with explicit errors.
- Validate scenario-bank filename inference.
- Preserve deterministic compressor output while reducing full-build time to
  roughly 19 seconds in this environment.
- Synchronize all workbook patch-safe scenario rows with the playable JSON maps.
- Synchronize fixed/graphics patch-safe rows with installed patch definitions.
- Preserve alternative editorial wording separately instead of silently
  changing playable text.
- Remove personal workstation paths from workbook generation and metadata.

### Packaging

- Added `pyproject.toml`, console-script installation, dependency metadata, and
  public CI wheel checks.
- Built a code-only wheel with **19 members** and no translation maps, title
  assets, source locks, ROMs, banks, or dumps.
- Installed and smoke-tested the wheel from outside the source checkout with
  Pillow 12.2.0 available.
- Confirmed a missing-baseline build fails cleanly with exit code 2 and creates
  no output directory.

## Verified release hashes

| Image | Bytes | SHA-256 |
| --- | ---: | --- |
| Zenpen | 131,000 | `60F646296635B13391A8666BA99F8B025D4A75865BD25DFD830F540BBE51F3FE` |
| Kouhen | 131,000 | `18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421` |
| Combined four-side | 262,000 | `21A48E6F0B955E7E970E3AAF86F147B366BB5AC02AFCEB681169ADD17E7C657F` |

## Distribution artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| Public source ZIP | `CD5E9064BBE7F499DF10BAE1FA0A6B14EF14938D166318FCFE88476CC6D9E006` |
| Private fixture overlay ZIP | `DE6E5539137B39C8950B07D9A972D4FF4E656A2C4E4CEB0DB3A8CB1ECB3FE917` |
| Code-only wheel | `4F384D1C7F9813456C28A08498B4DB7245434A327609CFED6A8494C3602C0A60` |
| Verified release ZIP | `7B5FD0C2F5AFA09986ACFE55A1B7203659A31572D473B9946A1F3ED9661A18B2` |

## Remaining release requirement

Static validation, deterministic reconstruction, and exact hash tests are now
strong. The remaining substantive task is a complete emulator playthrough of
both halves, including obscure branches, side changes, save/load behavior,
line wrapping, and visual inspection of every revised glyph and interface.
