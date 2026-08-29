"""Protect the public facades introduced by the module split."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist import (
    cli,
    cli_commands,
    cli_parser,
    release,
    release_metadata,
    title,
    title_assets,
    title_layout,
    title_patch,
    ui,
    ui_fixed_tables,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ModernModuleLayoutTests(unittest.TestCase):
    """Keep modernized implementation modules behind stable public imports."""

    def test_cli_facade_exports_the_parser_and_command_implementations(
        self,
    ) -> None:
        """Keep established command imports valid after the CLI split."""
        self.assertIs(cli.build_parser, cli_parser.build_parser)
        self.assertIs(
            cli.command_release_build, cli_commands.command_release_build
        )
        self.assertIs(
            cli.command_release_lock, cli_commands.command_release_lock
        )
        self.assertIs(
            cli.command_release_promote,
            cli_commands.command_release_promote,
        )

    def test_release_facade_exports_metadata_validation_helpers(self) -> None:
        """Keep release callers independent of metadata-module placement."""
        self.assertIs(
            release.discover_project_root,
            release_metadata.discover_project_root,
        )
        self.assertIs(
            release.validate_source_lock,
            release_metadata.validate_source_lock,
        )
        self.assertIs(
            release.validate_release_target,
            release_metadata.validate_release_target,
        )

    def test_title_facade_exports_layout_asset_and_patch_helpers(self) -> None:
        """Keep title callers independent of the internal three-way split."""
        self.assertIs(
            title.build_title_assets, title_assets.build_title_assets
        )
        self.assertIs(title.decode_title_rle, title_assets.decode_title_rle)
        self.assertIs(title.patched_nov4_title, title_patch.patched_nov4_title)
        self.assertEqual(title.SLIDE_PREP_SIZE, title_layout.SLIDE_PREP_SIZE)

    def test_ui_facade_exports_the_canonical_fixed_table_specs(self) -> None:
        """Keep callers on one declarative relocated-menu mapping."""
        for bank_name in ("TT1B", "T22", "TT6C"):
            with self.subTest(bank=bank_name):
                spec = ui.FIXED_RECORD_TABLE_SPECS[bank_name]
                self.assertIs(
                    spec.records,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_RECORDS"
                    ),
                )
                self.assertEqual(
                    spec.start,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_START_OFFSET"
                    ),
                )
                self.assertEqual(
                    spec.end,
                    getattr(
                        ui_fixed_tables, f"{bank_name}_FIXED_TEXT_END_OFFSET"
                    ),
                )

    def test_private_capture_fixture_paths_are_emulator_neutral(self) -> None:
        """Keep private runtime evidence separate from any emulator brand."""
        fixture_path = PROJECT_ROOT / "work" / "integration_fixtures.json"
        fixture_paths = json.loads(fixture_path.read_text(encoding="utf-8"))[
            "files"
        ]
        capture_paths = [
            path
            for path in fixture_paths
            if path.endswith(("_chr.dmp", "_cpu.dmp"))
        ]
        self.assertEqual(len(capture_paths), 4)
        self.assertTrue(
            all(
                path.startswith("work/runtime_capture/")
                for path in capture_paths
            )
        )


if __name__ == "__main__":
    unittest.main()
