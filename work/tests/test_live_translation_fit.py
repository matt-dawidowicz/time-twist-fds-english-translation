"""Recompute playable scenario footprints from the current translation maps."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generate_translation_workbook import (
    OUTPUTS,
    measure_translation_footprint,
)
from time_twist.capacity import (
    NATIVE_SCENARIO_CAPACITY_BYTES,
    RELOCATED_FIXED_TABLE_PREFIX_BYTES,
    playable_capacity,
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
        """Recompress every bank and fail only when current text exceeds capacity.

        Recovered native capacities describe the scenario region.
        Relocated full-word menu banks add
        a source-verified movable prefix to that scenario reservation; current
        usage is recomputed from scenario plus menu with the conservative
        68-entry flat baseline used by workbook analysis. The canonical release
        uses the separate frozen entropy pipeline and reports its actual layout
        and NOV3 headroom in the candidate manifest.
        """
        self.assertEqual(
            set(NATIVE_SCENARIO_CAPACITY_BYTES), set(KNOWN_SCENARIO_BANKS)
        )
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
            used = measure_translation_footprint(bank_name)
            scenario_capacity = NATIVE_SCENARIO_CAPACITY_BYTES[bank_name]
            capacity = playable_capacity(bank_name, scenario_capacity)
            self.assertEqual(
                published[bank_name],
                {
                    "used": used,
                    "capacity": capacity,
                    "remaining": capacity - used,
                },
            )
            self.assertIn(
                f"- {bank_name}: {used}/{capacity} bytes used;", progress
            )
            self.assertIn(f"{bank_name} {used}/{capacity} bytes", html)
            print(
                f"FIT {bank_name}: {used}/{capacity} "
                f"({capacity - used} bytes free)"
            )
            self.assertLessEqual(
                used,
                capacity,
                f"{bank_name} exceeds its conservative analysis footprint by "
                f"{used - capacity} bytes",
            )

    def test_measurement_reads_changed_playable_text(self) -> None:
        """A source edit must change the report measurement without a table edit."""
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
