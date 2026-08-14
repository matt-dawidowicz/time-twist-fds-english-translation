"""Public command-line entry point and compatibility exports.

Command handlers and argument registration are kept in dedicated modules
so contributors can navigate the CLI without crossing both concerns.
"""

from __future__ import annotations

import json

from . import cli_commands as _commands
from .cli_commands import (
    PERSONALITY_QUESTION_IDS,
    command_combine,
    command_extract,
    command_font_patch,
    command_manifest,
    command_release_build,
    command_release_lock,
    command_release_promote,
    command_replace_file,
    command_roundtrip,
    command_scenario_merge,
    command_title_patch,
    command_ui_patch,
    merge_translation_document,
    safe_filename,
)
from .cli_parser import build_parser

# Scenario command tests and external tooling have historically replaced this
# helper through ``time_twist.cli``. Keep that seam at the public facade while
# the implementation itself lives in ``cli_commands``.
_parse_source_bank = _commands._parse_source_bank


def _run_scenario_command(handler: object, args: object) -> None:
    """Run one moved scenario handler through the facade patch seam."""
    original = _commands._parse_source_bank
    _commands._parse_source_bank = _parse_source_bank
    try:
        handler(args)  # type: ignore[operator]
    finally:
        _commands._parse_source_bank = original


def command_scenario_extract(args: object) -> None:
    """Decode a scenario bank through the stable public CLI facade."""
    _run_scenario_command(_commands.command_scenario_extract, args)


def command_scenario_insert(args: object) -> None:
    """Insert a scenario bank through the stable public CLI facade."""
    _run_scenario_command(_commands.command_scenario_insert, args)


def command_scenario_footprint(args: object) -> None:
    """Report scenario capacity through the stable public CLI facade."""
    _run_scenario_command(_commands.command_scenario_footprint, args)


__all__ = (
    "PERSONALITY_QUESTION_IDS",
    "build_parser",
    "command_combine",
    "command_extract",
    "command_font_patch",
    "command_manifest",
    "command_release_build",
    "command_release_lock",
    "command_release_promote",
    "command_replace_file",
    "command_roundtrip",
    "command_scenario_extract",
    "command_scenario_footprint",
    "command_scenario_insert",
    "command_scenario_merge",
    "command_title_patch",
    "command_ui_patch",
    "main",
    "merge_translation_document",
    "safe_filename",
)


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, run one command, and present expected failures cleanly."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.function(args)
    except (
        OSError,
        ValueError,
        KeyError,
        OverflowError,
        json.JSONDecodeError,
    ) as error:
        message = str(error)
        if isinstance(error, KeyError) and len(message) >= 2:
            message = message.strip("'\"")
        parser.exit(2, f"{parser.prog}: error: {message}\n")


if __name__ == "__main__":
    main()
