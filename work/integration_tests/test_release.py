"""Private-overlay integration tests for the canonical entropy release path."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.fds import FdsImage
from time_twist.release import (
    DEFAULT_KOUHEN_BASELINE,
    DEFAULT_RELEASE_TARGET,
    DEFAULT_SLIDE_TITLE_ASSET,
    DEFAULT_SOURCE_LOCK,
    DEFAULT_TITLE_ASSET,
    DEFAULT_ZENPEN_BASELINE,
    ReleaseBuildError,
    build_release,
    sha256_bytes,
    validate_source_lock,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PR45_FOUR_SIDE_SHA256 = (
    "99C282A51968890204990FCE7EE433E83925DCF5505FB29B74F959C22B5B01E9"
)


class ReleaseBuildTests(unittest.TestCase):
    """Verify exact private-ROM behavior of the single release pipeline."""

    def test_source_lock_rejects_changed_hashes(self) -> None:
        """Reject any private or tracked release source that differs from its lock."""
        payload = json.loads(DEFAULT_SOURCE_LOCK.read_text(encoding="utf-8"))
        first = next(iter(payload["files"].values()))
        first["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad_lock.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReleaseBuildError, "unapproved"):
                validate_source_lock(path, project_root=PROJECT_ROOT)

    def test_complete_candidate_rebuild_preserves_pr45_bytes(self) -> None:
        """Rebuild deterministically and preserve the reviewed PR #45 candidate."""
        required = (
            DEFAULT_SOURCE_LOCK,
            DEFAULT_ZENPEN_BASELINE,
            DEFAULT_KOUHEN_BASELINE,
            DEFAULT_TITLE_ASSET,
            DEFAULT_SLIDE_TITLE_ASSET,
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
            self.assertEqual(first["codec"], "frozen-entropy-v1")
            self.assertEqual(first["decoder_format"], "entropy-only")
            self.assertEqual(first["nov3_exclusive_boundary"], "0xD7B5")
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
            self.assertEqual(sha256_bytes(four_side), PR45_FOUR_SIDE_SHA256)

            candidate_images = {
                "zenpen": FdsImage.from_bytes(zenpen),
                "kouhen": FdsImage.from_bytes(kouhen),
            }
            source_images = {
                "zenpen": FdsImage.read(DEFAULT_ZENPEN_BASELINE),
                "kouhen": FdsImage.read(DEFAULT_KOUHEN_BASELINE),
            }
            expected_changed = {
                "zenpen": {
                    (0, "TT3A"),
                    (0, "TT3B"),
                    (0, "NOV2"),
                    (0, "NOV4"),
                    (1, "TT1B"),
                    (1, "TT1A"),
                    (1, "TT2"),
                    (1, "T22"),
                },
                "kouhen": {
                    (0, "SON-KOUH"),
                    (0, "TT6C"),
                    (0, "TT6B"),
                    (0, "TT6A"),
                    (0, "TT6D"),
                    (1, "TT4"),
                    (1, "TT5"),
                    (1, "T25"),
                },
            }
            expected_resized = {"zenpen": {(0, "NOV4")}, "kouhen": set()}
            for image_name, candidate_image in candidate_images.items():
                source_image = source_images[image_name]
                actual_changed: set[tuple[int, str]] = set()
                actual_resized: set[tuple[int, str]] = set()
                self.assertEqual(len(candidate_image.sides), len(source_image.sides))
                for side_index, (source_side, candidate_side) in enumerate(
                    zip(source_image.sides, candidate_image.sides, strict=True)
                ):
                    self.assertEqual(candidate_side.disk_info, source_side.disk_info)
                    self.assertEqual(
                        candidate_side.file_count_block, source_side.file_count_block
                    )
                    self.assertEqual(len(candidate_side.files), len(source_side.files))
                    growth = 0
                    for source_file, candidate_file in zip(
                        source_side.files, candidate_side.files, strict=True
                    ):
                        identity = (side_index, source_file.name)
                        self.assertEqual(candidate_file.name, source_file.name)
                        if candidate_file.data != source_file.data:
                            actual_changed.add(identity)
                        if candidate_file.size != source_file.size:
                            actual_resized.add(identity)
                            self.assertEqual(
                                candidate_file.header[:13], source_file.header[:13]
                            )
                            self.assertEqual(
                                candidate_file.header[15:], source_file.header[15:]
                            )
                        else:
                            self.assertEqual(candidate_file.header, source_file.header)
                        growth += candidate_file.size - source_file.size
                    expected_padding = len(source_side.padding) - growth
                    self.assertEqual(
                        candidate_side.padding,
                        source_side.padding[:expected_padding],
                    )
                self.assertEqual(actual_changed, expected_changed[image_name])
                self.assertEqual(actual_resized, expected_resized[image_name])

            for bank_name, report in first["scenario_banks"].items():
                with self.subTest(bank=bank_name):
                    self.assertGreaterEqual(report["nov3_headroom"], 0)
                    self.assertLessEqual(int(report["loaded_end"], 16), 0xD7B5)

    def test_strict_release_rejects_unpromoted_checkout(self) -> None:
        """Keep strict release mode closed until a reviewed candidate is promoted."""
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
