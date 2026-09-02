"""Protect the public facades introduced by the module split."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist import (
    cli,
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

    def test_cli_entry_point_keeps_command_implementations_internal(
        self,
    ) -> None:
        """Expose parser/main publicly without compatibility command aliases."""
        self.assertIs(cli.build_parser, cli_parser.build_parser)
        for name in (
            "command_release_build",
            "command_release_lock",
            "command_scenario_insert",
            "command_ui_patch",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(cli, name))

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

    def test_ui_facade_exports_the_fixed_table_data(self) -> None:
        """Keep fixed-table callers independent of the declarative-data split."""
        self.assertIs(
            ui.TT1B_FIXED_TEXT_RECORDS,
            ui_fixed_tables.TT1B_FIXED_TEXT_RECORDS,
        )
        self.assertIs(
            ui.T22_FIXED_TEXT_RECORDS,
            ui_fixed_tables.T22_FIXED_TEXT_RECORDS,
        )
        self.assertIs(
            ui.TT6C_FIXED_TEXT_RECORDS,
            ui_fixed_tables.TT6C_FIXED_TEXT_RECORDS,
        )

    def test_private_capture_fixture_path_is_emulator_neutral(self) -> None:
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
        self.assertEqual(
            capture_paths,
            ["work/runtime_capture/zenpen_title_cpu.dmp"],
        )


if __name__ == "__main__":
    unittest.main()
