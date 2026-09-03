"""Measure fast and deep compression headroom for every scenario bank.

This diagnostic uses only public, reproducible project data: reviewed English
translation maps, recovered fixed-capacity facts, fixed-menu records, and the
canonical packed-text compressor. It deliberately does not require Japanese ROM
baselines.

For each bank it measures the normal fast release policy and the same corpus
with the fast-accept shortcut disabled. Deep search may use either the canonical
Python optimizer or the optional Python-verified native Rust accelerator.

A private ROM-backed candidate rebuild remains the final source-byte and
fixed-address compatibility gate. This tool answers the build-side question:
how much fixed-footprint text capacity is available before changing the codec?
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter

from time_twist.capacity import playable_capacity
from time_twist.compression import packed_size
from time_twist.english import encode_english
from time_twist.project import (
    KNOWN_SCENARIO_BANKS,
    required_dictionary_entries,
)
from time_twist.release_compression import (
    OPTIMIZATION_BACKENDS,
    compress_release_groups,
)
from time_twist.textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT, PackedSymbol
from time_twist.ui import (
    FIXED_RECORD_TABLE_SPECS,
    fixed_record_table_page_pointer_bytes,
)

RECORD_ID_RE = re.compile(
    r"^(?P<bank>[A-Z0-9]+?)/g(?P<group>\d+)/r(?P<record>\d+)$"
)


@dataclass(frozen=True)
class BankCompressionAudit:
    """One bank's fixed-capacity compression comparison."""

    bank: str
    optimized_backend: str
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


def _load_groups(
    translations_directory: Path,
    bank_name: str,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    """Encode one public translation map into stable group/record order."""
    path = translations_directory / f"{bank_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")

    indexed: dict[int, dict[int, tuple[PackedSymbol, ...]]] = {}
    for record_id, text in payload.items():
        if not isinstance(record_id, str) or not isinstance(text, str):
            raise ValueError(f"{path} must map string IDs to string text")
        match = RECORD_ID_RE.fullmatch(record_id)
        if match is None or match.group("bank") != bank_name:
            raise ValueError(f"invalid {bank_name} record ID: {record_id}")
        group_index = int(match.group("group"))
        record_index = int(match.group("record"))
        records = indexed.setdefault(group_index, {})
        if record_index in records:
            raise ValueError(f"duplicate record ID: {record_id}")
        records[record_index] = encode_english(text)

    expected_groups = list(range(len(indexed)))
    if sorted(indexed) != expected_groups:
        raise ValueError(
            f"{bank_name} groups are not contiguous: {sorted(indexed)}"
        )

    groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    for group_index in expected_groups:
        records = indexed[group_index]
        expected_records = list(range(len(records)))
        if sorted(records) != expected_records:
            raise ValueError(
                f"{bank_name}/g{group_index} records are not contiguous: "
                f"{sorted(records)}"
            )
        groups.append(tuple(records[index] for index in expected_records))
    return tuple(groups)


def _compress_bank(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    bank_name: str,
    *,
    maximize_headroom: bool,
    optimization_backend: str = "python",
) -> tuple[int, int, int, float]:
    """Return used bytes, capacity, dictionary count, and elapsed seconds."""
    capacity = playable_capacity(bank_name)
    pointer_bytes = 2 * (len(groups) - 1)
    started = perf_counter()

    if bank_name in FIXED_RECORD_TABLE_SPECS:
        spec = FIXED_RECORD_TABLE_SPECS[bank_name]
        menu_records = tuple(encode_english(text) for text in spec.records)
        combined_groups = (*groups, menu_records)
        structural_bytes = (
            pointer_bytes + fixed_record_table_page_pointer_bytes(bank_name)
        )
        compressed, dictionary = compress_release_groups(
            combined_groups,
            max_bytes=capacity - structural_bytes,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
            maximize_headroom=maximize_headroom,
            optimization_backend=(
                optimization_backend if maximize_headroom else "python"
            ),
        )
        used = packed_size(compressed, dictionary) + structural_bytes
    else:
        compressed, dictionary = compress_release_groups(
            groups,
            required_entries=required_dictionary_entries(bank_name),
            max_bytes=capacity - pointer_bytes,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
            maximize_headroom=maximize_headroom,
            optimization_backend=(
                optimization_backend if maximize_headroom else "python"
            ),
        )
        used = packed_size(compressed, dictionary) + pointer_bytes

    return used, capacity, len(dictionary), perf_counter() - started


def audit_bank(
    translations_directory: Path,
    bank_name: str,
    *,
    optimization_backend: str = "python",
) -> BankCompressionAudit:
    """Compare normal and maximize-headroom compression for one bank."""
    groups = _load_groups(translations_directory, bank_name)
    fast_used, capacity, fast_entries, fast_seconds = _compress_bank(
        groups,
        bank_name,
        maximize_headroom=False,
    )
    deep_used, deep_capacity, deep_entries, deep_seconds = _compress_bank(
        groups,
        bank_name,
        maximize_headroom=True,
        optimization_backend=optimization_backend,
    )
    if deep_capacity != capacity:
        raise ValueError(f"{bank_name} capacity changed between policies")
    if deep_used > fast_used:
        raise ValueError(
            f"{bank_name} optimized result grew from {fast_used} to "
            f"{deep_used} bytes"
        )
    return BankCompressionAudit(
        bank=bank_name,
        optimized_backend=optimization_backend,
        capacity_bytes=capacity,
        fast_packed_bytes=fast_used,
        optimized_packed_bytes=deep_used,
        fast_headroom_bytes=capacity - fast_used,
        optimized_headroom_bytes=capacity - deep_used,
        recovered_bytes=fast_used - deep_used,
        fast_dictionary_entries=fast_entries,
        optimized_dictionary_entries=deep_entries,
        fast_seconds=fast_seconds,
        optimized_seconds=deep_seconds,
    )


def audit_project(
    project_root: Path,
    *,
    banks: tuple[str, ...] | None = None,
    optimization_backend: str = "python",
) -> tuple[BankCompressionAudit, ...]:
    """Audit selected banks, defaulting to the complete public scenario corpus."""
    translations = project_root.resolve() / "work" / "translations"
    selected = banks if banks is not None else tuple(KNOWN_SCENARIO_BANKS)
    unknown = sorted(set(selected) - set(KNOWN_SCENARIO_BANKS))
    if unknown:
        raise ValueError(f"unknown scenario bank(s): {', '.join(unknown)}")
    return tuple(
        audit_bank(
            translations,
            bank,
            optimization_backend=optimization_backend,
        )
        for bank in selected
    )


def _print_table(results: tuple[BankCompressionAudit, ...]) -> None:
    """Print a compact human-readable headroom table."""
    header = (
        "Bank   Backend  Capacity  Fast  Deep  FastFree  DeepFree  Saved  "
        "Dict(F/D)  Time(F/D)s"
    )
    print(header)
    print("-" * len(header))
    for result in results:
        print(
            f"{result.bank:<6} "
            f"{result.optimized_backend:<7} "
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
        help="repository checkout containing work/translations",
    )
    parser.add_argument(
        "--bank",
        action="append",
        dest="banks",
        choices=tuple(KNOWN_SCENARIO_BANKS),
        help="audit only this bank; may be supplied more than once",
    )
    parser.add_argument(
        "--backend",
        choices=tuple(sorted(OPTIMIZATION_BACKENDS)),
        default="python",
        help="deep optimizer backend (default: python)",
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
    results = audit_project(
        args.project_root,
        banks=banks,
        optimization_backend=args.backend,
    )
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_table(results)


if __name__ == "__main__":
    main()
