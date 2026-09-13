#!/usr/bin/env python3
"""Audit all 721 fixed labels against recovered primary-menu use-site geometry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from time_twist import ui
from time_twist.fds import FdsImage
from time_twist.menu_geometry import (
    primary_menu_descriptors,
    validate_descriptor_geometry,
)
from time_twist.release_metadata import SCENARIO_LOCATIONS


def audit(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Return a source-backed geometry report for all recovered menu banks."""
    images = {
        "zenpen": FdsImage.read(zenpen),
        "kouhen": FdsImage.read(kouhen),
    }
    rows: list[dict[str, object]] = []
    total_labels = 0
    total_descriptors = 0
    all_named_pairs: set[tuple[str, str]] = set()
    for bank_name, (image_name, side) in SCENARIO_LOCATIONS.items():
        records_name = f"{bank_name}_FIXED_TEXT_RECORDS"
        if not hasattr(ui, records_name):
            continue
        labels = tuple(getattr(ui, records_name))
        entry = images[image_name].sides[side].find_file(bank_name)
        descriptors = primary_menu_descriptors(
            entry.data,
            load_address=entry.load_address,
        )
        pairs = validate_descriptor_geometry(labels, descriptors)
        named_pairs = {
            (labels[left - 1], labels[right - 1]) for left, right in pairs
        }
        all_named_pairs.update(named_pairs)
        total_labels += len(labels)
        total_descriptors += len(descriptors)
        rows.append(
            {
                "bank": bank_name,
                "labels": len(labels),
                "descriptors": len(descriptors),
                "max_descriptor_choices": max(map(len, descriptors), default=0),
                "possible_compacted_pairs": len(named_pairs),
            }
        )
    widest = sorted(
        (
            {
                "combined_glyphs": len(left) + len(right),
                "left": left,
                "right": right,
            }
            for left, right in all_named_pairs
        ),
        key=lambda row: (
            -int(row["combined_glyphs"]),
            str(row["left"]),
            str(row["right"]),
        ),
    )
    if total_labels != 721:
        raise ValueError(f"expected 721 fixed labels, audited {total_labels}")
    return {
        "labels": total_labels,
        "descriptors": total_descriptors,
        "possible_compacted_pairs": len(all_named_pairs),
        "banks": rows,
        "widest_pairs": widest[:20],
    }


def main() -> int:
    """Run the source-backed menu-geometry audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit(args.zenpen, args.kouhen)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "menu geometry audit: PASS "
            f"({report['labels']} labels, {report['descriptors']} descriptors, "
            f"{report['possible_compacted_pairs']} possible compacted pairs)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
