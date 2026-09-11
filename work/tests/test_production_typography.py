"""Regression tests for production punctuation policy."""

from __future__ import annotations

import json
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


class ProductionTypographyTests(unittest.TestCase):
    """Keep source-unjustified dash typography out of game-facing English."""

    def test_materialized_corpus_has_no_em_or_en_dashes(self) -> None:
        """Require ordinary punctuation unless a future source case is reviewed."""
        with tempfile.TemporaryDirectory(prefix="time_twist_typography_") as directory:
            output_directory = Path(directory)
            counts = materialize_production_maps(
                BANK_NAMES,
                base_directory=ROOT / "work" / "translations",
                override_directory=ROOT / "work" / "production_overrides",
                review_directory=ROOT / "review" / "production_retranslation",
                output_directory=output_directory,
            )
            self.assertEqual(sum(counts.values()), 1299)

            offenders: list[str] = []
            for bank_name in BANK_NAMES:
                records = json.loads(
                    (output_directory / f"{bank_name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                offenders.extend(
                    record_id
                    for record_id, text in records.items()
                    if "—" in text or "–" in text
                )

            self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
