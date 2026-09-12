"""Tests for the source-reachable retail gameplay VM opcode registry."""

from __future__ import annotations

import unittest

from time_twist.retail_vm import (
    RETAIL_VM_OPCODE_BY_VALUE,
    RETAIL_VM_OPCODES,
    RETAIL_VM_OPCODE_VALUES,
    retail_vm_opcode,
)

EXPECTED_RETAIL_OPCODES = (
    0x00,
    0x01,
    0x02,
    0x04,
    0x06,
    0x09,
    0x0E,
    0x0F,
    0x10,
    0x11,
    0x18,
    0x19,
    0x20,
    0x21,
    0x28,
    0x29,
    0x30,
    0x31,
    0x40,
    0x41,
    0x44,
    0x45,
    0x49,
    0x4D,
    0x50,
    0x51,
    0x52,
    0x53,
    0x54,
    0x58,
    0x60,
    0x61,
    0x62,
    0x63,
    0x64,
    0x65,
    0x66,
    0x67,
    0x68,
    0x69,
    0x6C,
    0x6D,
    0x70,
    0x83,
    0x90,
    0x91,
    0x92,
    0x93,
    0xA1,
    0xB0,
    0xB2,
    0xB3,
    0xB5,
    0xB6,
    0xB7,
    0xB9,
    0xBA,
    0xBB,
    0xBC,
    0xD2,
    0xE0,
)


class RetailVmRegistryTests(unittest.TestCase):
    """Protect the recovered retail opcode-language contract."""

    def test_registry_matches_source_reachable_opcode_set(self) -> None:
        """Require semantics for every reachable retail opcode."""
        self.assertEqual(RETAIL_VM_OPCODE_VALUES, EXPECTED_RETAIL_OPCODES)

    def test_registry_values_are_unique_and_complete(self) -> None:
        """Reject duplicate opcode rows or missing lookup entries."""
        self.assertEqual(
            len(RETAIL_VM_OPCODES), len(RETAIL_VM_OPCODE_BY_VALUE)
        )
        self.assertEqual(
            set(RETAIL_VM_OPCODE_VALUES), set(RETAIL_VM_OPCODE_BY_VALUE)
        )

    def test_every_registry_row_has_actionable_semantics(self) -> None:
        """Require names, operands, lengths, handlers, and evidence labels."""
        for entry in RETAIL_VM_OPCODES:
            with self.subTest(opcode=f"{entry.opcode:02X}"):
                self.assertTrue(entry.mnemonic)
                self.assertTrue(entry.operand_grammar)
                self.assertTrue(entry.length_rule)
                self.assertGreaterEqual(entry.handler, 0x6000)
                self.assertIn(
                    entry.evidence, {"VERIFIED", "DERIVED", "INFERRED"}
                )

    def test_lookup_rejects_engine_only_opcode(self) -> None:
        """Keep source-unused native forms outside the retail registry."""
        with self.assertRaises(KeyError):
            retail_vm_opcode(0x42)


if __name__ == "__main__":
    unittest.main()
