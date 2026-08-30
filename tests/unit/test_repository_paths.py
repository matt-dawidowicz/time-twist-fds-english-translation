"""Protect repository path discovery from directory-depth coupling."""

from __future__ import annotations

import re
import unittest

from tools.paths import PROJECT_ROOT, find_project_root

_DEPTH_COUPLED_PARENTS = re.compile(r"\.parents\[\s*\d+\s*\]")


class RepositoryPathTests(unittest.TestCase):
    """Keep shared repository discovery stable as files move between packages."""

    def test_project_root_is_found_from_nested_test_path(self) -> None:
        """Resolve the checkout without relying on the caller's nesting depth."""
        start = PROJECT_ROOT / "tests" / "unit" / "nested" / "example.py"
        self.assertEqual(find_project_root(start), PROJECT_ROOT)

    def test_test_sources_do_not_index_path_parents(self) -> None:
        """Require test repository paths to flow through the shared abstraction."""
        offenders: list[str] = []
        tests_root = PROJECT_ROOT / "tests"
        for path in sorted(tests_root.rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            if _DEPTH_COUPLED_PARENTS.search(source):
                offenders.append(path.relative_to(PROJECT_ROOT).as_posix())

        self.assertEqual(
            offenders,
            [],
            "test files must not depend on parents[n] directory depth: "
            + ", ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
