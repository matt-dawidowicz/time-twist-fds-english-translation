# Non-UI maintenance: atomic release publication failure handling

This note records the first focused follow-up to the 2026-10-13 performance
audit. It describes an actual bug found in the original release publisher,
the minimal fix, and its safety boundary. It does not replace the maintained
[release process](../MAINTAINER_RELEASE_PROCESS.md).

## Problem

`work/time_twist/release.py::_atomic_publish_file` stages a file in its
**destination directory** to preserve Windows ACL inheritance and uses
`os.replace` for the final atomic replacement. Before this change, the
`try/except` cleanup protected only `chmod` and `os.replace`.

A failure during `shutil.copyfileobj`, `flush`, or `fsync` occurred
**before** the cleanup handler began. This could leave a partial hidden
`.<destination>.*.tmp` file in the publication directory. Although the
existing target was not replaced, the abandoned file was unnecessary debris
and could confuse future operations or expose incomplete output.

## Correction

The entire staged-write and replacement sequence is now within the same
exception-handling boundary. A failed copy, flush, fsync, chmod, or replace
removes its temporary file and re-raises the original exception. Success
still creates the temporary file inside the destination directory, flushes
and fsyncs it, applies the source mode, and atomically replaces the target.
The preserved `_publish_staged_release` workflow continues to invalidate a
previous release manifest before publishing new output files.

## Regression and scope

`work/tests/test_release_publication_safety.py` injects a partial-write
failure and an fsync failure, then proves that the original destination bytes
remain untouched and that no temporary files are left behind. Existing
`test_release_unit.py` tests independently cover correct destination-local
replacement and manifest invalidation.

**No player-facing UI code, title graphics, game text, FDS formats, BPS
format, or ROM compiler algorithms are changed in this phase.** Canonical
English v1.1 hashes remain the release-equivalence contract; the full private
v25 rebuild and emulator gates are still required for a new game release.

This is a correctness and maintenance cleanup rather than a performance
optimization. An observable change is deliberately limited to removing
orphaned temporary files after an operating-system write failure.
