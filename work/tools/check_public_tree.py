"""Reject private ROM fixtures, machine-local state, and build debris.

Run this against the source tree before packaging or publishing it. The private
integration overlay is intentionally expected to fail this check.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

FORBIDDEN_SUFFIXES = {".fds", ".nes", ".rom", ".bin", ".dmp", ".pyc", ".pyo"}
FORBIDDEN_DIRECTORY_NAMES = {"build", "dist", "__pycache__"}
PERSONAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\Users\\[^\\/\s]+", re.IGNORECASE),
    re.compile(r"D:\\", re.IGNORECASE),
    re.compile(r"/Users/[^/\s]+/"),
    re.compile(r"/home/[^/\s]+/"),
)
REQUIRED_PUBLIC_MARKERS = (
    Path("pyproject.toml"),
    Path("work/time_twist"),
    Path("work/translations"),
    Path("work/title_assets"),
    Path("work/integration_fixtures.json"),
)


def check_public_tree(root: Path) -> list[str]:
    """Return human-readable public-source policy violations beneath ``root``."""
    root = root.expanduser().resolve()
    problems = [
        f"missing required public source path: {marker.as_posix()}"
        for marker in REQUIRED_PUBLIC_MARKERS
        if not (root / marker).exists()
    ]

    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if ".git" in relative.parts:
            continue
        if path.is_dir():
            if path.name in FORBIDDEN_DIRECTORY_NAMES or path.name.endswith(
                ".egg-info"
            ):
                problems.append(
                    f"generated/private directory present: {relative.as_posix()}"
                )
            continue
        if not path.is_file():
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        lower_name = path.name.lower()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(
                f"private/generated file present: {relative.as_posix()}"
            )
            continue
        if lower_name.startswith("mesen_") and lower_name.endswith(".zip"):
            problems.append(f"emulator archive present: {relative.as_posix()}")
            continue
        if lower_name.startswith("mesen_settings") and lower_name.endswith(
            ".json"
        ):
            problems.append(
                f"machine-local emulator settings present: {relative.as_posix()}"
            )
            continue
        if path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in PERSONAL_PATH_PATTERNS:
            match = pattern.search(text)
            if match:
                problems.append(
                    f"machine-local absolute path in {relative.as_posix()}: {match.group(0)}"
                )
                break
    return sorted(set(problems))


def main(argv: list[str] | None = None) -> int:
    """Check a source checkout and print a concise pass/fail report."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="project root (default: auto-resolved from this script)",
    )
    args = parser.parse_args(argv)
    problems = check_public_tree(args.root)
    if problems:
        print("public source tree check: FAIL")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("public source tree check: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
