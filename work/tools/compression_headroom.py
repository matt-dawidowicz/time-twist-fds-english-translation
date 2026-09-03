"""Measure fast and deep compression headroom for every scenario bank.

This diagnostic deliberately rebuilds real banks from the canonical Japanese
baselines and reviewed English translation maps. It does not write ROMs or
change release metadata. The normal release policy is measured first, then the
same bank is rebuilt with the fast-accept shortcut disabled so the strongest
existing deterministic optimizer is used even when the greedy result fits.

The report answers two separate questions:

* how much fixed-capacity space is currently unused; and
* how much additional space the existing optimizer can recover without any
  codec change or prose shortening.

Those measurements should precede any decision to add a native accelerator or
change the runtime text format.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from time_twist import release as release_module
from time_twist.fds import FdsImage
from time_twist.release_compression import (
    compress_release_groups as compression_policy,
)
from time_twist.release_metadata import SCENARIO_LOCATIONS, ReleasePaths


@dataclass(frozen=True)
class BankCompressionAudit:
    """One bank's fixed-capacity compression comparison."""

    bank: str
    capacity_bytes: int
    fast_packed_bytes: int
    optimized_packed_bytes: int
    fast_headroom_bytes: int
    optimized_headroom_bytes: int
    recovered_bytes: int
    fast_dictionary_entries: int
    optimized_dictionary_entries: int
    fast_seconds: float
    optimized_seconds: float


@contextmanager
def _maximize_headroom_policy() -> Iterator[None]:
    """Temporarily make the release facade use editorial compression policy."""
    original = release_module.compress_release_groups

    def deep_policy(*args: object, **kwargs: object) -> object:
        """Forward one release compression call with deep search forced on."""
        kwargs["maximize_headroom"] = True
        return compression_policy(*args, **kwargs)

    release_module.compress_release_groups = deep_policy  # type: ignore[assignment]
    try:
        yield
    finally:
        release_module.compress_release_groups = original


def _source_bank(
    bank_name: str,
    *,
    zenpen: FdsImage,
    kouhen: FdsImage,
) -> bytes:
    """Return one scenario component from its canonical two-side baseline."""
    image_name, side = SCENARIO_LOCATIONS[bank_name]
    image = zenpen if image_name == "zenpen" else kouhen
    return image.sides[side].find_file(bank_name).data


def _build_once(
    source: bytes,
    bank_name: str,
    *,
    paths: ReleasePaths,
    temporary_directory: Path,
) -> tuple[release_module.ScenarioBuildResult, float]:
    """Build one bank and return its result plus wall-clock seconds."""
    started = perf_counter()
    result = release_module.build_scenario_bank(
        source,
        bank_name,
        temporary_directory=temporary_directory,
        translations_directory=paths.translations,
    )
    return result, perf_counter() - started


def audit_bank(
    bank_name: str,
    *,
    paths: ReleasePaths,
    zenpen: FdsImage,
    kouhen: FdsImage,
    temporary_directory: Path,
) -> BankCompressionAudit:
    """Compare normal and maximize-headroom compression for one bank."""
    source = _source_bank(bank_name, zenpen=zenpen, kouhen=kouhen)
    fast, fast_seconds = _build_once(
        source,
        bank_name,
        paths=paths,
        temporary_directory=temporary_directory,
    )
    with _maximize_headroom_policy():
        optimized, optimized_seconds = _build_once(
            source,
            bank_name,
            paths=paths,
            temporary_directory=temporary_directory,
        )

    if optimized.capacity_bytes != fast.capacity_bytes:
        raise ValueError(
            f"{bank_name} capacity changed between compression policies"
        )
    if optimized.packed_bytes > fast.packed_bytes:
        raise ValueError(
            f"{bank_name} optimized result grew from {fast.packed_bytes} to "
            f"{optimized.packed_bytes} bytes"
        )
    capacity = fast.capacity_bytes
    return BankCompressionAudit(
        bank=bank_name,
        capacity_bytes=capacity,
        fast_packed_bytes=fast.packed_bytes,
        optimized_packed_bytes=optimized.packed_bytes,
        fast_headroom_bytes=capacity - fast.packed_bytes,
        optimized_headroom_bytes=capacity - optimized.packed_bytes,
        recovered_bytes=fast.packed_bytes - optimized.packed_bytes,
        fast_dictionary_entries=fast.dictionary_entries,
        optimized_dictionary_entries=optimized.dictionary_entries,
        fast_seconds=fast_seconds,
        optimized_seconds=optimized_seconds,
    )


def audit_project(
    project_root: Path,
    *,
    banks: tuple[str, ...] | None = None,
) -> tuple[BankCompressionAudit, ...]:
    """Audit selected banks, defaulting to the complete scenario corpus."""
    paths = ReleasePaths.from_project_root(project_root)
    zenpen = FdsImage.from_bytes(paths.zenpen_baseline.read_bytes())
    kouhen = FdsImage.from_bytes(paths.kouhen_baseline.read_bytes())
    selected = banks if banks is not None else tuple(SCENARIO_LOCATIONS)
    unknown = sorted(set(selected) - set(SCENARIO_LOCATIONS))
    if unknown:
        raise ValueError(f"unknown scenario bank(s): {', '.join(unknown)}")

    with tempfile.TemporaryDirectory(
        prefix="time-twist-headroom-"
    ) as directory:
        temporary_directory = Path(directory)
        return tuple(
            audit_bank(
                bank,
                paths=paths,
                zenpen=zenpen,
                kouhen=kouhen,
                temporary_directory=temporary_directory,
            )
            for bank in selected
        )


def _print_table(results: tuple[BankCompressionAudit, ...]) -> None:
    """Print a compact human-readable headroom table."""
    header = (
        "Bank   Capacity  Fast  Deep  FastFree  DeepFree  Saved  "
        "Dict(F/D)  Time(F/D)s"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.bank:<6} "
            f"{result.capacity_bytes:>8} "
            f"{result.fast_packed_bytes:>5} "
            f"{result.optimized_packed_bytes:>5} "
            f"{result.fast_headroom_bytes:>8} "
            f"{result.optimized_headroom_bytes:>8} "
            f"{result.recovered_bytes:>6} "
            f"{result.fast_dictionary_entries:>2}/"
            f"{result.optimized_dictionary_entries:<2}     "
            f"{result.fast_seconds:>7.3f}/"
            f"{result.optimized_seconds:<7.3f}"
        )
    print()
    print(
        "Total recovered bytes: "
        f"{sum(result.recovered_bytes for result in results)}"
    )
    print(
        "Total optimized free bytes: "
        f"{sum(result.optimized_headroom_bytes for result in results)}"
    )
    print(
        "Total optimization time: "
        f"{sum(result.optimized_seconds for result in results):.3f}s"
    )


def build_parser() -> argparse.ArgumentParser:
    """Return the standalone audit argument parser."""
    parser = argparse.ArgumentParser(
        description="Compare fast and deep Time Twist scenario compression.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="repository checkout containing work/baseline and work/translations",
    )
    parser.add_argument(
        "--bank",
        action="append",
        dest="banks",
        choices=tuple(SCENARIO_LOCATIONS),
        help="audit only this bank; may be supplied more than once",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of a table",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the compression audit without modifying project files."""
    args = build_parser().parse_args(argv)
    banks = tuple(args.banks) if args.banks else None
    results = audit_project(args.project_root, banks=banks)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_table(results)


if __name__ == "__main__":
    main()
