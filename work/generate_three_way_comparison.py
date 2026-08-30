"""Generate a private Japanese/current/competitor scenario review corpus.

All ROM and competitor-patch inputs are maintainer supplied.  The output
contains the competitor's full decoded script, so the default destination is
``work/runtime_capture/three_way_review``: a deliberately ignored private
analysis area, not a public release artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from time_twist.english import control_values
from time_twist.fds import SIDE_SIZE, FdsFile, FdsImage
from time_twist.three_way import (
    SCENARIO_SPECS,
    DecodedBank,
    ScenarioSpec,
    TextDialect,
    apply_ips,
    decode_scenario_file,
    parse_ips,
)

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
DEFAULT_OUTPUT_DIRECTORY = WORK / "runtime_capture" / "three_way_review"
CONTROL_RE = re.compile(r"\{CTRL:\d+\}")
FRAGMENT_END_RE = re.compile(
    r"\b(is|are|was|were|have|has|had|to|of|the|a|an)$",
    re.IGNORECASE,
)
LEADING_CONJUNCTION_RE = re.compile(
    r"(^|[.!?]\s+)(And|But|Because|So|Then)\b"
)
FDS_SIDE_SIGNATURE = b"\x01\x2aNINTENDO-HVC*"

# Published in the competitor release's README.  It identifies that patch's
# expected four-side base and is evidence only; the retail image is not stored.
COMPETITOR_EXPECTED_SOURCE = {
    "crc32": "E88E2399",
    "md5": "B310AB31C3FA89B5F3E491B1B7450E27",
    "sha1": "FF01B76C8BA84C6222FA043EFCBF82F1501B903B",
}


def _identity(path: Path) -> dict[str, object]:
    """Return exact local file identity without embedding its bytes."""

    data = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
        "sha1": hashlib.sha1(data).hexdigest().upper(),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest().upper(),
    }


def _side_header_offsets(data: bytes) -> list[int]:
    """Find every standard archival FDS disk-info signature in raw bytes."""

    offsets: list[int] = []
    position = 0
    while True:
        position = data.find(FDS_SIDE_SIGNATURE, position)
        if position < 0:
            return offsets
        offsets.append(position)
        position += 1


def _malformed_competitor_audit(
    japanese_zenpen: bytes,
    japanese_kouhen: bytes,
    competitor_zenpen: bytes,
    competitor_kouhen: bytes,
) -> dict[str, object]:
    """Explain the two oversized single-half competitor patch applications."""

    limit = min(len(japanese_zenpen), len(competitor_zenpen))
    zen_changed = {
        index
        for index in range(limit)
        if japanese_zenpen[index] != competitor_zenpen[index]
    }
    limit = min(len(japanese_kouhen), len(competitor_kouhen))
    kou_changed = {
        index
        for index in range(limit)
        if japanese_kouhen[index] != competitor_kouhen[index]
    }
    shared_changed = zen_changed & kou_changed
    same_output_at_shared_changes = all(
        competitor_zenpen[index] == competitor_kouhen[index]
        for index in shared_changed
    )
    suffix_start = min(len(japanese_zenpen), len(japanese_kouhen))
    zen_suffix = competitor_zenpen[suffix_start:]
    kou_suffix = competitor_kouhen[suffix_start:]
    return {
        "classification": (
            "same four-side IPS was applied separately to each two-side half"
        ),
        "zenpen_output_bytes": len(competitor_zenpen),
        "kouhen_output_bytes": len(competitor_kouhen),
        "zenpen_side_alignment_remainder": (
            len(competitor_zenpen) % SIDE_SIZE
        ),
        "kouhen_side_alignment_remainder": (
            len(competitor_kouhen) % SIDE_SIZE
        ),
        "zenpen_side_header_offsets": _side_header_offsets(
            competitor_zenpen
        ),
        "kouhen_side_header_offsets": _side_header_offsets(
            competitor_kouhen
        ),
        "zenpen_prefix_changed_bytes": len(zen_changed),
        "kouhen_prefix_changed_bytes": len(kou_changed),
        "shared_changed_offsets": len(shared_changed),
        "same_output_at_every_shared_changed_offset": (
            same_output_at_shared_changes
        ),
        "appended_suffix_bytes": len(zen_suffix),
        "appended_suffixes_are_identical": zen_suffix == kou_suffix,
        "appended_suffix_sha256": hashlib.sha256(zen_suffix)
        .hexdigest()
        .upper(),
    }


def _find_entry(image: FdsImage, spec: ScenarioSpec) -> FdsFile:
    """Find exactly one expected scenario filename on its recovered side."""

    matches = [
        entry
        for entry in image.sides[spec.side].files
        if entry.name == spec.name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"{spec.half} side {spec.side} has {len(matches)} "
            f"files named {spec.name}"
        )
    return matches[0]


def _load_public_maps(
    bank: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Load immutable Japanese evidence and the authoritative playable map."""

    document = json.loads(
        (WORK / "translated_scripts" / f"{bank}.json").read_text(
            encoding="utf-8"
        )
    )
    japanese = {
        record["id"]: record["japanese"]
        for group in document["groups"]
        for record in group["records"]
    }
    current = json.loads(
        (WORK / "translations" / f"{bank}.json").read_text(
            encoding="utf-8"
        )
    )
    return japanese, current


def _visible(text: str) -> str:
    """Remove structural controls for conservative prose-length heuristics."""

    return CONTROL_RE.sub("", text).strip()


def _review_reasons(current: str, competitor: str) -> tuple[str, ...]:
    """Return mechanical leads without asserting that either wording is best."""

    reasons: list[str] = []
    if control_values(current) != control_values(competitor):
        reasons.append("competitor-control-layout-differs")
    current_visible = _visible(current)
    competitor_visible = _visible(competitor)
    if (
        len(competitor_visible) >= 12
        and len(current_visible) + 10 < len(competitor_visible)
        and len(current_visible) < 0.72 * len(competitor_visible)
    ):
        reasons.append("possible-current-omission")
    if LEADING_CONJUNCTION_RE.search(current_visible) or FRAGMENT_END_RE.search(
        current_visible
    ):
        reasons.append("possible-current-fragment")
    if (
        len(current_visible) > 20
        and current_visible
        and current_visible[-1] not in ".!?\'\"-)"
    ):
        reasons.append("current-missing-terminal-punctuation")
    return tuple(reasons)


def _priority(reasons: tuple[str, ...], wording_differs: bool) -> str:
    """Classify high-priority mechanical leads separately from plain diffs."""

    high_priority = {
        "possible-current-omission",
        "possible-current-fragment",
        "current-missing-terminal-punctuation",
    }
    if any(reason in high_priority for reason in reasons):
        return "priority-review"
    if wording_differs:
        return "compare"
    return "same"


def _range_is_written(
    mask: bytes,
    entry_global_offset: int,
    interval: tuple[int, int],
) -> bool:
    """Test whether IPS records explicitly supplied one file-relative range."""

    start, end = interval
    return all(mask[entry_global_offset + start : entry_global_offset + end])


def _write_tsv(rows: list[dict[str, object]], path: Path) -> None:
    """Write flat comparison rows with JSON-encoded list-valued cells."""

    if not rows:
        raise ValueError("cannot write an empty three-way comparison")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )


def _build_comparison(
    japanese_images: dict[str, FdsImage],
    current_images: dict[str, FdsImage],
    competitor_images: dict[str, FdsImage],
    competitor_write_mask: bytes,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Decode, validate, align, and summarize all 1,299 scenario records."""

    rows: list[dict[str, object]] = []
    bank_summaries: dict[str, object] = {}
    authority: dict[str, object] = {}
    half_index = {"zenpen": 0, "kouhen": 1}
    for spec in SCENARIO_SPECS:
        japanese_entry = _find_entry(japanese_images[spec.half], spec)
        current_entry = _find_entry(current_images[spec.half], spec)
        competitor_entry = _find_entry(competitor_images[spec.half], spec)
        japanese_bank = decode_scenario_file(
            japanese_entry, spec.record_counts, TextDialect.JAPANESE
        )
        current_bank = decode_scenario_file(
            current_entry,
            spec.record_counts,
            TextDialect.CURRENT_ENGLISH,
        )
        competitor_bank = decode_scenario_file(
            competitor_entry,
            spec.record_counts,
            TextDialect.COMPETITOR_ENGLISH,
        )
        decoded_banks: tuple[DecodedBank, ...] = (
            japanese_bank,
            current_bank,
            competitor_bank,
        )
        record_counts = {len(bank.records) for bank in decoded_banks}
        if record_counts != {sum(spec.record_counts)}:
            raise ValueError(f"{spec.name} decoded record counts do not align")

        public_japanese, public_current = _load_public_maps(spec.name)
        base = (
            half_index[spec.half] * 2 * SIDE_SIZE
            + spec.side * SIDE_SIZE
            + competitor_entry.data_offset
        )
        text_coverage = [
            _range_is_written(competitor_write_mask, base, interval)
            for interval in competitor_bank.text_ranges
        ]
        if not all(text_coverage):
            raise ValueError(
                f"{spec.name} competitor text depends on bytes not explicitly "
                "written by the IPS; supply the patch's exact source image"
            )
        pointer_coverage = [
            _range_is_written(competitor_write_mask, base, interval)
            for interval in competitor_bank.pointer_ranges
        ]
        authority[spec.name] = {
            "text_and_dictionary_ranges": len(text_coverage),
            "text_and_dictionary_ranges_explicitly_written": sum(
                text_coverage
            ),
            "pointer_ranges": len(pointer_coverage),
            "pointer_ranges_explicitly_written": sum(pointer_coverage),
        }

        bank_rows: list[dict[str, object]] = []
        for japanese, current, competitor in zip(
            japanese_bank.records,
            current_bank.records,
            competitor_bank.records,
            strict=True,
        ):
            coordinate = (japanese.group, japanese.record)
            if coordinate != (current.group, current.record) or coordinate != (
                competitor.group,
                competitor.record,
            ):
                raise ValueError(f"{spec.name} logical coordinates diverged")
            text_id = f"{spec.name}/g{japanese.group}/r{japanese.record}"
            if public_japanese.get(text_id) != japanese.text:
                raise ValueError(
                    f"{text_id} Japanese ROM text differs from public evidence"
                )
            if public_current.get(text_id) != current.text:
                raise ValueError(
                    f"{text_id} current ROM text differs from playable map"
                )
            wording_differs = current.text != competitor.text
            reasons = _review_reasons(current.text, competitor.text)
            row: dict[str, object] = {
                "sequence": len(rows) + len(bank_rows) + 1,
                "half": spec.half,
                "side": spec.side,
                "fds_filename": spec.name,
                "bank": spec.name,
                "group": japanese.group,
                "record": japanese.record,
                "text_id": text_id,
                "japanese_exact": japanese.text,
                "current_english_exact": current.text,
                "competitor_english_exact": competitor.text,
                "japanese_controls": list(control_values(japanese.text)),
                "current_controls": list(control_values(current.text)),
                "competitor_controls": list(
                    control_values(competitor.text)
                ),
                "current_controls_match_japanese": (
                    control_values(current.text)
                    == control_values(japanese.text)
                ),
                "competitor_controls_match_japanese": (
                    control_values(competitor.text)
                    == control_values(japanese.text)
                ),
                "japanese_packed_bytes": japanese.packed_bytes,
                "current_packed_bytes": current.packed_bytes,
                "competitor_packed_bytes": competitor.packed_bytes,
                "current_visible_characters": len(_visible(current.text)),
                "competitor_visible_characters": len(
                    _visible(competitor.text)
                ),
                "competitor_minus_current_visible_characters": (
                    len(_visible(competitor.text))
                    - len(_visible(current.text))
                ),
                "wording_differs": wording_differs,
                "review_reasons": list(reasons),
                "review_priority": _priority(reasons, wording_differs),
                "proposed_revision": "",
                "reviewer_notes": "",
            }
            bank_rows.append(row)
        rows.extend(bank_rows)
        priorities = Counter(str(row["review_priority"]) for row in bank_rows)
        bank_summaries[spec.name] = {
            "records": len(bank_rows),
            "wording_differences": sum(
                bool(row["wording_differs"]) for row in bank_rows
            ),
            "priority_review": priorities["priority-review"],
            "compare": priorities["compare"],
            "same": priorities["same"],
            "current_control_mismatches": sum(
                not bool(row["current_controls_match_japanese"])
                for row in bank_rows
            ),
            "competitor_control_mismatches": sum(
                not bool(row["competitor_controls_match_japanese"])
                for row in bank_rows
            ),
            "japanese_packed_record_bytes": sum(
                int(row["japanese_packed_bytes"]) for row in bank_rows
            ),
            "current_packed_record_bytes": sum(
                int(row["current_packed_bytes"]) for row in bank_rows
            ),
            "competitor_packed_record_bytes": sum(
                int(row["competitor_packed_bytes"]) for row in bank_rows
            ),
            "current_dictionary_entries": current_bank.dictionary_entries,
            "competitor_dictionary_entries": (
                competitor_bank.dictionary_entries
            ),
        }

    if len(rows) != 1299:
        raise ValueError(f"expected 1299 scenario rows, decoded {len(rows)}")
    summary = {
        "records": len(rows),
        "wording_differences": sum(
            bool(row["wording_differs"]) for row in rows
        ),
        "exact_wording_matches": sum(
            not bool(row["wording_differs"]) for row in rows
        ),
        "priority_review": sum(
            row["review_priority"] == "priority-review" for row in rows
        ),
        "plain_comparison": sum(
            row["review_priority"] == "compare" for row in rows
        ),
        "current_control_mismatches": sum(
            not bool(row["current_controls_match_japanese"]) for row in rows
        ),
        "competitor_control_mismatches": sum(
            not bool(row["competitor_controls_match_japanese"])
            for row in rows
        ),
        "banks": bank_summaries,
        "competitor_patch_authority": authority,
    }
    return rows, summary


def _parser() -> argparse.ArgumentParser:
    """Build the explicit private-input command-line interface."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate an ignored private three-way Time Twist scenario review"
        )
    )
    parser.add_argument("--japanese-zenpen", type=Path, required=True)
    parser.add_argument("--japanese-kouhen", type=Path, required=True)
    parser.add_argument("--current-zenpen", type=Path, required=True)
    parser.add_argument("--current-kouhen", type=Path, required=True)
    parser.add_argument("--competitor-zenpen", type=Path, required=True)
    parser.add_argument("--competitor-kouhen", type=Path, required=True)
    parser.add_argument("--competitor-ips", type=Path, required=True)
    parser.add_argument(
        "--output-directory", type=Path, default=DEFAULT_OUTPUT_DIRECTORY
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Audit six images, reconstruct patch-authoritative text, and write rows."""

    args = _parser().parse_args(argv)
    paths = {
        "japanese_zenpen": args.japanese_zenpen,
        "japanese_kouhen": args.japanese_kouhen,
        "current_zenpen": args.current_zenpen,
        "current_kouhen": args.current_kouhen,
        "competitor_zenpen": args.competitor_zenpen,
        "competitor_kouhen": args.competitor_kouhen,
        "competitor_ips": args.competitor_ips,
    }
    identities = {name: _identity(path) for name, path in paths.items()}
    japanese_zenpen = args.japanese_zenpen.read_bytes()
    japanese_kouhen = args.japanese_kouhen.read_bytes()
    current_zenpen = args.current_zenpen.read_bytes()
    current_kouhen = args.current_kouhen.read_bytes()
    competitor_zenpen = args.competitor_zenpen.read_bytes()
    competitor_kouhen = args.competitor_kouhen.read_bytes()

    japanese_images = {
        "zenpen": FdsImage.from_bytes(japanese_zenpen),
        "kouhen": FdsImage.from_bytes(japanese_kouhen),
    }
    current_images = {
        "zenpen": FdsImage.from_bytes(current_zenpen),
        "kouhen": FdsImage.from_bytes(current_kouhen),
    }
    patch = parse_ips(args.competitor_ips.read_bytes())
    reconstructed, written = apply_ips(
        japanese_zenpen + japanese_kouhen, patch
    )
    expected_bytes = 4 * SIDE_SIZE
    if len(reconstructed) != expected_bytes:
        raise ValueError(
            f"reconstructed competitor target is {len(reconstructed)} bytes; "
            f"expected {expected_bytes}"
        )
    competitor_images = {
        "zenpen": FdsImage.from_bytes(reconstructed[: 2 * SIDE_SIZE]),
        "kouhen": FdsImage.from_bytes(reconstructed[2 * SIDE_SIZE :]),
    }
    rows, summary = _build_comparison(
        japanese_images, current_images, competitor_images, written
    )
    malformed_audit = _malformed_competitor_audit(
        japanese_zenpen,
        japanese_kouhen,
        competitor_zenpen,
        competitor_kouhen,
    )
    source_sha1 = hashlib.sha1(
        japanese_zenpen + japanese_kouhen
    ).hexdigest().upper()
    payload = {
        "schema": "time-twist-three-way-scenario-comparison-v1",
        "notice": (
            "Private review artifact: do not commit or redistribute. Japanese "
            "is authoritative; competitor wording is a diagnostic lead only."
        ),
        "inputs": identities,
        "japanese_manifests": {
            name: image.manifest() for name, image in japanese_images.items()
        },
        "current_manifests": {
            name: image.manifest() for name, image in current_images.items()
        },
        "competitor_malformed_output_audit": malformed_audit,
        "competitor_patch": {
            "records": len(patch.records),
            "truncate_size": patch.truncate_size,
            "expected_source": COMPETITOR_EXPECTED_SOURCE,
            "supplied_combined_source_sha1": source_sha1,
            "supplied_source_matches_competitor_release": (
                source_sha1 == COMPETITOR_EXPECTED_SOURCE["sha1"]
            ),
            "text_authority": (
                "Every decoded scenario and dictionary byte was explicitly "
                "written by IPS; source-derived pointer bytes are reported "
                "separately."
            ),
        },
        "summary": summary,
        "rows": rows,
    }
    args.output_directory.mkdir(parents=True, exist_ok=True)
    json_path = args.output_directory / "time_twist_three_way.json"
    tsv_path = args.output_directory / "time_twist_three_way.tsv"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_tsv(rows, tsv_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote private JSON: {json_path}")
    print(f"Wrote private TSV:  {tsv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
