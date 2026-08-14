"""Fixture-free regression tests for release-integrity hardening."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.release import (
    BUILD_ENVIRONMENT_SCHEMA,
    RELEASE_FILENAMES,
    RELEASE_MANIFEST_SCHEMA,
    ReleaseBuildError,
    build_code_provenance,
    build_environment_provenance,
    promote_release_target,
    sha256_bytes,
    source_lock_sha256,
    validate_release_manifest_metadata,
    write_source_lock,
)


def make_synthetic_project(root: Path) -> Path:
    """Create the minimal public project layout used by promotion tests."""
    work = root / "work"
    translations = work / "translations"
    title_assets = work / "title_assets"
    baseline = work / "baseline"
    code = work / "time_twist"
    translations.mkdir(parents=True)
    title_assets.mkdir()
    baseline.mkdir()
    code.mkdir()
    (root / "pyproject.toml").write_text(
        "[project]\nname='test'\n", encoding="utf-8"
    )
    (code / "__init__.py").write_text('"""Synthetic package."""\n')
    for bank in KNOWN_SCENARIO_BANKS:
        (translations / f"{bank}.json").write_text("{}\n", encoding="utf-8")
    (title_assets / "Time Twist approved native title.png").write_bytes(
        b"title"
    )
    (baseline / "time_twist_zenpen_japan.fds").write_bytes(b"zenpen")
    (baseline / "time_twist_kouhen_japan.fds").write_bytes(b"kouhen")
    return root


def valid_manifest(root: Path, candidate: Path) -> dict[str, object]:
    """Build a structurally complete synthetic candidate manifest."""
    lock = root / "work" / "release_sources.json"
    outputs: dict[str, dict[str, object]] = {}
    for name, filename in RELEASE_FILENAMES.items():
        data = f"{name} candidate".encode("ascii")
        (candidate / filename).write_bytes(data)
        outputs[name] = {
            "path": filename,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
        }
    scenario_banks = {
        bank: {
            "records": 1,
            "dictionary_entries": 0,
            "packed_bytes": 1,
            "capacity_bytes": 2,
            "remaining_bytes": 1,
            "sha256": "A" * 64,
        }
        for bank in KNOWN_SCENARIO_BANKS
    }
    return {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "mode": "candidate",
        "project_source_lock": "work/release_sources.json",
        "source_lock_sha256": source_lock_sha256(lock),
        "code_provenance": build_code_provenance(
            root, executing_code_root=root / "work" / "time_twist"
        ),
        "build_environment": build_environment_provenance(),
        "release_target": None,
        "release_target_sha256": None,
        "release_id": None,
        "subtitle": "On the Outskirts of History...",
        "scenario_banks": scenario_banks,
        "component_sha256": {
            "NOV2": "B" * 64,
            "NOV4": "C" * 64,
            "SON-KOUH": "D" * 64,
        },
        "outputs": outputs,
    }


def write_manifest(path: Path, payload: dict[str, object]) -> None:
    """Write a deterministic test candidate manifest."""
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class ReleaseIntegrityPolishTests(unittest.TestCase):
    """Exercise promotion and manifest integrity invariants."""

    def test_build_environment_records_python_and_pillow(self) -> None:
        """Verify the current contract described by this regression test."""
        environment = build_environment_provenance()
        self.assertEqual(environment["schema"], BUILD_ENVIRONMENT_SCHEMA)
        self.assertTrue(environment["python_implementation"])
        self.assertTrue(environment["python_version"])
        self.assertTrue(environment["pillow_version"])

    def test_manifest_validator_rejects_missing_audit_fields(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            validate_release_manifest_metadata(manifest)
            del manifest["component_sha256"]
            with self.assertRaisesRegex(
                ReleaseBuildError, "fields must be exactly"
            ):
                validate_release_manifest_metadata(manifest)

    def test_promotion_rejects_manifest_subtitle_not_in_source_lock(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            manifest["subtitle"] = "Edited after candidate build"
            manifest_path = candidate / "release_manifest.json"
            write_manifest(manifest_path, manifest)
            code_root = root / "work" / "time_twist"
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                self.assertRaisesRegex(
                    ReleaseBuildError, "subtitle does not match"
                ),
            ):
                promote_release_target(manifest_path, project_root=root)

    def test_promotion_rejects_candidate_not_matching_fresh_rebuild(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            manifest_path = candidate / "release_manifest.json"
            write_manifest(manifest_path, manifest)
            rebuilt = copy.deepcopy(manifest)
            rebuilt_outputs = copy.deepcopy(rebuilt["outputs"])
            rebuilt_outputs["zenpen"]["sha256"] = "F" * 64
            rebuilt["outputs"] = rebuilt_outputs
            code_root = root / "work" / "time_twist"
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                mock.patch(
                    "time_twist.release.build_release", return_value=rebuilt
                ) as rebuild,
                self.assertRaisesRegex(
                    ReleaseBuildError,
                    "outputs does not match a fresh canonical",
                ),
            ):
                promote_release_target(manifest_path, project_root=root)
            rebuild.assert_called_once()
            self.assertFalse((root / "work" / "release_target.json").exists())

    def test_promotion_accepts_candidate_matching_fresh_rebuild(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            manifest_path = candidate / "release_manifest.json"
            write_manifest(manifest_path, manifest)
            code_root = root / "work" / "time_twist"
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                mock.patch(
                    "time_twist.release.build_release", return_value=manifest
                ),
            ):
                target = promote_release_target(
                    manifest_path,
                    project_root=root,
                    release_id="reviewed",
                )
            self.assertEqual(target["release_id"], "reviewed")
            self.assertTrue((root / "work" / "release_target.json").is_file())

    def test_promotion_rechecks_candidate_outputs_before_target_write(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            manifest_path = candidate / "release_manifest.json"
            write_manifest(manifest_path, manifest)
            code_root = root / "work" / "time_twist"
            real_validator = __import__(
                "time_twist.release", fromlist=["_validate_candidate_outputs"]
            )._validate_candidate_outputs
            calls = 0

            def mutate_after_first_check(path: Path, records: object) -> None:
                """Provide a deterministic helper for the current contract tests."""
                nonlocal calls
                calls += 1
                real_validator(path, records)
                if calls == 1:
                    filename = RELEASE_FILENAMES["zenpen"]
                    (candidate / filename).write_bytes(b"tampered")

            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                mock.patch(
                    "time_twist.release.build_release", return_value=manifest
                ),
                mock.patch(
                    "time_twist.release._validate_candidate_outputs",
                    side_effect=mutate_after_first_check,
                ),
                self.assertRaisesRegex(
                    ReleaseBuildError, "candidate output .* changed"
                ),
            ):
                promote_release_target(manifest_path, project_root=root)
            self.assertEqual(calls, 2)
            self.assertFalse((root / "work" / "release_target.json").exists())

    def test_source_lock_update_rejects_approved_source_destination(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            baseline = (
                root / "work" / "baseline" / "time_twist_zenpen_japan.fds"
            )
            original = baseline.read_bytes()
            with self.assertRaisesRegex(
                ReleaseBuildError, "collides with protected"
            ):
                write_source_lock(baseline, project_root=root)
            self.assertEqual(baseline.read_bytes(), original)

    def test_promotion_target_rejects_candidate_manifest_destination(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            manifest = valid_manifest(root, candidate)
            manifest_path = candidate / "release_manifest.json"
            write_manifest(manifest_path, manifest)
            original = manifest_path.read_bytes()
            code_root = root / "work" / "time_twist"
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                self.assertRaisesRegex(
                    ReleaseBuildError, "candidate manifest"
                ),
            ):
                promote_release_target(
                    manifest_path,
                    target_path=manifest_path,
                    project_root=root,
                )
            self.assertEqual(manifest_path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
