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
    LEGACY_RELEASE_TARGET_SCHEMA,
    RELEASE_FILENAMES,
    RELEASE_MANIFEST_SCHEMA,
    RELEASE_TARGET_SCHEMA,
    SOURCE_LOCK_SCHEMA,
    SOURCE_NORMALIZATION_LF,
    SOURCE_NORMALIZATION_RAW,
    ReleaseBuildError,
    _publish_staged_release,
    build_code_provenance,
    build_release,
    build_source_lock_payload,
    discover_project_root,
    display_path,
    promote_release_target,
    release_code_tree_sha256,
    sha256_bytes,
    source_lock_sha256,
    validate_release_target,
    validate_source_lock,
    validate_source_lock_metadata,
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

    def test_failed_publication_invalidates_previous_manifest(self) -> None:
        """Never leave an old manifest attesting a partly replaced output set."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            output = root / "output"
            staging.mkdir()
            output.mkdir()
            for filename in RELEASE_FILENAMES.values():
                (staging / filename).write_bytes(b"new")
            (staging / "release_manifest.json").write_bytes(b"new manifest")
            previous_manifest = output / "release_manifest.json"
            previous_manifest.write_bytes(b"old manifest")

            with (
                mock.patch(
                    "time_twist.release._atomic_publish_file",
                    side_effect=OSError("simulated publication failure"),
                ),
                self.assertRaisesRegex(OSError, "simulated"),
            ):
                _publish_staged_release(staging, output)

            self.assertFalse(previous_manifest.exists())

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

    def test_source_lock_normalizes_translation_line_endings(self) -> None:
        """Treat LF and CRLF translation JSON as the same approved input."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            translation = root / "work" / "translations" / "TT1A.json"
            translation.write_bytes(b'{\n  "line": "approved"\n}\n')
            payload = write_source_lock(project_root=root)

            record = payload["files"]["work/translations/TT1A.json"]
            self.assertEqual(record["normalization"], SOURCE_NORMALIZATION_LF)
            translation.write_bytes(b'{\r\n  "line": "approved"\r\n}\r\n')

            self.assertEqual(validate_source_lock(project_root=root), payload)

    def test_source_lock_rejects_changed_normalized_translation(self) -> None:
        """Line-ending tolerance must not hide a text-content change."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            write_source_lock(project_root=root)
            translation = root / "work" / "translations" / "TT1A.json"
            translation.write_bytes(b'{\r\n  "changed": true\r\n}\r\n')

            with self.assertRaisesRegex(
                ReleaseBuildError, "unapproved release input changed"
            ):
                validate_source_lock(project_root=root)

    def test_source_lock_keeps_binary_inputs_byte_exact(self) -> None:
        """Never apply text normalization to ROMs or title artwork."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            payload = write_source_lock(project_root=root)
            relative = "work/baseline/time_twist_zenpen_japan.fds"
            self.assertEqual(
                payload["files"][relative]["normalization"],
                SOURCE_NORMALIZATION_RAW,
            )
            baseline = root / relative
            baseline.write_bytes(baseline.read_bytes() + b"\r\n")

            with self.assertRaisesRegex(
                ReleaseBuildError, "unapproved release input changed"
            ):
                validate_source_lock(project_root=root)

    def test_source_lock_document_hash_normalizes_line_endings(self) -> None:
        """Bind targets to one logical lock document on Windows and Unix."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes(b'{\n  "value": 1\n}\n')
            crlf.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')
            self.assertEqual(source_lock_sha256(lf), source_lock_sha256(crlf))

    def test_source_lock_metadata_enforces_path_normalization_policy(
        self,
    ) -> None:
        """Reject a binary-as-text policy that could weaken exact locking."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            payload = build_source_lock_payload(root)
            relative = "work/baseline/time_twist_zenpen_japan.fds"
            payload["files"][relative][
                "normalization"
            ] = SOURCE_NORMALIZATION_LF
            with self.assertRaisesRegex(
                ReleaseBuildError, "invalid source normalization"
            ):
                validate_source_lock_metadata(payload)

    def test_source_lock_payload_uses_current_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            payload = build_source_lock_payload(root)
            self.assertEqual(payload["schema"], SOURCE_LOCK_SCHEMA)

    def test_release_target_is_tied_to_source_lock(self) -> None:
        payload = {
            "schema": RELEASE_TARGET_SCHEMA,
            "release_id": "test",
            "source_lock_sha256": "A" * 64,
            "code_provenance": build_code_provenance(PROJECT_ROOT),
            "promoted_from_manifest_sha256": "C" * 64,
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

    def test_distinct_execution_and_checkout_paths_hash_logically(
        self,
    ) -> None:
        """Compare installed and checkout trees by logical package identity."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            checkout_code = root / "work" / "time_twist"
            installed_code = (
                Path(directory) / "venv" / "site-packages" / "time_twist"
            )
            checkout_code.mkdir(parents=True)
            installed_code.mkdir(parents=True)
            (checkout_code / "release.py").write_bytes(b"value = 1\r\n")
            (installed_code / "release.py").write_bytes(b"value = 1\n")

            provenance = build_code_provenance(
                root, executing_code_root=installed_code
            )

            self.assertEqual(provenance["code_root"], "work/time_twist")
            self.assertEqual(
                provenance["tree_sha256"], release_code_tree_sha256(root)
            )

    def test_mismatched_execution_and_checkout_trees_fail_closed(self) -> None:
        """Reject an installed implementation with different source contents."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "checkout"
            checkout_code = root / "work" / "time_twist"
            installed_code = Path(directory) / "installed" / "time_twist"
            checkout_code.mkdir(parents=True)
            installed_code.mkdir(parents=True)
            (checkout_code / "release.py").write_text("value = 1\n")
            (installed_code / "release.py").write_text("value = 2\n")

            with self.assertRaisesRegex(
                ReleaseBuildError, "installed/executing.*differs"
            ):
                build_code_provenance(root, executing_code_root=installed_code)

    def test_release_build_checks_code_before_inputs_or_generation(
        self,
    ) -> None:
        """Fail on executor mismatch before validating private release inputs."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            with (
                mock.patch("time_twist.release.validate_source_lock") as lock,
                self.assertRaisesRegex(
                    ReleaseBuildError, "installed/executing.*differs"
                ),
            ):
                build_release(
                    Path(directory) / "output",
                    project_root=root,
                    verify_target=False,
                )
            lock.assert_not_called()

    def test_strict_build_rejects_legacy_target_before_rom_generation(
        self,
    ) -> None:
        """Report the migration gate before parsing or rebuilding ROM inputs."""
        with tempfile.TemporaryDirectory() as directory:
            root = make_synthetic_project(Path(directory) / "project")
            work = root / "work"
            write_source_lock(project_root=root)
            (work / "release_target.json").write_text(
                json.dumps(
                    {
                        "schema": LEGACY_RELEASE_TARGET_SCHEMA,
                        "source_lock_sha256": source_lock_sha256(
                            work / "release_sources.json"
                        ),
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT",
                    work / "time_twist",
                ),
                mock.patch("time_twist.release.FdsImage.read") as read_image,
                self.assertRaisesRegex(ReleaseBuildError, "legacy.*playtest"),
            ):
                build_release(
                    Path(directory) / "output",
                    project_root=root,
                )
            read_image.assert_not_called()

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
                provenance = build_code_provenance(
                    root, executing_code_root=code
                )
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
            "promoted_from_manifest_sha256": "C" * 64,
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

    def test_release_target_rejects_boolean_numeric_fields(self) -> None:
        """JSON booleans must not pass integer provenance or size checks."""
        provenance = build_code_provenance(PROJECT_ROOT)
        provenance["file_count"] = True
        payload = {
            "schema": RELEASE_TARGET_SCHEMA,
            "release_id": "test",
            "source_lock_sha256": "A" * 64,
            "code_provenance": provenance,
            "promoted_from_manifest_sha256": "C" * 64,
            "outputs": {
                name: {"bytes": True, "sha256": "B" * 64}
                for name in ("zenpen", "kouhen", "four_side")
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "target.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseBuildError, "file count"):
                validate_release_target(
                    path,
                    source_lock_sha256="A" * 64,
                    project_root=PROJECT_ROOT,
                )
            payload["code_provenance"] = build_code_provenance(PROJECT_ROOT)
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseBuildError, "byte size"):
                validate_release_target(
                    path,
                    source_lock_sha256="A" * 64,
                    project_root=PROJECT_ROOT,
                )

    def test_release_target_reports_malformed_json_with_its_path(self) -> None:
        """Turn malformed metadata into a concise release-domain error."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken-target.json"
            path.write_text('{"schema":', encoding="utf-8")
            with self.assertRaisesRegex(
                ReleaseBuildError, r"malformed JSON: .*broken-target\.json"
            ):
                validate_release_target(
                    path,
                    source_lock_sha256="A" * 64,
                    project_root=PROJECT_ROOT,
                )

    def test_checked_in_target_is_current_or_explicitly_absent(self) -> None:
        """Require either a valid current target or documented pre-promotion state."""
        target_path = PROJECT_ROOT / "work" / "release_target.json"
        lock_path = PROJECT_ROOT / "work" / "release_sources.json"
        source_lock = json.loads(lock_path.read_text(encoding="utf-8"))
        validate_source_lock_metadata(source_lock)
        lock_sha256 = source_lock_sha256(lock_path)

        if target_path.is_file():
            target = json.loads(target_path.read_text(encoding="utf-8"))
            self.assertEqual(target.get("schema"), RELEASE_TARGET_SCHEMA)
            validate_release_target(
                target_path,
                source_lock_sha256=lock_sha256,
                project_root=PROJECT_ROOT,
            )
            return

        documentation = (PROJECT_ROOT / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("No release target is checked in", documentation)
        with self.assertRaisesRegex(
            ReleaseBuildError, "release target is missing"
        ):
            validate_release_target(
                target_path,
                source_lock_sha256=lock_sha256,
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

    def test_promotion_accepts_external_lock_when_rebuild_matches(
        self,
    ) -> None:
        """Keep external-lock support while requiring canonical reproduction."""
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
            code_root = work / "time_twist"
            manifest_payload = {
                "schema": RELEASE_MANIFEST_SCHEMA,
                "mode": "candidate",
                "project_source_lock": external_lock.resolve().as_posix(),
                "source_lock_sha256": source_lock_sha256(external_lock),
                "code_provenance": build_code_provenance(
                    root, executing_code_root=code_root
                ),
                "build_environment": {
                    "schema": "Time Twist build environment v1",
                    "python_implementation": "CPython",
                    "python_version": "3.12",
                    "pillow_version": "12.0",
                },
                "release_target": None,
                "release_target_sha256": None,
                "release_id": None,
                "subtitle": "On the Outskirts of History...",
                "scenario_banks": {
                    bank: {
                        "records": 1,
                        "dictionary_entries": 0,
                        "packed_bytes": 1,
                        "capacity_bytes": 2,
                        "remaining_bytes": 1,
                        "sha256": "A" * 64,
                    }
                    for bank in KNOWN_SCENARIO_BANKS
                },
                "component_sha256": {
                    "NOV2": "B" * 64,
                    "NOV4": "C" * 64,
                    "SON-KOUH": "D" * 64,
                },
                "outputs": outputs,
            }
            manifest_path.write_text(
                json.dumps(manifest_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            target_path = work / "release_target.json"
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                mock.patch(
                    "time_twist.release.build_release",
                    return_value=manifest_payload,
                ),
            ):
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

            outputs["zenpen"]["path"] = "..\\escaped.fds"
            manifest_path.write_text(
                json.dumps(manifest_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            with (
                mock.patch(
                    "time_twist.release.EXECUTING_PACKAGE_ROOT", code_root
                ),
                self.assertRaisesRegex(ReleaseBuildError, "canonical path"),
            ):
                promote_release_target(
                    manifest_path,
                    target_path=target_path,
                    project_root=root,
                )


if __name__ == "__main__":
    unittest.main()
