"""Audit canonical relocated menu labels against an optional candidate FDS.

This helper is intentionally conservative: it does not patch anything. It can
run in source-only mode to list the labels declared by the modern
``FIXED_RECORD_TABLE_SPECS`` mapping or against a built candidate to prove the
packed records decode back to those same full-word English labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from time_twist import ui
from time_twist.compression import expand_dictionary_symbols
from time_twist.english import render_english, validate_display_width
from time_twist.fds import FdsImage
from time_twist.release import SCENARIO_LOCATIONS
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import PackedSymbol, SymbolKind, split_records

AUDIT_FIELDNAMES = (
    "bank",
    "index",
    "source_label",
    "decoded_label",
    "slot_bytes",
    "representation",
    "proposed_full_label",
    "fallback_label",
    "status",
    "width_ok",
    "width_error",
    "candidate_fds_sha256",
    "bank_sha256",
)


def _side_index(image_name: str, side: int) -> int:
    """Convert release image/side coordinates to four-side image indices."""
    return side if image_name == "zenpen" else side + 2


def _load_targets(path: Path | None) -> dict[tuple[str, int], str]:
    """Load optional proposed full-word labels from a CSV report."""
    if path is None:
        return {}
    targets: dict[tuple[str, int], str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bank = row.get("bank")
            index = row.get("index")
            target = row.get("full_word_target")
            if bank and index is not None and target:
                targets[(bank, int(index))] = target
    return targets


def _decode_table_records(
    table: bytes,
    record_count: int,
) -> tuple[list[tuple[PackedSymbol, ...]], list[int]]:
    """Decode one relocated menu table sequentially and record slot sizes."""
    packed_records: list[tuple[PackedSymbol, ...]] = []
    slot_sizes: list[int] = []
    offset = 0
    for _ in range(record_count):
        records, next_offset = split_records(
            table,
            offset=offset,
            limit=1,
            extended_dictionary=True,
        )
        packed_records.append(tuple(records[0]))
        slot_sizes.append(next_offset - offset)
        offset = next_offset
    if offset != len(table):
        raise ValueError(
            f"fixed menu table parsed {offset} bytes, expected {len(table)}"
        )
    return packed_records, slot_sizes


def audit(
    candidate_fds: Path | None, targets_csv: Path | None
) -> list[dict[str, object]]:
    """Return one audit row per canonical relocated menu/choice label."""
    image = FdsImage.read(candidate_fds) if candidate_fds is not None else None
    candidate_sha256 = (
        hashlib.sha256(candidate_fds.read_bytes()).hexdigest().upper()
        if candidate_fds is not None
        else ""
    )
    targets = _load_targets(targets_csv)
    rows: list[dict[str, object]] = []
    with TemporaryDirectory(prefix="time_twist_menu_audit_") as temporary:
        for bank_name, location in SCENARIO_LOCATIONS.items():
            spec = ui.FIXED_RECORD_TABLE_SPECS.get(bank_name)
            if spec is None:
                continue
            records = spec.records
            decoded: list[str | None] = [None] * len(records)
            slots: list[int | None] = [None] * len(records)
            representation: list[str] = ["source-only"] * len(records)
            bank_sha256 = ""
            if image is not None:
                image_name, side = location
                entry = image.sides[_side_index(image_name, side)].find_file(
                    bank_name
                )
                bank_sha256 = hashlib.sha256(entry.data).hexdigest().upper()
                start = (
                    int.from_bytes(entry.data[0x14:0x16], "little")
                    - entry.load_address
                )
                end = (
                    int.from_bytes(entry.data[0x1A:0x1C], "little")
                    - entry.load_address
                )
                packed_records, slot_sizes = _decode_table_records(
                    entry.data[start:end], len(records)
                )
                slots = [*slot_sizes]
                menu_dictionary_floor = max(
                    (
                        symbol.value
                        for record in packed_records
                        for symbol in record
                        if symbol.kind is SymbolKind.DICTIONARY
                    ),
                    default=0,
                )
                bank_path = Path(temporary) / f"{bank_name}.bin"
                bank_path.write_bytes(entry.data)
                bank = parse_scenario_bank(
                    bank_path,
                    minimum_dictionary_entries=menu_dictionary_floor,
                    extended_dictionary=True,
                )
                for record_index, record_symbols in enumerate(packed_records):
                    decoded[record_index] = render_english(
                        expand_dictionary_symbols(
                            record_symbols, bank.dictionary
                        )
                    ).rstrip()
                    representation[record_index] = (
                        "dictionary"
                        if any(
                            symbol.kind is SymbolKind.DICTIONARY
                            for symbol in record_symbols
                        )
                        else "literal"
                    )
            for index, label in enumerate(records):
                proposed = targets.get((bank_name, index), "")
                decoded_label = decoded[index]
                status = "source-only"
                if decoded_label is not None:
                    status = (
                        "full-word" if decoded_label == label else "mismatch"
                    )
                width_ok = True
                width_error = ""
                try:
                    validate_display_width(decoded_label or label)
                except Exception as error:  # pragma: no cover - diagnostic text
                    width_ok = False
                    width_error = str(error)
                rows.append(
                    {
                        "bank": bank_name,
                        "index": index,
                        "source_label": label,
                        "decoded_label": decoded_label or "",
                        "slot_bytes": slots[index] or "",
                        "representation": representation[index],
                        "proposed_full_label": proposed,
                        "fallback_label": "",
                        "status": status,
                        "width_ok": width_ok,
                        "width_error": width_error,
                        "candidate_fds_sha256": candidate_sha256,
                        "bank_sha256": bank_sha256,
                    }
                )
    return rows


def main() -> int:
    """Run the fixed-label audit command and fail closed on empty evidence."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-fds", type=Path)
    parser.add_argument("--targets-csv", type=Path)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    rows = audit(args.candidate_fds, args.targets_csv)
    if not rows:
        print(
            "menu audit failed: canonical fixed-record specs produced no rows",
            file=sys.stderr,
        )
        return 1
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    failures = [
        row
        for row in rows
        if row["status"] == "mismatch" or not row["width_ok"]
    ]
    full_words = sum(row["status"] == "full-word" for row in rows)
    print(
        f"audited {len(rows)} fixed labels; full-word={full_words}; "
        f"failures={len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
