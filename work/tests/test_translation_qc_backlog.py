"""Regression coverage for the evidence-dependent translation QC backlog."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_BANKS = ROOT / "work" / "translation_workbook_banks"
EXPECTED_CONTEXT_IDS = {
    "TT3A/g2/r30",
    "TT3B/g0/r24",
    "TT4/g4/r14",
}


def _bank_rows(bank_name: str) -> list[dict[str, object]]:
    """Load generated workbook rows for one bank."""
    payload = json.loads(
        (WORKBOOK_BANKS / f"{bank_name}.json").read_text(encoding="utf-8")
    )
    return payload["rows"]


def _row(bank_name: str, record_id: str) -> dict[str, object]:
    """Return one generated workbook row by stable record ID."""
    for row in _bank_rows(bank_name):
        if row["original_record_id"] == record_id:
            return row
    raise AssertionError(f"missing workbook row: {record_id}")


class TranslationQCBacklogTests(unittest.TestCase):
    """Keep resolved QC items out of the evidence-dependent backlog."""

    def test_only_three_records_require_gameplay_or_visual_context(
        self,
    ) -> None:
        """Keep the remaining backlog limited to genuinely staging-dependent rows."""
        unresolved: set[str] = set()
        for path in sorted(WORKBOOK_BANKS.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for row in payload["rows"]:
                if row["requires_gameplay_context"] == "yes":
                    unresolved.add(row["original_record_id"])

        self.assertEqual(unresolved, EXPECTED_CONTEXT_IDS)

    def test_tt1b_exhibit_question_is_resolved(self) -> None:
        """Treat the girl's question reading as settled by the protagonist's reply."""
        row = _row("TT1B", "TT1B/g0/r28")
        self.assertEqual(row["confidence_level"], "High")
        self.assertEqual(row["unresolved_ambiguity"], "")
        self.assertEqual(row["translation_status"], "Final proposed")
        self.assertEqual(row["requires_gameplay_context"], "no")
        self.assertIn(
            "Have you seen all the exhibits?", row["literal_english_meaning"]
        )

    def test_wait_prompt_exception_is_resolved_and_documented(self) -> None:
        """Keep NOV2's intentional one-line engine patch out of the visual backlog."""
        row = _row("NOV2", "NOV2/wait")
        self.assertEqual(row["confidence_level"], "High")
        self.assertEqual(row["unresolved_ambiguity"], "")
        self.assertEqual(row["translation_status"], "Final proposed")
        self.assertEqual(row["requires_gameplay_context"], "no")
        self.assertEqual(
            row["patch_safe_english_translation"], "PLEASE WAIT..."
        )
        self.assertEqual(row["control_codes_match"], "no")
        self.assertIn(
            "Integration coverage verifies",
            row["linguistic_and_cultural_notes"],
        )


if __name__ == "__main__":
    unittest.main()
