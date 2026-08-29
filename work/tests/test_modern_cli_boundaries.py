"""Regression tests for the modern release/standalone command boundary."""

from __future__ import annotations

import unittest

from time_twist.cli_commands import _require_standalone_scenario_bank
from time_twist.cli_parser import build_parser
from time_twist.release import SCENARIO_UI_PATCHERS
from time_twist.ui import FIXED_RECORD_TABLE_SPECS


class ModernCliBoundaryTests(unittest.TestCase):
    """Keep relocated menu banks on the canonical release path."""

    def test_release_uses_only_the_tt1a_same_size_scenario_patcher(
        self,
    ) -> None:
        """Relocated menu banks must bypass the legacy patcher map."""
        self.assertEqual(set(SCENARIO_UI_PATCHERS), {"TT1A"})

    def test_relocated_banks_reject_standalone_translated_operations(
        self,
    ) -> None:
        """Direct maintainers to release-build for every relocated-menu bank."""
        for bank_name in FIXED_RECORD_TABLE_SPECS:
            with (
                self.subTest(bank=bank_name),
                self.assertRaisesRegex(SystemExit, "release-build"),
            ):
                _require_standalone_scenario_bank(bank_name, "scenario-insert")
        _require_standalone_scenario_bank("TT1A", "scenario-insert")
        _require_standalone_scenario_bank("TT6D", "scenario-insert")

    def test_ui_patch_parser_exposes_only_standalone_components(self) -> None:
        """Do not advertise the superseded scenario fixed-slot patchers."""
        parser = build_parser()
        namespace = parser.parse_args(
            ["ui-patch", "source.bin", "output.bin", "--component", "TT1A"]
        )
        self.assertEqual(namespace.component, "TT1A")
        with self.assertRaises(SystemExit):
            parser.parse_args(
                ["ui-patch", "source.bin", "output.bin", "--component", "TT2"]
            )


if __name__ == "__main__":
    unittest.main()
