"""Private-overlay integration tests for current source-lock, candidate, and release-promotion safeguards."""

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
    """Group current regression tests by project contract."""

    def test_source_lock_rejects_changed_hashes(self) -> None:
        """Verify the current contract described by this regression test."""
        payload = json.loads(DEFAULT_SOURCE_LOCK.read_text(encoding="utf-8"))
        first = next(iter(payload["files"].values()))
        first["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad_lock.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseBuildError, "unapproved"):
                validate_source_lock(path, project_root=PROJECT_ROOT)

    def test_complete_candidate_rebuild_is_byte_deterministic(self) -> None:
        """Verify the current contract described by this regression test."""
        required = (
            DEFAULT_SOURCE_LOCK,
            DEFAULT_ZENPEN_BASELINE,
            DEFAULT_KOUHEN_BASELINE,
            DEFAULT_TITLE_ASSET,
        )
        self.assertTrue(all(path.is_file() for path in required))
        with tempfile.TemporaryDirectory() as directory:
            first_directory = Path(directory) / "first"
            second_directory = Path(directory) / "second"
            first = build_release(
                first_directory,
                project_root=PROJECT_ROOT,
                verify_target=False,
            )
            second = build_release(
                second_directory,
                project_root=PROJECT_ROOT,
                verify_target=False,
            )
            self.assertEqual(first, second)
            self.assertEqual(first["mode"], "candidate")
            self.assertEqual(
                (first_directory / "release_manifest.json").read_bytes(),
                (second_directory / "release_manifest.json").read_bytes(),
            )
            for record in first["outputs"].values():
                filename = record["path"]
                self.assertEqual(
                    (first_directory / filename).read_bytes(),
                    (second_directory / filename).read_bytes(),
                )
            zenpen = (
                first_directory / first["outputs"]["zenpen"]["path"]
            ).read_bytes()
            kouhen = (
                first_directory / first["outputs"]["kouhen"]["path"]
            ).read_bytes()
            four_side = (
                first_directory / first["outputs"]["four_side"]["path"]
            ).read_bytes()
            self.assertEqual(four_side, zenpen + kouhen)

    def test_strict_release_rejects_unpromoted_checkout(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertFalse(DEFAULT_RELEASE_TARGET.exists())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "strict"
            with self.assertRaisesRegex(
                ReleaseBuildError, "release target is missing.*release-promote"
            ):
                build_release(output, project_root=PROJECT_ROOT)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
