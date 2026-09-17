"""Recompute playable scenario footprints from the current translation maps."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generate_translation_workbook import OUTPUTS, measure_translation_footprint
from generate_translation_workbook_ci import measure_current_footprints
from time_twist.capacity import (
    NATIVE_SCENARIO_CAPACITY_BYTES,
    RELOCATED_FIXED_TABLE_PREFIX_BYTES,
)
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.ui import FIXED_RECORD_TABLE_SPECS


class LiveTranslationFitTests(unittest.TestCase):
    """Prove current playable text still fits every recovered bank capacity."""

    def test_relocated_capacity_facts_cover_exactly_the_repacked_banks(
        self,
    ) -> None:
        """Keep ROM-free capacity evidence aligned with the release architecture."""
        self.assertEqual(
            set(RELOCATED_FIXED_TABLE_PREFIX_BYTES),
            set(FIXED_RECORD_TABLE_SPECS),
        )

    def test_current_translation_maps_fit(self) -> None:
        """Match the published report to the checked current-fit evidence.

        The public workbook uses the fast 68-entry baseline where it fits. If
        that conservative pass overflows, ``measure_current_footprints`` may
        substitute only an explicitly checked deterministic-optimizer result.
        TT4 currently uses that path: the fast baseline is 27 bytes over while
        the production optimizer packs the reviewed text inside the recovered
        reservation. The canonical ROM-backed release manifest remains the
        authority for the final built-image layout.
        """
        self.assertEqual(
            set(NATIVE_SCENARIO_CAPACITY_BYTES), set(KNOWN_SCENARIO_BANKS)
        )
        measured = measure_current_footprints()
        payload = json.loads(
            (
                OUTPUTS / "Time_Twist_complete_translation_workbook.json"
            ).read_text(encoding="utf-8")
        )
        published = payload["patch_validation"]["revised_bank_footprints"]
        progress = (OUTPUTS / "Time_Twist_translation_progress.md").read_text(
            encoding="utf-8"
        )
        html = (
            OUTPUTS / "Time_Twist_complete_translation_workbook.html"
        ).read_text(encoding="utf-8")
        for bank_name in KNOWN_SCENARIO_BANKS:
            footprint = measured[bank_name]
            used = footprint["used"]
            capacity = footprint["capacity"]
            self.assertEqual(published[bank_name], footprint)
            self.assertIn(
                f"- {bank_name}: {used}/{capacity} bytes used;", progress
            )
            self.assertIn(f"{bank_name} {used}/{capacity} bytes", html)
            print(
                f"FIT {bank_name}: {used}/{capacity} "
                f"({footprint['remaining']} bytes free)"
            )
            self.assertLessEqual(
                used,
                capacity,
                f"{bank_name} exceeds its checked analysis footprint by "
                f"{used - capacity} bytes",
            )

    def test_measurement_reads_changed_playable_text(self) -> None:
        """A source edit must change the raw measurement without a table edit."""
        original = measure_translation_footprint("TT6D")
        with tempfile.TemporaryDirectory() as directory:
            translations = Path(directory)
            (translations / "TT6D.json").write_text(
                json.dumps({"TT6D/g0/r0": "A"}), encoding="utf-8"
            )
            with patch(
                "generate_translation_workbook.TRANSLATIONS", translations
            ):
                changed = measure_translation_footprint("TT6D")
        self.assertLess(changed, original)


if __name__ == "__main__":
    unittest.main()
