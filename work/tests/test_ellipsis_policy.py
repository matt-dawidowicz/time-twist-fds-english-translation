"""Regression coverage for canonical ellipsis punctuation in playable English."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from time_twist.production_translation import merged_translation_map
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.ui import (
    DISK_NUMBER_ERROR_PATCHES,
    DISK_PROMPT_PATCHES,
    DISK_SET_ERROR_ENGLISH,
    FIXED_RECORD_TABLE_SPECS,
    SIDE_NUMBER_ERROR_PATCHES,
    WAIT_PROMPT_TEXT,
    WRONG_DISK_PATCHES,
)

ROOT = Path(__file__).resolve().parents[2]
ASCII_ELLIPSIS_RE = re.compile(r"(?<!\.)\.{3}(?!\.)")


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
                if ASCII_ELLIPSIS_RE.search(text)
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
            if ASCII_ELLIPSIS_RE.search(label)
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
            WAIT_PROMPT_TEXT,
        ]
        offenders = [
            text for text in texts if ASCII_ELLIPSIS_RE.search(text)
        ]
        self.assertEqual(
            [],
            offenders,
            "ASCII ellipses remain:\n" + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
