"""Protect the approved dash-free canonical English without touching ROM data."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map
from time_twist.project import KNOWN_SCENARIO_BANKS

ROOT = Path(__file__).resolve().parents[2]
TRANSLATIONS = ROOT / "work" / "translations"


class ProductionTypographyTests(unittest.TestCase):
    """Detect unreviewed em/en dashes in the complete canonical text corpus."""

    def test_canonical_scenario_dashes_follow_editorial_policy(self) -> None:
        """Require all 1,305 entries to retain the approved punctuation."""
        offenders: list[str] = []
        record_count = 0
        for bank in KNOWN_SCENARIO_BANKS:
            entries = merged_translation_map(
                bank,
                base_directory=TRANSLATIONS,
            )
            record_count += len(entries)
            offenders.extend(
                f"{record_id}: {value}"
                for record_id, value in entries.items()
                if "—" in value or "–" in value
            )
        self.assertEqual(record_count, 1305)
        self.assertEqual(
            [],
            offenders,
            "Unreviewed em/en dashes:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
