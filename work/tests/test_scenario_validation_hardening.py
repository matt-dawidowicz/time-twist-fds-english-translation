"""Regression tests for current scenario validation and capacity-safety behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from time_twist.cli_commands import command_scenario_extract
from time_twist.compression import (
    _compress_english_groups_beam,
    _compress_english_groups_greedy,
    _improve_dictionary_order,
    compress_english_groups,
    expand_dictionary_symbols,
    packed_size,
)
from time_twist.english import EnglishTextError, encode_english
from time_twist.fds import FdsFormatError, FdsImage
from time_twist.project import required_dictionary_entries
from time_twist.scenario import (
    ScenarioError,
    parse_scenario_bank,
    rebuild_scenario_bank,
)
from time_twist.scenario_validation import encode_validated_english
from time_twist.textcodec import (
    PackedSymbol,
    SymbolKind,
    pack_records,
    split_records,
)

LOAD_ADDRESS = 0xA200


def _synthetic_bank(
    path: Path,
    *,
    record: tuple[PackedSymbol, ...] | None = None,
    dictionary_text: tuple[str, ...] = (),
) -> None:
    """Provide a deterministic helper for the current contract tests."""
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
    """Group current regression tests by project contract."""

    def test_beam_search_can_beat_a_greedy_dictionary(self) -> None:
        """Keep a corpus where overlapping choices punish greedy selection."""
        texts = (
            "ABACCABDCABDCABD",
            "BCDACABC",
            "BCDAABAC",
            "DABAABCDABAC",
            "CABDBABCBCAB",
            "ABCDCABCDABABCAB",
            "BCDAAABABABC",
        )
        groups = (tuple(encode_english(text) for text in texts),)

        greedy = _compress_english_groups_greedy(groups)
        beam = _compress_english_groups_beam(groups)

        self.assertLess(packed_size(*beam), packed_size(*greedy))
        self.assertEqual(beam, _compress_english_groups_beam(groups))
        expanded = tuple(
            tuple(
                expand_dictionary_symbols(record, beam[1]) for record in group
            )
            for group in beam[0]
        )
        self.assertEqual(expanded, groups)

    def test_beam_search_preserves_required_dictionary_prefix(self) -> None:
        """Keep fixed-UI dictionary indices stable during alternative search."""
        groups = (
            (
                encode_english("ABABAB CABCABC"),
                encode_english("ABABAB DABDAB"),
            ),
        )
        required = (encode_english("AB"),)

        _, dictionary = _compress_english_groups_beam(
            groups, required_entries=required
        )

        self.assertEqual(dictionary[: len(required)], required)

    def test_dictionary_order_search_can_improve_overlapping_entries(
        self,
    ) -> None:
        """Prove that optional-entry order can reduce the exact packed size."""
        texts = (
            "ABCDBCABDABAABABCABD",
            "CABDAABA",
            "BCDACABDCABCCABDBABC",
            "ABACDABA",
            "BCDABCABABCDABABBCDA",
            "BCABABAB",
            "BCDAABACAABA",
            "BCABBABCCABDABABABAC",
            "BCDACABCBCDADABA",
            "BABCCABDABCD",
        )
        groups = (tuple(encode_english(text) for text in texts),)
        greedy = _compress_english_groups_greedy(groups)

        reordered = _improve_dictionary_order(groups, greedy[1])

        self.assertLess(packed_size(*reordered), packed_size(*greedy))
        expanded = tuple(
            tuple(
                expand_dictionary_symbols(record, reordered[1])
                for record in group
            )
            for group in reordered[0]
        )
        self.assertEqual(expanded, groups)

    def test_optimize_selects_the_smallest_valid_result(self) -> None:
        """Wire alternative search into the opt-in production entry point."""
        texts = (
            "ABACCABDCABDCABD",
            "BCDACABC",
            "BCDAABAC",
            "DABAABCDABAC",
            "CABDBABCBCAB",
            "ABCDCABCDABABCAB",
            "BCDAAABABABC",
        )
        groups = (tuple(encode_english(text) for text in texts),)
        greedy = compress_english_groups(groups)

        optimized = compress_english_groups(
            groups,
            max_bytes=packed_size(*greedy),
            optimize=True,
        )

        self.assertLess(packed_size(*optimized), packed_size(*greedy))
        expanded = tuple(
            tuple(
                expand_dictionary_symbols(record, optimized[1])
                for record in group
            )
            for group in optimized[0]
        )
        self.assertEqual(expanded, groups)

    def test_optimize_excludes_release_invalid_candidates(self) -> None:
        """Choose the smallest candidate that satisfies a bank constraint."""
        texts = (
            "ABACCABDCABDCABD",
            "BCDACABC",
            "BCDAABAC",
            "DABAABCDABAC",
            "CABDBABCBCAB",
            "ABCDCABCDABABCAB",
            "BCDAAABABABC",
        )
        groups = (tuple(encode_english(text) for text in texts),)
        greedy = compress_english_groups(groups)
        greedy_size = packed_size(*greedy)

        constrained = compress_english_groups(
            groups,
            max_bytes=greedy_size,
            optimize=True,
            candidate_validator=lambda candidate_groups, dictionary: (
                packed_size(candidate_groups, dictionary) >= greedy_size
            ),
        )

        self.assertEqual(packed_size(*constrained), greedy_size)

    def test_extract_discards_stale_english_fields(self) -> None:
        """Keep decoded source records independent of previous English output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bank = root / "TT1A_source.bin"
            output = root / "scenario.json"
            _synthetic_bank(bank)

            command_scenario_extract(SimpleNamespace(bank=bank, output=output))
            document = json.loads(output.read_text(encoding="utf-8"))
            document["groups"][0]["records"][0]["english"] = "STALE"
            output.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            command_scenario_extract(SimpleNamespace(bank=bank, output=output))
            refreshed = json.loads(output.read_text(encoding="utf-8"))
            record = refreshed["groups"][0]["records"][0]
            self.assertEqual(record["id"], "TT1A/g0/r0")
            self.assertNotIn("english", record)

    def test_dictionary_boundary_can_include_fixed_ui_only_entries(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
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

    def test_fixed_ui_dictionary_requirement_fails_closed(self) -> None:
        """Verify the current contract described by this regression test."""
        groups = ((encode_english("AB"),),)
        required = required_dictionary_entries("TT2")
        self.assertTrue(getattr(required, "requires_full_dictionary", False))
        with self.assertRaisesRegex(ValueError, "exactly 31"):
            compress_english_groups(groups, required_entries=required)

    def test_undersized_fixed_slot_labels_are_reserved(self) -> None:
        """Keep complete labels encodable after alternative dictionary search."""
        expected = {
            "TT3A": ("Back", "Frankie"),
            "TT3B": ("Cougar", "ight"),
        }

        for bank_name, labels in expected.items():
            required = required_dictionary_entries(bank_name)
            with self.subTest(bank=bank_name):
                self.assertTrue(
                    set(map(encode_english, labels)).issubset(required)
                )

    def test_rebuild_rejects_per_group_record_count_change(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.bin"
            _synthetic_bank(path)
            bank = parse_scenario_bank(path)
            with self.assertRaisesRegex(ScenarioError, "expected 1 records"):
                rebuild_scenario_bank(bank, ((),))

    def test_rebuild_rejects_more_than_31_dictionary_entries(self) -> None:
        """Verify the current contract described by this regression test."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.bin"
            _synthetic_bank(path)
            bank = parse_scenario_bank(path)
            groups = ((bank.records[0].symbols,),)
            dictionary = tuple(encode_english("A") for _ in range(32))
            with self.assertRaisesRegex(ScenarioError, "maximum is 31"):
                rebuild_scenario_bank(
                    bank,
                    groups,
                    dictionary=dictionary,
                )

    def test_shared_validator_keeps_personality_wrap_exception(self) -> None:
        """Verify the current contract described by this regression test."""
        text = "A" * 23 + " " + "B" * 24
        with self.assertRaises(EnglishTextError):
            encode_validated_english("TT2/g0/r0", text, "")
        encoded = encode_validated_english("TT1A/g0/r6", text, "")
        self.assertTrue(encoded)

    def test_blue_sky_record_allows_audited_presentation_break(self) -> None:
        """Permit a natural two-row translation only on the reviewed record."""
        text = "When was the last time{CTRL:0}I saw a blue sky?"

        encoded = encode_validated_english("TT1B/g0/r1", text, "")

        self.assertTrue(encoded)

    def test_unreviewed_record_rejects_extra_presentation_break(self) -> None:
        """Keep English-only row advances opt-in rather than globally permissive."""
        text = "When was the last time{CTRL:0}I saw a blue sky?"

        with self.assertRaisesRegex(EnglishTextError, "control tags changed"):
            encode_validated_english("TT1B/g0/r2", text, "")

    def test_audited_record_still_rejects_nonpresentation_controls(self) -> None:
        """Do not let the presentation exception alter timing/state controls."""
        text = "When was the last time{CTRL:4}I saw a blue sky?"

        with self.assertRaisesRegex(
            EnglishTextError,
            "beyond audited presentation breaks",
        ):
            encode_validated_english("TT1B/g0/r1", text, "")

    def test_capacity_fallback_retries_without_candidate_pruning(self) -> None:
        """Verify the current contract described by this regression test."""
        record = encode_english("AB" * 16)
        groups = ((record,),)
        uncompressed = packed_size(groups, ())
        with patch(
            "time_twist.compression.MAX_CANDIDATES_TO_EVALUATE",
            0,
        ):
            compressed, dictionary = compress_english_groups(
                groups,
                max_bytes=uncompressed - 1,
            )
        self.assertTrue(dictionary)
        self.assertLess(packed_size(compressed, dictionary), uncompressed)

    def test_fds_parser_rejects_zero_side_images(self) -> None:
        """Verify the current contract described by this regression test."""
        with self.assertRaisesRegex(FdsFormatError, "no sides"):
            FdsImage.from_bytes(b"")

        header = bytearray(16)
        header[:4] = b"FDS\x1a"
        with self.assertRaisesRegex(FdsFormatError, "no sides"):
            FdsImage.from_bytes(bytes(header))

    def test_split_records_rejects_negative_limit(self) -> None:
        """Verify the current contract described by this regression test."""
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            split_records(b"", limit=-1)

    def test_release_pins_pillow_version(self) -> None:
        """Verify the current contract described by this regression test."""
        project_root = Path(__file__).resolve().parents[2]
        pyproject = (project_root / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('"Pillow==12.3.0"', pyproject)


if __name__ == "__main__":
    unittest.main()
