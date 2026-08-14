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
from tempfile import TemporaryDirectory

from time_twist import ui
from time_twist.compression import expand_dictionary_symbols
from time_twist.english import render_english, validate_display_width
from time_twist.fds import FdsImage
from time_twist.release import SCENARIO_LOCATIONS
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import split_records
from time_twist.ui import _record_starts

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
    with TemporaryDirectory(prefix="time_twist_menu_audit_") as temporary:
        for bank_name, location in SCENARIO_LOCATIONS.items():
            records_name = f"{bank_name}_FIXED_TEXT_RECORDS"
            if not hasattr(ui, records_name):
                continue
            records = getattr(ui, records_name)
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
                bank_path = Path(temporary) / f"{bank_name}.bin"
                bank_path.write_bytes(entry.data)
                bank = parse_scenario_bank(
                    bank_path, minimum_dictionary_entries=31
                )
                start = getattr(ui, f"{bank_name}_FIXED_TEXT_START_OFFSET")
                end = getattr(ui, f"{bank_name}_FIXED_TEXT_END_OFFSET")
                table = entry.data[start:end]
                starts = _record_starts(table, len(records))
                for record_index, start_offset in enumerate(starts):
                    symbols, next_offset = split_records(
                        table, offset=start_offset, limit=1
                    )
                    slots[record_index] = next_offset - start_offset
                    record_symbols = symbols[0]
                    decoded[record_index] = render_english(
                        expand_dictionary_symbols(
                            record_symbols, bank.dictionary
                        )
                    ).rstrip()
                    representation[record_index] = (
                        "dictionary"
                        if any(
                            symbol.kind.name == "DICTIONARY"
                            for symbol in record_symbols
                        )
                        else "literal"
                    )
            for index, label in enumerate(records):
                proposed = targets.get((bank_name, index), "")
                decoded_label = decoded[index]
                fallback = ui.FIXED_TEXT_BLOCKED_FALLBACKS.get(
                    bank_name, {}
                ).get(index)
                status = "source-only"
                if decoded_label is not None:
                    if decoded_label == label:
                        status = "full-word"
                    elif fallback is not None and decoded_label == fallback:
                        status = "blocked"
                    else:
                        status = "mismatch"
                width_ok = True
                width_error = ""
                try:
                    validate_display_width(decoded_label or label)
                except (
                    Exception
                ) as error:  # pragma: no cover - diagnostic text
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
                        "fallback_label": fallback or "",
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
    blocked = sum(row["status"] == "blocked" for row in rows)
    print(
        f"audited {len(rows)} fixed labels; full-word={full_words}; "
        f"blocked={blocked}; failures={len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
