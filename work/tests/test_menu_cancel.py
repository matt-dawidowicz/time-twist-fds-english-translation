"""Guard menu-parent preservation and the rejected-Back redraw paths."""

from __future__ import annotations

import unittest

from time_twist.menu_cancel import (
    BACK_DISPATCH_FINAL,
    BACK_DISPATCH_OFFSET,
    FINAL_MENU_CANCEL_SURFACES,
    MENU_SETUP_FINAL,
    MENU_SETUP_OFFSET,
    SELF_PARENT_GUARD,
    SELF_PARENT_GUARD_OFFSET,
    patch_menu_cancel,
)
from time_twist.release_metadata import ReleaseBuildError


class MenuCancelTests(unittest.TestCase):
    """Check source drift and final post-build Back/Cancel bytes."""

    def setUp(self) -> None:
        """Build only the three audited instruction regions."""
        self.engine = bytearray(0x4000)
        self.engine[0xBA3:0xBBB] = bytes.fromhex(
            "A0 00 B1 C5 29 08 F0 C5 A5 C5 85 9B A5 C6 85 9C "
            "A5 9D 85 9F A5 9E 85 A0"
        )
        self.engine[0x39DC:0x39EA] = bytes.fromhex(
            "A5 9C F0 FB 20 2E 6A F0 F6 A9 04 4C B6 7D"
        )
        self.engine[0xA2E:0xA3A] = SELF_PARENT_GUARD

    def test_child_setup_preserves_parent_and_rejected_back_redraws(
        self,
    ) -> None:
        """Resolve each finalizer branch to the intended live engine path."""
        result = patch_menu_cancel(bytes(self.engine))
        for operand, target in (
            (0xBAA, 0xBBB),
            (0x39DF, 0x398C),
            (0x39E4, 0x398C),
        ):
            displacement = int.from_bytes(
                result[operand : operand + 1], signed=True
            )
            self.assertEqual(operand + 1 + displacement, target)
        self.assertEqual(
            result[MENU_SETUP_OFFSET : MENU_SETUP_OFFSET + len(MENU_SETUP_FINAL)],
            MENU_SETUP_FINAL,
        )
        self.assertEqual(
            result[
                BACK_DISPATCH_OFFSET
                : BACK_DISPATCH_OFFSET + len(BACK_DISPATCH_FINAL)
            ],
            BACK_DISPATCH_FINAL,
        )
        self.assertEqual(
            result[
                SELF_PARENT_GUARD_OFFSET
                : SELF_PARENT_GUARD_OFFSET + len(SELF_PARENT_GUARD)
            ],
            SELF_PARENT_GUARD,
        )
        for offset, expected, _label in FINAL_MENU_CANCEL_SURFACES:
            self.assertEqual(result[offset : offset + len(expected)], expected)
        self.assertEqual(
            sum(a != b for a, b in zip(self.engine, result, strict=True)), 3
        )

    def test_changed_setup_dispatch_or_self_guard_is_rejected(self) -> None:
        """Never install branches into an unverified engine revision."""
        for offset in (0xBA7, 0x39E0, 0xA30):
            with self.subTest(offset=offset):
                changed = bytearray(self.engine)
                changed[offset] ^= 1
                with self.assertRaisesRegex(
                    ReleaseBuildError, "source mismatch"
                ):
                    patch_menu_cancel(bytes(changed))

    def test_reapplication_is_rejected(self) -> None:
        """Require exactly the expected pre-finalizer engine."""
        with self.assertRaises(ReleaseBuildError):
            patch_menu_cancel(patch_menu_cancel(bytes(self.engine)))


if __name__ == "__main__":
    unittest.main()
