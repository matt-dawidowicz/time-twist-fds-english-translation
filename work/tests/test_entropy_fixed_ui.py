"""Regression coverage for entropy-owned fixed decoder surfaces."""

from __future__ import annotations

import hashlib
import unittest

from time_twist.english import encode_english
from time_twist.entropy_codec import unpack_entropy_stream
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from time_twist.entropy_fixed_ui import (
    NOV4_DICTIONARY_END,
    NOV4_DICTIONARY_START,
    NOV4_DICTIONARY_TEXT,
    NOV4_GROUP_END,
    NOV4_GROUP_START,
    NOV4_GROUP_TEXT,
    NOV4_MENU_END,
    NOV4_MENU_START,
    NOV4_MENU_TEXT,
    NOV4_POINTERS,
    NOV4_SOURCE_SIZE,
    TT1A_CHOICE_PATCHES,
    TT1A_ENTRY_ADDRESSES,
    TT1A_LOAD_ADDRESS,
    TT1A_TABLE_CAPACITY,
    TT1A_TABLE_END,
    TT1A_TABLE_POINTERS,
    TT1A_TABLE_START,
    EntropyFixedTextError,
    entropy_fixed_text_coverage,
    nov4_entropy_payloads,
    patched_nov4_entropy_text,
    patched_tt1a_entropy_ui,
    tt1a_entropy_payload,
    tt1a_entropy_payloads,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _semantic(record):
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _pad(payload: bytes, size: int) -> bytes:
    return payload + bytes(size - len(payload))


def _write_word(data: bytearray, offset: int, value: int) -> None:
    data[offset : offset + 2] = value.to_bytes(2, "little")


class EntropyFixedUiTests(unittest.TestCase):
    def test_payload_oracles_and_capacity(self) -> None:
        menu, group, dictionary = nov4_entropy_payloads()
        tt1a = tt1a_entropy_payload()

        self.assertEqual(len(menu), 97)
        self.assertEqual(
            _sha256(menu),
            "5675CE858A06C5ACE82EBB5D495DB32AD34BC2F7FB94AE0A1CDA62941C192D3D",
        )
        self.assertEqual(len(group), 47)
        self.assertEqual(
            _sha256(group),
            "9B00C0D174E7566A4CBF6B95F8200A961B8CB323E35DDC3CAA32EFA1FC1002E6",
        )
        self.assertEqual(len(dictionary), 19)
        self.assertEqual(
            _sha256(dictionary),
            "ABCF4B7F02519D1A90DCC3A5E5522C9249833199A52A99019364E23C3F31DAC2",
        )
        self.assertEqual(len(tt1a), 80)
        self.assertEqual(
            _sha256(tt1a),
            "25D9B9DFF381D2E16D17F336FA5EBDF405D8215BF979CF5558EA388553492F25",
        )
        self.assertEqual(sum(map(len, tt1a_entropy_payloads())), 67)

        self.assertLessEqual(len(menu), NOV4_MENU_END - NOV4_MENU_START)
        self.assertLessEqual(len(group), NOV4_GROUP_END - NOV4_GROUP_START)
        self.assertLessEqual(
            len(dictionary), NOV4_DICTIONARY_END - NOV4_DICTIONARY_START
        )
        self.assertLessEqual(len(tt1a), TT1A_TABLE_CAPACITY)

    def test_padded_region_oracles_are_frozen(self) -> None:
        menu, group, dictionary = nov4_entropy_payloads()
        tt1a = tt1a_entropy_payload()
        self.assertEqual(
            _sha256(_pad(menu, NOV4_MENU_END - NOV4_MENU_START)),
            "4EA71F675D0700196173AB571E4E4083F0B5F6C7AB68E0B22F45A04008D9B8A1",
        )
        self.assertEqual(
            _sha256(_pad(group, NOV4_GROUP_END - NOV4_GROUP_START)),
            "48977FA6BF9B9A949BEE06F9E353D28D598A396B34B4F5DD27CB319A262178B9",
        )
        self.assertEqual(
            _sha256(
                _pad(
                    dictionary,
                    NOV4_DICTIONARY_END - NOV4_DICTIONARY_START,
                )
            ),
            "12F0F22ED0D44C1A4CF2BEC567E972F83C183AAA1A351C83CB64E096585E8B2D",
        )
        self.assertEqual(
            _sha256(tt1a),
            "25D9B9DFF381D2E16D17F336FA5EBDF405D8215BF979CF5558EA388553492F25",
        )

    def test_nov4_streams_round_trip_to_english_semantics(self) -> None:
        menu, group, dictionary = nov4_entropy_payloads()
        decoded_dictionary = unpack_entropy_stream(
            dictionary,
            record_count=len(NOV4_DICTIONARY_TEXT),
        )
        expansions = expand_entropy_dictionary(decoded_dictionary)
        for blob, texts in ((menu, NOV4_MENU_TEXT), (group, NOV4_GROUP_TEXT)):
            decoded = unpack_entropy_stream(blob, record_count=len(texts))
            for record, text in zip(decoded, texts, strict=True):
                expanded = expand_entropy_record(record, expansions)
                self.assertEqual(
                    _semantic(expanded), _semantic(encode_english(text))
                )

    def test_first_menu_start_record_is_entropy_not_native(self) -> None:
        menu, _group, dictionary = nov4_entropy_payloads()
        decoded_dictionary = unpack_entropy_stream(
            dictionary,
            record_count=len(NOV4_DICTIONARY_TEXT),
        )
        expansions = expand_entropy_dictionary(decoded_dictionary)
        decoded_menu = unpack_entropy_stream(
            menu, record_count=len(NOV4_MENU_TEXT)
        )
        start = expand_entropy_record(decoded_menu[3], expansions)
        self.assertEqual(_semantic(start), _semantic(encode_english("Start")))

    def test_tt1a_slots_preserve_every_native_entry_address(self) -> None:
        self.assertEqual(
            TT1A_ENTRY_ADDRESSES,
            (
                0xA45B,
                0xA45E,
                0xA462,
                0xA465,
                0xA46A,
                0xA46E,
                0xA472,
                0xA476,
                0xA47A,
                0xA47E,
                0xA482,
                0xA489,
                0xA48D,
                0xA491,
                0xA495,
                0xA49A,
                0xA49F,
                0xA4A4,
                0xA4A8,
            ),
        )
        for index, ((offset, source, text), payload) in enumerate(
            zip(TT1A_CHOICE_PATCHES, tt1a_entropy_payloads(), strict=True)
        ):
            self.assertLessEqual(len(payload), len(source))
            decoded = unpack_entropy_stream(payload, record_count=1)
            self.assertEqual(len(decoded), 1)
            self.assertEqual(
                _semantic(decoded[0]), _semantic(encode_english(text))
            )
            self.assertEqual(
                TT1A_LOAD_ADDRESS + offset, TT1A_ENTRY_ADDRESSES[index]
            )

    def test_idempotent_nov4_patcher_preserves_pointer_contract(self) -> None:
        menu, group, dictionary = nov4_entropy_payloads()
        source = bytearray(NOV4_SOURCE_SIZE)
        for offset, address in NOV4_POINTERS.items():
            _write_word(source, offset, address)
        source[NOV4_MENU_START:NOV4_MENU_END] = _pad(
            menu, NOV4_MENU_END - NOV4_MENU_START
        )
        source[NOV4_GROUP_START:NOV4_GROUP_END] = _pad(
            group, NOV4_GROUP_END - NOV4_GROUP_START
        )
        source[NOV4_DICTIONARY_START:NOV4_DICTIONARY_END] = _pad(
            dictionary, NOV4_DICTIONARY_END - NOV4_DICTIONARY_START
        )
        patched = patched_nov4_entropy_text(bytes(source))
        self.assertEqual(patched, bytes(source))
        for offset, address in NOV4_POINTERS.items():
            self.assertEqual(
                int.from_bytes(patched[offset : offset + 2], "little"), address
            )

    def test_idempotent_tt1a_patcher_preserves_pointer_contract(self) -> None:
        source = bytearray(0x1000)
        for offset, address in TT1A_TABLE_POINTERS.items():
            _write_word(source, offset, address)
        source[TT1A_TABLE_START:TT1A_TABLE_END] = tt1a_entropy_payload()
        patched = patched_tt1a_entropy_ui(bytes(source))
        self.assertEqual(patched, bytes(source))
        for offset, address in TT1A_TABLE_POINTERS.items():
            self.assertEqual(
                int.from_bytes(patched[offset : offset + 2], "little"), address
            )

    def test_partial_nov4_conversion_is_rejected(self) -> None:
        menu, group, dictionary = nov4_entropy_payloads()
        source = bytearray(NOV4_SOURCE_SIZE)
        for offset, address in NOV4_POINTERS.items():
            _write_word(source, offset, address)
        source[NOV4_MENU_START:NOV4_MENU_END] = _pad(
            menu, NOV4_MENU_END - NOV4_MENU_START
        )
        source[NOV4_GROUP_START:NOV4_GROUP_END] = _pad(
            group, NOV4_GROUP_END - NOV4_GROUP_START
        )
        source[NOV4_DICTIONARY_START:NOV4_DICTIONARY_END] = _pad(
            dictionary, NOV4_DICTIONARY_END - NOV4_DICTIONARY_START
        )
        source[NOV4_GROUP_START] ^= 0x01
        with self.assertRaises(EntropyFixedTextError):
            patched_nov4_entropy_text(bytes(source))

    def test_manifest_coverage_inventory_is_complete_and_bounded(self) -> None:
        self.assertEqual(
            entropy_fixed_text_coverage(),
            {
                "NOV4_menu": {
                    "records": 26,
                    "streams": 1,
                    "packed_bytes": 97,
                    "capacity_bytes": 134,
                },
                "NOV4_internal": {
                    "records": 7,
                    "streams": 1,
                    "packed_bytes": 47,
                    "capacity_bytes": 60,
                },
                "NOV4_dictionary": {
                    "records": 4,
                    "streams": 1,
                    "packed_bytes": 19,
                    "capacity_bytes": 28,
                },
                "TT1A_choices": {
                    "records": 19,
                    "streams": 19,
                    "packed_bytes": 67,
                    "capacity_bytes": 80,
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
