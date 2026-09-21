"""Fast pre-merge hygiene checks for translation/release changes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*args: str) -> None:
    """Run one required hygiene command from the repository root."""
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    """Fail fast on syntax, formatting, materialization, or checkpoint drift."""
    python = sys.executable
    run(python, "-m", "compileall", "-q", "work")
    run(
        python,
        "work/tools/materialize_production_translations.py",
        "--repo-root",
        ".",
        "--output",
        "work/build/production_translations",
    )
    run(python, "-m", "black", "--check", "--diff", "work")
    run(python, "-m", "ruff", "check", "work")
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
    run(
        python,
        "-m",
        "unittest",
        "discover",
        "-s",
        "work/tests",
        "-p",
        "test_v38_recovered_checkpoint.py",
        "-v",
    )


if __name__ == "__main__":
    main()
