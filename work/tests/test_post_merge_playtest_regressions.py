"""CI gate for every runtime fix added since the last merged playtest sync."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from time_twist import ui
from time_twist.english import encode_english
from time_twist.entropy_codec import unpack_entropy_stream
from time_twist.entropy_runtime import _INTERNAL_TABLE_STREAM
from time_twist.release_build import _patch_tt4_fisherman_quiz_branches
from time_twist.production_translation import (
    QUIZ_QUESTION_RECORDS,
    _validate_cross_record_staging,
    _validate_quiz_question_geometry,
    merged_translation_map,
)

ROOT = Path(__file__).resolve().parents[2]
CONTROL_RE = re.compile(r"\{CTRL:[0-7]\}")


def _semantic(record):
    """Return kind/value pairs for one packed semantic record."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _production(bank_name: str) -> dict[str, str]:
    """Materialize one authoritative production bank."""
    return merged_translation_map(
        bank_name,
        base_directory=ROOT / "work" / "translations",
        override_directory=ROOT / "work" / "production_overrides",
        review_directory=ROOT / "review" / "production_retranslation",
    )


class PostMergePlaytestRegressionTests(unittest.TestCase):
    """Freeze every runtime correction made after main@9eb601f."""

    def test_retail_part2_player_flow_is_documented(self) -> None:
        """Keep the proven Zenpen-to-Kouhen startup path player-visible."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        playtesting = (ROOT / "PLAYTESTING.md").read_text(encoding="utf-8")
        matrix = (ROOT / "docs" / "PLAYTEST_MATRIX.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Playing Part 2 (Kouhen)", readme)
        self.assertIn("Part 1 / Side A", readme)
        self.assertIn("Part 2 / Side B", readme)
        self.assertIn("fourth side", readme.lower())

        self.assertIn("TO BE CONTINUED...", playtesting)
        self.assertIn("choose `Part 2`", playtesting)
        self.assertIn("`TT2` Side B (the fourth side)", playtesting)
        self.assertIn("Retail second-half startup", matrix)
        self.assertIn("select `TT2` Side B (fourth side)", matrix)

    def test_shared_disk_card_uses_full_spacing(self) -> None:
        """Protect the production Part 2 / Side A spacing fix."""
        records = unpack_entropy_stream(
            _INTERNAL_TABLE_STREAM, record_count=51
        )
        expected = (
            "Part 1",
            "Part 2",
            "{CTRL:0}Side A",
            "{CTRL:0}Side B",
            "{CTRL:0}{CTRL:0}Insert now.",
        )
        for record, text in zip(records[3:8], expected, strict=True):
            self.assertEqual(
                _semantic(record),
                _semantic(encode_english(text)),
            )

    def test_all_info_cards_keep_field_boundaries(self) -> None:
        """Protect both automatic-intro and Info-button identity cards."""
        cards = {
            ("TT2", "TT2/g1/r5"): ("Name:", "Trade:"),
            ("TT2", "TT2/g1/r6"): ("Name:", "Trade:"),
            ("TT3A", "TT3A/g0/r14"): (
                "TIME:",
                "LOCATION:",
                "NAME:",
                "RANK:",
            ),
            ("TT4", "TT4/g1/r22"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT5", "TT5/g1/r6"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT6A", "TT6A/g0/r8"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
            ("TT6A", "TT6A/g1/r10"): (
                "TIME:",
                "PLACE:",
                "NAME:",
                "OCCUPATION:",
            ),
        }
        cache: dict[str, dict[str, str]] = {}
        for (bank_name, record_id), labels in cards.items():
            text = cache.setdefault(bank_name, _production(bank_name))[
                record_id
            ]
            segments = CONTROL_RE.split(text)
            for segment in segments:
                present = [label for label in labels if label in segment]
                with self.subTest(record_id=record_id, segment=segment):
                    self.assertLessEqual(len(present), 1)

    def test_athens_treatment_menu_remains_compact(self) -> None:
        """Keep the three geometry-sensitive treatment actions short."""
        self.assertEqual(
            ui.TT4_FIXED_TEXT_RECORDS[46:49],
            ("Squeeze", "Prick", "Leave it"),
        )

    def test_priest_statue_page_ends_on_complete_clause(self) -> None:
        """Do not leave the priest's accusation hanging on 'some local'."""
        text = _production("TT4")["TT4/g0/r9"]
        self.assertIn(
            "the statue! I nearly{CTRL:0}fainted…{CTRL:2}"
            "Probably local thugs{CTRL:0}did it.{CTRL:3}",
            text,
        )
        self.assertNotIn("I nearly{CTRL:2}", text)

    def test_athens_missing_boy_pause_follows_complete_question(self) -> None:
        """Do not require A in the middle of the ten-year-old question."""
        text = _production("TT4")["TT4/g2/r14"]
        self.assertIn(
            "around ten years old?{CTRL:6}Me: I'm not sure…",
            text,
        )
        self.assertNotIn("ten years{CTRL:6}", text)

    def test_cross_record_a_press_overwrite_protection_is_global(self) -> None:
        """Keep every production bank out of rows reused by its next record."""
        for path in sorted((ROOT / "work" / "translations").glob("*.json")):
            bank_name = path.stem
            if bank_name not in {
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
            }:
                continue
            base = json.loads(path.read_text(encoding="utf-8"))
            production = _production(bank_name)
            _validate_cross_record_staging(bank_name, base, production)

        self.assertEqual(
            _production("TT4")["TT4/g1/r26"],
            "His shoulder is burned.",
        )

    def test_all_scenario_quizzes_keep_native_geometry(self) -> None:
        """Protect all 25 chapter-quiz prompts, not only the fisherman."""
        self.assertEqual(len(QUIZ_QUESTION_RECORDS), 25)
        for bank_name in ("TT2", "TT3A", "TT4", "TT5", "TT6B"):
            base = json.loads(
                (
                    ROOT / "work" / "translations" / f"{bank_name}.json"
                ).read_text(encoding="utf-8")
            )
            production = _production(bank_name)
            _validate_quiz_question_geometry(bank_name, base, production)

    def test_first_fisherman_answer_menu_is_localized(self) -> None:
        """Keep the first answer set meaningful for an English player."""
        self.assertEqual(
            ui.TT4_FIXED_TEXT_RECORDS[77:81],
            ("Polis", "Agora", "Acropolis", "Colony"),
        )

    def test_temple_quiz_top_pair_fits_runtime_window(self) -> None:
        """Keep the temple quiz's paired top row inside its narrower window."""
        choices = ui.TT4_FIXED_TEXT_RECORDS[86:91]
        self.assertEqual(
            choices,
            ("Delphi", "Pantheon", "Parthenon", "Olympia", "Karnak"),
        )
        # This five-choice window pairs choice 1 with choice 5. Keep the
        # paired row at or below the playtested 13-glyph ceiling.
        self.assertLessEqual(len(choices[0]) + len(choices[4]), 13)

    def test_crop_quiz_pairs_short_labels_with_long_labels(self) -> None:
        """Keep the six-choice crop menu inside the same narrow runtime window."""
        choices = ui.TT4_FIXED_TEXT_RECORDS[91:97]
        self.assertEqual(
            choices,
            ("Strawberry", "Melon", "Brown rice", "Pearl", "Fig", "Coffee"),
        )
        self.assertLessEqual(len(choices[0]) + len(choices[4]), 13)
        self.assertLessEqual(len(choices[1]) + len(choices[5]), 13)

    def test_reordered_quiz_choices_move_correct_vm_targets(self) -> None:
        """Keep answer correctness aligned with the reordered English menus."""
        data = bytearray(b"\x00" * 0x1000)
        load_address = 0xA200
        temple_offset = 0xAE3E - load_address
        crop_offset = 0xAE4C - load_address
        data[temple_offset : temple_offset + 6] = bytes.fromhex(
            "31 DB DB DB DB 06"
        )
        data[crop_offset : crop_offset + 7] = bytes.fromhex(
            "31 CD CD 07 CD CD CD"
        )
        patched = _patch_tt4_fisherman_quiz_branches(bytes(data))
        self.assertEqual(
            patched[temple_offset : temple_offset + 6],
            bytes.fromhex("31 DB DB 06 DB DB"),
        )
        self.assertEqual(
            patched[crop_offset : crop_offset + 7],
            bytes.fromhex("31 CD CD CD CD 07 CD"),
        )

    def test_fisherman_quiz_stays_natural_and_two_line(self) -> None:
        """Freeze the runtime-safe natural Athens fisherman question forms."""
        tt4 = _production("TT4")
        expected = {
            "TT4/g5/r7": "{CTRL:0}{CTRL:0}What were city-states{CTRL:0}in Greece called?",
            "TT4/g5/r10": "{CTRL:0}{CTRL:0}Which city-state was{CTRL:0}Athens' greatest rival?",
            "TT4/g5/r11": "{CTRL:0}{CTRL:0}Who was the great hero{CTRL:0}of Greek mythology?",
            "TT4/g5/r12": "{CTRL:0}{CTRL:0}Which temple was built{CTRL:0}for the goddess Athena?",
            "TT4/g5/r13": (
                "{CTRL:0}{CTRL:0}What crop joined olives"
                "{CTRL:0}and grapes in Greece?"
            ),
        }
        for record_id, text in expected.items():
            with self.subTest(record_id=record_id):
                self.assertEqual(tt4[record_id], text)


if __name__ == "__main__":
    unittest.main()
