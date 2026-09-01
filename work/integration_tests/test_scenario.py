"""Private-overlay integration tests for current packed scenario text, font, dictionary, and fixed-footprint contracts."""

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

WORK_DIR = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    def test_all_translation_maps_are_complete_and_contain_no_japanese(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        paths = sorted((WORK_DIR / "translations").glob("*.json"))
        if not paths:
            self.fail("translation maps are not available")
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
        """Verify the current contract described by this regression test."""
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
        """Verify the current contract described by this regression test."""
        common = PackedSymbol(SymbolKind.COMMON, 0, 0, 0)
        dictionary_symbol = PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0)
        dictionary = ((common,),)
        self.assertEqual(
            render_symbols((dictionary_symbol,), dictionary), "あ"
        )

    def test_duplicate_group_pointers_are_rejected(self) -> None:
        """Verify the current contract described by this regression test."""
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

    def test_font_patch_rejects_unknown_same_size_source(self) -> None:
        """Verify the current contract described by this regression test."""
        source = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        data = bytearray(source.read_bytes())
        data[0] ^= 0x01
        with self.assertRaisesRegex(Exception, "supported pre-font source"):
            patched_nov4_font(bytes(data))

    def test_tt1b_layout_and_first_record(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side1_00_TT1B_A200.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        bank = parse_scenario_bank(path)
        self.assertEqual(bank.group_addresses[0], 0xADE4)
        self.assertEqual(bank.dictionary_address, 0xBCDA)
        self.assertEqual(len(bank.records), 137)
        self.assertEqual(len(bank.dictionary), 29)

    def test_scenario_banks_rebuild_byte_identically(self) -> None:
        """Verify the current contract described by this regression test."""
        paths = sorted((WORK_DIR / "extracted_zenpen").glob("*.bin"))
        paths += sorted((WORK_DIR / "extracted_kouhen").glob("*.bin"))
        scenario_names = {
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
        }
        paths = [
            path
            for path in paths
            if any(f"_{name}_" in path.name for name in scenario_names)
        ]
        if not paths:
            self.fail("workspace fixtures are not available")
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
        """Verify the current contract described by this regression test."""
        paths = sorted((WORK_DIR / "extracted_zenpen").glob("*.bin"))
        paths += sorted((WORK_DIR / "extracted_kouhen").glob("*.bin"))
        scenario_names = {
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
        }
        paths = [
            path
            for path in paths
            if any(f"_{name}_" in path.name for name in scenario_names)
        ]
        if not paths:
            self.fail("workspace fixtures are not available")
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
        """Verify the current contract described by this regression test."""
        repertoire = "".join(
            dict.fromkeys(
                COMMON_CHARACTERS + "".join(EXTENDED_CHARACTERS.values())
            )
        )
        self.assertEqual(len(COMMON_CHARACTERS), 48)
        self.assertEqual(len(repertoire), 73)
        text = repertoire + "{CTRL:1}" + repertoire
        self.assertEqual(render_english(encode_english(text)), text)

    def test_english_font_preserves_runtime_table_shape(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(set(EXTENDED_TILE_IDS), set(range(37, 64)))
        path = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
        original = path.read_bytes()
        patched = patched_nov4_font(original)
        self.assertEqual(len(patched), len(original))
        self.assertNotEqual(patched, original)

    def test_pixel_font_is_complete_and_case_legible(self) -> None:
        """Verify the current contract described by this regression test."""
        repertoire = "".join(
            dict.fromkeys(
                COMMON_CHARACTERS + "".join(EXTENDED_CHARACTERS.values())
            )
        )
        for char in repertoire:
            with self.subTest(char=char):
                self.assertEqual(len(render_glyph(char)), 8)
        self.assertNotEqual(render_glyph("a"), render_glyph("A"))
        self.assertEqual(render_glyph(" "), b"\xff" * 8)

    def test_accented_e_shares_the_lowercase_e_baseline(self) -> None:
        """Verify the current contract described by this regression test."""
        plain = render_glyph("e")
        accented = render_glyph("é")
        self.assertEqual(accented[2:7], plain[2:7])
        self.assertEqual(accented[7], 0xFF)
        self.assertNotEqual(accented[:2], b"\xff\xff")
        self.assertEqual(PIXEL_FONT_5X7["é"][:2], ("00010", "00100"))

    def test_lowercase_p_uses_the_shared_lowercase_x_height(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assertEqual(PIXEL_FONT_5X7["p"][:2], ("00000", "00000"))
        self.assertEqual(PIXEL_FONT_5X7["p"][-2:], ("10000", "10000"))

    def test_tt1b_sky_line_is_natural_and_width_safe(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translations/TT1B.json"
        if not path.exists():
            self.fail("TT1B translation fixture is not available")
        translations = json.loads(path.read_text(encoding="utf-8"))
        line = translations["TT1B/g0/r1"]
        self.assertEqual(line, "Blue sky... when was it?")
        validate_display_width(line)

    def test_tt1a_fortune_prediction_has_terminal_punctuation(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translations/TT1A.json"
        if not path.exists():
            self.fail("TT1A translation fixture is not available")
        translations = json.loads(path.read_text(encoding="utf-8"))
        line = translations["TT1A/g0/r27"]
        self.assertIn("She runs into your arms.{CTRL:3}", line)
        validate_display_width(line)

    def test_editorial_regressions_preserve_meaning_and_terminology(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""

        def translations(bank_name: str) -> dict[str, str]:
            """Provide a deterministic helper for the current contract tests."""
            path = WORK_DIR / f"translations/{bank_name}.json"
            if not path.exists():
                self.fail(f"{bank_name} translation fixture is not available")
            return json.loads(path.read_text(encoding="utf-8"))

        tt1a = translations("TT1A")
        self.assertEqual(
            tt1a["TT1A/g0/r1"],
            "News: Dr. Simon,{CTRL:0}a reclusive genius in{CTRL:2}"
            "physics, made this{CTRL:0}statement on time travel{CTRL:4}"
            "late last night.",
        )
        self.assertNotIn("on TV", tt1a["TT1A/g0/r1"])

        tt1b = translations("TT1B")
        self.assertEqual(
            tt1b["TT1B/g0/r28"],
            "Me: Um...{CTRL:1}Girl: Seen everything?{CTRL:0}Me: No...",
        )
        self.assertIn("G-g-g-gah!", tt1b["TT1B/g0/r31"])
        self.assertIn("My telepathy", tt1b["TT1B/g0/r31"])
        self.assertIn("You might say so.", tt1b["TT1B/g0/r31"])
        self.assertIn("finally paid off.", tt1b["TT1B/g0/r31"])
        self.assertIn("You're busty.", tt1b["TT1B/g1/r14"])
        self.assertIn("I'm no land shark.", tt1b["TT1B/g2/r5"])

        t22 = translations("T22")
        self.assertIn("You are my god{CTRL:6}of justice.", t22["T22/g0/r10"])
        self.assertIn("I pledge all", t22["T22/g0/r10"])

        tt3a = translations("TT3A")
        self.assertIn("Assassination plot", tt3a["TT3A/g1/r19"])
        self.assertEqual(
            tt3a["TT3A/g3/r2"],
            "Man: One of Rebecca's?{CTRL:1}Me: No. I fled the camp{CTRL:0}"
            "last night.",
        )
        self.assertIn("the Gestapo!", tt3a["TT3A/g4/r21"])
        self.assertIn("A fragment of the note.", tt3a["TT3A/g2/r30"])

        tt4 = translations("TT4")
        self.assertFalse(any("Yomi" in line for line in tt4.values()))
        self.assertIn("The underworld", tt4["TT4/g4/r4"])

        tt5 = translations("TT5")
        self.assertTrue(
            tt5["TT5/g0/r2"].startswith("Belle: Thank you, truly.")
        )
        self.assertEqual(tt5["TT5/g0/r7"].count("Belle:"), 1)
        self.assertIn("Stay in the South.", tt5["TT5/g0/r18"])
        self.assertNotIn("Dixie", tt5["TT5/g0/r18"])

        tt6a = translations("TT6A")
        self.assertIn("My fiancee Mary", tt6a["TT6A/g0/r13"])
        self.assertIn("She says she had no idea", tt6a["TT6A/g0/r13"])
        self.assertIn("The fiend descended...", tt6a["TT6A/g0/r18"])

        tt6c = translations("TT6C")
        self.assertIn("Voice: The perfect name.", tt6c["TT6C/g1/r9"])
        self.assertIn("I'm the savior", tt6c["TT6C/g2/r13"])

    def test_fixed_footprint_rebuild_keeps_the_original_tail_address(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        if not path.exists():
            self.fail("workspace fixture is not available")
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

    def test_translated_banks_match_sources_and_preserve_fixed_tails(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        fixtures = (
            (
                "TT1A",
                WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin",
                WORK_DIR / "translated_banks/TT1A_fixed_footprint.bin",
                WORK_DIR / "translations/TT1A.json",
            ),
            (
                "TT1B",
                WORK_DIR / "extracted_zenpen/side1_00_TT1B_A200.bin",
                WORK_DIR / "translated_banks/TT1B_fixed_footprint.bin",
                WORK_DIR / "translations/TT1B.json",
            ),
            (
                "TT2",
                WORK_DIR / "extracted_zenpen/side1_02_TT2_A200.bin",
                WORK_DIR / "translated_banks/TT2_fixed_footprint.bin",
                WORK_DIR / "translations/TT2.json",
            ),
            (
                "T22",
                WORK_DIR / "extracted_zenpen/side1_03_T22_A200.bin",
                WORK_DIR / "translated_banks/T22_fixed_footprint.bin",
                WORK_DIR / "translations/T22.json",
            ),
            (
                "TT3A",
                WORK_DIR / "extracted_zenpen/side0_01_TT3A_A200.bin",
                WORK_DIR / "translated_banks/TT3A_fixed_footprint.bin",
                WORK_DIR / "translations/TT3A.json",
            ),
            (
                "TT3B",
                WORK_DIR / "extracted_zenpen/side0_02_TT3B_A200.bin",
                WORK_DIR / "translated_banks/TT3B_fixed_footprint.bin",
                WORK_DIR / "translations/TT3B.json",
            ),
            (
                "TT4",
                WORK_DIR / "extracted_kouhen/side1_00_TT4_A200.bin",
                WORK_DIR / "translated_banks/TT4_fixed_footprint.bin",
                WORK_DIR / "translations/TT4.json",
            ),
            (
                "TT5",
                WORK_DIR / "extracted_kouhen/side1_01_TT5_A200.bin",
                WORK_DIR / "translated_banks/TT5_fixed_footprint.bin",
                WORK_DIR / "translations/TT5.json",
            ),
            (
                "T25",
                WORK_DIR / "extracted_kouhen/side1_02_T25_A200.bin",
                WORK_DIR / "translated_banks/T25_fixed_footprint.bin",
                WORK_DIR / "translations/T25.json",
            ),
            (
                "TT6A",
                WORK_DIR / "extracted_kouhen/side0_04_TT6A_A200.bin",
                WORK_DIR / "translated_banks/TT6A_fixed_footprint.bin",
                WORK_DIR / "translations/TT6A.json",
            ),
            (
                "TT6B",
                WORK_DIR / "extracted_kouhen/side0_03_TT6B_A200.bin",
                WORK_DIR / "translated_banks/TT6B_fixed_footprint.bin",
                WORK_DIR / "translations/TT6B.json",
            ),
            (
                "TT6C",
                WORK_DIR / "extracted_kouhen/side0_02_TT6C_A200.bin",
                WORK_DIR / "translated_banks/TT6C_fixed_footprint.bin",
                WORK_DIR / "translations/TT6C.json",
            ),
            (
                "TT6D",
                WORK_DIR / "extracted_kouhen/side0_05_TT6D_A200.bin",
                WORK_DIR / "translated_banks/TT6D_fixed_footprint.bin",
                WORK_DIR / "translations/TT6D.json",
            ),
        )
        if not all(
            path.exists() for fixture in fixtures for path in fixture[1:]
        ):
            self.fail("translated bank fixtures are not available")

        for (
            bank_name,
            original_path,
            translated_path,
            translations_path,
        ) in fixtures:
            with self.subTest(bank=bank_name):
                original = parse_scenario_bank(original_path)
                translated = parse_scenario_bank(translated_path)
                expected = json.loads(
                    translations_path.read_text(encoding="utf-8")
                )
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
                    record_id = f"{bank_name}/g{record.group_index}/r{record.record_index}"
                    self.assertEqual(
                        render_english(
                            expand_dictionary_symbols(
                                record.symbols, translated.dictionary
                            )
                        ),
                        expected[record_id],
                    )

    def test_all_completed_translation_segments_fit_the_display(self) -> None:
        """Verify the current contract described by this regression test."""
        for bank_name in (
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
        ):
            path = WORK_DIR / f"translations/{bank_name}.json"
            if not path.exists():
                self.fail("translation fixtures are not available")
            translations = json.loads(path.read_text(encoding="utf-8"))
            for record_id, english in translations.items():
                with self.subTest(record=record_id):
                    validate_display_width(
                        english,
                        allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
                    )

    def test_personality_questions_are_complete_and_width_safe(self) -> None:
        """Verify the current contract described by this regression test."""
        path = WORK_DIR / "translations/TT1A.json"
        if not path.exists():
            self.fail("translation fixture is not available")
        translations = json.loads(path.read_text(encoding="utf-8"))
        expected = [
            "Do you prefer consommé  to miso soup?",
            "Swim 50 meters or more?",
            "Do you laugh at random?",
            "Are the Giants the best?",
            "Have you dated at least three girls?",
            "Have you had sleep      paralysis?",
            "Do you want to hit      3 or more people?",
            "Have you curled up and  cried?",
            "Don't want work cutting into your free time?",
            "Do brand names matter?",
            "Do you leave work until tomorrow?",
            "Do you believe only you can protect yourself?",
            "Want to help society    someday?",
            "Do you want a brief,    full life?",
            "Is love all you need?",
        ]
        actual = [
            translations[f"TT1A/g0/r{record}"] for record in range(6, 21)
        ]
        self.assertEqual(actual, expected)
        for question in actual:
            validate_display_width(question, allow_wrap=True)

    def test_scenario_refresh_preserves_existing_english(self) -> None:
        """Verify the current contract described by this regression test."""
        bank_path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"
        if not bank_path.exists():
            self.fail("workspace fixture is not available")
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
        """Verify the current contract described by this regression test."""
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
        for original, rebuilt in zip(groups[0], compressed[0], strict=True):
            self.assertEqual(
                expand_dictionary_symbols(rebuilt, dictionary), original
            )

    def test_translation_merge_validates_ids_and_controls(self) -> None:
        """Verify the current contract described by this regression test."""
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
