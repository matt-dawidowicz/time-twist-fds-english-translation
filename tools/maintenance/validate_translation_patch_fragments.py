"""Validate public translation patch fragments without private script data.

The public source handoff deliberately omits ``work/translations/*.json``.
Patch fragments in ``work/translation_patches`` therefore store only the small
record-level changes needed for a maintainer to apply them in the private
checkout. This tool verifies that each fragment is internally safe before it is
handed off: record IDs match their bank, control-code order is preserved, the
replacement uses the supported English glyph map, and every visible segment fits
within the 24-column renderer limit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from time_twist.english import (
    EnglishTextError,
    control_values,
    encode_english,
    validate_display_width,
)


def _load_fragment(path: Path) -> dict[str, Any]:
    """Load one public patch fragment and reject non-object JSON early.

    Keeping this boundary narrow means the validator can report a useful
    per-file error before it attempts record-ID, control-code, glyph, or width
    checks.  It never needs private full-bank translation maps.
    """
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: fragment must be a JSON object")
    return data


def validate_fragment(path: Path) -> list[str]:
    """Return validation errors for one patch fragment."""
    errors: list[str] = []
    try:
        data = _load_fragment(path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return [f"{path}: {error}"]

    schema = data.get("schema")
    if schema != "Time Twist translation patch fragment v1":
        errors.append(f"{path}: unsupported schema {schema!r}")

    bank = data.get("bank")
    if not isinstance(bank, str) or not bank:
        errors.append(f"{path}: missing bank")
        bank = ""

    records = data.get("records")
    if not isinstance(records, list) or not records:
        errors.append(f"{path}: records must be a nonempty list")
        return errors

    seen: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"{path}: record {index}"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        record_id = record.get("id")
        current = record.get("current")
        replacement = record.get("replacement")
        if not isinstance(record_id, str) or not record_id:
            errors.append(f"{prefix}: missing id")
            continue
        prefix = f"{path}: {record_id}"
        if record_id in seen:
            errors.append(f"{prefix}: duplicate id")
        seen.add(record_id)
        if bank and not record_id.startswith(f"{bank}/"):
            errors.append(f"{prefix}: id does not match bank {bank}")
        if not isinstance(current, str) or not current:
            errors.append(f"{prefix}: current must be a nonempty string")
            continue
        if not isinstance(replacement, str) or not replacement:
            errors.append(f"{prefix}: replacement must be a nonempty string")
            continue
        if control_values(current) != control_values(replacement):
            errors.append(f"{prefix}: replacement changes control-code order")
        try:
            validate_display_width(replacement)
            encode_english(replacement)
        except EnglishTextError as error:
            errors.append(f"{prefix}: {error}")
    return errors


def discover_fragments(root: Path) -> list[Path]:
    """Return all JSON translation patch fragments under a project root."""
    patch_dir = root / "work" / "translation_patches"
    if not patch_dir.exists():
        return []
    return sorted(p for p in patch_dir.glob("*.json") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    """Validate discovered patch fragments and return a process exit status."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="project root (default: auto-resolved from this script)",
    )
    args = parser.parse_args(argv)
    fragments = discover_fragments(args.root)
    if not fragments:
        print("translation patch fragment validation: no fragments found")
        return 0
    errors: list[str] = []
    for fragment in fragments:
        errors.extend(validate_fragment(fragment))
    if errors:
        print("translation patch fragment validation: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"translation patch fragment validation: PASS ({len(fragments)} fragment(s))"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
