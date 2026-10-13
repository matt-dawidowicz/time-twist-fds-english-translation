"""Freeze author-defined CLI names, help, choices, and dispatch behavior.

The original main-branch parser and the refactored parser both produce the
same snapshot. Argparse-injected help actions and presentation-only wrapping
are excluded because they differ across supported Python versions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unittest
from pathlib import Path

from time_twist.cli_parser import SCENARIO_BANK_CHOICES, build_parser

ORIGINAL_CLI_CONTRACT_SHA256 = (
    "24820006CE672E3D1667B74840BAEE5EA6F6AEDBFE8A249BD99F099FD2B40C77"
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


def _registered_commands() -> tuple[argparse.ArgumentParser, object]:
    """Locate the public root parser and registered command action."""
    root = build_parser()
    subparsers = next(
        action
        for action in root._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    return root, subparsers


def _author_defined_contract() -> list[object]:
    """Serialize only the command attributes explicitly authored by us."""
    root, subparsers = _registered_commands()
    commands = [("root", root), *subparsers.choices.items()]
    contract = []
    for name, parser in commands:
        actions = []
        for action in parser._actions:
            if isinstance(action, argparse._HelpAction):
                continue
            actions.append(
                [
                    action.dest,
                    action.option_strings,
                    action.help,
                    list(action.choices) if action.choices is not None else None,
                ]
            )
        contract.append(
            [name, parser.prog, parser.description, parser.epilog, actions]
        )
    return contract


class CliParserEquivalenceTests(unittest.TestCase):
    """Lock public interface text and intentional command registrations."""

    def test_author_defined_cli_matches_original(self) -> None:
        """Protect all names, positional/optional flags, help, and choices."""
        payload = json.dumps(
            _author_defined_contract(),
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
        self.assertEqual(
            hashlib.sha256(payload.encode("utf-8")).hexdigest().upper(),
            ORIGINAL_CLI_CONTRACT_SHA256,
        )
        root, subparsers = _registered_commands()
        self.assertEqual(tuple(subparsers.choices), EXPECTED_COMMANDS)
        self.assertEqual(root.prog, "time-twist")
        for name, command in subparsers.choices.items():
            self.assertEqual(
                command._defaults["function"].__name__,
                "command_" + name.replace("-", "_"),
            )

    def test_identical_scenario_bank_choice_policy(self) -> None:
        """Keep both scenario commands on the same fixed bank-name set."""
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
