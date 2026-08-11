from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from time_twist.cli import build_parser, main
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.release import (
    RELEASE_FILENAMES,
    RELEASE_MANIFEST_SCHEMA,
    RELEASE_TARGET_SCHEMA,
    ReleaseBuildError,
    _publish_staged_release,
    build_code_provenance,
    discover_project_root,
    display_path,
    promote_release_target,
    release_code_tree_sha256,
    sha256_bytes,
    sha256_file,
    validate_release_target,
    write_source_lock,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_synthetic_project(root: Path) -> Path:
    """Create the public source inputs needed by release unit tests."""
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


class ReleaseConfigurationUnitTests(unittest.TestCase):
    def test_publisher_replaces_from_destination_local_temporary_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "private-stage"
            output = root / "published"
            staging.mkdir()
            payloads = {
                RELEASE_FILENAMES[name]: f"{name} payload".encode("ascii")
                for name in ("zenpen", "kouhen", "four_side")
            }
            payloads["release_manifest.json"] = b"{}\n"
            for filename, payload in payloads.items():
                (staging / filename).write_bytes(payload)

            replacements: list[tuple[Path, Path]] = []
            real_replace = os.replace

            def recording_replace(
                source: str | Path, destination: str | Path
            ) -> None:
                replacements.append((Path(source), Path(destination)))
                real_replace(source, destination)

            with mock.patch(
                "time_twist.release.os.replace",
                side_effect=recording_replace,
            ):
                _publish_staged_release(staging, output)

            self.assertEqual(len(replacements), len(payloads))
            self.assertTrue(
                all(source.parent == output for source, _ in replacements)
            )
            self.assertTrue(
                all(
                    destination.parent == output
                    for _, destination in replacements
                )
            )
            for filename, payload in payloads.items():
                self.assertEqual((output / filename).read_bytes(), payload)
            self.assertFalse(any(output.glob(".*.tmp")))

    def test_project_root_is_discovered_from_nested_directory(self) -> None:
        self.assertEqual(
            discover_project_root(start=PROJECT_ROOT / "work" / "tests"),
            PROJECT_ROOT,
        )

    def test_explicit_non_project_is_rejected(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(ReleaseBuildError, "not a Time Twist"),
        ):
            discover_project_root(Path(directory))

    def test_external_paths_are_manifest_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            external = Path(directory) / "lock.json"
            self.assertEqual(
                display_path(external, PROJECT_ROOT),
                external.resolve().as_posix(),
            )

    def test_release_target_is_tied_to_source_lock(self) -> None:
        payload = {
            "schema": RELEASE_TARGET_SCHEMA,
            "release_id": "test",
            "source_lock_sha256": "A" * 64,
            "code_provenance": build_code_provenance(PROJECT_ROOT),
            "outputs": {
                name: {"bytes": 1, "sha256": "B" * 64}
                for name in ("zenpen", "kouhen", "four_side")
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                ReleaseBuildError, "different source lock"
            ):
                validate_release_target(
                    path,
                    source_lock_sha256="C" * 64,
                    project_root=PROJECT_ROOT,
                )

    def test_code_tree_hash_is_path_order_and_line_ending_independent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first"
            second = Path(directory) / "second"
            for root in (first, second):
                (root / "work" / "time_twist").mkdir(parents=True)
            (first / "work" / "time_twist" / "a.py").write_bytes(
                b"value = 1\n"
            )
            (first / "work" / "time_twist" / "b.py").write_bytes(
                b"other = 2\n"
            )
            (second / "work" / "time_twist" / "b.py").write_bytes(
                b"other = 2\r\n"
            )
            (second / "work" / "time_twist" / "a.py").write_bytes(
                b"value = 1\r\n"
            )
            self.assertEqual(
                release_code_tree_sha256(first),
                release_code_tree_sha256(second),
            )

    def test_code_tree_hash_binds_normalized_path_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "work" / "time_twist"
            code.mkdir(parents=True)
            source = code / "a.py"
            source.write_bytes(b"value = 1\n")
            original = release_code_tree_sha256(root)
            source.rename(code / "renamed.py")
            self.assertNotEqual(original, release_code_tree_sha256(root))

    def test_code_provenance_does_not_require_git(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code = root / "work" / "time_twist"
            code.mkdir(parents=True)
            (code / "module.py").write_bytes(b"value = 1\n")
            with mock.patch(
                "time_twist.release.subprocess.run",
                side_effect=FileNotFoundError,
            ):
                provenance = build_code_provenance(root)
            self.assertIsNone(provenance["git_commit"])
            self.assertIsNone(provenance["git_dirty"])
            self.assertEqual(provenance["file_count"], 1)
            self.assertEqual(
                provenance["tree_sha256"], release_code_tree_sha256(root)
            )

    def test_release_target_rejects_different_code_tree(self) -> None:
        provenance = build_code_provenance(PROJECT_ROOT)
        provenance["tree_sha256"] = "0" * 64
        payload = {
            "schema": RELEASE_TARGET_SCHEMA,
            "release_id": "test",
            "source_lock_sha256": "A" * 64,
            "code_provenance": provenance,
            "outputs": {
                name: {"bytes": 1, "sha256": "B" * 64}
                for name in ("zenpen", "kouhen", "four_side")
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                ReleaseBuildError, "different release-critical code"
            ):
                validate_release_target(
                    path,
                    source_lock_sha256="A" * 64,
                    project_root=PROJECT_ROOT,
                )

    def test_cli_uses_console_script_name_and_repository_defaults(
        self,
    ) -> None:
        parser = build_parser()
        self.assertEqual(parser.prog, "time-twist")
        args = parser.parse_args(["release-build"])
        self.assertIsNone(args.project_root)
        self.assertIsNone(args.lock)
        self.assertIsNone(args.target)
        self.assertIsNone(args.output_dir)
        self.assertFalse(args.candidate)

    def test_known_cli_error_has_no_traceback(self) -> None:
        stderr = io.StringIO()
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["release-build", "--project-root", directory])
        self.assertEqual(raised.exception.code, 2)
        rendered = stderr.getvalue()
        self.assertIn("time-twist: error:", rendered)
        self.assertNotIn("Traceback", rendered)

    def test_promotion_accepts_reviewed_noncanonical_hashes_and_external_lock(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            work = root / "work"

            external_lock = Path(directory) / "approved-inputs.json"
            write_source_lock(external_lock, project_root=root)
            candidate = Path(directory) / "candidate"
            candidate.mkdir()
            output_payloads = {
                "zenpen": b"new zenpen candidate",
                "kouhen": b"new kouhen candidate",
                "four_side": b"new combined candidate",
            }
            outputs = {}
            for name, data in output_payloads.items():
                filename = RELEASE_FILENAMES[name]
                (candidate / filename).write_bytes(data)
                outputs[name] = {
                    "path": filename,
                    "bytes": len(data),
                    "sha256": sha256_bytes(data),
                }
            manifest_path = candidate / "release_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": RELEASE_MANIFEST_SCHEMA,
                        "mode": "candidate",
                        "project_source_lock": external_lock.resolve().as_posix(),
                        "source_lock_sha256": sha256_file(external_lock),
                        "code_provenance": build_code_provenance(root),
                        "outputs": outputs,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            target_path = work / "release_target.json"
            target = promote_release_target(
                manifest_path,
                target_path=target_path,
                project_root=root,
                release_id="new-reviewed-output",
            )
            self.assertEqual(target["release_id"], "new-reviewed-output")
            self.assertEqual(
                target["outputs"]["kouhen"]["sha256"],
                sha256_bytes(output_payloads["kouhen"]),
            )
            self.assertNotEqual(
                target["outputs"]["kouhen"]["sha256"],
                "18445D6DA88278F5C52A8EBFC001F00FD00261D640EBDCD66D6AE2147A2A4421",
            )


if __name__ == "__main__":
    unittest.main()
