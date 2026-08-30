"""Canonical repository paths for developer-facing tooling."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """Locate the checkout root from any tool or test path."""
    seed = (start or Path(__file__)).expanduser().resolve()
    if seed.is_file():
        seed = seed.parent
    for candidate in (seed, *seed.parents):
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src" / "time_twist").is_dir()
            and (candidate / "work" / "translations").is_dir()
        ):
            return candidate
    raise RuntimeError(f"could not locate Time Twist project root from {seed}")


PROJECT_ROOT = find_project_root()
SOURCE_ROOT = PROJECT_ROOT / "src"
WORK_ROOT = PROJECT_ROOT / "work"
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
