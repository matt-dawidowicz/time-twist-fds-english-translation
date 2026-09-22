"""Focused regression suite for the frozen production entropy path."""

from __future__ import annotations

import hashlib
import random
import unittest
from pathlib import Path

from time_twist.english import encode_english
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
    _INTERNAL_TABLE_STREAM,
    BASE_RUNTIME_PATCHES,
    CATEGORY_CODE_BYTES,
    DIALOGUE_CADENCE_PATCHES,
    DYNAMIC_MENU_LAYOUT_PATCHES,
    ENTROPY_MENU_INIT_CPU_ADDRESS,
    ENTROPY_POINTER_INIT_CPU_ADDRESS,
    ENTROPY_PREREQUISITE_PATCHES,
    ENTROPY_RUNTIME_PATCHES,
    ENTROPY_SELECTION_SPAN_CPU_ADDRESS,
    FRONTEND_CODE_BYTES,
    MENU_MAX_STAGED_GLYPHS,
    MENU_WIDTH_WORK_RAM_ADDRESS,
    NOV3_LOAD_ADDRESS,
    PALETTE_CPU_RANGE,
    PARENT_BACK_GUARD_PATCHES,
    SCANNER_CODE_BYTES,
)
from time_twist.entropy_scenario import build_entropy_scenario_bank
from time_twist.scenario import ScenarioBank, ScenarioRecord
from time_twist.textcodec import PackedSymbol, SymbolKind


def _s(kind: SymbolKind, value: int) -> PackedSymbol:
    """Encode one source string for the entropy tests."""
    return PackedSymbol(kind, value, 0, 0)


def _common(value: int) -> PackedSymbol:
    """Build one common-symbol token for the entropy tests."""
    return _s(SymbolKind.COMMON, value)


def _semantic(record):
    """Return the semantic text representation used by this module."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _sha256(data: bytes) -> str:
    """Return the SHA-256 digest for the supplied data."""
    return hashlib.sha256(data).hexdigest().upper()


class EntropyProductionTests(unittest.TestCase):
    """Group regression coverage for EntropyProduction."""

    def test_runtime_abi_is_frozen(self) -> None:
        """Verify runtime abi is frozen."""
        self.assertEqual(
            CATEGORY_PREFIXES,
            (
                "0111",
                "11000",
                "111",
                "001",
                "101",
                "1101",
                "00001",
                "1001",
                "0110",
                "0001",
                "1000",
                "010",
                "000001",
                "0000001",
                "0000000",
                "11001",
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

    def test_shared_disk_card_uses_full_spaced_labels(self) -> None:
        """Keep every shared NOV2 disk-change card on full English labels."""
        records = unpack_entropy_stream(
            _INTERNAL_TABLE_STREAM, record_count=51
        )
        expected = (
            "Part 1",
            "Part 2",
            "{CTRL:0}Side A",
            "{CTRL:0}Side B",
            "{CTRL:0}{CTRL:0}Insert now.",
        )
        for record, text in zip(records[3:8], expected, strict=True):
            self.assertEqual(
                _semantic(record), _semantic(encode_english(text))
            )

    def test_mixed_bit_contiguous_streams_round_trip(self) -> None:
        """Verify mixed bit contiguous streams round trip."""
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
        """Verify menu pages are independently byte addressable."""
        records = tuple((_common(index % 48),) for index in range(70))
        packed, starts = pack_entropy_pages(records, records_per_page=32)
        self.assertEqual(len(starts), 3)
        for page, start in enumerate(starts):
            end = starts[page + 1] if page + 1 < len(starts) else len(packed)
            expected = records[page * 32 : page * 32 + 32]
            self.assertEqual(
                unpack_entropy_stream(
                    packed[start:end], record_count=len(expected)
                ),
                expected,
            )

    def test_optimizer_is_deterministic_and_lossless(self) -> None:
        """Verify optimizer is deterministic and lossless."""
        phrase = (_common(1), _common(2), _common(3), _common(4))
        groups = (
            tuple(
                (*phrase, _common(index % 8), *phrase) for index in range(18)
            ),
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
        """Verify scenario layout preserves fixed tail."""
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

    def test_base_renderer_patches_are_frozen(self) -> None:
        """Keep the proven pre-entropy renderer repairs byte-identical."""
        self.assertEqual(
            tuple(patch.cpu_address for patch in BASE_RUNTIME_PATCHES),
            (0x81D3, 0x8378),
        )
        self.assertEqual(
            tuple(patch.replacement for patch in BASE_RUNTIME_PATCHES),
            (
                bytes.fromhex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
                bytes.fromhex("B0"),
            ),
        )

    def test_dialogue_cadence_patch_is_isolated_and_exact(self) -> None:
        """Lock the speed-only scheduler rewrite and its state/frame behavior."""
        self.assertEqual(len(DIALOGUE_CADENCE_PATCHES), 1)
        patch = DIALOGUE_CADENCE_PATCHES[0]
        self.assertEqual(patch.cpu_address, 0x7F0F)
        self.assertEqual(len(patch.expected), 34)
        self.assertEqual(len(patch.replacement), 34)
        self.assertEqual(
            patch.expected,
            bytes.fromhex(
                "A5 2B 29 01 F0 1C A9 00 85 63 85 66 A5 69 C9 08 F0 0D "
                "C9 11 F0 09 C9 15 F0 05 C9 19 F0 01 60 4C 31 7F"
            ),
        )
        self.assertEqual(
            patch.replacement,
            bytes.fromhex(
                "A5 2B 29 01 F0 1C 4A 85 63 85 66 A5 69 C9 04 D0 06 "
                "A5 2B 29 06 F0 0B C9 08 F0 07 49 11 29 13 F0 01 60"
            ),
        )

        def dispatches(state: int, frame: int) -> bool:
            if frame & 1 == 0:
                return True
            if state == 0x04 and frame & 0x06 == 0:
                return True
            if state == 0x08:
                return True
            return ((state ^ 0x11) & 0x13) == 0

        # The compact high-state predicate is exact over NOV2's $00-$1A
        # scheduler range; this specifically guards against the earlier
        # decimal/hex transcription error.
        native_odd = {0x08, 0x11, 0x15, 0x19}
        self.assertEqual(
            {state for state in range(0x1B) if dispatches(state, 0x03)},
            native_odd,
        )
        self.assertEqual(
            {state for state in range(0x1B) if dispatches(state, 0x01)},
            native_odd | {0x04},
        )

        # Across 16 NTSC frames: ordinary states run 8 times, state $04 runs
        # 10 times (+25%), and the four native exceptions still run 16 times.
        self.assertEqual(
            sum(dispatches(0x03, frame) for frame in range(16)),
            8,
        )
        self.assertEqual(
            sum(dispatches(0x04, frame) for frame in range(16)),
            10,
        )
        for state in native_odd:
            self.assertEqual(
                sum(dispatches(state, frame) for frame in range(16)),
                16,
            )

    def test_dynamic_menu_layout_patches_are_source_locked(self) -> None:
        """Freeze the variable-width renderer without touching palette RAM."""
        self.assertEqual(
            tuple(patch.cpu_address for patch in DYNAMIC_MENU_LAYOUT_PATCHES),
            (0x6D8A, 0x6DDC, 0x945D, 0x9481, 0x94E5, 0x9885),
        )
        patches = {patch.label: patch for patch in DYNAMIC_MENU_LAYOUT_PATCHES}
        self.assertEqual(
            patches["expanded variable-width menu clear span"].replacement,
            bytes.fromhex("24"),
        )
        self.assertIn(
            bytes.fromhex("BD 2D 04 4A 4A 4A D0 02 A9 06 85 31"),
            patches["metadata-driven menu renderer geometry"].replacement,
        )
        self.assertEqual(MENU_WIDTH_WORK_RAM_ADDRESS, 0x042D)
        self.assertEqual(MENU_MAX_STAGED_GLYPHS, 18)

    def test_entropy_prerequisites_are_only_native_nested_depth(self) -> None:
        """Verify entropy prerequisites are only native nested depth."""
        self.assertEqual(
            tuple(patch.cpu_address for patch in ENTROPY_PREREQUISITE_PATCHES),
            (0x82C5, 0x8311),
        )
        self.assertEqual(
            tuple(patch.expected for patch in ENTROPY_PREREQUISITE_PATCHES),
            (bytes.fromhex("A9 FF 85 71"), bytes.fromhex("A9 00 85 71")),
        )
        self.assertEqual(
            tuple(patch.replacement for patch in ENTROPY_PREREQUISITE_PATCHES),
            (bytes.fromhex("E6 71 EA EA"), bytes.fromhex("C6 71 EA EA")),
        )

    def test_generated_6502_blocks_fit_and_do_not_overlap(self) -> None:
        """Verify generated 6502 blocks fit and do not overlap."""
        self.assertEqual(SCANNER_CODE_BYTES, 159)
        self.assertEqual(FRONTEND_CODE_BYTES, 64)
        self.assertEqual(CATEGORY_CODE_BYTES, 59)
        self.assertEqual(ENTROPY_POINTER_INIT_CPU_ADDRESS, 0x8124)
        self.assertEqual(ENTROPY_MENU_INIT_CPU_ADDRESS, 0x812E)
        self.assertEqual(ENTROPY_SELECTION_SPAN_CPU_ADDRESS, 0x8137)
        occupied: set[int] = set()
        for patch in ENTROPY_RUNTIME_PATCHES:
            touched = set(
                range(patch.cpu_address, patch.cpu_address + patch.size)
            )
            self.assertTrue(occupied.isdisjoint(touched), patch.label)
            occupied.update(touched)
        self.assertLess(max(occupied), NOV3_LOAD_ADDRESS)

    def test_parent_back_guard_is_choice_count_independent(self) -> None:
        """Lock root-menu B suppression to parent existence, never choice count."""
        patches = {patch.label: patch for patch in PARENT_BACK_GUARD_PATCHES}
        self.assertEqual(len(patches), 4)
        scanner = {patch.label: patch for patch in ENTROPY_RUNTIME_PATCHES}[
            "bit-contiguous entropy scanner"
        ]
        stub_offset = 0x814A - scanner.cpu_address
        self.assertEqual(
            scanner.replacement[stub_offset : stub_offset + 5],
            bytes.fromhex("84 9C 4C BB 6B"),
        )
        self.assertEqual(
            patches[
                "route no-parent menu setup through Back guard"
            ].replacement,
            bytes.fromhex("F0 C5"),
        )
        # None of the parent-guard replacements read $98 (LDY $98 = A4 98),
        # the retired choice-count discriminator.
        self.assertFalse(
            any(
                bytes.fromhex("A4 98") in patch.replacement
                for patch in PARENT_BACK_GUARD_PATCHES
            )
        )

    def test_generated_runtime_binary_is_frozen(self) -> None:
        """Verify generated runtime binary is frozen."""
        patches = {patch.label: patch for patch in ENTROPY_RUNTIME_PATCHES}
        scanner = patches["bit-contiguous entropy scanner"].replacement[
            :SCANNER_CODE_BYTES
        ]
        frontend = patches["entropy semantic dispatch frontend"].replacement[
            :FRONTEND_CODE_BYTES
        ]
        category = patches["entropy prefix-category decoder"].replacement[
            :CATEGORY_CODE_BYTES
        ]
        self.assertEqual(
            _sha256(scanner),
            "0D67AA4B4105720FF45907D4ECA8427AA76A0902D685949514BCC6AA6D7CD237",
        )
        self.assertEqual(
            _sha256(frontend),
            "19AAE5C50313AA051E39395A0C7BF50A24F8D733AF09E4A64134C3C068AC1AF6",
        )
        self.assertEqual(
            _sha256(category),
            "13BB5546C4DAA3C3D688F07F75FBFFD226725EB9BD72CD6238CBB662308485A2",
        )

    def test_menu_selection_brackets_use_work_ram_width_metadata(self) -> None:
        """Place both menu cursors from the same per-entry pixel width."""
        patches = {patch.label: patch for patch in ENTROPY_RUNTIME_PATCHES}
        scanner = patches["bit-contiguous entropy scanner"].replacement

        span_offset = ENTROPY_SELECTION_SPAN_CPU_ADDRESS - 0x80B1
        span_stub = scanner[span_offset : span_offset + 25]
        self.assertEqual(
            span_stub,
            bytes.fromhex(
                "98 48 A4 A8 B9 2D 04 18 69 08 65 14 85 31 "
                "68 A8 A5 31 60 84 9C 4C BB 6B EA"
            ),
        )
        self.assertEqual(MENU_WIDTH_WORK_RAM_ADDRESS, 0x042D)

        capture = patches["capture decoded menu width in Work RAM"]
        self.assertEqual(capture.cpu_address, 0x946B)
        self.assertEqual(capture.replacement, bytes.fromhex("20 DF 6D 60 EA"))
        dynamic = patches["dynamic menu trailing cursor span"]
        self.assertEqual(dynamic.cpu_address, 0x989F)
        self.assertEqual(
            dynamic.replacement,
            bytes.fromhex("20 37 81 24 48 85 14"),
        )

        menu_patches = {
            patch.label: patch for patch in DYNAMIC_MENU_LAYOUT_PATCHES
        }
        self.assertTrue(
            menu_patches[
                "width-aware leading menu cursor"
            ].replacement.startswith(bytes.fromhex("20 8D 6D"))
        )

        # Pixel metadata stores glyph_count * 8. The trailing helper adds one
        # tile after the text, so 3/7/18 glyph labels consume 32/64/152 pixels.
        for glyphs, expected_span in ((3, 0x20), (7, 0x40), (18, 0x98)):
            self.assertEqual(glyphs * 8 + 8, expected_span)

        palette = set(PALETTE_CPU_RANGE)
        for patch in (*DYNAMIC_MENU_LAYOUT_PATCHES, *ENTROPY_RUNTIME_PATCHES):
            touched = set(
                range(
                    patch.cpu_address,
                    patch.cpu_address + len(patch.replacement),
                )
            )
            self.assertTrue(palette.isdisjoint(touched), patch.label)

    def test_entropy_runtime_preserves_x_and_avoids_native_zero_page_74(
        self,
    ) -> None:
        """Verify entropy runtime preserves x and avoids native zero page 74."""
        patches = {patch.label: patch for patch in ENTROPY_RUNTIME_PATCHES}
        scanner = patches["bit-contiguous entropy scanner"].replacement[
            :SCANNER_CODE_BYTES
        ]
        frontend = patches["entropy semantic dispatch frontend"].replacement[
            :FRONTEND_CODE_BYTES
        ]

        # Scanner saves X once after fresh-stream setup and restores it on its
        # single return path. Frontend saves X before category decoding and
        # restores it before tail-dispatching into the native handlers.
        self.assertEqual(scanner[11:13], bytes.fromhex("8A 48"))
        self.assertIn(bytes.fromhex("68 AA 60"), scanner)
        self.assertEqual(frontend[:2], bytes.fromhex("8A 48"))
        self.assertIn(bytes.fromhex("68 AA 98"), frontend)

        for opcode in (
            bytes.fromhex("85 74"),
            bytes.fromhex("A5 74"),
            bytes.fromhex("A4 74"),
        ):
            self.assertNotIn(opcode, scanner)
            self.assertNotIn(opcode, frontend)


if __name__ == "__main__":
    unittest.main()
