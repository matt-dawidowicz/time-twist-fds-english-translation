"""Build a review queue for the production retranslation.

The workbook already preserves a source-reviewed natural-English layer beside
what is currently playable.  This audit turns that preservation data into an
editorial queue; it never auto-promotes prose into the ROM.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

CONTROL_RE = re.compile(r"\{CTRL:[0-7]\}|⟦CTRL:[0-7]⟧")
BANK_ORDER = (
    "TT1A",
    "TT1B",
    "TT2",
    "T22",
    "TT3A",
    "TT3B",
    "TT4",
    "TT5",
    "T25",
    "TT6A",
    "TT6B",
    "TT6C",
    "TT6D",
)


def _visible(text: str) -> str:
    """Support the visible operation for this module."""
    return CONTROL_RE.sub(" / ", text).replace("  ", " ").strip()


def _segments(text: str) -> list[str]:
    """Support the segments operation for this module."""
    return [segment for segment in CONTROL_RE.split(text) if segment]


def _priority(row: dict[str, object]) -> int:
    """Support the priority operation for this module."""
    playable = str(row.get("patch_safe_english_translation", ""))
    natural = str(row.get("final_natural_english_translation", ""))
    score = 0
    if playable != natural:
        score += 5
    if str(row.get("nuance_lost_in_patch_safe_version", "")).strip():
        score += 4
    if bool(row.get("requires_technical_expansion")):
        score += 4
    if bool(row.get("requires_gameplay_context")):
        score += 2

    visible = _visible(playable)
    # High-signal translationese patterns.  These do not prove a bad line; they
    # simply move suspicious records earlier in the human review queue.
    suspicious = (
        " when?",
        " where?",
        " who?",
        " what?",
        " no one here",
        " got the ",
        " money's all",
        " last saw ",
    )
    lowered = f" {visible.lower()} "
    if any(pattern in lowered for pattern in suspicious):
        score += 2
    if any(len(segment) >= 23 for segment in _segments(playable)):
        score += 1
    return score


def rows(root: Path) -> list[dict[str, object]]:
    """Return prioritized localization audit rows from all workbook banks."""
    output: list[dict[str, object]] = []
    for bank in BANK_ORDER:
        path = root / "work" / "translation_workbook_banks" / f"{bank}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        for source in payload["rows"]:
            if source.get("record_type") != "scenario":
                continue
            playable = str(source["patch_safe_english_translation"])
            natural = str(source["final_natural_english_translation"])
            item = {
                "priority": _priority(source),
                "bank": bank,
                "record_id": source["original_record_id"],
                "speaker": source.get("speaker_or_narration_identity", ""),
                "exact_japanese": source.get("exact_japanese_source", ""),
                "playable_english": playable,
                "natural_english": natural,
                "differs_from_natural": playable != natural,
                "nuance_lost": source.get(
                    "nuance_lost_in_patch_safe_version", ""
                ),
                "requires_technical_expansion": source.get(
                    "requires_technical_expansion", False
                ),
                "requires_gameplay_context": source.get(
                    "requires_gameplay_context", False
                ),
                "longest_playable_segment": max(
                    (len(segment) for segment in _segments(playable)),
                    default=0,
                ),
                "longest_natural_segment": max(
                    (len(segment) for segment in _segments(natural)), default=0
                ),
            }
            output.append(item)
    output.sort(
        key=lambda item: (
            -int(item["priority"]),
            BANK_ORDER.index(str(item["bank"])),
            str(item["record_id"]),
        )
    )
    return output


def main() -> int:
    """Write the prioritized localization audit CSV."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    review_rows = rows(args.repo_root)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)

    compromised = sum(bool(row["differs_from_natural"]) for row in review_rows)
    print(
        f"queued {len(review_rows)} scenario records; "
        f"{compromised} differ from the preserved natural-English layer"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
