"""Recompute playable scenario footprints from the current translation maps."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from generate_translation_workbook import PATCH_FOOTPRINT_RESULTS
from time_twist.capacity import (
    RELOCATED_FIXED_TABLE_PREFIX_BYTES,
    playable_capacity,
)
from time_twist.compression import compress_english_groups, packed_size
from time_twist.english import encode_english
from time_twist.project import (
    KNOWN_SCENARIO_BANKS,
    required_dictionary_entries,
)
from time_twist.textcodec import (
    EXTENDED_DICTIONARY_ENTRY_COUNT,
    PackedSymbol,
)
from time_twist.ui import (
    FIXED_RECORD_TABLE_SPECS,
    fixed_record_table_page_pointer_bytes,
)

WORK = Path(__file__).resolve().parents[1]
TRANSLATIONS = WORK / "translations"
RECORD_ID_RE = re.compile(
    r"^(?P<bank>[A-Z0-9]+?)/g(?P<group>\d+)/r(?P<record>\d+)$"
)


def _load_groups(
    bank_name: str,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    """Encode one public translation map into stable group/record order."""
    payload = json.loads(
        (TRANSLATIONS / f"{bank_name}.json").read_text(encoding="utf-8")
    )
    indexed: dict[int, dict[int, tuple[PackedSymbol, ...]]] = {}
    for record_id, text in payload.items():
        match = RECORD_ID_RE.fullmatch(record_id)
        if match is None or match.group("bank") != bank_name:
            raise AssertionError(f"invalid {bank_name} record ID: {record_id}")
        group_index = int(match.group("group"))
        record_index = int(match.group("record"))
        group = indexed.setdefault(group_index, {})
        if record_index in group:
            raise AssertionError(f"duplicate record ID: {record_id}")
        group[record_index] = encode_english(text)

    expected_groups = list(range(len(indexed)))
    if sorted(indexed) != expected_groups:
        raise AssertionError(
            f"{bank_name} groups are not contiguous: {sorted(indexed)}"
        )

    groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    for group_index in expected_groups:
        records = indexed[group_index]
        expected_records = list(range(len(records)))
        if sorted(records) != expected_records:
            raise AssertionError(
                f"{bank_name}/g{group_index} records are not contiguous: "
                f"{sorted(records)}"
            )
        groups.append(tuple(records[index] for index in expected_records))
    return tuple(groups)


def measure_translation_footprint(bank_name: str) -> int:
    """Mirror the release compressor using only public translation/UI sources."""
    groups = _load_groups(bank_name)
    scenario_capacity = PATCH_FOOTPRINT_RESULTS[bank_name]["capacity"]
    capacity = playable_capacity(bank_name, scenario_capacity)
    pointer_bytes = 2 * (len(groups) - 1)

    if bank_name in FIXED_RECORD_TABLE_SPECS:
        spec = FIXED_RECORD_TABLE_SPECS[bank_name]
        menu_records = tuple(encode_english(text) for text in spec.records)
        combined_groups = (*groups, menu_records)
        structural_bytes = (
            pointer_bytes + fixed_record_table_page_pointer_bytes(bank_name)
        )
        compressed, dictionary = compress_english_groups(
            combined_groups,
            max_bytes=capacity - structural_bytes,
            optimize=True,
            maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        )
        return packed_size(compressed, dictionary) + structural_bytes

    compressed, dictionary = compress_english_groups(
        groups,
        required_entries=required_dictionary_entries(bank_name),
        max_bytes=capacity - pointer_bytes,
        optimize=True,
        maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
    )
    return packed_size(compressed, dictionary) + pointer_bytes


class LiveTranslationFitTests(unittest.TestCase):
    """Prove current playable text still fits every recovered bank capacity."""

    def test_relocated_capacity_facts_cover_exactly_the_repacked_banks(self) -> None:
        """Keep ROM-free capacity evidence aligned with the release architecture."""
        self.assertEqual(
            set(RELOCATED_FIXED_TABLE_PREFIX_BYTES),
            set(FIXED_RECORD_TABLE_SPECS),
        )

    def test_current_translation_maps_fit(self) -> None:
        """Recompress every bank and fail only when current text exceeds capacity.

        ``PATCH_FOOTPRINT_RESULTS[*][\"used\"]`` and its ``capacity`` field are
        historical scenario-region evidence. Relocated full-word menu banks add
        a source-verified movable prefix to that scenario reservation; current
        usage is recomputed from scenario plus menu with the same 68-entry
        compressor as the canonical release builder.
        """
        self.assertEqual(
            set(PATCH_FOOTPRINT_RESULTS), set(KNOWN_SCENARIO_BANKS)
        )
        for bank_name in KNOWN_SCENARIO_BANKS:
            recorded = PATCH_FOOTPRINT_RESULTS[bank_name]
            used = measure_translation_footprint(bank_name)
            scenario_capacity = recorded["capacity"]
            capacity = playable_capacity(bank_name, scenario_capacity)
            delta = used - recorded["used"]
            evidence = (
                "current" if delta == 0 else f"recorded delta {delta:+d}"
            )
            print(
                f"FIT {bank_name}: {used}/{capacity} "
                f"({capacity - used} bytes free; {evidence})"
            )
            self.assertLessEqual(
                used,
                capacity,
                f"{bank_name} exceeds its canonical English footprint by "
                f"{used - capacity} bytes",
            )


if __name__ == "__main__":
    unittest.main()
