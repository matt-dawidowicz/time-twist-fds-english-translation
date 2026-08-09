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
    ReleaseBuildError,
    _publish_staged_release,
    discover_project_root,
    display_path,
    promote_release_target,
    sha256_bytes,
    sha256_file,
    validate_release_target,
    write_source_lock,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ReleaseBuildError, "not a Time Twist"):
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
            "schema": "Time Twist release target v1",
            "release_id": "test",
            "source_lock_sha256": "A" * 64,
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
                validate_release_target(path, source_lock_sha256="C" * 64)

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
        with tempfile.TemporaryDirectory() as directory:
            with (
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
            root = Path(directory) / "project"
            work = root / "work"
            translations = work / "translations"
            title_assets = work / "title_assets"
            baseline = work / "baseline"
            translations.mkdir(parents=True)
            title_assets.mkdir()
            baseline.mkdir()
            (root / "pyproject.toml").write_text(
                "[project]\nname='test'\n", encoding="utf-8"
            )
            for bank in KNOWN_SCENARIO_BANKS:
                (translations / f"{bank}.json").write_text(
                    "{}\n", encoding="utf-8"
                )
            (
                title_assets / "Time Twist approved native title.png"
            ).write_bytes(b"title")
            (baseline / "time_twist_zenpen_japan.fds").write_bytes(b"zenpen")
            (baseline / "time_twist_kouhen_japan.fds").write_bytes(b"kouhen")

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
                        "schema": "Time Twist reproducible release manifest v2",
                        "mode": "candidate",
                        "project_source_lock": external_lock.resolve().as_posix(),
                        "source_lock_sha256": sha256_file(external_lock),
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
