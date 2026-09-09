"""Measure the complete production retranslation against recovered bank space."""

from __future__ import annotations

import tempfile
from pathlib import Path

import generate_translation_workbook as workbook
from time_twist.capacity import NATIVE_SCENARIO_CAPACITY_BYTES, playable_capacity
from time_twist.production_translation import materialize_production_maps
from time_twist.project import KNOWN_SCENARIO_BANKS


BANK_NAMES = tuple(KNOWN_SCENARIO_BANKS)


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
        for bank_name in BANK_NAMES:
            used = workbook.measure_translation_footprint(bank_name)
            capacity = playable_capacity(
                bank_name,
                NATIVE_SCENARIO_CAPACITY_BYTES[bank_name],
            )
            remaining = capacity - used
            state = "FIT" if remaining >= 0 else "OVER"
            print(
                f"PRODUCTION {state} {bank_name}: {used}/{capacity} bytes "
                f"({remaining:+d})"
            )
            overflow += max(0, -remaining)

        if overflow:
            print(f"PRODUCTION TOTAL OVERFLOW: {overflow} bytes")
            return 2
        print("PRODUCTION FIT: every scenario bank fits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
