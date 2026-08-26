"""Private-overlay integration tests for current source-lock, candidate, and release-promotion safeguards."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.compression import expand_dictionary_symbols
from time_twist.english import render_english
from time_twist.fds import FdsImage
from time_twist.release import (
    DEFAULT_KOUHEN_BASELINE,
    DEFAULT_RELEASE_TARGET,
    DEFAULT_SLIDE_TITLE_ASSET,
    DEFAULT_SOURCE_LOCK,
    DEFAULT_TITLE_ASSET,
    DEFAULT_ZENPEN_BASELINE,
    SCENARIO_LOCATIONS,
    ReleaseBuildError,
    build_release,
    validate_source_lock,
)
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import split_records
from time_twist.ui import FIXED_RECORD_TABLE_SPECS

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

            image = FdsImage.from_bytes(four_side)
            for bank_name, spec in FIXED_RECORD_TABLE_SPECS.items():
                image_name, side = SCENARIO_LOCATIONS[bank_name]
                side_index = side if image_name == "zenpen" else side + 2
                entry = image.sides[side_index].find_file(bank_name)
                bank_path = first_directory / f"{bank_name}.bin"
                bank_path.write_bytes(entry.data)
                dictionary_entries = first["scenario_banks"][bank_name][
                    "dictionary_entries"
                ]
                parsed = parse_scenario_bank(
                    bank_path,
                    minimum_dictionary_entries=dictionary_entries,
                    extended_dictionary=True,
                )
                start = (
                    int.from_bytes(entry.data[0x14:0x16], "little")
                    - entry.load_address
                )
                page_index = (
                    int.from_bytes(entry.data[0x1A:0x1C], "little")
                    - entry.load_address
                )
                records, end = split_records(
                    entry.data,
                    offset=start,
                    limit=len(spec.records),
                    extended_dictionary=True,
                )
                self.assertEqual(end, page_index)
                self.assertEqual(
                    tuple(
                        render_english(
                            expand_dictionary_symbols(
                                record,
                                parsed.dictionary,
                            )
                        )
                        for record in records
                    ),
                    spec.records,
                )

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
