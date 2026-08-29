"""Run fixture-free unit tests or the private ROM integration suite.

Public CI runs ``unit``. Maintainers can overlay the small private input bundle
and run ``integration`` or ``all``. Integration preflight validates the two
baseline FDS images plus emulator captures, then regenerates all extracted ROM
payloads from those baselines. Generated translation/build/output binaries are
never permanent test fixtures.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

WORK_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WORK_ROOT.parent
FIXTURE_MANIFEST = WORK_ROOT / "integration_fixtures.json"
sys.path.insert(0, str(WORK_ROOT))

from time_twist.fds import FdsImage  # noqa: E402

UNIT_TEST_REQUIREMENTS = {
    "PIL": "Pillow==12.3.0",
    "hypothesis": "hypothesis>=6.100,<7",
}
PRIVATE_FIXTURE_SCHEMA = "Time Twist private integration fixtures v2"
BASELINE_EXTRACTIONS = (
    (
        WORK_ROOT / "baseline" / "time_twist_zenpen_japan.fds",
        WORK_ROOT / "extracted_zenpen",
    ),
    (
        WORK_ROOT / "baseline" / "time_twist_kouhen_japan.fds",
        WORK_ROOT / "extracted_kouhen",
    ),
)
OBSOLETE_GENERATED_DIRECTORIES = (
    WORK_ROOT / "build",
    WORK_ROOT / "translated_banks",
)


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
    """Return an uppercase SHA-256 digest without loading the whole file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_filename(name: str) -> str:
    """Mirror the public extractor's portable FDS filename transformation."""
    return "".join(
        char if char.isalnum() or char in "-_" else "_" for char in name
    )


def _extract_baseline(image_path: Path, output_directory: Path) -> None:
    """Regenerate one deterministic extracted-bank directory from a baseline."""
    if output_directory.exists():
        shutil.rmtree(output_directory)
    output_directory.mkdir(parents=True)
    image = FdsImage.read(image_path)
    for side in image.sides:
        for entry in side.files:
            filename = (
                f"side{side.index}_{entry.index:02d}_"
                f"{_safe_filename(entry.name)}_{entry.load_address:04X}.bin"
            )
            (output_directory / filename).write_bytes(entry.data)


def validate_integration_fixtures() -> None:
    """Validate irreducible private inputs before generating derived fixtures."""
    payload = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    if payload.get("schema") != PRIVATE_FIXTURE_SCHEMA:
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
        if not isinstance(record, dict):
            failures.append(f"invalid manifest record {relative}")
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
            "private integration inputs are incomplete or changed. Overlay "
            "the private input bundle at the project root:\n"
            f"{shown}{suffix}"
        )


def prepare_integration_workspace() -> None:
    """Rebuild derived source extracts and remove obsolete generated oracles."""
    for directory in OBSOLETE_GENERATED_DIRECTORIES:
        if directory.exists():
            shutil.rmtree(directory)
    for image_path, output_directory in BASELINE_EXTRACTIONS:
        _extract_baseline(image_path, output_directory)


def discover(directory: str) -> unittest.TestSuite:
    """Discover an importable suite beneath ``work``."""
    return unittest.defaultTestLoader.discover(
        start_dir=str(WORK_ROOT / directory),
        pattern="test*.py",
        top_level_dir=str(WORK_ROOT),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the selected suite and reject all skips."""
    parser = argparse.ArgumentParser(prog="python work/run_tests.py")
    parser.add_argument(
        "suite",
        nargs="?",
        choices=("unit", "integration", "all"),
        default="unit",
    )
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    # Tests and helper scripts may open project-relative resources. Normalize
    # execution so invoking this runner from any directory uses this checkout.
    os.chdir(PROJECT_ROOT)

    # Hypothesis otherwise stores a database under ``.hypothesis`` in the
    # checkout. Generated examples are useful only for this invocation.
    previous_storage = os.environ.get("HYPOTHESIS_STORAGE_DIRECTORY")
    with tempfile.TemporaryDirectory(
        prefix="time-twist-hypothesis-"
    ) as temporary_storage:
        os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = temporary_storage
        suite = unittest.TestSuite()
        if args.suite in {"unit", "all"}:
            validate_unit_dependencies()
            suite.addTests(discover("tests"))
        if args.suite in {"integration", "all"}:
            validate_integration_fixtures()
            prepare_integration_workspace()
            suite.addTests(discover("integration_tests"))

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
