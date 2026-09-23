"""Regression tests for the sole canonical scenario-English source."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.production_translation import (
    CANONICAL_RECORD_COUNTS,
    CHECKPOINT_QUIZ_LAYOUTS,
    STRUCTURAL_LAYOUT_RECORDS,
    ProductionTranslationError,
    layout_review_text,
    materialize_production_maps,
    merged_translation_map,
)
from time_twist.project import KNOWN_SCENARIO_BANKS

ROOT = Path(__file__).resolve().parents[2]
TRANSLATIONS = ROOT / "work" / "translations"


def _canonical(bank_name: str) -> dict[str, str]:
    """Load one validated canonical bank through the release-facing API."""
    return merged_translation_map(
        bank_name,
        base_directory=TRANSLATIONS,
    )


class CanonicalProductionTranslationTests(unittest.TestCase):
    """Keep release translation selection single-source and fail-closed."""

    def test_all_thirteen_banks_are_complete(self) -> None:
        """Require exactly 1,299 canonical scenario records."""
        self.assertEqual(
            set(CANONICAL_RECORD_COUNTS), set(KNOWN_SCENARIO_BANKS)
        )
        self.assertEqual(sum(CANONICAL_RECORD_COUNTS.values()), 1299)
        total = 0
        for bank in KNOWN_SCENARIO_BANKS:
            materialized = _canonical(bank)
            self.assertEqual(
                len(materialized),
                CANONICAL_RECORD_COUNTS[bank],
                bank,
            )
            total += len(materialized)
        self.assertEqual(total, 1299)

    def test_release_api_returns_exact_canonical_file(self) -> None:
        """Do not rewrite or select alternative wording during materialization."""
        for bank in KNOWN_SCENARIO_BANKS:
            expected = json.loads(
                (TRANSLATIONS / f"{bank}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(_canonical(bank), expected, bank)

    def test_materializer_is_an_exact_validating_copy(self) -> None:
        """Stage canonical maps without changing one word or control."""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            counts = materialize_production_maps(
                tuple(KNOWN_SCENARIO_BANKS),
                base_directory=TRANSLATIONS,
                output_directory=output,
            )
            self.assertEqual(sum(counts.values()), 1299)
            for bank in KNOWN_SCENARIO_BANKS:
                self.assertEqual(
                    (output / f"{bank}.json").read_bytes(),
                    (TRANSLATIONS / f"{bank}.json").read_bytes(),
                    bank,
                )

    def test_legacy_layer_arguments_are_rejected(self) -> None:
        """Never allow a second English source to enter release selection."""
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "legacy translation layering is retired",
        ):
            merged_translation_map(
                "TT1B",
                base_directory=TRANSLATIONS,
                override_directory=ROOT / "unused",
            )
        with self.assertRaisesRegex(
            ProductionTranslationError,
            "legacy translation layering is retired",
        ):
            merged_translation_map(
                "TT1B",
                base_directory=TRANSLATIONS,
                review_directory=ROOT / "unused",
            )

    def test_known_latest_translation_fixes_are_canonical(self) -> None:
        """Lock source-significant corrections that exposed stale-layer failures."""
        tt1b = _canonical("TT1B")
        self.assertEqual(
            tt1b["TT1B/g0/r1"],
            "When was the last time I{CTRL:0}saw a blue sky?",
        )
        self.assertNotIn("When did I last see it?", tt1b.values())

        tt1a = _canonical("TT1A")
        self.assertEqual(
            tt1a["TT1A/g0/r3"],
            (
                "The Fortune-Telling{CTRL:0}Service Center presents:{CTRL:0}"
                '"Today\'s Fortune"{CTRL:0}Enter your blood type.'
            ),
        )

        self.assertEqual(
            tt1a["TT1A/g0/r5"],
            (
                "We'll begin with a{CTRL:0}personality test.{CTRL:0}"
                "Please answer each{CTRL:0}question."
            ),
        )

        tt3a = _canonical("TT3A")
        self.assertEqual(
            tt3a["TT3A/g2/r30"],
            (
                "A torn piece of a note,{CTRL:0}written in blue ink: "
                '"…4{CTRL:0}km southwest…"{CTRL:0}"…Rebecca"'
            ),
        )
        self.assertIn(
            "Mary: I was sure he'd{CTRL:4}believe me…",
            _canonical("TT6A")["TT6A/g1/r28"],
        )

    def test_reviewed_quiz_layout_exceptions_are_structural_only(self) -> None:
        """Do not grandfather ordinary prose around the modern wrap policy."""
        self.assertIn("TT1A/g0/r3", STRUCTURAL_LAYOUT_RECORDS)
        self.assertIn("TT1A/g0/r5", STRUCTURAL_LAYOUT_RECORDS)
        self.assertNotIn("TT1A/g0/r3", CHECKPOINT_QUIZ_LAYOUTS)
        self.assertNotIn("TT1A/g0/r5", CHECKPOINT_QUIZ_LAYOUTS)
        expected = {
            "TT3A/g4/r7",
            "TT4/g5/r7",
            "TT4/g5/r11",
            "TT5/g2/r16",
            "TT6B/g1/r30",
            "TT6B/g2/r1",
            "TT6B/g2/r2",
            "TT6B/g2/r3",
        }
        self.assertEqual(set(CHECKPOINT_QUIZ_LAYOUTS), expected)
        self.assertLessEqual(
            set(CHECKPOINT_QUIZ_LAYOUTS), STRUCTURAL_LAYOUT_RECORDS
        )

    def test_generic_layout_is_strictly_greedy(self) -> None:
        """Future prose edits must fill rows before inserting soft breaks."""
        output = layout_review_text(
            "TEST/g0/r0",
            "Have you ever had sleep paralysis?",
            "Have you ever{CTRL:0}had sleep{CTRL:0}paralysis?",
        )
        self.assertEqual(
            output,
            "Have you ever had sleep{CTRL:0}paralysis?",
        )

    def test_generic_layout_starts_new_speakers_on_fresh_rows(self) -> None:
        """Keep speaker turns separate while filling within each turn."""
        output = layout_review_text(
            "TEST/g0/r0",
            "Girl: Eek! Me: Hold on to me!",
            "Girl: Eek!{CTRL:0}Me: Hold on to me!",
        )
        self.assertEqual(
            output,
            "Girl: Eek!{CTRL:0}Me: Hold on to me!",
        )

    def test_retired_translation_sources_are_absent(self) -> None:
        """Keep historical English data out of the active source tree."""
        retired = (
            ROOT / "review" / "production_retranslation",
            ROOT / "work" / "production_overrides",
            ROOT / "work" / "translation_workbook_banks",
        )
        for path in retired:
            self.assertFalse(path.exists(), path)

        for filename in (
            "generate_bilingual_comparison.py",
            "generate_bilingual_comparison_ci.py",
            "generate_translation_workbook.py",
            "generate_translation_workbook_ci.py",
        ):
            self.assertFalse((ROOT / "work" / filename).exists(), filename)

    def test_active_tree_has_no_retired_translation_path_references(
        self,
    ) -> None:
        """Allow retired path names only in audit/history documentation."""
        forbidden = (
            "/".join(("review", "production_retranslation")),
            "/".join(("work", "production_overrides")),
            "/".join(("work", "translation_workbook_banks")),
        )
        suffixes = {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt"}
        offenders: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            relative = path.relative_to(ROOT)
            if relative.parts and relative.parts[0] == "audit":
                continue
            if relative.parts[:2] == ("docs", "history"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(value in text for value in forbidden):
                offenders.append(relative.as_posix())

        self.assertEqual(
            offenders,
            [],
            "retired translation path referenced by active source:\n"
            + "\n".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
