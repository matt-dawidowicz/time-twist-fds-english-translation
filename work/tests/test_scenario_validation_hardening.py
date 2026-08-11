from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from time_twist.cli import command_scenario_extract, command_scenario_insert
from time_twist.compression import compress_english_groups, packed_size
from time_twist.english import EnglishTextError, encode_english
from time_twist.scenario import parse_scenario_bank
from time_twist.scenario_validation import encode_validated_english
from time_twist.textcodec import PackedSymbol, SymbolKind, pack_records

LOAD_ADDRESS = 0xA200


def _synthetic_bank(
    path: Path,
    *,
    record: tuple[PackedSymbol, ...] | None = None,
    dictionary_text: tuple[str, ...] = (),
) -> None:
    if record is None:
        record = encode_english("A")
    group_stream = pack_records((record,))
    dictionary = tuple(encode_english(text) for text in dictionary_text)
    dictionary_stream = pack_records(dictionary)
    group_zero_offset = 0x40
    group_table_offset = group_zero_offset + len(group_stream)
    dictionary_offset = group_table_offset
    prefix = bytearray(group_zero_offset)
    prefix[0x16:0x18] = (LOAD_ADDRESS + dictionary_offset).to_bytes(
        2, "little"
    )
    prefix[0x24:0x26] = (LOAD_ADDRESS + group_table_offset).to_bytes(
        2, "little"
    )
    prefix[0x26:0x28] = (LOAD_ADDRESS + group_zero_offset).to_bytes(
        2, "little"
    )
    path.write_bytes(prefix + group_stream + dictionary_stream + b"\xea" * 16)


class ScenarioValidationHardeningTests(unittest.TestCase):
    def test_extract_preserves_english_only_for_matching_stable_id(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "TT1A_source.bin"
            second = root / "TT6D_source.bin"
            output = root / "scenario.json"
            _synthetic_bank(first)
            _synthetic_bank(second)

            command_scenario_extract(
                SimpleNamespace(bank=first, output=output)
            )
            document = json.loads(output.read_text(encoding="utf-8"))
            document["groups"][0]["records"][0]["english"] = "KEEP"
            output.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            command_scenario_extract(
                SimpleNamespace(bank=second, output=output)
            )
            refreshed = json.loads(output.read_text(encoding="utf-8"))
            record = refreshed["groups"][0]["records"][0]
            self.assertEqual(record["id"], "TT6D/g0/r0")
            self.assertEqual(record["english"], "")

    def test_insert_rejects_mismatched_record_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bank = root / "TT1A_source.bin"
            scenario = root / "scenario.json"
            output = root / "rebuilt.bin"
            _synthetic_bank(bank)
            command_scenario_extract(
                SimpleNamespace(bank=bank, output=scenario)
            )
            document = json.loads(scenario.read_text(encoding="utf-8"))
            record = document["groups"][0]["records"][0]
            record["id"] = "TT1A/g0/r99"
            record["english"] = "A"
            scenario.write_text(json.dumps(document), encoding="utf-8")

            args = SimpleNamespace(
                bank=bank,
                translation=scenario,
                output=output,
                no_compress=True,
            )
            with self.assertRaisesRegex(SystemExit, "record ID mismatch"):
                command_scenario_insert(args)

    def test_insert_enforces_display_width(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bank = root / "TT1A_source.bin"
            scenario = root / "scenario.json"
            output = root / "rebuilt.bin"
            _synthetic_bank(bank)
            command_scenario_extract(
                SimpleNamespace(bank=bank, output=scenario)
            )
            document = json.loads(scenario.read_text(encoding="utf-8"))
            document["groups"][0]["records"][0]["english"] = "A" * 25
            scenario.write_text(json.dumps(document), encoding="utf-8")

            args = SimpleNamespace(
                bank=bank,
                translation=scenario,
                output=output,
                no_compress=True,
            )
            with self.assertRaisesRegex(SystemExit, "invalid English text"):
                command_scenario_insert(args)

    def test_dictionary_boundary_can_include_fixed_ui_only_entries(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.bin"
            reference = (PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0),)
            _synthetic_bank(
                path,
                record=reference,
                dictionary_text=("A", "SECOND"),
            )
            reachable = parse_scenario_bank(path)
            complete = parse_scenario_bank(path, minimum_dictionary_entries=2)
            self.assertEqual(len(reachable.dictionary), 1)
            self.assertEqual(len(complete.dictionary), 2)
            self.assertGreater(
                complete.dictionary_end_offset,
                reachable.dictionary_end_offset,
            )

    def test_shared_validator_keeps_personality_wrap_exception(self) -> None:
        text = "A" * 23 + " " + "B" * 24
        with self.assertRaises(EnglishTextError):
            encode_validated_english("TT2/g0/r0", text, "")
        encoded = encode_validated_english("TT1A/g0/r6", text, "")
        self.assertTrue(encoded)

    def test_capacity_fallback_retries_without_candidate_pruning(self) -> None:
        record = encode_english("AB" * 16)
        groups = ((record,),)
        uncompressed = packed_size(groups, ())
        with patch(
            "time_twist._compression_core.MAX_CANDIDATES_TO_EVALUATE",
            0,
        ):
            compressed, dictionary = compress_english_groups(
                groups,
                max_bytes=uncompressed - 1,
            )
        self.assertTrue(dictionary)
        self.assertLess(packed_size(compressed, dictionary), uncompressed)


if __name__ == "__main__":
    unittest.main()
