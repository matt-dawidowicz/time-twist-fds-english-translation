from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.release import (
    DEFAULT_KOUHEN_BASELINE,
    DEFAULT_RELEASE_TARGET,
    DEFAULT_SOURCE_LOCK,
    DEFAULT_TITLE_ASSET,
    DEFAULT_ZENPEN_BASELINE,
    ReleaseBuildError,
    build_release,
    validate_source_lock,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ReleaseBuildTests(unittest.TestCase):
    def test_source_lock_rejects_changed_hashes(self) -> None:
        payload = json.loads(DEFAULT_SOURCE_LOCK.read_text(encoding="utf-8"))
        first = next(iter(payload["files"].values()))
        first["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad_lock.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseBuildError, "unapproved"):
                validate_source_lock(path, project_root=PROJECT_ROOT)

    def test_complete_release_rebuild_matches_promoted_target(self) -> None:
        required = (
            DEFAULT_SOURCE_LOCK,
            DEFAULT_RELEASE_TARGET,
            DEFAULT_ZENPEN_BASELINE,
            DEFAULT_KOUHEN_BASELINE,
            DEFAULT_TITLE_ASSET,
        )
        self.assertTrue(all(path.is_file() for path in required))
        target = json.loads(DEFAULT_RELEASE_TARGET.read_text(encoding="utf-8"))
        expected = {
            name: record["sha256"]
            for name, record in target["outputs"].items()
        }
        with tempfile.TemporaryDirectory() as directory:
            manifest = build_release(
                Path(directory), project_root=PROJECT_ROOT
            )
            actual = {
                name: record["sha256"]
                for name, record in manifest["outputs"].items()
            }
            self.assertEqual(manifest["mode"], "verified")
            self.assertEqual(actual, expected)
            zenpen = (
                Path(directory) / manifest["outputs"]["zenpen"]["path"]
            ).read_bytes()
            kouhen = (
                Path(directory) / manifest["outputs"]["kouhen"]["path"]
            ).read_bytes()
            four_side = (
                Path(directory) / manifest["outputs"]["four_side"]["path"]
            ).read_bytes()
            self.assertEqual(four_side, zenpen + kouhen)


if __name__ == "__main__":
    unittest.main()
