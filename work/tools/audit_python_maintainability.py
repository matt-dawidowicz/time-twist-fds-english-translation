"""Inventory every public Python source without importing or executing it.

This read-only AST audit flags large functions, missing documentation, and
potentially duplicated bodies. A call-site search alone cannot prove dead
code: public APIs, private integration tests and dynamic uses also exist.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LONG_FUNCTION_LINES = 80


def _source_paths(root: Path) -> tuple[Path, ...]:
    """Find production, test, and maintenance Python sources."""
    return tuple(
        sorted(
            path
            for directory in (root / "work", root / "release_patcher")
            for path in directory.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def _body_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Hash a function body, ignoring only its introductory docstring."""
    body = node.body
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    structural = ast.dump(
        ast.Module(body=body, type_ignores=[]), include_attributes=False
    )
    return hashlib.sha256(structural.encode("utf-8")).hexdigest()


def audit(root: Path) -> dict[str, object]:
    """Describe every Python source and conservative refactor candidates."""
    files: list[dict[str, object]] = []
    large: list[dict[str, object]] = []
    undocumented: list[str] = []
    risky: list[str] = []
    fingerprints: dict[str, list[str]] = defaultdict(list)
    all_functions = 0
    total_lines = 0

    for source in _source_paths(root):
        relative = source.relative_to(root).as_posix()
        source_text = source.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=relative)
        lines = source_text.splitlines()
        functions = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        total_lines += len(lines)
        all_functions += len(functions)
        files.append(
            {
                "path": relative,
                "lines": len(lines),
                "definitions": len(functions),
                "module_docstring": bool(ast.get_docstring(tree)),
            }
        )
        production = relative.startswith(
            ("work/time_twist/", "release_patcher/")
        ) and not relative.endswith("test_public_patcher.py")
        for function in functions:
            location = f"{relative}:{function.lineno} {function.name}"
            size = function.end_lineno - function.lineno + 1
            if size >= LONG_FUNCTION_LINES:
                large.append({"location": location, "lines": size})
            if production and not ast.get_docstring(function):
                undocumented.append(location)
            if size >= 6:
                fingerprints[_body_fingerprint(function)].append(location)

        for node in ast.walk(tree):
            issue = None
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issue = "bare except"
            elif isinstance(node, ast.ImportFrom) and any(
                name.name == "*" for name in node.names
            ):
                issue = "wildcard import"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {
                    "eval",
                    "exec",
                }:
                    issue = f"dynamic {node.func.id}()"
                elif any(
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                    for kw in node.keywords
                ):
                    issue = "subprocess shell=True"
            if issue is not None:
                risky.append(f"{relative}:{node.lineno} {issue}")

    duplicates = [
        values for values in fingerprints.values() if len(values) > 1
    ]
    return {
        "schema": "Time Twist Python maintainability audit v1",
        "python_files": len(files),
        "source_lines": total_lines,
        "function_definitions": all_functions,
        "files": files,
        "large_functions": sorted(
            large, key=lambda entry: (-entry["lines"], entry["location"])
        ),
        "undocumented_production_functions": sorted(undocumented),
        "potential_duplicate_bodies": sorted(
            duplicates, key=lambda entries: entries[0]
        ),
        "risk_patterns": sorted(risky),
    }


def markdown(report: dict[str, object]) -> str:
    """Summarize the full JSON inventory for human review."""
    lines = [
        "# Python source audit (generated)",
        "",
        "Static AST analysis is not proof of dead code or runtime safety.",
        "The JSON form contains a line count for every scanned file.",
        "",
        f"- Python files: {report['python_files']}",
        f"- Source lines: {report['source_lines']}",
        f"- Function definitions: {report['function_definitions']}",
        "",
        "## Long functions (review candidates)",
        "",
    ]
    lines += [
        f"- `{item['location']}`: {item['lines']} lines"
        for item in report["large_functions"][:30]
    ]
    lines += ["", "## Missing production-function docstrings", ""]
    lines += [
        f"- `{name}`" for name in report["undocumented_production_functions"]
    ]
    lines += ["", "## Identical function bodies (manual review only)", ""]
    for group in report["potential_duplicate_bodies"]:
        lines.append("- " + ", ".join(f"`{name}`" for name in group))
    lines += ["", "## Risk patterns", ""]
    lines += [f"- `{item}`" for item in report["risk_patterns"]]
    if not report["risk_patterns"]:
        lines.append(
            "- No scanned dynamic execution, wildcard imports, bare "
            "exceptions, or literal shell=True calls."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    """Print detailed JSON or concise Markdown for repeatable audits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown"
    )
    args = parser.parse_args()
    result = audit(ROOT)
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(markdown(result), end="")


if __name__ == "__main__":
    main()
