"""Synthetic project construction shared by release unit tests."""

from __future__ import annotations

from pathlib import Path

from time_twist.project import KNOWN_SCENARIO_BANKS


def make_synthetic_project(root: Path) -> Path:
    """Create the minimal public checkout contract used by release tests."""
    work = root / "work"
    translations = work / "translations"
    title_assets = work / "title_assets"
    baseline = work / "baseline"
    code = root / "src" / "time_twist"
    translations.mkdir(parents=True)
    title_assets.mkdir()
    baseline.mkdir()
    code.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "[project]\nname='test'\n", encoding="utf-8"
    )
    (code / "__init__.py").write_text(
        '"""Synthetic package."""\n', encoding="utf-8"
    )
    for bank in KNOWN_SCENARIO_BANKS:
        (translations / f"{bank}.json").write_text("{}\n", encoding="utf-8")
    (title_assets / "Time Twist approved native title.png").write_bytes(
        b"title"
    )
    (title_assets / "Time Twist approved native slide.png").write_bytes(
        b"slide"
    )
    (baseline / "time_twist_zenpen_japan.fds").write_bytes(b"zenpen")
    (baseline / "time_twist_kouhen_japan.fds").write_bytes(b"kouhen")
    return root
