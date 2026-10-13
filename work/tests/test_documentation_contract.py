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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORK_ROOT = PROJECT_ROOT / "work"


class DocumentationContractTests(unittest.TestCase):
    """Enforce the documentation baseline for all maintained Python code."""

    @staticmethod
    def _trees() -> list[tuple[Path, ast.Module]]:
        """Parse every maintained Python source file without importing it.

        Static parsing keeps this policy fixture-free: checking a docstring must
        never require a ROM, title asset, emulator, or translation map.
        """
        return [
            (
                path,
                ast.parse(path.read_text(encoding="utf-8")),
            )
            for path in sorted(WORK_ROOT.rglob("*.py"))
            if "__pycache__" not in path.parts
        ]

    def test_package_docstrings_are_not_generated_placeholders(self) -> None:
        """Reject empty boilerplate in the maintained runtime package."""
        placeholders: list[str] = []
        package = WORK_ROOT / "time_twist"
        for path, tree in self._trees():
            if path.parent != package:
                continue
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                doc = ast.get_docstring(node)
                if doc is None:
                    continue
                first_line = doc.splitlines()[0]
                if (
                    first_line.startswith("Support the ")
                    and first_line.endswith(" operation for this module.")
                ) or first_line.endswith(" state and behavior."):
                    placeholders.append(
                        f"{path.relative_to(PROJECT_ROOT)}:"
                        f"{getattr(node, 'lineno', 1)}: {first_line}"
                    )
        self.assertEqual(
            placeholders,
            [],
            "Replace generated boilerplate with behavior/format contracts:\n"
            + "\n".join(placeholders),
        )

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
