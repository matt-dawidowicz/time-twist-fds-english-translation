"""Split a fixed-menu candidate audit into readable outcome reports."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write audit rows with their existing stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]) if rows else ()
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    """Create full-word, dictionary, and explicit-blocker CSV reports."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--manifest-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with args.audit_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    literal = [
        row
        for row in rows
        if row["status"] == "full-word" and row["representation"] == "literal"
    ]
    dictionary = [
        row
        for row in rows
        if row["status"] == "full-word"
        and row["representation"] == "dictionary"
    ]
    blocked = [row for row in rows if row["status"] == "blocked"]
    mismatches = [row for row in rows if row["status"] == "mismatch"]
    _write_csv(args.output_dir / "fixed_menu_full_word_literal.csv", literal)
    _write_csv(
        args.output_dir / "fixed_menu_full_word_dictionary.csv", dictionary
    )
    _write_csv(args.output_dir / "fixed_menu_label_blockers.csv", blocked)
    _write_csv(args.output_dir / "fixed_menu_label_mismatches.csv", mismatches)

    by_bank: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "full_word_literal": 0,
            "full_word_dictionary": 0,
            "blocked": 0,
        }
    )
    for row in rows:
        if row["status"] == "blocked":
            by_bank[row["bank"]]["blocked"] += 1
        elif row["status"] == "full-word":
            key = f"full_word_{row['representation']}"
            by_bank[row["bank"]][key] += 1
    summary = {
        "records": len(rows),
        "full_word_literal": len(literal),
        "full_word_dictionary": len(dictionary),
        "blocked": len(blocked),
        "mismatches": len(mismatches),
        "by_bank": dict(sorted(by_bank.items())),
    }
    (args.output_dir / "fixed_menu_label_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = json.loads(args.manifest_json.read_text(encoding="utf-8"))
    compression_rows = []
    for bank, result in sorted(manifest["scenario_banks"].items()):
        compression_rows.append(
            {
                "bank": bank,
                "records": result["records"],
                "dictionary_entries": result["dictionary_entries"],
                "packed_bytes": result["packed_bytes"],
                "capacity_bytes": result["capacity_bytes"],
                "remaining_bytes": result["remaining_bytes"],
                "sha256": result["sha256"],
            }
        )
    _write_csv(
        args.output_dir / "compression_report_by_bank.csv", compression_rows
    )
    print(
        f"full-word literal={len(literal)} dictionary={len(dictionary)} "
        f"blocked={len(blocked)} mismatches={len(mismatches)}"
    )
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
