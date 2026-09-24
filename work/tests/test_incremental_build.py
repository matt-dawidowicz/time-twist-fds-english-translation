"""Fixture-free tests for fast source-first entropy recompilation."""

from __future__ import annotations

import unittest

from time_twist.english import encode_english
from time_twist.entropy_codec import pack_entropy_stream
from time_twist.incremental_build import (
    FIXED_TAIL_BOUNDARIES,
    GROUP_RECORD_COUNTS,
    IncrementalBuildError,
    _allocate_groups,
    _bank_layout_report,
    _load_entropy_bank,
    rebuild_entropy_bank,
)
from time_twist.scenario import (
    DICTIONARY_POINTER_OFFSET,
    GROUP_TABLE_POINTER_OFFSET,
    GROUP_ZERO_POINTER_OFFSET,
    LOAD_ADDRESS,
)
from time_twist.textcodec import PackedSymbol, SymbolKind


def _write_word(data: bytearray, offset: int, value: int) -> None:
    """Write one little-endian word into a synthetic compiled bank."""
    data[offset : offset + 2] = value.to_bytes(2, "little")


def _tt6d_bank(
    *,
    forward_dictionary: bool = False,
    dictionary_slack: int = 0,
) -> tuple[bytes, dict[str, str]]:
    """Build a valid synthetic TT6D entropy bank and matching English map."""
    boundary = FIXED_TAIL_BOUNDARIES["TT6D"]
    data = bytearray(b"\x00" * 800)
    labels = ("AB", "B", "C", "D", "E", "F", "G", "H")
    if forward_dictionary:
        d2 = encode_english("AB")
        d1 = (PackedSymbol(SymbolKind.DICTIONARY, 2, 0, 0),)
        dictionary = (d1, d2)
        first = (PackedSymbol(SymbolKind.DICTIONARY, 1, 0, 0),)
    else:
        dictionary = (encode_english("AB"),)
        first = encode_english("AB")
    group = (
        first,
        *(encode_english(label) for label in labels[1:]),
    )
    group_blob = pack_entropy_stream(group)
    group_offset = 100
    data[group_offset : group_offset + len(group_blob)] = group_blob

    dictionary_blob = pack_entropy_stream(dictionary)
    dictionary_offset = boundary - dictionary_slack - len(dictionary_blob)
    data[dictionary_offset : dictionary_offset + len(dictionary_blob)] = (
        dictionary_blob
    )
    _write_word(data, 10, 0)
    _write_word(
        data,
        DICTIONARY_POINTER_OFFSET,
        LOAD_ADDRESS + dictionary_offset,
    )
    _write_word(
        data,
        GROUP_TABLE_POINTER_OFFSET,
        LOAD_ADDRESS + dictionary_offset,
    )
    _write_word(
        data,
        GROUP_ZERO_POINTER_OFFSET,
        LOAD_ADDRESS + group_offset,
    )
    translations = {
        f"TT6D/g0/r{index}": label for index, label in enumerate(labels)
    }
    return bytes(data), translations


def _tt1a_bank() -> tuple[bytes, dict[str, str]]:
    """Build TT1A with fixed suffix bytes and an appended renderer payload."""
    boundary = FIXED_TAIL_BOUNDARIES["TT1A"]
    table_offset = 80
    group_zero_offset = 100
    group_zero_labels = tuple("A" for _ in range(32))
    group_one_labels = ("B", "C", "D")
    group_zero = tuple(encode_english(label) for label in group_zero_labels)
    group_one = tuple(encode_english(label) for label in group_one_labels)
    blob_zero = pack_entropy_stream(group_zero)
    group_one_offset = group_zero_offset + len(blob_zero)
    blob_one = pack_entropy_stream(group_one)
    renderer = b"TT1A-RENDERER"
    renderer_offset = boundary + 16
    data = bytearray(b"\x00" * (renderer_offset + len(renderer)))
    data[group_zero_offset : group_zero_offset + len(blob_zero)] = blob_zero
    data[group_one_offset : group_one_offset + len(blob_one)] = blob_one
    data[boundary:renderer_offset] = bytes(range(16))
    data[renderer_offset:] = renderer
    _write_word(data, 10, 0)
    _write_word(
        data,
        DICTIONARY_POINTER_OFFSET,
        LOAD_ADDRESS + 1,
    )
    _write_word(
        data,
        GROUP_TABLE_POINTER_OFFSET,
        LOAD_ADDRESS + table_offset,
    )
    _write_word(
        data,
        GROUP_ZERO_POINTER_OFFSET,
        LOAD_ADDRESS + group_zero_offset,
    )
    _write_word(
        data,
        table_offset,
        LOAD_ADDRESS + group_one_offset,
    )
    _write_word(data, 0x14, LOAD_ADDRESS + renderer_offset)
    translations = {
        **{
            f"TT1A/g0/r{index}": label
            for index, label in enumerate(group_zero_labels)
        },
        **{
            f"TT1A/g1/r{index}": label
            for index, label in enumerate(group_one_labels)
        },
    }
    return bytes(data), translations


class IncrementalBuildTests(unittest.TestCase):
    """Keep incremental recompilation deterministic and bounded."""

    def test_dictionary_backed_noop_is_byte_identical(self) -> None:
        """Return original bytes when canonical English already matches."""
        data, translations = _tt6d_bank()
        result = rebuild_entropy_bank(data, "TT6D", translations)
        self.assertEqual(result.data, data)
        self.assertEqual(result.changed_records, ())

    def test_dictionary_backed_edit_preserves_fixed_suffix(self) -> None:
        """Rebuild an edit without modifying fixed code/data."""
        data, translations = _tt6d_bank()
        translations["TT6D/g0/r0"] = "ABABAB"
        result = rebuild_entropy_bank(data, "TT6D", translations)
        self.assertEqual(
            result.changed_records,
            ("TT6D/g0/r0",),
        )
        boundary = FIXED_TAIL_BOUNDARIES["TT6D"]
        self.assertEqual(
            result.data[boundary:],
            data[boundary:],
        )
        verified = rebuild_entropy_bank(
            result.data,
            "TT6D",
            translations,
        )
        self.assertEqual(verified.data, result.data)
        self.assertEqual(verified.changed_records, ())

    def test_forward_dictionary_reference_is_supported(self) -> None:
        """Resolve forward references in recovered dictionaries."""
        data, translations = _tt6d_bank(forward_dictionary=True)
        result = rebuild_entropy_bank(
            data,
            "TT6D",
            translations,
        )
        self.assertEqual(result.data, data)
        self.assertEqual(result.changed_records, ())

    def test_dictionary_zero_slack_is_accepted(self) -> None:
        """Ignore zero-filled resident slack after the dictionary stream."""
        data, translations = _tt6d_bank(dictionary_slack=12)
        result = rebuild_entropy_bank(data, "TT6D", translations)
        self.assertEqual(result.data, data)
        self.assertEqual(result.changed_records, ())

    def test_tt1a_special_path_rebuilds_without_dictionary(self) -> None:
        """Handle TT1A's direct two-stream layout without a dictionary."""
        data, translations = _tt1a_bank()
        initial = rebuild_entropy_bank(
            data,
            "TT1A",
            translations,
        )
        self.assertEqual(initial.data, data)
        translations["TT1A/g1/r0"] = "BBBB"
        result = rebuild_entropy_bank(
            data,
            "TT1A",
            translations,
        )
        self.assertEqual(
            result.changed_records,
            ("TT1A/g1/r0",),
        )
        boundary = FIXED_TAIL_BOUNDARIES["TT1A"]
        original_renderer = int.from_bytes(data[0x14:0x16], "little")
        original_renderer -= LOAD_ADDRESS
        rebuilt_renderer = int.from_bytes(result.data[0x14:0x16], "little")
        rebuilt_renderer -= LOAD_ADDRESS
        self.assertEqual(
            result.data[boundary:rebuilt_renderer],
            data[boundary:original_renderer],
        )
        self.assertEqual(
            result.data[rebuilt_renderer:],
            data[original_renderer:],
        )
        verified = rebuild_entropy_bank(
            result.data,
            "TT1A",
            translations,
        )
        self.assertEqual(verified.data, result.data)

    def test_layout_report_exposes_capacity_and_source_state(self) -> None:
        """Report dictionary, placement, and remaining capacity."""
        data, translations = _tt6d_bank(dictionary_slack=12)
        state = _load_entropy_bank(data, "TT6D")
        report = _bank_layout_report(state, ())
        self.assertEqual(report.bank_name, "TT6D")
        self.assertEqual(report.dictionary_entries, 1)
        self.assertGreater(report.dictionary_bytes, 0)
        self.assertEqual(report.resident_groups, (0,))
        self.assertEqual(report.spilled_groups, ())
        self.assertIsNone(report.split_group)
        self.assertGreaterEqual(report.resident_free_bytes, 12)
        self.assertGreater(report.nov3_headroom_bytes, 0)
        self.assertEqual(report.changed_records, ())
        verified = rebuild_entropy_bank(data, "TT6D", translations)
        self.assertEqual(verified.changed_records, ())

    def test_tt1a_complete_incremental_contract_is_preserved(self) -> None:
        """Lock TT1A fixed suffix, renderer, pointers, and repeatability."""
        data, translations = _tt1a_bank()
        translations["TT1A/g1/r0"] = "BBBB"
        result = rebuild_entropy_bank(data, "TT1A", translations)
        boundary = FIXED_TAIL_BOUNDARIES["TT1A"]
        original_renderer = int.from_bytes(data[0x14:0x16], "little")
        original_renderer -= LOAD_ADDRESS
        rebuilt_renderer = int.from_bytes(result.data[0x14:0x16], "little")
        rebuilt_renderer -= LOAD_ADDRESS

        self.assertGreaterEqual(rebuilt_renderer, boundary)
        self.assertLess(rebuilt_renderer, len(result.data))
        self.assertEqual(
            result.data[rebuilt_renderer:],
            data[original_renderer:],
        )
        self.assertEqual(
            result.data[boundary:rebuilt_renderer],
            data[boundary:original_renderer],
        )

        table = int.from_bytes(
            result.data[
                GROUP_TABLE_POINTER_OFFSET : GROUP_TABLE_POINTER_OFFSET + 2
            ],
            "little",
        )
        group_zero = int.from_bytes(
            result.data[
                GROUP_ZERO_POINTER_OFFSET : GROUP_ZERO_POINTER_OFFSET + 2
            ],
            "little",
        )
        self.assertGreaterEqual(table, LOAD_ADDRESS)
        self.assertLess(table - LOAD_ADDRESS, boundary)
        self.assertGreaterEqual(group_zero, LOAD_ADDRESS)
        self.assertLess(group_zero - LOAD_ADDRESS, boundary)

        state = _load_entropy_bank(result.data, "TT1A")
        report = _bank_layout_report(state, result.changed_records)
        self.assertEqual(report.dictionary_entries, 0)
        self.assertEqual(report.dictionary_bytes, 0)
        self.assertIsNone(report.split_group)
        self.assertGreater(report.nov3_headroom_bytes, 0)

        repeated = rebuild_entropy_bank(
            result.data,
            "TT1A",
            translations,
        )
        self.assertEqual(repeated.data, result.data)
        self.assertEqual(repeated.changed_records, ())

    def test_allocator_can_select_split_group(self) -> None:
        """Use the native thunk when a whole group fits nowhere."""
        record = tuple(encode_english("ABCDEFGHIJKLMNOP"))
        groups = (tuple(record for _ in range(10)),)
        plan = _allocate_groups(
            groups,
            dictionary_bytes=1,
            resident_capacity=46,
            tail_capacity=158,
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["split"], (0, 1))

    def test_allocator_rejects_all_spill_layout(self) -> None:
        """Keep at least one resident group so later rebuilds retain an origin."""
        groups = ((encode_english("ABCDEFG"),),)
        plan = _allocate_groups(
            groups,
            dictionary_bytes=0,
            resident_capacity=0,
            tail_capacity=100,
        )
        self.assertIsNone(plan)

    def test_rejects_wrong_canonical_topology(self) -> None:
        """Fail closed when record IDs do not match the stable ABI."""
        data, translations = _tt6d_bank()
        del translations["TT6D/g0/r7"]
        with self.assertRaisesRegex(
            IncrementalBuildError,
            "topology",
        ):
            rebuild_entropy_bank(
                data,
                "TT6D",
                translations,
            )

    def test_all_topologies_remain_explicit(self) -> None:
        """Lock all 1,299 scenario records in one topology table."""
        self.assertEqual(len(GROUP_RECORD_COUNTS), 13)
        total = sum(sum(counts) for counts in GROUP_RECORD_COUNTS.values())
        self.assertEqual(total, 1299)


if __name__ == "__main__":
    unittest.main()
