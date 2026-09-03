"""Rank natural-English line layouts by exact whole-bank compression cost.

The tool preserves supplied prose verbatim and varies only presentation row
breaks. Each legal layout is substituted into an in-memory copy of the public
translation map, validated against the audited presentation-control policy, and
compressed as part of the complete bank.

It requires no proprietary ROM. Recovered public capacity facts and fixed-menu
records reproduce the build-side packing problem; a later private ROM-backed
candidate remains the final fixed-address/source-byte gate.
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
from time_twist.editorial_layout import presentation_break_variants
from time_twist.english import encode_english
from time_twist.project import (
    KNOWN_SCENARIO_BANKS,
    required_dictionary_entries,
)
from time_twist.release_compression import compress_release_groups
from time_twist.scenario_validation import (
    PRESENTATION_BREAK_RECORD_IDS,
    encode_validated_english,
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
class LayoutAuditResult:
    """Exact compressed-bank measurement for one presentation layout."""

    layout: str
    packed_bytes: int
    capacity_bytes: int
    headroom_bytes: int
    dictionary_entries: int
    seconds: float


def _translation_map(project_root: Path, bank_name: str) -> dict[str, str]:
    """Load one reviewed bank translation map with string-only validation."""
    path = project_root / "work" / "translations" / f"{bank_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in payload.items()
    ):
        raise ValueError(f"{path} must map string record IDs to strings")
    return payload


def _groups_from_map(
    bank_name: str,
    translations: dict[str, str],
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    """Encode one translation map into stable group/record order."""
    indexed: dict[int, dict[int, tuple[PackedSymbol, ...]]] = {}
    for record_id, text in translations.items():
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


def _deep_measure(
    bank_name: str,
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> tuple[int, int, int, float]:
    """Return optimized used bytes, capacity, dictionary entries, and time."""
    capacity = playable_capacity(bank_name)
    pointer_bytes = 2 * (len(groups) - 1)
    started = perf_counter()
    if bank_name in FIXED_RECORD_TABLE_SPECS:
        spec = FIXED_RECORD_TABLE_SPECS[bank_name]
        menu_records = tuple(encode_english(text) for text in spec.records)
        combined = (*groups, menu_records)
        structural_bytes = (
            pointer_bytes + fixed_record_table_page_pointer_bytes(bank_name)
        )
        compressed, dictionary = compress_release_groups(
            combined,
            max_bytes=capacity - structural_bytes,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
            maximize_headroom=True,
        )
        used = packed_size(compressed, dictionary) + structural_bytes
    else:
        compressed, dictionary = compress_release_groups(
            groups,
            required_entries=required_dictionary_entries(bank_name),
            max_bytes=capacity - pointer_bytes,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
            maximize_headroom=True,
        )
        used = packed_size(compressed, dictionary) + pointer_bytes
    return used, capacity, len(dictionary), perf_counter() - started


def audit_layouts(
    project_root: Path,
    *,
    bank_name: str,
    record_id: str,
    natural_text: str,
) -> tuple[LayoutAuditResult, ...]:
    """Deep-compress every legal layout of one reviewed natural sentence."""
    if bank_name not in KNOWN_SCENARIO_BANKS:
        raise ValueError(f"unknown scenario bank {bank_name}")
    if not record_id.startswith(f"{bank_name}/"):
        raise ValueError(f"record {record_id} does not belong to {bank_name}")
    if record_id not in PRESENTATION_BREAK_RECORD_IDS:
        raise ValueError(
            f"{record_id} is not allowlisted for English presentation breaks"
        )

    root = project_root.resolve()
    translations = _translation_map(root, bank_name)
    if record_id not in translations:
        raise ValueError(
            f"{record_id} is absent from {bank_name} translations"
        )
    layouts = presentation_break_variants(natural_text)

    results: list[LayoutAuditResult] = []
    for layout in layouts:
        # The current pilot has no source control codes. Passing an empty source
        # sequence exercises the same validator rule that permits only additional
        # CTRL:0 presentation advances on this reviewed record.
        encode_validated_english(record_id, layout, "")
        candidate = dict(translations)
        candidate[record_id] = layout
        groups = _groups_from_map(bank_name, candidate)
        used, capacity, entries, seconds = _deep_measure(bank_name, groups)
        results.append(
            LayoutAuditResult(
                layout=layout,
                packed_bytes=used,
                capacity_bytes=capacity,
                headroom_bytes=capacity - used,
                dictionary_entries=entries,
                seconds=seconds,
            )
        )

    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.packed_bytes,
                result.layout.count("{CTRL:0}"),
                result.layout,
            ),
        )
    )


def _print_results(results: tuple[LayoutAuditResult, ...]) -> None:
    """Print ranked layouts with visible row separators and exact byte costs."""
    print("Rank  Packed  Free  Dict  Seconds  Layout")
    print("----  ------  ----  ----  -------  ------")
    for rank, result in enumerate(results, start=1):
        visible = result.layout.replace("{CTRL:0}", " / ")
        print(
            f"{rank:>4}  {result.packed_bytes:>6}  "
            f"{result.headroom_bytes:>4}  {result.dictionary_entries:>4}  "
            f"{result.seconds:>7.3f}  {visible}"
        )


def build_parser() -> argparse.ArgumentParser:
    """Return command-line arguments for one record-level layout audit."""
    parser = argparse.ArgumentParser(
        description="Rank legal English row breaks by whole-bank packed size.",
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--bank", required=True, choices=tuple(KNOWN_SCENARIO_BANKS)
    )
    parser.add_argument("--record", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run one compression-aware layout audit without modifying source files."""
    args = build_parser().parse_args(argv)
    results = audit_layouts(
        args.project_root,
        bank_name=args.bank,
        record_id=args.record,
        natural_text=args.text,
    )
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_results(results)


if __name__ == "__main__":
    main()
