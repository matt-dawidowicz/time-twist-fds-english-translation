"""Guard menu-parent preservation and the rejected-Back redraw paths."""

from __future__ import annotations

import unittest

from time_twist.menu_cancel import patch_menu_cancel
from time_twist.release_metadata import ReleaseBuildError


class MenuCancelTests(unittest.TestCase):
    """Check source drift and branch destinations without private ROM data."""

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
        self.engine[0xA2E:0xA3A] = bytes.fromhex(
            "A5 9C C5 C6 D0 04 A5 9B C5 C5 60 EA"
        )

    def test_child_setup_preserves_parent_and_rejected_back_redraws(
        self,
    ) -> None:
        """Resolve each branch to the correct live engine path."""
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
        self.assertEqual(result[0xA2E:0xA3A], self.engine[0xA2E:0xA3A])
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
        """Require exactly the expected pre-patch engine."""
        with self.assertRaises(ReleaseBuildError):
            patch_menu_cancel(patch_menu_cancel(bytes(self.engine)))


if __name__ == "__main__":
    unittest.main()
