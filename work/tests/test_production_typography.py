"""Regression tests for production punctuation and spacing policy."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from time_twist.production_translation import materialize_production_maps

ROOT = Path(__file__).resolve().parents[2]
BANK_NAMES = (
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
CONTROL_RE = re.compile(r"\{CTRL:\d+\}")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[,.!?;:]")
PUNCT_ONLY_LABEL_RE = re.compile(r"^[^:]+: [.!?]+$")
MISSING_SPACE_AFTER_PUNCT_RE = re.compile(r"(?:[,;!?]|:(?!\d))(?=[A-Za-z])")
MISSING_SPACE_AFTER_PERIOD_RE = re.compile(r"(?<![A-Z])\.(?=[A-Z][a-z])")
DOUBLED_ROW_ADVANCE_RE = re.compile(r"\{CTRL:([04])\}\{CTRL:\1\}")
APPROVED_NEW_DOUBLED_ROW_ADVANCES = {
    "TT3A/g3/r13": "{CTRL:0}{CTRL:0}",
}


def _materialized_records(output_directory: Path) -> dict[str, str]:
    """Materialize and return the complete production corpus."""
    counts = materialize_production_maps(
        BANK_NAMES,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
        output_directory=output_directory,
    )
    if sum(counts.values()) != 1299:
        raise AssertionError(f"expected 1299 production records, got {sum(counts.values())}")

    records: dict[str, str] = {}
    for bank_name in BANK_NAMES:
        records.update(
            json.loads(
                (output_directory / f"{bank_name}.json").read_text(encoding="utf-8")
            )
        )
    return records


def _base_records() -> dict[str, str]:
    """Return the certified base translation corpus keyed by record id."""
    records: dict[str, str] = {}
    for bank_name in BANK_NAMES:
        records.update(
            json.loads(
                (ROOT / "work" / "translations" / f"{bank_name}.json").read_text(
                    encoding="utf-8"
                )
            )
        )
    return records


class ProductionTypographyTests(unittest.TestCase):
    """Keep game-facing punctuation and spacing mechanically clean."""

    maxDiff = None

    def test_materialized_corpus_has_no_em_or_en_dashes(self) -> None:
        """Require ordinary punctuation unless a future source case is reviewed."""
        with tempfile.TemporaryDirectory(
            prefix="time_twist_typography_"
        ) as directory:
            records = _materialized_records(Path(directory))
            offenders = [
                record_id
                for record_id, text in records.items()
                if "—" in text or "–" in text
            ]
            self.assertEqual(offenders, [])

    def test_materialized_visible_segments_have_clean_spacing(self) -> None:
        """Reject unambiguous whitespace defects without second-guessing controls."""
        with tempfile.TemporaryDirectory(prefix="time_twist_spacing_") as directory:
            records = _materialized_records(Path(directory))
            offenders: list[str] = []
            for record_id, text in records.items():
                for segment in CONTROL_RE.split(text):
                    if not segment:
                        continue
                    problems: list[str] = []
                    if segment != segment.strip():
                        problems.append("leading/trailing space")
                    if "  " in segment:
                        problems.append("double space")
                    if "\t" in segment or "\n" in segment or "\r" in segment:
                        problems.append("embedded whitespace control")
                    if (
                        SPACE_BEFORE_PUNCT_RE.search(segment)
                        and not PUNCT_ONLY_LABEL_RE.fullmatch(segment)
                    ):
                        problems.append("space before punctuation")
                    if MISSING_SPACE_AFTER_PUNCT_RE.search(segment):
                        problems.append("missing space after punctuation")
                    if MISSING_SPACE_AFTER_PERIOD_RE.search(segment):
                        problems.append("missing space after period")
                    if problems:
                        offenders.append(
                            f"{record_id}: {', '.join(problems)}: {segment!r}"
                        )

            self.assertEqual(offenders, [])

    def test_materialized_corpus_has_no_unapproved_new_blank_rows(self) -> None:
        """Do not introduce doubled row advances unless layout review approved them."""
        with tempfile.TemporaryDirectory(prefix="time_twist_blank_rows_") as directory:
            production = _materialized_records(Path(directory))
            base = _base_records()
            offenders: list[str] = []

            for record_id, text in production.items():
                production_pairs = DOUBLED_ROW_ADVANCE_RE.findall(text)
                base_pairs = DOUBLED_ROW_ADVANCE_RE.findall(base[record_id])
                if production_pairs == base_pairs:
                    continue

                approved = APPROVED_NEW_DOUBLED_ROW_ADVANCES.get(record_id)
                if approved and approved in text and not production_pairs[: len(base_pairs)] != base_pairs:
                    continue

                new_pairs = production_pairs.copy()
                for pair in base_pairs:
                    if pair in new_pairs:
                        new_pairs.remove(pair)
                if new_pairs:
                    offenders.append(
                        f"{record_id}: introduced doubled CTRL:{', CTRL:'.join(new_pairs)}"
                    )

            self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
