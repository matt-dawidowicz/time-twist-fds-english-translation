"""Regression tests for bounded production scenario spill placement."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.english import encode_english
from time_twist.production_scenario import (
    LEGACY_ADAPTIVE_PRG_RAM_END,
    NOV3_SAFE_END,
    ProductionScenarioError,
    build_spill_scenario_bank,
)
from time_twist.scenario import ScenarioBank, ScenarioRecord
from time_twist.textcodec import PackedSymbol, SymbolKind


class ProductionScenarioTests(unittest.TestCase):
    """Keep spill placement pointer-driven, fixed-tail preserving, and bounded."""

    @staticmethod
    def _bank(group_count: int = 3) -> ScenarioBank:
        """Create a small synthetic source bank with a protected fixed tail."""
        load = 0xA200
        size = 0x140
        data = bytearray((index * 37) & 0xFF for index in range(size))
        records = tuple(
            ScenarioRecord(group, 0, encode_english("source"))
            for group in range(group_count)
        )
        return ScenarioBank(
            path=Path("synthetic-production.bin"),
            data=bytes(data),
            load_address=load,
            dictionary_address=load + 0x70,
            group_table_address=load + 0x68,
            group_addresses=tuple(
                load + 0x40 + 8 * group for group in range(group_count)
            ),
            dictionary=(),
            dictionary_end_offset=0x80,
            records=records,
        )

    def test_default_ceiling_is_nov3_not_legacy_e000(self) -> None:
        self.assertEqual(NOV3_SAFE_END, 0xD7B5)
        self.assertEqual(LEGACY_ADAPTIVE_PRG_RAM_END, 0xE000)
        self.assertLess(NOV3_SAFE_END, LEGACY_ADAPTIVE_PRG_RAM_END)

    def test_whole_groups_spill_without_moving_fixed_tail(self) -> None:
        """Use old text RAM first and append only groups that do not fit."""
        bank = self._bank()
        groups = (
            (encode_english("A" * 40),),
            (encode_english("B" * 40),),
            (encode_english("C" * 40),),
        )

        layout = build_spill_scenario_bank(bank, groups, ())

        self.assertTrue(layout.resident_groups)
        self.assertTrue(layout.spilled_groups)
        self.assertEqual(
            layout.data[bank.dictionary_end_offset : len(bank.data)],
            bank.data[bank.dictionary_end_offset :],
        )
        self.assertGreater(len(layout.data), len(bank.data))
        self.assertLessEqual(layout.loaded_end, NOV3_SAFE_END)
        self.assertEqual(layout.dictionary_address, layout.loaded_end)

    def test_high_nested_dictionary_reference_round_trips(self) -> None:
        """Allow a spilled record to use production dictionary entry 69."""
        bank = self._bank(group_count=1)
        reference_one = PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0)
        reference_69 = PackedSymbol(SymbolKind.DICTIONARY, 69, 0, 0)
        dictionary = tuple(encode_english("A") for _ in range(68)) + (
            (reference_one, *encode_english("B")),
        )
        groups = (((reference_69, reference_69),),)

        layout = build_spill_scenario_bank(bank, groups, dictionary)

        self.assertEqual(layout.group_addresses[0], bank.load_address + 0x40)
        self.assertGreaterEqual(
            layout.dictionary_address, bank.load_address + len(bank.data)
        )
        self.assertLessEqual(layout.loaded_end, NOV3_SAFE_END)

    def test_spill_fails_before_crossing_prg_ram_end(self) -> None:
        """Reject a candidate before appended text crosses its configured ceiling."""
        bank = self._bank()
        groups = (
            (encode_english("A" * 40),),
            (encode_english("B" * 40),),
            (encode_english("C" * 40),),
        )
        impossible_end = bank.load_address + len(bank.data) + 1

        with self.assertRaisesRegex(ProductionScenarioError, "PRG RAM"):
            build_spill_scenario_bank(
                bank,
                groups,
                (),
                prg_ram_end=impossible_end,
            )


if __name__ == "__main__":
    unittest.main()
