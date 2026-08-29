"""Audit the active all-full-word fixed menu target constants."""

from __future__ import annotations

import csv
from pathlib import Path

from time_twist import ui
from time_twist.english import encode_english, validate_display_width
from time_twist.release import SCENARIO_LOCATIONS
from time_twist.textcodec import pack_records


def rows() -> list[dict[str, object]]:
    """Return one source-level row per fixed menu/choice target."""
    output: list[dict[str, object]] = []
    for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items():
        if bank_name not in SCENARIO_LOCATIONS:
            raise ValueError(f"unknown relocated menu bank: {bank_name}")
        for index, label in enumerate(spec.records):
            encode_ok = True
            encode_error = ""
            width_ok = True
            width_error = ""
            packed_bytes: int | str = ""
            try:
                packed_bytes = len(pack_records((encode_english(label),)))
            except Exception as error:  # pragma: no cover - diagnostic path
                encode_ok = False
                encode_error = str(error)
            try:
                validate_display_width(label)
            except Exception as error:  # pragma: no cover - diagnostic path
                width_ok = False
                width_error = str(error)
            output.append(
                {
                    "bank": bank_name,
                    "index": index,
                    "full_word_target": label,
                    "packed_bytes_literal": packed_bytes,
                    "encode_ok": encode_ok,
                    "encode_error": encode_error,
                    "width_ok": width_ok,
                    "width_error": width_error,
                }
            )
    return output


def main() -> int:
    """Write the source-level target audit CSV."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    data = rows()
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(data[0])
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    failures = [
        row for row in data if not row["encode_ok"] or not row["width_ok"]
    ]
    print(f"audited {len(data)} full-word targets; failures={len(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
