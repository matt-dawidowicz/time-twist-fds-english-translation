"""Audit fixed-address menu labels against source constants and an optional FDS.

This helper is intentionally conservative: it does not patch anything.  It can
be run in source-only mode to list the labels declared by ``time_twist.ui`` or
against a built candidate to prove the packed records decode back to the same
English labels.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from time_twist import ui
from time_twist.english import render_english
from time_twist.entropy_codec import (
    split_entropy_stream,
    unpack_entropy_stream,
)
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from time_twist.fds import FdsImage
from time_twist.menu_geometry import validate_menu_label
from time_twist.release import SCENARIO_LOCATIONS
from time_twist.scenario import DICTIONARY_POINTER_OFFSET
from time_twist.textcodec import PackedSymbol, SymbolKind

AUDIT_FIELDNAMES = (
    "bank",
    "index",
    "source_label",
    "decoded_label",
    "slot_bytes",
    "representation",
    "proposed_full_label",
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


def _candidate_menu_records(
    data: bytes,
    *,
    bank_name: str,
    load_address: int,
    record_count: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode the byte-addressed entropy pages from one release bank."""
    spec = ui.FIXED_RECORD_TABLE_SPECS[bank_name]
    page_index_address = int.from_bytes(
        data[
            ui.FIXED_RECORD_PAGE_POINTER_OFFSET : ui.FIXED_RECORD_PAGE_POINTER_OFFSET
            + 2
        ],
        "little",
    )
    page_index_offset = page_index_address - load_address
    pointer_bytes = ui.fixed_record_table_page_pointer_bytes(bank_name)
    if not spec.start <= page_index_offset <= len(data):
        raise ValueError(f"{bank_name} candidate menu page index is invalid")
    if page_index_offset + pointer_bytes > len(data):
        raise ValueError(f"{bank_name} candidate menu page index is truncated")

    page_starts = [spec.start]
    page_starts.extend(
        int.from_bytes(data[offset : offset + 2], "little") - load_address
        for offset in range(
            page_index_offset,
            page_index_offset + pointer_bytes,
            2,
        )
    )
    page_ends = (*page_starts[1:], page_index_offset)
    decoded: list[tuple[PackedSymbol, ...]] = []
    for page_index, (start, end) in enumerate(
        zip(page_starts, page_ends, strict=True)
    ):
        remaining = record_count - page_index * ui.FIXED_RECORDS_PER_PAGE
        count = min(ui.FIXED_RECORDS_PER_PAGE, remaining)
        if count <= 0 or not 0 <= start <= end <= len(data):
            raise ValueError(f"{bank_name} candidate menu page is malformed")
        decoded.extend(
            unpack_entropy_stream(data[start:end], record_count=count)
        )
    if len(decoded) != record_count:
        raise ValueError(
            f"{bank_name} candidate menu decoded {len(decoded)} records, "
            f"expected {record_count}"
        )
    return tuple(decoded)


def _candidate_dictionary_prefix(
    data: bytes,
    *,
    load_address: int,
    required_entries: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode only the entropy dictionary prefix reachable from the menu."""
    if required_entries == 0:
        return ()
    dictionary_address = int.from_bytes(
        data[DICTIONARY_POINTER_OFFSET : DICTIONARY_POINTER_OFFSET + 2],
        "little",
    )
    dictionary_offset = dictionary_address - load_address
    if not 0 <= dictionary_offset < len(data):
        raise ValueError("candidate entropy dictionary pointer is invalid")
    records, _, _ = split_entropy_stream(
        data[dictionary_offset:], offset=0, limit=required_entries
    )
    return tuple(tuple(record) for record in records)


def audit(
    candidate_fds: Path | None, targets_csv: Path | None
) -> list[dict[str, object]]:
    """Return one audit row per fixed menu/choice label."""
    image = FdsImage.read(candidate_fds) if candidate_fds is not None else None
    candidate_sha256 = (
        hashlib.sha256(candidate_fds.read_bytes()).hexdigest().upper()
        if candidate_fds is not None
        else ""
    )
    targets = _load_targets(targets_csv)
    rows: list[dict[str, object]] = []
    for bank_name, location in SCENARIO_LOCATIONS.items():
        records_name = f"{bank_name}_FIXED_TEXT_RECORDS"
        if not hasattr(ui, records_name):
            continue
        records = getattr(ui, records_name)
        decoded: list[str | None] = [None] * len(records)
        representation: list[str] = ["source-only"] * len(records)
        bank_sha256 = ""
        if image is not None:
            image_name, side = location
            entry = image.sides[_side_index(image_name, side)].find_file(
                bank_name
            )
            bank_sha256 = hashlib.sha256(entry.data).hexdigest().upper()
            packed_records = _candidate_menu_records(
                entry.data,
                bank_name=bank_name,
                load_address=entry.load_address,
                record_count=len(records),
            )
            menu_dictionary_floor = max(
                (
                    symbol.value
                    for record in packed_records
                    for symbol in record
                    if symbol.kind is SymbolKind.DICTIONARY
                ),
                default=0,
            )
            dictionary = _candidate_dictionary_prefix(
                entry.data,
                load_address=entry.load_address,
                required_entries=menu_dictionary_floor,
            )
            expansions = expand_entropy_dictionary(dictionary)
            for record_index, record_symbols in enumerate(packed_records):
                decoded[record_index] = render_english(
                    expand_entropy_record(record_symbols, expansions)
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
                status = "full-word" if decoded_label == label else "mismatch"
            width_ok = True
            width_error = ""
            try:
                validate_menu_label(decoded_label or label)
            except Exception as error:  # pragma: no cover - diagnostic text
                width_ok = False
                width_error = str(error)
            rows.append(
                {
                    "bank": bank_name,
                    "index": index,
                    "source_label": label,
                    "decoded_label": decoded_label or "",
                    # Entropy records are bit-contiguous inside 32-record
                    # pages, so there is no per-record byte slot to report.
                    "slot_bytes": "",
                    "representation": representation[index],
                    "proposed_full_label": proposed,
                    "status": status,
                    "width_ok": width_ok,
                    "width_error": width_error,
                    "candidate_fds_sha256": candidate_sha256,
                    "bank_sha256": bank_sha256,
                }
            )
    return rows


def main() -> int:
    """Run the fixed-label audit command."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-fds", type=Path)
    parser.add_argument("--targets-csv", type=Path)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()
    rows = audit(args.candidate_fds, args.targets_csv)
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
