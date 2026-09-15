"""Keep the checked-in portion of the release source lock synchronized."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from time_twist.release import ReleasePaths, authoritative_source_paths
from time_twist.title import DEFAULT_SUBTITLE

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_LOCK = PROJECT_ROOT / "work" / "release_sources.json"
INTEGRATION_FIXTURES = PROJECT_ROOT / "work" / "integration_fixtures.json"
PRIVATE_RETAIL_BASELINES = {
    "work/baseline/time_twist_zenpen_japan.fds",
    "work/baseline/time_twist_kouhen_japan.fds",
}


def _locked_bytes(path: Path, normalization: str) -> bytes:
    """Read a public release input using the source-lock normalization contract."""
    data = path.read_bytes()
    if normalization == "raw":
        return data
    if normalization == "lf":
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    raise AssertionError(
        f"unsupported source-lock normalization: {normalization!r}"
    )


class CurrentPublicSourceLockTests(unittest.TestCase):
    """Verify source-lock freshness without requiring private retail ROMs."""

    def test_checked_in_release_sources_match_lock(self) -> None:
        """Fail CI when an authoritative release source drifts from its lock."""
        payload = json.loads(SOURCE_LOCK.read_text(encoding="utf-8"))
        files = payload["files"]
        paths = ReleasePaths.from_project_root(PROJECT_ROOT)
        authoritative = {
            path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
            for path in authoritative_source_paths(paths)
        }
        fixtures = json.loads(
            INTEGRATION_FIXTURES.read_text(encoding="utf-8")
        )["files"]

        self.assertEqual(payload["subtitle"], DEFAULT_SUBTITLE)
        self.assertEqual(set(files), authoritative)

        for relative in sorted(authoritative):
            record = files[relative]
            if relative in PRIVATE_RETAIL_BASELINES:
                fixture = fixtures[relative]
                self.assertEqual(record["normalization"], "raw")
                self.assertEqual(record["bytes"], fixture["bytes"])
                self.assertEqual(record["sha256"], fixture["sha256"])
                continue

            path = PROJECT_ROOT / relative
            self.assertTrue(
                path.is_file(), f"locked public source is missing: {relative}"
            )
            data = _locked_bytes(path, record["normalization"])
            digest = hashlib.sha256(data).hexdigest().upper()

            self.assertEqual(
                len(data),
                record["bytes"],
                f"source-lock byte count is stale: {relative}",
            )
            self.assertEqual(
                digest,
                record["sha256"],
                f"source-lock SHA-256 is stale: {relative}",
            )


if __name__ == "__main__":
    unittest.main()
