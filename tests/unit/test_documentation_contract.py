"""Keep the current source tree navigable for future translators and hackers.

The project is intentionally source-only: contributors often need to understand
packed text, recovered FDS overlays, or a guarded binary patch without having
the private retail inputs locally.  Requiring documentation on every Python
module, class, and function makes the public checkout explain its own intent.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tests.support.paths import PROJECT_ROOT

WORK_ROOT = PROJECT_ROOT / "work"


class DocumentationContractTests(unittest.TestCase):
    """Enforce the documentation baseline for all maintained Python code."""

    @staticmethod
    def _trees() -> list[tuple[Path, ast.Module]]:
        """Parse every maintained Python source file without importing it.

        Static parsing keeps this policy fixture-free: checking a docstring must
        never require a ROM, title asset, emulator, or private translation map.
        """
        return [
            (
                path,
                ast.parse(path.read_text(encoding="utf-8")),
            )
            for path in sorted(WORK_ROOT.rglob("*.py"))
            if "__pycache__" not in path.parts
        ]

    def test_every_module_class_and_function_explains_its_purpose(
        self,
    ) -> None:
        """Require documentation for every maintained Python definition.

        A terse name is not enough for this project: a future contributor must
        be able to distinguish current release safeguards from source-format
        facts, test helpers, and intentionally preserved game behavior.
        """
        missing: list[str] = []
        for path, tree in self._trees():
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            if ast.get_docstring(tree) is None:
                missing.append(f"{relative}: module docstring")
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ClassDef)
                    and ast.get_docstring(node) is None
                ):
                    missing.append(
                        f"{relative}:{node.lineno}: class {node.name}"
                    )
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and (ast.get_docstring(node) is None):
                    missing.append(
                        f"{relative}:{node.lineno}: function {node.name}"
                    )
        self.assertEqual(
            missing,
            [],
            "Add a purpose docstring before introducing new maintained code:\n"
            + "\n".join(missing),
        )


if __name__ == "__main__":
    unittest.main()
