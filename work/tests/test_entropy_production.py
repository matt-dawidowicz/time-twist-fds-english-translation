"""Focused regression suite for the frozen production entropy path."""

from __future__ import annotations

import random
import unittest
from pathlib import Path

from time_twist.entropy_codec import (
    CATEGORY_BASES,
    CATEGORY_PAYLOAD_BITS,
    CATEGORY_PREFIXES,
    pack_entropy_pages,
    pack_entropy_stream,
    unpack_entropy_stream,
)
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
    optimize_entropy_dictionary,
)
from time_twist.entropy_runtime import (
    CATEGORY_CODE_BYTES,
    ENTROPY_MENU_INIT_CPU_ADDRESS,
    ENTROPY_POINTER_INIT_CPU_ADDRESS,
    ENTROPY_RUNTIME_PATCHES,
    FRONTEND_CODE_BYTES,
    NOV3_LOAD_ADDRESS,
    SCANNER_CODE_BYTES,
)
from time_twist.entropy_scenario import build_entropy_scenario_bank
from time_twist.scenario import ScenarioBank, ScenarioRecord
from time_twist.textcodec import PackedSymbol, SymbolKind


def _s(kind: SymbolKind, value: int) -> PackedSymbol:
    return PackedSymbol(kind, value, 0, 0)


def _common(value: int) -> PackedSymbol:
    return _s(SymbolKind.COMMON, value)


def _semantic(record):
    return tuple((symbol.kind, symbol.value) for symbol in record)


class EntropyProductionTests(unittest.TestCase):
    def test_runtime_abi_is_frozen(self) -> None:
        self.assertEqual(
            CATEGORY_PREFIXES,
            (
                "0111", "11000", "111", "001", "101", "1101",
                "00001", "1001", "0110", "0001", "1000", "010",
                "000001", "0000001", "0000000", "11001",
            ),
        )
        self.assertEqual(
            CATEGORY_PAYLOAD_BITS,
            (0, 3, 2, 2, 3, 3, 3, 4, 3, 3, 4, 5, 5, 5, 7, 5),
        )
        self.assertEqual(
            CATEGORY_BASES,
            (5, 0, 0, 4, 8, 16, 24, 32, 1, 9, 17, 33, 65, 97, 129, 37),
        )
        self.assertEqual(NOV3_LOAD_ADDRESS, 0xD7B5)

    def test_mixed_bit_contiguous_streams_round_trip(self) -> None:
        rng = random.Random(0xD7B5)
        for _ in range(40):
            records = []
            for _ in range(rng.randrange(1, 12)):
                row = []
                for _ in range(rng.randrange(0, 18)):
                    choice = rng.randrange(4)
                    if choice == 0:
                        row.append(_common(rng.randrange(48)))
                    elif choice == 1:
                        row.append(
                            _s(SymbolKind.DICTIONARY, rng.randrange(1, 256))
                        )
                    elif choice == 2:
                        row.append(
                            _s(SymbolKind.EXTENDED, rng.randrange(37, 64))
                        )
                    else:
                        row.append(
                            _s(
                                SymbolKind.CONTROL,
                                rng.choice((0, 1, 2, 3, 4, 6, 7)),
                            )
                        )
                records.append(tuple(row))
            source = tuple(records)
            packed = pack_entropy_stream(source)
            self.assertEqual(
                unpack_entropy_stream(packed, record_count=len(source)),
                source,
            )

    def test_menu_pages_are_independently_byte_addressable(self) -> None:
        records = tuple((_common(index % 48),) for index in range(70))
        packed, starts = pack_entropy_pages(records, records_per_page=32)
        self.assertEqual(len(starts), 3)
        for page, start in enumerate(starts):
            end = starts[page + 1] if page + 1 < len(starts) else len(packed)
            expected = records[page * 32 : page * 32 + 32]
            self.assertEqual(
                unpack_entropy_stream(packed[start:end], record_count=len(expected)),
                expected,
            )

    def test_optimizer_is_deterministic_and_lossless(self) -> None:
        phrase = (_common(1), _common(2), _common(3), _common(4))
        groups = (
            tuple((*phrase, _common(index % 8), *phrase) for index in range(18)),
        )
        first = optimize_entropy_dictionary(
            groups, maximum_entries=24, trial_candidates=6
        )
        second = optimize_entropy_dictionary(
            groups, maximum_entries=24, trial_candidates=6
        )
        self.assertEqual(first, second)
        expansions = expand_entropy_dictionary(first.dictionary)
        for packed, literal in zip(first.groups[0], groups[0], strict=True):
            self.assertEqual(
                _semantic(expand_entropy_record(packed, expansions)),
                _semantic(literal),
            )

    def test_scenario_layout_preserves_fixed_tail(self) -> None:
        load = 0xA200
        data = bytearray(b"\x00" * 0x120)
        data[0x90:] = bytes((index * 13 + 7) & 0xFF for index in range(0x90))
        bank = ScenarioBank(
            path=Path("TTTEST.bin"),
            data=bytes(data),
            load_address=load,
            dictionary_address=load + 0x80,
            group_table_address=load + 0x70,
            group_addresses=(load + 0x40, load + 0x60),
            dictionary=((_common(7),),),
            dictionary_end_offset=0x90,
            records=(
                ScenarioRecord(0, 0, (_common(1),)),
                ScenarioRecord(1, 0, (_common(2),)),
            ),
        )
        dictionary = ((_common(1), _common(2)),)
        groups = (
            ((_s(SymbolKind.DICTIONARY, 1), _common(3)),),
            ((_common(4), _common(5)),),
        )
        layout = build_entropy_scenario_bank(bank, groups, dictionary)
        self.assertLessEqual(layout.loaded_end, NOV3_LOAD_ADDRESS)
        self.assertEqual(
            layout.data[bank.dictionary_end_offset : len(bank.data)],
            bank.data[bank.dictionary_end_offset :],
        )

    def test_generated_6502_blocks_fit_and_do_not_overlap(self) -> None:
        self.assertEqual(SCANNER_CODE_BYTES, 134)
        self.assertEqual(FRONTEND_CODE_BYTES, 64)
        self.assertEqual(CATEGORY_CODE_BYTES, 59)
        self.assertEqual(ENTROPY_POINTER_INIT_CPU_ADDRESS, 0x8124)
        self.assertEqual(ENTROPY_MENU_INIT_CPU_ADDRESS, 0x812E)
        occupied: set[int] = set()
        for patch in ENTROPY_RUNTIME_PATCHES:
            touched = set(range(patch.cpu_address, patch.cpu_address + patch.size))
            self.assertTrue(occupied.isdisjoint(touched), patch.label)
            occupied.update(touched)
        self.assertLess(max(occupied), NOV3_LOAD_ADDRESS)

    def test_entropy_runtime_does_not_borrow_native_zero_page_74(self) -> None:
        patches = {patch.label: patch for patch in ENTROPY_RUNTIME_PATCHES}
        scanner = patches["bit-contiguous entropy scanner"].replacement[
            :SCANNER_CODE_BYTES
        ]
        frontend = patches["entropy semantic dispatch frontend"].replacement[
            :FRONTEND_CODE_BYTES
        ]
        for opcode in (bytes.fromhex("85 74"), bytes.fromhex("A5 74"), bytes.fromhex("A4 74")):
            self.assertNotIn(opcode, scanner)
            self.assertNotIn(opcode, frontend)


if __name__ == "__main__":
    unittest.main()
