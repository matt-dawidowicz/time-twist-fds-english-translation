"""Regression coverage for entropy dictionary presentation-control boundaries."""

from __future__ import annotations

import unittest

from time_twist.entropy_compression import optimize_entropy_dictionary
from time_twist.textcodec import PackedSymbol, SymbolKind


def _symbol(kind: SymbolKind, value: int) -> PackedSymbol:
    return PackedSymbol(kind, value, 0, 0)


class EntropyControlBoundaryTests(unittest.TestCase):
    """Keep presentation controls outside every optimized dictionary expansion."""

    def test_optimizer_never_places_control_inside_dictionary_expansion(self) -> None:
        ctrl = _symbol(SymbolKind.CONTROL, 0)
        a = _symbol(SymbolKind.COMMON, 42)
        b = _symbol(SymbolKind.COMMON, 8)
        c = _symbol(SymbolKind.COMMON, 3)
        d = _symbol(SymbolKind.COMMON, 6)

        # Repetition on both sides of CTRL:0 deliberately makes a phrase spanning
        # the control attractive unless candidate generation treats controls as
        # hard grammar boundaries.
        record = (ctrl, ctrl, a, b, c, d, ctrl, a, b, c, d)
        groups = ((record, record, record, record, record, record),)

        result = optimize_entropy_dictionary(groups)

        self.assertTrue(result.dictionary)
        self.assertTrue(
            all(
                symbol.kind is not SymbolKind.CONTROL
                for expansion in result.expansions
                for symbol in expansion
            )
        )
        for packed_record in result.groups[0]:
            self.assertEqual(
                [symbol.value for symbol in packed_record[:2]],
                [0, 0],
            )
            self.assertTrue(
                all(
                    symbol.kind is SymbolKind.CONTROL
                    for symbol in packed_record[:2]
                )
            )


if __name__ == "__main__":
    unittest.main()
