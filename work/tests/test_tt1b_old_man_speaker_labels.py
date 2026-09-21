"""Regression coverage for TT1B's source-specific old-man speaker label."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map

ROOT = Path(__file__).resolve().parents[2]


def _production(bank_name: str) -> dict[str, str]:
    """Materialize one authoritative production bank."""
    return merged_translation_map(
        bank_name,
        base_directory=ROOT / "work" / "translations",
    )


class TT1BOldManSpeakerLabelTests(unittest.TestCase):
    """Distinguish TT1B roujin from TT6A's actual elder title."""

    def test_tt1b_museum_owner_uses_old_man(self) -> None:
        """Translate TT1B roujin literally rather than adding an elder title."""
        tt1b = _production("TT1B")
        record_ids = (
            "TT1B/g2/r9",
            "TT1B/g2/r10",
            "TT1B/g2/r17",
            "TT1B/g2/r18",
            "TT1B/g2/r19",
            "TT1B/g2/r20",
            "TT1B/g2/r21",
            "TT1B/g2/r22",
            "TT1B/g2/r23",
            "TT1B/g2/r24",
        )

        for record_id in record_ids:
            with self.subTest(record_id=record_id):
                self.assertIn("Old Man:", tt1b[record_id])
                self.assertNotIn("Elder:", tt1b[record_id])

    def test_tt6a_actual_elder_title_is_preserved(self) -> None:
        """Keep Elder for TT6A chourou; this is not a global replacement."""
        tt6a = _production("TT6A")
        self.assertIn("Elder:", tt6a["TT6A/g0/r26"])


if __name__ == "__main__":
    unittest.main()
