"""Resolve repository paths without coupling tests to directory depth."""

from __future__ import annotations

from pathlib import Path


def _find_project_root(start: Path) -> Path:
    """Find the checkout root from a test or maintenance-tool path."""
    resolved = start.expanduser().resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "work" / "time_twist"
        ).is_dir():
            return candidate
    raise RuntimeError(f"could not locate project root from {start}")


PROJECT_ROOT = _find_project_root(Path(__file__))
WORK_ROOT = PROJECT_ROOT / "work"
UNIT_TEST_ROOT = PROJECT_ROOT / "tests" / "unit"
INTEGRATION_TEST_ROOT = PROJECT_ROOT / "tests" / "integration"
FIXTURE_MANIFEST = (
    PROJECT_ROOT / "tests" / "fixtures" / "integration_fixtures.json"
)
