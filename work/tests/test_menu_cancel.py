"""Guard final Back/Cancel behavior after the frozen compiler."""

from __future__ import annotations

import unittest

from time_twist.menu_cancel import (
    BACK_DISPATCH_OFFSET,
    BACK_DISPATCH_REPLACEMENT,
    MENU_SETUP_OFFSET,
    MENU_SETUP_EXPECTED,
    NO_PARENT_STUB_EXPECTED,
    NO_PARENT_STUB_OFFSET,
    NO_PARENT_TRAMPOLINE_EXPECTED,
    NO_PARENT_TRAMPOLINE_OFFSET,
    SELF_PARENT_GUARD_OFFSET,
    SELF_PARENT_GUARD_REPLACEMENT,
    patch_menu_cancel,
)
from time_twist.release_metadata import ReleaseBuildError


class MenuCancelTests(unittest.TestCase):
    """Check source drift and the final parent-only Back contract."""

    def setUp(self) -> None:
        """Build only the audited frozen-compiler instruction regions."""
        self.engine = bytearray(0x4000)
        self.engine[MENU_SETUP_OFFSET : MENU_SETUP_OFFSET + len(MENU_SETUP_EXPECTED)] = (
            MENU_SETUP_EXPECTED
        )
        self.engine[
            NO_PARENT_TRAMPOLINE_OFFSET
            : NO_PARENT_TRAMPOLINE_OFFSET + len(NO_PARENT_TRAMPOLINE_EXPECTED)
        ] = NO_PARENT_TRAMPOLINE_EXPECTED
        self.engine[
            NO_PARENT_STUB_OFFSET : NO_PARENT_STUB_OFFSET
            + len(NO_PARENT_STUB_EXPECTED)
        ] = NO_PARENT_STUB_EXPECTED
        self.engine[0x39DC:0x39EA] = bytes.fromhex(
            "A5 9C F0 FB 20 2E 6A F0 F6 A9 04 4C B6 7D"
        )
        self.engine[0x0A2E:0x0A3A] = bytes.fromhex(
            "A5 9C C5 C6 D0 04 A5 9B C5 C5 60 EA"
        )

    def test_back_depends_only_on_saved_parent_marker(self) -> None:
        """Retire PC-equality as a parent-validity test."""
        result = patch_menu_cancel(bytes(self.engine))

        self.assertEqual(
            result[
                BACK_DISPATCH_OFFSET
                : BACK_DISPATCH_OFFSET + len(BACK_DISPATCH_REPLACEMENT)
            ],
            BACK_DISPATCH_REPLACEMENT,
        )
        self.assertEqual(
            result[
                SELF_PARENT_GUARD_OFFSET
                : SELF_PARENT_GUARD_OFFSET + len(SELF_PARENT_GUARD_REPLACEMENT)
            ],
            SELF_PARENT_GUARD_REPLACEMENT,
        )

        # Root/no-parent setup remains the frozen compiler's explicit $9C=0
        # contract. Nothing in the finalizer changes that path.
        self.assertEqual(
            result[MENU_SETUP_OFFSET : MENU_SETUP_OFFSET + len(MENU_SETUP_EXPECTED)],
            MENU_SETUP_EXPECTED,
        )
        self.assertEqual(
            result[
                NO_PARENT_TRAMPOLINE_OFFSET
                : NO_PARENT_TRAMPOLINE_OFFSET + len(NO_PARENT_TRAMPOLINE_EXPECTED)
            ],
            NO_PARENT_TRAMPOLINE_EXPECTED,
        )
        self.assertEqual(
            result[
                NO_PARENT_STUB_OFFSET
                : NO_PARENT_STUB_OFFSET + len(NO_PARENT_STUB_EXPECTED)
            ],
            NO_PARENT_STUB_EXPECTED,
        )

        # The dispatcher is exactly:
        #   LDA $9C / BNE +1 / RTS / ...
        # It never compares $9B/$9C with $C5/$C6, so a valid one-choice child
        # can Back even when the parent PC equals the frozen current script PC.
        self.assertEqual(BACK_DISPATCH_REPLACEMENT[:5], bytes.fromhex("A5 9C D0 01 60"))

    def test_changed_frozen_surface_is_rejected(self) -> None:
        """Never finalize an unverified frozen-compiler runtime."""
        for offset in (
            MENU_SETUP_OFFSET + 4,
            NO_PARENT_TRAMPOLINE_OFFSET,
            NO_PARENT_STUB_OFFSET,
            BACK_DISPATCH_OFFSET + 2,
            SELF_PARENT_GUARD_OFFSET + 2,
        ):
            with self.subTest(offset=offset):
                changed = bytearray(self.engine)
                changed[offset] ^= 1
                with self.assertRaisesRegex(ReleaseBuildError, "source mismatch"):
                    patch_menu_cancel(bytes(changed))

    def test_reapplication_is_rejected(self) -> None:
        """Require exactly the expected frozen-compiler input."""
        with self.assertRaises(ReleaseBuildError):
            patch_menu_cancel(patch_menu_cancel(bytes(self.engine)))


if __name__ == "__main__":
    unittest.main()
