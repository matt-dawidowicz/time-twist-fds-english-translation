from __future__ import annotations

import tempfile
import unittest
import json
import re
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
from time_twist.font import (
    EXTENDED_TILE_IDS,
    PIXEL_FONT_5X7,
    patched_nov4_font,
    render_glyph,
)
from time_twist.scenario import (
    ScenarioError,
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from time_twist.textcodec import PackedSymbol, SymbolKind


class ScenarioTests(unittest.TestCase):
    def test_all_translation_maps_are_complete_and_contain_no_japanese(self) -> None:
        paths = sorted(Path("work/translations").glob("*.json"))
        if not paths:
            self.skipTest("translation maps are not available")
        total = 0
        japanese = re.compile(r"[ぁ-ゟ゠-ヿ一-龯]")
        for path in paths:
            translations = json.loads(path.read_text(encoding="utf-8"))
            total += len(translations)
            for record_id, english in translations.items():
                with self.subTest(record_id=record_id):
                    self.assertIsInstance(english, str)
                    self.assertTrue(english)
                    self.assertIsNone(japanese.search(english))
        self.assertEqual(total, 1299)

    def test_recovered_character_map(self) -> None:
        self.assertEqual(decode_common(0), "あ")
        self.assertEqual(decode_common(45), "ん")
        self.assertEqual(decode_extended(5), "が")
        self.assertEqual(decode_extended(32), "ぱ")
        self.assertEqual(decode_extended(37), "ぁ")
        self.assertEqual(decode_extended(42), "っ")
        self.assertEqual(decode_extended(45), "ょ")
        self.assertEqual(decode_extended(46), "1")
        self.assertEqual(decode_extended(63), " ")

    def test_dictionary_symbols_are_one_based(self) -> None:
        common = PackedSymbol(SymbolKind.COMMON, 0, 0, 0)
        dictionary_symbol = PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0)
        dictionary = ((common,),)
        self.assertEqual(render_symbols((dictionary_symbol,), dictionary), "あ")

    def test_tt1b_layout_and_first_record(self) -> None:
        path = Path(
            "work/extracted_zenpen/side1_00_TT1B_A200.bin"
        )
        if not path.exists():
            self.skipTest("workspace fixture is not available")
        bank = parse_scenario_bank(path)
        self.assertEqual(bank.group_addresses[0], 0xADE4)
        self.assertEqual(bank.dictionary_address, 0xBCDA)
        self.assertEqual(len(bank.records), 137)
        self.assertEqual(len(bank.dictionary), 29)

    def test_scenario_banks_rebuild_byte_identically(self) -> None:
        paths = sorted(Path("work/extracted_zenpen").glob("*.bin"))
        paths += sorted(Path("work/extracted_kouhen").glob("*.bin"))
        scenario_names = {
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
            "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        }
        paths = [
            path for path in paths
            if any(f"_{name}_" in path.name for name in scenario_names)
        ]
        if not paths:
            self.skipTest("workspace fixtures are not available")
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
                    bank, groups, dictionary=bank.dictionary
                )
                self.assertEqual(rebuilt, path.read_bytes())

    def test_original_scenario_dictionaries_are_flat(self) -> None:
        paths = sorted(Path("work/extracted_zenpen").glob("*.bin"))
        paths += sorted(Path("work/extracted_kouhen").glob("*.bin"))
        scenario_names = {
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
            "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        }
        paths = [
            path for path in paths
            if any(f"_{name}_" in path.name for name in scenario_names)
        ]
        if not paths:
            self.skipTest("workspace fixtures are not available")
        for path in paths:
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
        repertoire = "".join(dict.fromkeys(
            COMMON_CHARACTERS + "".join(EXTENDED_CHARACTERS.values())
        ))
        self.assertEqual(len(COMMON_CHARACTERS), 48)
        self.assertEqual(len(repertoire), 74)
        text = repertoire + "{CTRL:1}" + repertoire
        self.assertEqual(render_english(encode_english(text)), text)

    def test_english_font_preserves_runtime_table_shape(self) -> None:
        self.assertEqual(set(EXTENDED_TILE_IDS), set(range(37, 64)))
        path = Path("work/extracted_zenpen/side0_08_NOV4_A200.bin")
        if not path.exists():
            self.skipTest("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov4_font(original)
        self.assertEqual(len(patched), len(original))
        self.assertNotEqual(patched, original)

    def test_pixel_font_is_complete_and_case_legible(self) -> None:
        repertoire = "".join(dict.fromkeys(
            COMMON_CHARACTERS + "".join(EXTENDED_CHARACTERS.values())
        ))
        for char in repertoire:
            with self.subTest(char=char):
                self.assertEqual(len(render_glyph(char)), 8)
        self.assertNotEqual(render_glyph("a"), render_glyph("A"))
        self.assertEqual(render_glyph(" "), b"\xFF" * 8)

    def test_accented_e_shares_the_lowercase_e_baseline(self) -> None:
        plain = render_glyph("e")
        accented = render_glyph("é")
        self.assertEqual(accented[2:7], plain[2:7])
        self.assertEqual(accented[7], 0xFF)
        self.assertNotEqual(accented[:2], b"\xFF\xFF")
        self.assertEqual(PIXEL_FONT_5X7["é"][:2], ("00010", "00100"))

    def test_lowercase_p_uses_the_shared_lowercase_x_height(self) -> None:
        self.assertEqual(PIXEL_FONT_5X7["p"][:2], ("00000", "00000"))
        self.assertEqual(PIXEL_FONT_5X7["p"][-2:], ("10000", "10000"))

    def test_tt1b_sky_line_is_natural_and_width_safe(self) -> None:
        path = Path("work/translations/TT1B.json")
        if not path.exists():
            self.skipTest("TT1B translation fixture is not available")
        translations = json.loads(path.read_text(encoding="utf-8"))
        line = translations["TT1B/g0/r1"]
        self.assertEqual(line, "When did I last see it?")
        validate_display_width(line)

    def test_fixed_footprint_rebuild_keeps_the_original_tail_address(self) -> None:
        path = Path("work/extracted_zenpen/side1_01_TT1A_A200.bin")
        if not path.exists():
            self.skipTest("workspace fixture is not available")
        bank = parse_scenario_bank(path)
        short_groups = tuple(
            tuple(() for _ in group_records)
            for group_records in (
                tuple(
                    record for record in bank.records
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
        oversized = (oversized_group,) + short_groups[1:]
        with self.assertRaises(ScenarioError):
            rebuild_scenario_bank(
                bank,
                oversized,
                preserve_memory_footprint=True,
            )

    def test_translated_banks_match_sources_and_preserve_fixed_tails(self) -> None:
        fixtures = (
            (
                "TT1A",
                Path("work/extracted_zenpen/side1_01_TT1A_A200.bin"),
                Path("work/translated_banks/TT1A_fixed_footprint.bin"),
                Path("work/translations/TT1A.json"),
            ),
            (
                "TT1B",
                Path("work/extracted_zenpen/side1_00_TT1B_A200.bin"),
                Path("work/translated_banks/TT1B_fixed_footprint.bin"),
                Path("work/translations/TT1B.json"),
            ),
            (
                "TT2",
                Path("work/extracted_zenpen/side1_02_TT2_A200.bin"),
                Path("work/translated_banks/TT2_fixed_footprint.bin"),
                Path("work/translations/TT2.json"),
            ),
            (
                "T22",
                Path("work/extracted_zenpen/side1_03_T22_A200.bin"),
                Path("work/translated_banks/T22_fixed_footprint.bin"),
                Path("work/translations/T22.json"),
            ),
            (
                "TT3A",
                Path("work/extracted_zenpen/side0_01_TT3A_A200.bin"),
                Path("work/translated_banks/TT3A_fixed_footprint.bin"),
                Path("work/translations/TT3A.json"),
            ),
            (
                "TT3B",
                Path("work/extracted_zenpen/side0_02_TT3B_A200.bin"),
                Path("work/translated_banks/TT3B_fixed_footprint.bin"),
                Path("work/translations/TT3B.json"),
            ),
            (
                "TT4",
                Path("work/extracted_kouhen/side1_00_TT4_A200.bin"),
                Path("work/translated_banks/TT4_fixed_footprint.bin"),
                Path("work/translations/TT4.json"),
            ),
            (
                "TT5",
                Path("work/extracted_kouhen/side1_01_TT5_A200.bin"),
                Path("work/translated_banks/TT5_fixed_footprint.bin"),
                Path("work/translations/TT5.json"),
            ),
            (
                "T25",
                Path("work/extracted_kouhen/side1_02_T25_A200.bin"),
                Path("work/translated_banks/T25_fixed_footprint.bin"),
                Path("work/translations/T25.json"),
            ),
            (
                "TT6A",
                Path("work/extracted_kouhen/side0_04_TT6A_A200.bin"),
                Path("work/translated_banks/TT6A_fixed_footprint.bin"),
                Path("work/translations/TT6A.json"),
            ),
            (
                "TT6B",
                Path("work/extracted_kouhen/side0_03_TT6B_A200.bin"),
                Path("work/translated_banks/TT6B_fixed_footprint.bin"),
                Path("work/translations/TT6B.json"),
            ),
            (
                "TT6C",
                Path("work/extracted_kouhen/side0_02_TT6C_A200.bin"),
                Path("work/translated_banks/TT6C_fixed_footprint.bin"),
                Path("work/translations/TT6C.json"),
            ),
            (
                "TT6D",
                Path("work/extracted_kouhen/side0_05_TT6D_A200.bin"),
                Path("work/translated_banks/TT6D_fixed_footprint.bin"),
                Path("work/translations/TT6D.json"),
            ),
        )
        if not all(path.exists() for fixture in fixtures for path in fixture[1:]):
            self.skipTest("translated bank fixtures are not available")

        for bank_name, original_path, translated_path, translations_path in fixtures:
            with self.subTest(bank=bank_name):
                original = parse_scenario_bank(original_path)
                translated = parse_scenario_bank(translated_path)
                expected = json.loads(translations_path.read_text(encoding="utf-8"))
                self.assertEqual(len(translated.data), len(original.data))
                self.assertEqual(
                    translated.data[original.dictionary_end_offset :],
                    original.data[original.dictionary_end_offset :],
                )
                self.assertFalse(
                    any(
                        symbol.kind is SymbolKind.DICTIONARY
                        for entry in translated.dictionary
                        for symbol in entry
                    )
                )
                self.assertEqual(len(translated.records), len(expected))
                for record in translated.records:
                    record_id = (
                        f"{bank_name}/g{record.group_index}/r{record.record_index}"
                    )
                    self.assertEqual(
                        render_english(
                            expand_dictionary_symbols(
                                record.symbols, translated.dictionary
                            )
                        ),
                        expected[record_id],
                    )

    def test_all_completed_translation_segments_fit_the_display(self) -> None:
        for bank_name in (
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B", "TT4", "TT5",
            "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        ):
            path = Path(f"work/translations/{bank_name}.json")
            if not path.exists():
                self.skipTest("translation fixtures are not available")
            translations = json.loads(path.read_text(encoding="utf-8"))
            for record_id, english in translations.items():
                with self.subTest(record=record_id):
                    validate_display_width(
                        english,
                        allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
                    )

    def test_personality_questions_are_complete_and_width_safe(self) -> None:
        path = Path("work/translations/TT1A.json")
        if not path.exists():
            self.skipTest("translation fixture is not available")
        translations = json.loads(path.read_text(encoding="utf-8"))
        rows = [
            ("Do you prefer consommé", "to miso soup?"),
            ("Can you swim 50 meters?", None),
            ("Do you laugh at random?", None),
            ("Are the Giants the best?", None),
            ("Have you dated at least", "three girls?"),
            ("Have you had sleep", "paralysis?"),
            ("Do you want to hit", "3 or more people?"),
            ("Have you curled up and", "cried?"),
            ("Do you put play first?", None),
            ("Do brand names matter?", None),
            ("Do you leave work until", "tomorrow?"),
            ("Do you believe only you", "can protect yourself?"),
            ("Will you help society", "someday?"),
            ("Do you want a brief,", "full life?"),
            ("Is love all you need?", None),
        ]
        expected = [
            first if second is None else first.ljust(24) + second
            for first, second in rows
        ]
        actual = [translations[f"TT1A/g0/r{record}"] for record in range(6, 21)]
        self.assertEqual(actual, expected)
        for question in actual:
            validate_display_width(question, allow_wrap=True)
        for question, (first, second) in zip(actual, rows):
            self.assertEqual(question[:24].rstrip(), first)
            if second is not None:
                self.assertEqual(question[24:], second)

    def test_scenario_refresh_preserves_existing_english(self) -> None:
        bank_path = Path("work/extracted_zenpen/side1_01_TT1A_A200.bin")
        if not bank_path.exists():
            self.skipTest("workspace fixture is not available")
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

    def test_english_dictionary_compresses_and_expands_losslessly(self) -> None:
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
        self.assertTrue(
            all(
                symbol.kind is not SymbolKind.DICTIONARY
                for entry in dictionary
                for symbol in entry
            )
        )
        self.assertLess(
            packed_size(compressed, dictionary),
            packed_size(groups, ()),
        )
        for original, rebuilt in zip(groups[0], compressed[0]):
            self.assertEqual(
                expand_dictionary_symbols(rebuilt, dictionary), original
            )

    def test_translation_merge_validates_ids_and_controls(self) -> None:
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
