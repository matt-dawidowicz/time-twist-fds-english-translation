"""Measure the complete production retranslation against recovered bank space."""

from __future__ import annotations

import tempfile
from pathlib import Path

import generate_translation_workbook as workbook
from time_twist.capacity import NATIVE_SCENARIO_CAPACITY_BYTES, playable_capacity
from time_twist.compression import compress_english_groups, packed_size
from time_twist.english import encode_english
from time_twist.production_codec import (
    compress_production_groups,
    production_packed_size,
)
from time_twist.production_translation import materialize_production_maps
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT
from time_twist.ui import (
    FIXED_RECORD_TABLE_SPECS,
    fixed_record_table_page_pointer_bytes,
)


BANK_NAMES = tuple(KNOWN_SCENARIO_BANKS)
SPACE_RUN_ENTRIES = tuple(encode_english(" " * size) for size in (16, 8, 4, 2))


def _groups_and_structure(bank_name: str) -> tuple[object, int]:
    """Return dialogue/menu groups and non-compressible pointer bytes."""
    groups = workbook._load_translation_groups(bank_name)  # noqa: SLF001
    pointer_bytes = 2 * (len(groups) - 1)
    if bank_name not in FIXED_RECORD_TABLE_SPECS:
        return groups, pointer_bytes

    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    menu_records = tuple(encode_english(text) for text in spec.records)
    combined_groups = (*groups, menu_records)
    structural_bytes = (
        pointer_bytes + fixed_record_table_page_pointer_bytes(bank_name)
    )
    return combined_groups, structural_bytes


def _measure_space_run_dictionary(bank_name: str) -> int:
    """Measure a decoder-compatible dictionary with reusable wrap padding."""
    groups, structural_bytes = _groups_and_structure(bank_name)
    capacity = playable_capacity(
        bank_name,
        NATIVE_SCENARIO_CAPACITY_BYTES[bank_name],
    )
    compressed, dictionary = compress_english_groups(
        groups,
        required_entries=SPACE_RUN_ENTRIES,
        max_bytes=capacity - structural_bytes,
        optimize=False,
        maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
    )
    return packed_size(compressed, dictionary) + structural_bytes


def _measure_adaptive_dictionary(bank_name: str) -> tuple[int, int]:
    """Measure the production 1-255 hierarchical dictionary compressor."""
    groups, structural_bytes = _groups_and_structure(bank_name)
    compressed, dictionary = compress_production_groups(groups)
    return (
        production_packed_size(compressed, dictionary) + structural_bytes,
        len(dictionary),
    )


def main() -> int:
    """Materialize reviewed prose and print exact conservative bank footprints."""
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="time_twist_production_fit_") as directory:
        materialized = Path(directory)
        counts = materialize_production_maps(
            BANK_NAMES,
            base_directory=root / "work" / "translations",
            override_directory=root / "work" / "production_overrides",
            review_directory=root / "review" / "production_retranslation",
            output_directory=materialized,
        )
        workbook.TRANSLATIONS = materialized

        total_records = sum(counts.values())
        print(
            f"PRODUCTION MATERIALIZED: {total_records} records across "
            f"{len(counts)} banks"
        )
        overflow = 0
        baseline_overflow = 0
        for bank_name in BANK_NAMES:
            baseline = workbook.measure_translation_footprint(bank_name)
            space_run = _measure_space_run_dictionary(bank_name)
            adaptive, entry_count = _measure_adaptive_dictionary(bank_name)
            used = min(baseline, space_run, adaptive)
            capacity = playable_capacity(
                bank_name,
                NATIVE_SCENARIO_CAPACITY_BYTES[bank_name],
            )
            remaining = capacity - used
            state = "FIT" if remaining >= 0 else "OVER"
            print(
                f"PRODUCTION {state} {bank_name}: best={used}/{capacity} "
                f"({remaining:+d}); flat68={baseline}; space-runs={space_run}; "
                f"adaptive255={adaptive} ({entry_count} entries)"
            )
            overflow += max(0, -remaining)
            baseline_overflow += max(0, baseline - capacity)

        print(
            f"PRODUCTION BASELINE OVERFLOW: {baseline_overflow} bytes; "
            f"BEST OVERFLOW: {overflow} bytes"
        )
        if overflow:
            return 2
        print("PRODUCTION FIT: every scenario bank fits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
