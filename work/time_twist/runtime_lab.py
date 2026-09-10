"""Fast runtime-debug entry points for the 2026-08-29 vs current comparison.

This module deliberately avoids the broad public CLI.  Runtime debugging needs a
small number of repeatable operations: inspect the code delta, compare two FDS
images, run the focused tests in one interpreter, and build the current entropy
candidate without spawning helper scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .fds import FdsFile, FdsImage

BASELINE_COMMIT = "ad5ebe9fced6807c6398691db1b36c58e9b1d095"
CODE_PATHS = ("work/time_twist", "work/tools", "pyproject.toml")
FOCUSED_TESTS = (
    "test_entropy_production",
    "test_production_runtime",
    "test_production_scenario",
    "test_textcodec",
)


@dataclass(frozen=True)
class FileDelta:
    """One changed named FDS payload."""

    side: int
    name: str
    load_address: int
    old_size: int
    new_size: int
    changed_bytes: int
    first_difference: int | None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _indexed_files(image: FdsImage) -> dict[tuple[int, str, int], FdsFile]:
    return {
        (side.index, entry.name, entry.load_address): entry
        for side in image.sides
        for entry in side.files
    }


def _first_difference(left: bytes, right: bytes) -> int | None:
    common = min(len(left), len(right))
    mismatch = next((i for i in range(common) if left[i] != right[i]), None)
    if mismatch is not None:
        return mismatch
    return common if len(left) != len(right) else None


def compare_fds(old_path: Path, new_path: Path) -> list[FileDelta]:
    """Parse each image once and return changed named payloads."""
    old = _indexed_files(FdsImage.read(old_path))
    new = _indexed_files(FdsImage.read(new_path))
    if old.keys() != new.keys():
        missing = sorted(old.keys() - new.keys())
        added = sorted(new.keys() - old.keys())
        raise ValueError(
            "FDS file inventory changed; "
            f"missing={missing}, added={added}"
        )

    deltas: list[FileDelta] = []
    for key in sorted(old):
        left = old[key].data
        right = new[key].data
        if left == right:
            continue
        common = min(len(left), len(right))
        changed = sum(a != b for a, b in zip(left[:common], right[:common]))
        changed += abs(len(left) - len(right))
        deltas.append(
            FileDelta(
                side=key[0],
                name=key[1],
                load_address=key[2],
                old_size=len(left),
                new_size=len(right),
                changed_bytes=changed,
                first_difference=_first_difference(left, right),
            )
        )
    return deltas


def command_fds(args: argparse.Namespace) -> int:
    old_raw = args.old.read_bytes()
    new_raw = args.new.read_bytes()
    print(f"old SHA-256 {_sha256(old_raw)}")
    print(f"new SHA-256 {_sha256(new_raw)}")
    deltas = compare_fds(args.old, args.new)
    print(f"changed payloads: {len(deltas)}")
    for item in deltas:
        first = (
            "-"
            if item.first_difference is None
            else f"0x{item.first_difference:04X}"
        )
        print(
            f"side {item.side} {item.name:8s} @${item.load_address:04X} "
            f"{item.old_size}->{item.new_size} bytes; "
            f"changed={item.changed_bytes}; first={first}"
        )
    return 0


def command_code(args: argparse.Namespace) -> int:
    """Ask git for the whole baseline/current code delta in one process."""
    command = [
        "git",
        "diff",
        "--numstat",
        "--find-renames",
        args.base,
        args.head,
        "--",
        *CODE_PATHS,
    ]
    completed = subprocess.run(
        command, check=False, text=True, capture_output=True
    )
    if completed.returncode:
        sys.stderr.write(completed.stderr)
        return completed.returncode
    sys.stdout.write(completed.stdout)
    return 0


def command_smoke(_args: argparse.Namespace) -> int:
    """Run the runtime-focused suite in one Python process."""
    root = Path(__file__).resolve().parents[1]
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in FOCUSED_TESTS:
        suite.addTests(loader.discover(root / "tests", pattern=f"{name}.py"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


def command_patch_runtime(args: argparse.Namespace) -> int:
    """Patch NOV2 runtime in-process without a helper-script subprocess."""
    from .production_runtime import patch_fds_image

    source = args.input.read_bytes()
    patched = patch_fds_image(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    changed = sum(a != b for a, b in zip(source, patched, strict=True))
    print(f"{args.output} SHA-256 {_sha256(patched)}; changed={changed}")
    return 0


def command_build(args: argparse.Namespace) -> int:
    """Build a candidate in-process; default to one four-side artifact."""
    from .title import DEFAULT_SUBTITLE

    project_root = Path(__file__).resolve().parents[2]
    title = args.title or (
        project_root / "work/title_assets/Time Twist approved native title.png"
    )
    slide = args.slide_title or (
        project_root / "work/title_assets/Time Twist approved native slide.png"
    )
    translations = args.translations or project_root / "work/translations"
    if args.mode == "entropy":
        from .entropy_release import build_entropy_images as builder

        builder_kwargs = {}
    else:
        from .production_release import build_production_images as builder

        builder_kwargs = {"adaptive_dictionary": not args.flat_68}
    outputs, manifest = builder(
        args.zenpen.read_bytes(),
        args.kouhen.read_bytes(),
        translations_directory=translations,
        title_asset=title,
        slide_title_asset=slide,
        subtitle=args.subtitle or DEFAULT_SUBTITLE,
        **builder_kwargs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(outputs["four_side"])
    if args.all_images:
        label = "Entropy" if args.mode == "entropy" else "Production"
        args.output.with_name(
            f"Time-Twist-English-{label}-Zenpen.fds"
        ).write_bytes(outputs["zenpen"])
        args.output.with_name(
            f"Time-Twist-English-{label}-Kouhen.fds"
        ).write_bytes(outputs["kouhen"])
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    print(f"{args.output} SHA-256 {_sha256(outputs['four_side'])}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="time-twist-runtime",
        description="Fast 2026-08-29 vs current runtime-debug operations.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    code = sub.add_parser(
        "code", help="show only the baseline/current code delta"
    )
    code.add_argument("--base", default=BASELINE_COMMIT)
    code.add_argument("--head", default="HEAD")
    code.set_defaults(function=command_code)

    fds = sub.add_parser("fds", help="compare named payloads in two FDS images")
    fds.add_argument("old", type=Path)
    fds.add_argument("new", type=Path)
    fds.set_defaults(function=command_fds)

    smoke = sub.add_parser("smoke", help="run focused runtime tests once")
    smoke.set_defaults(function=command_smoke)

    patch_runtime = sub.add_parser(
        "patch-runtime", help="apply production NOV2 hardening in-process"
    )
    patch_runtime.add_argument("input", type=Path)
    patch_runtime.add_argument("output", type=Path)
    patch_runtime.set_defaults(function=command_patch_runtime)

    build = sub.add_parser("build", help="build a candidate in-process")
    build.add_argument(
        "--mode", choices=("entropy", "production"), default="entropy"
    )
    build.add_argument("--zenpen", type=Path, required=True)
    build.add_argument("--kouhen", type=Path, required=True)
    build.add_argument("--translations", type=Path)
    build.add_argument(
        "--output",
        type=Path,
        default=Path("build/runtime/current.fds"),
    )
    build.add_argument("--manifest", type=Path)
    build.add_argument("--title", type=Path)
    build.add_argument("--slide-title", type=Path)
    build.add_argument("--subtitle")
    build.add_argument(
        "--flat-68",
        action="store_true",
        help="production mode only: disable adaptive entries 69-255",
    )
    build.add_argument(
        "--all-images",
        action="store_true",
        help="also write the separate Zenpen and Kouhen images",
    )
    build.set_defaults(function=command_build)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.function(args))


if __name__ == "__main__":
    raise SystemExit(main())
