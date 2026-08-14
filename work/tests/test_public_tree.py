"""Regression tests for the current source-only public-tree policy."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.check_public_tree import check_public_tree


class PublicTreePolicyTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    @staticmethod
    def make_public_skeleton(root: Path) -> None:
        """Provide a deterministic helper for the current contract tests."""
        (root / "work" / "time_twist").mkdir(parents=True)
        (root / "work" / "translations").mkdir()
        (root / "work" / "title_assets").mkdir()
        (root / "pyproject.toml").write_text(
            "[project]\nname='test'\n", encoding="utf-8"
        )
        (root / "work" / "integration_fixtures.json").write_text(
            "{}\n", encoding="utf-8"
        )

    def test_clean_synthetic_public_tree_passes(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_public_skeleton(root)
            self.assertEqual(check_public_tree(root), [])

    def test_private_artifacts_and_personal_paths_are_rejected(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_public_skeleton(root)
            (root / "private.fds").write_bytes(b"fixture")
            (root / "candidate.zip").write_bytes(b"fixture")
            (root / "runtime-state.mss").write_bytes(b"fixture")
            (root / "emulator_settings.json").write_text(
                "{}\n", encoding="utf-8"
            )
            personal_path = (
                "C:" + "\\Users\\" + "developer\\Downloads\\review.html"
            )
            (root / "notes.txt").write_text(personal_path, encoding="utf-8")
            problems = check_public_tree(root)
            self.assertTrue(
                any("private.fds" in problem for problem in problems)
            )
            self.assertTrue(
                any("candidate.zip" in problem for problem in problems)
            )
            self.assertTrue(
                any("runtime-state.mss" in problem for problem in problems)
            )
            self.assertTrue(
                any(
                    "emulator_settings.json" in problem for problem in problems
                )
            )
            self.assertTrue(
                any(
                    "machine-local absolute path" in problem
                    for problem in problems
                )
            )


if __name__ == "__main__":
    unittest.main()
