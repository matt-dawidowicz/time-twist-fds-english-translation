"""Ensure CLI refactoring preserves every public help surface and bank choice.

The fixed hash was calculated using the original main-branch parser, before
splitting its command registrations into groups. We compare the complete
root and 15 subcommand help texts; no private ROMs are required.
"""

from __future__ import annotations

import argparse
import hashlib
import unittest
from pathlib import Path

from time_twist.cli_parser import SCENARIO_BANK_CHOICES, build_parser

ORIGINAL_COMPLETE_HELP_SHA256 = (
    "164307CE3324534AF273E013A820FD6D5C3A234366966F8A7D0A466C43A44408"
)
EXPECTED_COMMANDS = (
    "manifest",
    "extract",
    "roundtrip",
    "combine",
    "scenario-extract",
    "scenario-merge",
    "scenario-footprint",
    "font-patch",
    "title-patch",
    "replace-file",
    "build",
    "inspect-layout",
    "release-lock",
    "release-build",
    "release-promote",
)


class CliParserEquivalenceTests(unittest.TestCase):
    """Lock public help, registration order, and source-bank argument choices."""

    def test_complete_help_matches_original_parser(self) -> None:
        """Verify every command's human-readable API, not just root help."""
        parser = build_parser()
        subparsers = next(
            item
            for item in parser._actions
            if isinstance(item, argparse._SubParsersAction)
        )
        self.assertEqual(tuple(subparsers.choices), EXPECTED_COMMANDS)
        help_text = parser.format_help() + "\n".join(
            name + ":\n" + command.format_help()
            for name, command in subparsers.choices.items()
        )
        self.assertEqual(
            hashlib.sha256(help_text.encode("utf-8")).hexdigest().upper(),
            ORIGINAL_COMPLETE_HELP_SHA256,
        )

    def test_identical_scenario_bank_choice_policy(self) -> None:
        """Keep two related commands on the same fixed accepted-bank set."""
        self.assertEqual(len(SCENARIO_BANK_CHOICES), 13)
        for subcommand in ("scenario-extract", "scenario-footprint"):
            args = [subcommand, "sample.bin", "--bank-name", "TT6D"]
            if subcommand == "scenario-extract":
                args.append("review.json")
            result = build_parser().parse_args(args)
            self.assertEqual(result.bank, Path("sample.bin"))
            self.assertEqual(result.bank_name, "TT6D")


if __name__ == "__main__":
    unittest.main()
