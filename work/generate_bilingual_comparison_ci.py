"""Regenerate the bilingual comparison without requiring retail bank files.

The main comparison generator normally cross-checks fixed-address Japanese UI
records directly against extracted retail scenario banks. Public CI cannot
contain those copyrighted bank binaries, so this wrapper supplies the same
immutable decoded Japanese text and packed record lengths from the tracked
``fixed_source_tables.json`` evidence file. When retail source extracts are
available locally, the wrapper still decodes and compares them before use.
"""

from __future__ import annotations

import json
from pathlib import Path

import generate_bilingual_comparison as comparison
from time_twist import ui
from time_twist.scenario import render_symbols
from time_twist.textcodec import split_records

FIXED_SOURCE_TABLES = Path(__file__).with_name("fixed_source_tables.json")


def _tracked_tables() -> dict[str, list[tuple[str, int]]]:
    """Load and validate the tracked fixed-table Japanese source evidence."""
    payload = json.loads(FIXED_SOURCE_TABLES.read_text(encoding="utf-8"))
    if payload.get("schema") != 1:
        raise ValueError("unsupported fixed-source-table schema")
    raw_banks = payload.get("banks")
    if not isinstance(raw_banks, dict):
        raise ValueError("fixed-source-table manifest has no banks object")

    tables: dict[str, list[tuple[str, int]]] = {}
    for bank, raw_rows in raw_banks.items():
        if not isinstance(bank, str) or not isinstance(raw_rows, list):
            raise ValueError("invalid fixed-source-table bank entry")
        rows: list[tuple[str, int]] = []
        for raw_row in raw_rows:
            if (
                not isinstance(raw_row, list)
                or len(raw_row) != 2
                or not isinstance(raw_row[0], str)
                or not isinstance(raw_row[1], int)
                or raw_row[1] <= 0
            ):
                raise ValueError(f"invalid fixed-source-table row in {bank}")
            rows.append((raw_row[0], raw_row[1]))
        tables[bank] = rows
    return tables


def _decoded_source_records(
    bank: str,
    start: int,
    end: int,
    record_count: int,
) -> list[tuple[str, int]] | None:
    """Decode fixed records from retail source when those bytes are available."""
    document = comparison._read_source_document(bank)
    try:
        source_path = comparison._source_path(document)
    except FileNotFoundError:
        return None

    data = source_path.read_bytes()
    dictionary = ui._tt2_dictionary(data)
    packed = data[start:end]
    records, parsed_end = split_records(
        packed,
        0,
        record_count=record_count,
        extended_dictionary=False,
    )
    if parsed_end != len(packed):
        raise ValueError(
            f"{bank} fixed table parsed {parsed_end} bytes, expected {len(packed)}"
        )
    starts = ui._record_starts(0, records)
    ends = ui._record_ends(starts, len(packed))
    return [
        (render_symbols(record.symbols, dictionary), row_end - row_start)
        for record, row_start, row_end in zip(records, starts, ends, strict=True)
    ]


def _fixed_rows(start_sequence: int) -> list[comparison.ComparisonRow]:
    """Build fixed-address rows from tracked evidence and optional retail proof."""
    tables = _tracked_tables()
    rows: list[comparison.ComparisonRow] = []
    sequence = start_sequence

    expected_banks = {bank for bank, *_rest in comparison.FIXED_SPECS}
    if set(tables) != expected_banks:
        missing = sorted(expected_banks - set(tables))
        extra = sorted(set(tables) - expected_banks)
        raise ValueError(f"fixed-source-table bank mismatch: missing={missing}, extra={extra}")

    for bank, start, end, english_records in comparison.FIXED_SPECS:
        tracked = tables[bank]
        if len(tracked) != len(english_records):
            raise ValueError(
                f"{bank} tracked fixed rows {len(tracked)} != English rows "
                f"{len(english_records)}"
            )

        decoded = _decoded_source_records(bank, start, end, len(english_records))
        if decoded is not None and decoded != tracked:
            raise ValueError(f"{bank} tracked fixed-table evidence differs from retail source")

        record_start = 0
        for index, ((japanese, packed_bytes), english) in enumerate(
            zip(tracked, english_records, strict=True)
        ):
            rows.append(
                comparison._make_row(
                    sequence=sequence,
                    bank=bank,
                    text_id=f"{bank}/fixed/r{index:03d}",
                    kind="fixed-address",
                    source_location=f"${0xA200 + start + record_start:04X}",
                    packed_bytes=str(packed_bytes),
                    japanese=japanese,
                    english=english,
                )
            )
            sequence += 1
            record_start += packed_bytes

        if record_start != end - start:
            raise ValueError(
                f"{bank} tracked fixed table covers {record_start} bytes, "
                f"expected {end - start}"
            )

    return rows


def main() -> None:
    """Run the normal comparison generator with CI-safe fixed-table sourcing."""
    comparison._fixed_rows = _fixed_rows
    comparison.main()


if __name__ == "__main__":
    main()
