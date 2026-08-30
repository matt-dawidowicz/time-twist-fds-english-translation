"""Protect test paths from directory-depth coupling."""

from __future__ import annotations

import re
import unittest

from tests.support.paths import PROJECT_ROOT

_DEPTH_COUPLED_PARENTS = re.compile(r"\.parents\[\s*\d+\s*\]")


class TestPathArchitectureTests(unittest.TestCase):
    """Keep test-source path discovery independent of file nesting depth."""

    def test_test_sources_do_not_index_path_parents(self) -> None:
        """Require repository paths to flow through the shared abstraction."""
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
