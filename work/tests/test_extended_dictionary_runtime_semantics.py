"""Semantic regression for the NOV2 extended English dictionary patch."""

from __future__ import annotations

import unittest

from time_twist.english import encode_english
from time_twist.textcodec import (
    BitReader,
    BitWriter,
    PackedSymbol,
    SymbolKind,
    decode_symbol,
    encode_symbol,
)
from time_twist.ui import NOV2_EXTENDED_DICTIONARY_PATCH


class ExtendedDictionaryRuntimeSemanticsTests(unittest.TestCase):
    """Model the recovered 6502 control-flow boundary around dictionary refs."""

    def test_extended_reference_does_not_read_a_second_dictionary_payload(
        self,
    ) -> None:
        """Keep the following symbol aligned after dictionary entries 32-68."""
        writer = BitWriter()
        reference = PackedSymbol(SymbolKind.DICTIONARY, 35, 0, 0)
        following = encode_english("A")[0]
        encode_symbol(writer, reference)
        encode_symbol(writer, following)

        reader = BitReader(writer.to_bytes())
        decoded_reference = decode_symbol(reader, extended_dictionary=True)
        self.assertEqual(decoded_reference.kind, SymbolKind.DICTIONARY)
        self.assertEqual(decoded_reference.value, 35)
        self.assertEqual(reader.bit_position, 9)

        # The patch has already decoded and converted the dictionary number.
        # $82BE is the native entry point that clears $3A and reads another
        # five-bit dictionary payload; $82C5 begins expansion after that read.
        jump_target = int.from_bytes(
            NOV2_EXTENDED_DICTIONARY_PATCH.replacement[-2:], "little"
        )
        if jump_target == 0x82BE:
            reader.read_bits(5)
        elif jump_target != 0x82C5:
            self.fail(
                f"unexpected dictionary-expander target ${jump_target:04X}"
            )

        decoded_following = decode_symbol(reader, extended_dictionary=True)
        self.assertEqual(decoded_following.kind, following.kind)
        self.assertEqual(decoded_following.value, following.value)
        self.assertEqual(reader.bit_position, 15)


if __name__ == "__main__":
    unittest.main()
