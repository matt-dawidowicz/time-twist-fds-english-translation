"""Run fixture-free unit tests or the private ROM integration suite.

Public CI runs ``unit``. Maintainers can overlay the separately
distributed private fixture bundle and run ``integration`` or ``all``.
The runner verifies fixture hashes before discovery so missing local ROM
data is an explicit setup error, never a misleading skipped test.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support.paths import (
    FIXTURE_MANIFEST,
    INTEGRATION_TEST_ROOT,
    PROJECT_ROOT,
    UNIT_TEST_ROOT,
    WORK_ROOT,
)

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(WORK_ROOT))

UNIT_TEST_REQUIREMENTS = {
    "PIL": "Pillow==12.3.0",
    "hypothesis": "hypothesis>=6.100,<7",
}


def validate_unit_dependencies() -> None:
    """Fail clearly when fixture-free unit-test dependencies are missing."""
    missing = [
        requirement
        for module, requirement in UNIT_TEST_REQUIREMENTS.items()
        if importlib.util.find_spec(module) is None
    ]
    if not missing:
        return
    shown = "\n".join(f"  - {requirement}" for requirement in missing)
    raise SystemExit(
        "unit test dependencies are missing. Install the development "
        "dependencies before running the public test suite, for example:\n"
        '  python -m pip install -e ".[dev]"\n'
        "or, for test-only dependencies:\n"
        "  python -m pip install -r requirements.txt\n"
        f"Missing:\n{shown}"
    )


def sha256(path: Path) -> str:
    """Return an uppercase SHA-256 digest for one local fixture."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_integration_fixtures() -> None:
    """Fail before discovery unless the complete private overlay exists."""
    payload = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != "Time Twist private integration fixtures v1":
        raise SystemExit("unsupported integration fixture manifest schema")
    files = payload.get("files")
    if not isinstance(files, dict):
        raise SystemExit("integration fixture manifest has no file mapping")

    failures: list[str] = []
    for relative, record in files.items():
        path = PROJECT_ROOT / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
            continue
        if path.stat().st_size != record.get("bytes"):
            failures.append(f"wrong size {relative}")
            continue
        if sha256(path) != record.get("sha256"):
            failures.append(f"wrong hash {relative}")
    if failures:
        shown = "\n".join(f"  - {failure}" for failure in failures[:12])
        extra = len(failures) - 12
        suffix = f"\n  - ... and {extra} more" if extra > 0 else ""
        raise SystemExit(
            "private integration fixtures are incomplete or changed. "
            "Overlay the private fixture bundle at the project root:\n"
            f"{shown}{suffix}"
        )


def discover(directory: Path) -> unittest.TestSuite:
    """Discover an importable suite beneath the top-level test package."""
    return unittest.defaultTestLoader.discover(
        start_dir=str(directory),
        pattern="test*.py",
        top_level_dir=str(PROJECT_ROOT),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the selected suite and reject all skips."""
    parser = argparse.ArgumentParser(
        prog="python -m tools.maintenance.run_tests"
    )
    parser.add_argument(
        "suite",
        nargs="?",
        choices=("unit", "integration", "all"),
        default="unit",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    os.chdir(PROJECT_ROOT)

    previous_storage = os.environ.get("HYPOTHESIS_STORAGE_DIRECTORY")
    with tempfile.TemporaryDirectory(
        prefix="time-twist-hypothesis-"
    ) as temporary_storage:
        os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = temporary_storage
        suite = unittest.TestSuite()
        if args.suite in {"unit", "all"}:
            validate_unit_dependencies()
            suite.addTests(discover(UNIT_TEST_ROOT))
        if args.suite in {"integration", "all"}:
            validate_integration_fixtures()
            suite.addTests(discover(INTEGRATION_TEST_ROOT))

        result = unittest.TextTestRunner(verbosity=1 if args.quiet else 2).run(
            suite
        )

    if previous_storage is None:
        os.environ.pop("HYPOTHESIS_STORAGE_DIRECTORY", None)
    else:
        os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = previous_storage
    if result.skipped:
        print(
            "skipped tests are not permitted in supported test suites",
            file=sys.stderr,
        )
        return 1
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
