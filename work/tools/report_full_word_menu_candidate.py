"""Split a verified fixed-menu candidate audit into readable reports."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

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
COMPRESSION_FIELDNAMES = (
    "bank",
    "records",
    "dictionary_entries",
    "packed_bytes",
    "capacity_bytes",
    "remaining_bytes",
    "sha256",
)
REPORTABLE_STATUSES = frozenset({"full-word", "blocked"})


class CandidateAuditError(ValueError):
    """Report an incomplete, invalid, or stale candidate menu audit."""


def _is_sha256(value: str) -> bool:
    """Return whether ``value`` is an uppercase or lowercase SHA-256 digest."""
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _write_csv(
    path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]
) -> None:
    """Write rows with their stable field order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_audit(path: Path) -> list[dict[str, str]]:
    """Read a complete candidate audit with the required provenance fields."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != set(
            AUDIT_FIELDNAMES
        ):
            raise CandidateAuditError(
                "audit CSV must contain exactly the current audit columns"
            )
        rows = list(reader)
    if not rows:
        raise CandidateAuditError("audit CSV has no fixed-label rows")
    return rows


def _read_manifest(path: Path) -> dict[str, object]:
    """Read the manifest fields required to bind an audit to its candidate."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CandidateAuditError("release manifest must be a JSON object")
    return payload


def _validate_audit(
    rows: list[dict[str, str]], manifest: dict[str, object]
) -> str:
    """Validate reportable outcomes and bind every row to one manifest."""
    invalid_statuses = sorted(
        {
            row["status"]
            for row in rows
            if row["status"] not in REPORTABLE_STATUSES
        }
    )
    if invalid_statuses:
        raise CandidateAuditError(
            "audit has non-reportable statuses: "
            f"{', '.join(invalid_statuses)}"
        )
    invalid_widths = [row for row in rows if row["width_ok"].lower() != "true"]
    if invalid_widths:
        raise CandidateAuditError(
            f"audit has {len(invalid_widths)} display-width failure(s)"
        )
    invalid_representations = sorted(
        {
            row["representation"]
            for row in rows
            if row["status"] == "full-word"
            and row["representation"] not in {"literal", "dictionary"}
        }
    )
    if invalid_representations:
        raise CandidateAuditError(
            "audit has invalid full-word representations: "
            f"{', '.join(invalid_representations)}"
        )

    candidate_hashes = {row["candidate_fds_sha256"] for row in rows}
    if len(candidate_hashes) != 1:
        raise CandidateAuditError(
            "audit rows name different candidate FDS files"
        )
    candidate_sha256 = candidate_hashes.pop()
    if not _is_sha256(candidate_sha256):
        raise CandidateAuditError("audit has no valid candidate FDS SHA-256")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise CandidateAuditError("release manifest has no output mapping")
    four_side = outputs.get("four_side")
    if not isinstance(four_side, dict):
        raise CandidateAuditError("release manifest has no four-side output")
    if four_side.get("sha256") != candidate_sha256:
        raise CandidateAuditError(
            "audit candidate FDS SHA-256 does not match the release manifest"
        )

    scenario_banks = manifest.get("scenario_banks")
    if not isinstance(scenario_banks, dict):
        raise CandidateAuditError(
            "release manifest has no scenario-bank mapping"
        )
    for row in rows:
        result = scenario_banks.get(row["bank"])
        if not isinstance(result, dict):
            raise CandidateAuditError(
                f"release manifest has no scenario bank {row['bank']!r}"
            )
        expected_sha256 = result.get("sha256")
        if not isinstance(expected_sha256, str) or not _is_sha256(
            expected_sha256
        ):
            raise CandidateAuditError(
                f"release manifest has invalid SHA-256 for {row['bank']}"
            )
        if row["bank_sha256"] != expected_sha256:
            raise CandidateAuditError(
                f"audit bank SHA-256 does not match the release manifest for "
                f"{row['bank']}"
            )
    return candidate_sha256


def report(
    audit_csv: Path, manifest_json: Path, output_dir: Path
) -> dict[str, object]:
    """Validate one candidate audit and write its derived public reports."""
    rows = _read_audit(audit_csv)
    manifest = _read_manifest(manifest_json)
    candidate_sha256 = _validate_audit(rows, manifest)

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
    mismatches: list[dict[str, str]] = []
    _write_csv(
        output_dir / "fixed_menu_full_word_literal.csv",
        AUDIT_FIELDNAMES,
        literal,
    )
    _write_csv(
        output_dir / "fixed_menu_full_word_dictionary.csv",
        AUDIT_FIELDNAMES,
        dictionary,
    )
    _write_csv(
        output_dir / "fixed_menu_label_blockers.csv", AUDIT_FIELDNAMES, blocked
    )
    _write_csv(
        output_dir / "fixed_menu_label_mismatches.csv",
        AUDIT_FIELDNAMES,
        mismatches,
    )

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
    summary: dict[str, object] = {
        "candidate_fds_sha256": candidate_sha256,
        "records": len(rows),
        "full_word_literal": len(literal),
        "full_word_dictionary": len(dictionary),
        "blocked": len(blocked),
        "mismatches": len(mismatches),
        "by_bank": dict(sorted(by_bank.items())),
    }
    (output_dir / "fixed_menu_label_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    compression_rows = []
    scenario_banks = manifest["scenario_banks"]
    assert isinstance(scenario_banks, dict)
    for bank, result in sorted(scenario_banks.items()):
        assert isinstance(result, dict)
        compression_rows.append(
            {
                "bank": bank,
                "records": str(result["records"]),
                "dictionary_entries": str(result["dictionary_entries"]),
                "packed_bytes": str(result["packed_bytes"]),
                "capacity_bytes": str(result["capacity_bytes"]),
                "remaining_bytes": str(result["remaining_bytes"]),
                "sha256": str(result["sha256"]),
            }
        )
    _write_csv(
        output_dir / "compression_report_by_bank.csv",
        COMPRESSION_FIELDNAMES,
        compression_rows,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    """Create full-word, dictionary, and explicit-blocker CSV reports."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-csv", type=Path, required=True)
    parser.add_argument("--manifest-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = report(args.audit_csv, args.manifest_json, args.output_dir)
    except CandidateAuditError as error:
        print(f"candidate audit rejected: {error}", file=sys.stderr)
        return 1
    print(
        f"full-word literal={summary['full_word_literal']} "
        f"dictionary={summary['full_word_dictionary']} "
        f"blocked={summary['blocked']} mismatches={summary['mismatches']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
