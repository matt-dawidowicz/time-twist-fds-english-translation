"""Protect every CLI command's definitions across Python formatter versions.

Golden contract was calculated from the original main-branch implementation.
Unlike rendered argparse help, it excludes Python-version-specific line wraps
while retaining all descriptions, help strings, defaults, callbacks, and args.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unittest
from pathlib import Path

from time_twist.cli_parser import SCENARIO_BANK_CHOICES, build_parser

ORIGINAL_CLI_CONTRACT_SHA256 = (
    "DE5026C031C18027669111499844C7D2D67C8FE1C9A023CBD084153C005D3E20"
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


def _literal(value):
    """Encode argparse defaults and choices without object identity."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, tuple | list):
        return [_literal(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _literal(item) for key, item in sorted(value.items())}
    if callable(value):
        return f"callable:{value.__module__}.{value.__qualname__}"
    return f"type:{type(value).__module__}.{type(value).__qualname__}"


def _registry() -> list[dict[str, object]]:
    """Snapshot the public parser contract independently of help wrapping."""
    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    commands = [("root", parser), *subparsers.choices.items()]
    registry = []
    for name, command in commands:
        actions = []
        for action in command._actions:
            choices = (
                list(action.choices)
                if isinstance(action, argparse._SubParsersAction)
                else _literal(action.choices)
            )
            actions.append(
                {
                    "type": type(action).__name__,
                    "options": action.option_strings,
                    "dest": action.dest,
                    "nargs": _literal(action.nargs),
                    "required": action.required,
                    "choices": choices,
                    "metavar": _literal(action.metavar),
                    "value_type": _literal(action.type),
                    "default": _literal(action.default),
                    "const": _literal(action.const),
                    "help": action.help,
                }
            )
        registry.append(
            {
                "name": name,
                "prog": command.prog,
                "description": command.description,
                "epilog": command.epilog,
                "actions": actions,
                "defaults": {
                    key: _literal(value)
                    for key, value in sorted(command._defaults.items())
                },
            }
        )
    return registry


class CliParserEquivalenceTests(unittest.TestCase):
    """Lock user-visible command definitions and bank-input choices."""

    def test_registered_api_matches_original_parser(self) -> None:
        """Compare all arguments, help, dispatch, defaults, and order."""
        contract = json.dumps(
            _registry(), sort_keys=True, ensure_ascii=True, separators=(",", ":")
        )
        self.assertEqual(
            hashlib.sha256(contract.encode("utf-8")).hexdigest().upper(),
            ORIGINAL_CLI_CONTRACT_SHA256,
        )
        self.assertEqual(
            tuple(entry["name"] for entry in _registry()[1:]),
            EXPECTED_COMMANDS,
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
