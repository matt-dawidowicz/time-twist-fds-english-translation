"""Protect stable public facades across internal module boundaries."""

from __future__ import annotations

import unittest

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


class PublicApiTests(unittest.TestCase):
    """Keep callers independent of internal implementation-module placement."""

    def test_cli_facade_exports_parser_and_command_implementations(self) -> None:
        """Keep established command imports valid across the CLI split."""
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

    def test_ui_facade_exports_fixed_table_data(self) -> None:
        """Keep UI callers independent of declarative table placement."""
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


if __name__ == "__main__":
    unittest.main()
