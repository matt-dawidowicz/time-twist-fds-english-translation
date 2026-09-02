"""Public command-line entry point for the maintained ``time-twist`` CLI."""

from __future__ import annotations

import json

from .cli_parser import build_parser

__all__ = ("build_parser", "main")


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
