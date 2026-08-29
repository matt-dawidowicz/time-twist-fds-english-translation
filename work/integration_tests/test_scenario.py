"""Private integration tests for source banks and current scenario authority."""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from time_twist.charmap import decode_common, decode_extended
from time_twist.cli import (
    PERSONALITY_QUESTION_IDS,
    command_scenario_extract,
    merge_translation_document,
)
from time_twist.compression import (
    compress_english_groups,
    expand_dictionary_symbols,
    packed_size,
)
from time_twist.english import (
    COMMON_CHARACTERS,
    EXTENDED_CHARACTERS,
    encode_english,
    render_english,
    validate_display_width,
)
from time_twist.project import KNOWN_SCENARIO_BANKS
from time_twist.scenario import (
    ScenarioError,
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from time_twist.textcodec import PackedSymbol, SymbolKind

WORK_DIR = Path(__file__).resolve().parents[1]
TRANSLATIONS = WORK_DIR / "translations"
SCENARIO_NAMES = set(KNOWN_SCENARIO_BANKS)


def _source_scenario_paths() -> tuple[Path, ...]:
    """Return every regenerated original scenario bank in stable path order."""
    paths = sorted((WORK_DIR / "extracted_zenpen").glob("*.bin"))
    paths += sorted((WORK_DIR / "extracted_kouhen").glob("*.bin"))
    return tuple(
        path
        for path in paths
        if any(f"_{name}_" in path.name for name in SCENARIO_NAMES)
    )


def _translations(bank_name: str) -> dict[str, str]:
    """Load one current ID-keyed translation map."""
    payload = json.loads(
        (TRANSLATIONS / f"{bank_name}.json").read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise AssertionError(f"{bank_name} translation map is not an object")
    return payload


class ScenarioTests(unittest.TestCase):
    """Protect source parsing and the current, source-locked English maps."""

    def test_all_translation_maps_are_complete_and_contain_no_japanese(
        self,
    ) -> None:
        """Require nonempty English for all 1,299 scenario records."""
        total = 0
        japanese = re.compile(r"[ぁ-ゟ゠-ヿ一-龯]")
        for bank_name in KNOWN_SCENARIO_BANKS:
            translations = _translations(bank_name)
            total += len(translations)
            for record_id, english in translations.items():
                with self.subTest(record=record_id):
                    self.assertIsInstance(english, str)
                    self.assertTrue(english)
                    self.assertIsNone(japanese.search(english))
        self.assertEqual(total, 1299)

    def test_recovered_character_map(self) -> None:
        """Lock representative Japanese common/extended source symbols."""
        self.assertEqual(decode_common(0), "あ")
        self.assertEqual(decode_common(45), "ん")
        self.assertEqual(decode_extended(5), "が")
        self.assertEqual(decode_extended(32), "ぱ")
        self.assertEqual(decode_extended(37), "ぁ")
        self.assertEqual(decode_extended(42), "っ")
        self.assertEqual(decode_extended(45), "ょ")
        self.assertEqual(decode_extended(46), "1")
        self.assertEqual(decode_extended(63), " ")

    def test_duplicate_group_pointers_are_rejected(self) -> None:
        """Reject a source bank whose group table no longer increases."""
        source = WORK_DIR / "extracted_zenpen/side1_00_TT1B_A200.bin"
        data = bytearray(source.read_bytes())
        first_group = int.from_bytes(data[0x26:0x28], "little")
        table_address = int.from_bytes(data[0x24:0x26], "little")
        table_offset = table_address - 0xA200
        data[table_offset : table_offset + 2] = first_group.to_bytes(
            2, "little"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TT1B.bin"
            path.write_bytes(data)
            with self.assertRaisesRegex(ScenarioError, "strictly ordered"):
                parse_scenario_bank(path)

    def test_scenario_banks_rebuild_byte_identically(self) -> None:
        """Round-trip every regenerated original scenario bank exactly."""
        paths = _source_scenario_paths()
        self.assertEqual(len(paths), len(KNOWN_SCENARIO_BANKS))
        for path in paths:
            with self.subTest(path=path.name):
                bank = parse_scenario_bank(path)
                groups = tuple(
                    tuple(
                        record.symbols
                        for record in bank.records
                        if record.group_index == group_index
                    )
                    for group_index in range(len(bank.group_addresses))
                )
                rebuilt = rebuild_scenario_bank(
                    bank,
                    groups,
                    dictionary=bank.dictionary,
                )
                self.assertEqual(rebuilt, path.read_bytes())

    def test_original_scenario_dictionaries_are_flat(self) -> None:
        """Require original dictionary entries to contain no nested refs."""
        for path in _source_scenario_paths():
            with self.subTest(path=path.name):
                bank = parse_scenario_bank(path)
                self.assertFalse(
                    any(
                        symbol.kind is SymbolKind.DICTIONARY
                        for entry in bank.dictionary
                        for symbol in entry
                    )
                )

    def test_english_map_round_trip_and_capacity(self) -> None:
        """Round-trip the complete current 73-glyph English repertoire."""
        repertoire = "".join(
            dict.fromkeys(
                COMMON_CHARACTERS + "".join(EXTENDED_CHARACTERS.values())
            )
        )
        self.assertEqual(len(COMMON_CHARACTERS), 48)
        self.assertEqual(len(repertoire), 73)
        text = repertoire + "{CTRL:1}" + repertoire
        self.assertEqual(render_english(encode_english(text)), text)

    def test_current_translation_maps_fit_the_display(self) -> None:
        """Validate every current line through the native 24-column policy."""
        for bank_name in KNOWN_SCENARIO_BANKS:
            for record_id, english in _translations(bank_name).items():
                with self.subTest(record=record_id):
                    validate_display_width(
                        english,
                        allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
                    )

    def test_personality_questions_are_complete_and_width_safe(self) -> None:
        """Keep the 15-question block complete without freezing old wording."""
        translations = _translations("TT1A")
        expected_ids = tuple(f"TT1A/g0/r{record}" for record in range(6, 21))
        self.assertEqual(set(PERSONALITY_QUESTION_IDS), set(expected_ids))
        for record_id in expected_ids:
            question = translations[record_id]
            with self.subTest(record=record_id):
                self.assertTrue(question.strip())
                self.assertNotIn("{CTRL:", question)
                self.assertLessEqual(len(question), 48)
                validate_display_width(question, allow_wrap=True)

    def test_semantic_regressions_preserve_current_story_fixes(self) -> None:
        """Lock high-value meaning fixes without duplicating whole scripts."""
        tt1a = _translations("TT1A")
        self.assertNotIn("on TV", tt1a["TT1A/g0/r1"])

        tt1b = _translations("TT1B")
        self.assertIn("I'm no developer.", tt1b["TT1B/g2/r5"])

        tt3a = _translations("TT3A")
        self.assertIn("Assassination plot", tt3a["TT3A/g1/r19"])
        self.assertIn("Escape group code", tt3a["TT3A/g1/r21"])
        self.assertIn("Drop dead, Hitler!", tt3a["TT3A/g1/r21"])
        self.assertIn("Rebecca's", tt3a["TT3A/g3/r2"])
        self.assertIn("A fragment of the note.", tt3a["TT3A/g2/r30"])

        tt4 = _translations("TT4")
        self.assertFalse(any("Yomi" in line for line in tt4.values()))

        tt6d = _translations("TT6D")
        self.assertIn("I thought I had died.", tt6d["TT6D/g0/r1"])

    def test_fixed_footprint_rebuild_keeps_the_original_tail_address(
        self,
    ) -> None:
        """Keep non-text bytes fixed for the non-relocated TT1A bank."""
        path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        bank = parse_scenario_bank(path)
        short_groups = tuple(
            tuple(() for _ in group_records)
            for group_records in (
                tuple(
                    record
                    for record in bank.records
                    if record.group_index == group_index
                )
                for group_index in range(len(bank.group_addresses))
            )
        )
        rebuilt = rebuild_scenario_bank(
            bank,
            short_groups,
            preserve_memory_footprint=True,
        )
        self.assertEqual(len(rebuilt), len(bank.data))
        self.assertEqual(
            rebuilt[bank.dictionary_end_offset :],
            bank.data[bank.dictionary_end_offset :],
        )

        oversized_group = (
            tuple(
                PackedSymbol(SymbolKind.COMMON, 1, 0, 0)
                for _ in range(len(bank.data) * 2)
            ),
        )
        oversized = (oversized_group, *short_groups[1:])
        with self.assertRaises(ScenarioError):
            rebuild_scenario_bank(
                bank,
                oversized,
                preserve_memory_footprint=True,
            )

    def test_scenario_refresh_preserves_existing_english(self) -> None:
        """Retain hand-edited English when stable record IDs still match."""
        bank_path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "TT1A.json"
            args = SimpleNamespace(bank=bank_path, output=output)
            command_scenario_extract(args)
            document = json.loads(output.read_text(encoding="utf-8"))
            record = document["groups"][0]["records"][0]
            record["english"] = "Proof{CTRL:1}Text"
            output.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            command_scenario_extract(args)
            refreshed = json.loads(output.read_text(encoding="utf-8"))
            refreshed_record = refreshed["groups"][0]["records"][0]
            self.assertEqual(refreshed_record["id"], "TT1A/g0/r0")
            self.assertEqual(refreshed_record["english"], "Proof{CTRL:1}Text")

    def test_english_dictionary_compresses_and_expands_losslessly(
        self,
    ) -> None:
        """Require dictionary compression to preserve exact English symbols."""
        original_records = tuple(
            encode_english(
                "the time traveler returned to the time machine."
                "{CTRL:1}the time traveler waited."
            )
            for _ in range(12)
        )
        groups = (original_records,)
        compressed, dictionary = compress_english_groups(groups)
        self.assertGreater(len(dictionary), 0)
        self.assertLess(
            packed_size(compressed, dictionary),
            packed_size(groups, ()),
        )
        for original, rebuilt in zip(groups[0], compressed[0], strict=True):
            self.assertEqual(
                expand_dictionary_symbols(rebuilt, dictionary), original
            )

    def test_translation_merge_validates_ids_and_controls(self) -> None:
        """Reject missing controls, unknown IDs, and over-wide merged text."""
        document = {
            "groups": [
                {
                    "group": 0,
                    "records": [
                        {
                            "id": "TEST/g0/r0",
                            "japanese": "source{CTRL:1}text",
                            "english": "",
                        }
                    ],
                }
            ]
        }
        merged = merge_translation_document(
            document, {"TEST/g0/r0": "English{CTRL:1}text"}
        )
        self.assertEqual(
            merged["groups"][0]["records"][0]["english"],
            "English{CTRL:1}text",
        )
        with self.assertRaises(SystemExit):
            merge_translation_document(
                document, {"TEST/g0/r0": "English without the control"}
            )
        with self.assertRaisesRegex(SystemExit, "25 columns"):
            merge_translation_document(
                document,
                {"TEST/g0/r0": "1234567890123456789012345{CTRL:1}text"},
            )


if __name__ == "__main__":
    unittest.main()
