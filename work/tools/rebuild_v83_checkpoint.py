"""Rebuild v83 from the exact Simon-corrected public four-side release."""

from __future__ import annotations

import argparse
from pathlib import Path

from time_twist.v83_checkpoint import (
    V83_SHA256,
    promote_release_to_v83,
    validate_v83_sources,
)


def main() -> None:
    """Validate the input, reconstruct v83, audit source, and write the ROM."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = promote_release_to_v83(args.source.read_bytes())
    root = Path(__file__).resolve().parents[2]
    validate_v83_sources(result, root / "work" / "translations")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(result)
    print(f"Verified 1,305 records and 721 labels; SHA-256 {V83_SHA256}")


if __name__ == "__main__":
    main()
