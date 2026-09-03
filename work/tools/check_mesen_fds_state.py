#!/usr/bin/env python3
"""Reject stale Mesen FDS write overlays before runtime certification."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


class MesenFdsStateError(RuntimeError):
    """Raised when runtime certification would start from dirty Mesen state."""


def find_active_sidecars(
    candidate_fds: Path,
    mesen_save_dir: Path,
) -> tuple[Path, ...]:
    """Return active Mesen IPS sidecars matching one FDS candidate filename."""
    if candidate_fds.suffix.casefold() != ".fds":
        raise MesenFdsStateError(f"candidate must be an .fds image: {candidate_fds}")
    if not candidate_fds.is_file():
        raise MesenFdsStateError(f"candidate does not exist: {candidate_fds}")
    if not mesen_save_dir.is_dir():
        raise MesenFdsStateError(
            f"Mesen save directory does not exist: {mesen_save_dir}"
        )

    expected_name = f"{candidate_fds.stem}.ips".casefold()
    matches = (
        path
        for path in mesen_save_dir.rglob("*")
        if path.is_file() and path.name.casefold() == expected_name
    )
    return tuple(sorted(matches, key=lambda path: str(path).casefold()))


def check_clean_state(candidate_fds: Path, mesen_save_dir: Path) -> None:
    """Fail if Mesen can apply an existing write overlay to the candidate."""
    matches = find_active_sidecars(candidate_fds, mesen_save_dir)
    if not matches:
        return

    rendered = "\n".join(f"  - {path}" for path in matches)
    raise MesenFdsStateError(
        "active Mesen FDS write overlay found for this candidate:\n"
        f"{rendered}\n"
        "Close Mesen and move or rename the matching .ips file before the "
        "first cold boot of a newly built candidate. Keep it as evidence "
        "rather than deleting it blindly."
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the Mesen clean-state preflight."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify that Mesen has no filename-matched FDS .ips write overlay "
            "that could contaminate runtime certification."
        )
    )
    parser.add_argument(
        "--candidate-fds",
        required=True,
        type=Path,
        help="FDS candidate that will be tested in Mesen.",
    )
    parser.add_argument(
        "--mesen-save-dir",
        required=True,
        type=Path,
        help="Mesen Saves directory to inspect recursively.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Mesen clean-state preflight."""
    args = _build_parser().parse_args(argv)
    try:
        check_clean_state(args.candidate_fds, args.mesen_save_dir)
    except MesenFdsStateError as exc:
        print(f"MESEN FDS STATE: FAIL\n{exc}", file=sys.stderr)
        return 1

    print(
        "MESEN FDS STATE: PASS\n"
        "No active filename-matched .ips overlay was found."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
