"""Reject private ROM fixtures, machine-local state, and build debris.

Run this against the source tree before packaging or publishing it. In a Git
checkout, only tracked files and non-ignored untracked files are audited so
ignored maintainer state remains private by construction. The private
integration overlay is intentionally expected to fail this check if exposed to
the public file set.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

FORBIDDEN_SUFFIXES = {
    ".fds",
    ".mss",
    ".nes",
    ".rom",
    ".bin",
    ".dmp",
    ".pyc",
    ".pyo",
    ".zip",
}
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
    Path("work/source_records"),
    Path("work/title_assets"),
    Path("work/integration_fixtures.json"),
)
CHECKER_RELATIVE_PATH = Path("work/tools/check_public_tree.py")


def _git_visible_files(root: Path) -> list[Path] | None:
    """Return files Git considers publishable, or ``None`` outside a checkout."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return [
        root / Path(os.fsdecode(raw_path))
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    ]


def _candidate_paths(root: Path):
    """Yield the public candidate paths, falling back to a raw tree walk."""
    git_visible = _git_visible_files(root)
    if git_visible is not None:
        yield from git_visible
        return
    yield from root.rglob("*")


def _forbidden_parent(relative: Path) -> Path | None:
    """Return the first forbidden parent directory represented by ``relative``."""
    for index, part in enumerate(relative.parts[:-1]):
        if part in FORBIDDEN_DIRECTORY_NAMES or part.endswith(".egg-info"):
            return Path(*relative.parts[: index + 1])
    return None


def check_public_tree(root: Path) -> list[str]:
    """Return human-readable public-source policy violations beneath ``root``."""
    root = root.expanduser().resolve()
    problems = [
        f"missing required public source path: {marker.as_posix()}"
        for marker in REQUIRED_PUBLIC_MARKERS
        if not (root / marker).exists()
    ]

    for path in _candidate_paths(root):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if ".git" in relative.parts:
            continue

        forbidden_parent = _forbidden_parent(relative)
        if forbidden_parent is not None:
            problems.append(
                "generated/private directory present: "
                f"{forbidden_parent.as_posix()}"
            )
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
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(
                f"private/generated file present: {relative.as_posix()}"
            )
            continue
        if "settings" in path.stem.lower() and path.suffix.lower() == ".json":
            problems.append(
                f"machine-local emulator settings present: {relative.as_posix()}"
            )
            continue
        if relative == CHECKER_RELATIVE_PATH:
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
