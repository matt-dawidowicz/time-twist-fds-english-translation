"""Materialize complete production translation maps from reviewed prose."""

from __future__ import annotations

import argparse
from pathlib import Path

from time_twist.production_translation import materialize_production_maps

BANK_NAMES = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
)


def main() -> int:
    """Write the complete game-facing production maps to a chosen directory."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    counts = materialize_production_maps(
        BANK_NAMES,
        base_directory=root / "work" / "translations",
        override_directory=root / "work" / "production_overrides",
        review_directory=root / "review" / "production_retranslation",
        output_directory=args.output.resolve(),
    )
    total = sum(counts.values())
    print(f"materialized {total} scenario records across {len(counts)} banks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
