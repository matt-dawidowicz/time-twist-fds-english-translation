"""Fast local feedback for ordinary translation and code iteration.

This intentionally does not duplicate the complete CI/release gate. It catches
syntax errors, validates the public source tree, and runs the small canonical
translation regression suite. Full lint, typing, unit tests, packaging, and
release certification belong at PR/release boundaries.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> None:
    """Run one required quick-check command from the repository root."""
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    """Run the cheap deterministic checks used during normal iteration."""
    python = sys.executable
    run(python, "-m", "compileall", "-q", "work/time_twist", "work/tools")
    run(python, "work/tools/check_public_tree.py")
    run(
        python,
        "-m",
        "unittest",
        "discover",
        "-s",
        "work/tests",
        "-p",
        "test_production_translation.py",
        "-v",
    )


if __name__ == "__main__":
    main()
