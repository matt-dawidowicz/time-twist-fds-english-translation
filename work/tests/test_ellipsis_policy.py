"""Regression coverage for canonical ellipsis punctuation in playable English."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.ui import (
    DISK_NUMBER_ERROR_PATCHES,
    DISK_PROMPT_PATCHES,
    DISK_SET_ERROR_ENGLISH,
    SIDE_NUMBER_ERROR_PATCHES,
    WRONG_DISK_PATCHES,
)
from time_twist.ui_fixed_tables import FIXED_RECORD_TABLE_SPECS

ROOT = Path(__file__).resolve().parents[2]


class EllipsisPolicyTests(unittest.TestCase):
    """Keep literal three-dot ellipses out of production-facing English text."""

    def test_scenario_production_uses_true_ellipsis_glyphs(self) -> None:
        """Require every materialized scenario record to use U+2026 for ellipses."""
        offenders: list[str] = []
        for bank in KNOWN_SCENARIO_BANKS:
            production = merged_translation_map(
                bank,
                base_directory=ROOT / "work" / "translations",
                override_directory=ROOT / "work" / "production_overrides",
                review_directory=ROOT / "review" / "production_retranslation",
            )
            offenders.extend(
                f"{record_id}: {text}"
                for record_id, text in production.items()
                if "..." in text
            )
        self.assertEqual(
            [],
            offenders,
            "ASCII ellipses remain:\n" + "\n".join(offenders),
        )

    def test_fixed_menu_labels_use_true_ellipsis_glyphs(self) -> None:
        """Reject ASCII ellipses from every canonical fixed menu label table."""
        offenders = [
            f"{bank}: {label}"
            for bank, spec in FIXED_RECORD_TABLE_SPECS.items()
            for label in spec.records
            if "..." in label
        ]
        self.assertEqual(
            [],
            offenders,
            "ASCII ellipses remain:\n" + "\n".join(offenders),
        )

    def test_fixed_prompt_strings_use_true_ellipsis_glyphs(self) -> None:
        """Reject ASCII ellipses from fixed prompt strings that remain semantic text."""
        texts = [
            *(english for _, _, english in DISK_PROMPT_PATCHES),
            DISK_SET_ERROR_ENGLISH,
            *(english for _, _, english in SIDE_NUMBER_ERROR_PATCHES),
            *(english for _, _, english in DISK_NUMBER_ERROR_PATCHES),
            *(english for _, _, english in WRONG_DISK_PATCHES),
        ]
        offenders = [text for text in texts if "..." in text]
        self.assertEqual(
            [],
            offenders,
            "ASCII ellipses remain:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
