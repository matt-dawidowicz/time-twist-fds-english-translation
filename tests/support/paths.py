"""Test-suite paths derived from the shared repository abstraction."""

from __future__ import annotations

from tools.paths import PROJECT_ROOT, SOURCE_ROOT, WORK_ROOT

UNIT_TEST_ROOT = PROJECT_ROOT / "tests" / "unit"
INTEGRATION_TEST_ROOT = PROJECT_ROOT / "tests" / "integration"
FIXTURE_MANIFEST = (
    PROJECT_ROOT / "tests" / "fixtures" / "integration_fixtures.json"
)

__all__ = [
    "FIXTURE_MANIFEST",
    "INTEGRATION_TEST_ROOT",
    "PROJECT_ROOT",
    "SOURCE_ROOT",
    "UNIT_TEST_ROOT",
    "WORK_ROOT",
]
