"""Repair inherited menu-parent handling and redraw rejected Back input."""

from __future__ import annotations

from .release_metadata import ReleaseBuildError

# Descriptor bit 3 saves a return destination; zero preserves the inherited
# destination. It does not mean that the new menu has no parent.
MENU_SETUP_OFFSET = 0x0BA3
MENU_SETUP_EXPECTED = bytes.fromhex(
    "A0 00 B1 C5 29 08 F0 C5 A5 C5 85 9B A5 C6 85 9C "
    "A5 9D 85 9F A5 9E 85 A0"
)
BACK_DISPATCH_OFFSET = 0x39DC
BACK_DISPATCH_EXPECTED = bytes.fromhex(
    "A5 9C F0 FB 20 2E 6A F0 F6 A9 04 4C B6 7D"
)
SELF_PARENT_GUARD_OFFSET = 0x0A2E
SELF_PARENT_GUARD = bytes.fromhex("A5 9C C5 C6 D0 04 A5 9B C5 C5 60 EA")
PATCHES = ((0x0BAA, 0xC5, 0x10), (0x39DF, 0xFB, 0xAC), (0x39E4, 0xF6, 0xA7))


def patch_menu_cancel(nov2: bytes) -> bytes:
    """Verify the inherited engine revision and change three branch operands.

    Preserve the saved parent for child menus. A missing or self-referencing
    parent still rejects Back, but now follows the normal cursor/menu refresh
    path at $998C instead of returning before the display is restored.
    """
    for offset, expected in (
        (MENU_SETUP_OFFSET, MENU_SETUP_EXPECTED),
        (BACK_DISPATCH_OFFSET, BACK_DISPATCH_EXPECTED),
        (SELF_PARENT_GUARD_OFFSET, SELF_PARENT_GUARD),
    ):
        if nov2[offset : offset + len(expected)] != expected:
            raise ReleaseBuildError(
                f"menu cancel source mismatch at ${offset + 0x6000:04X}"
            )
    result = bytearray(nov2)
    for offset, _expected, replacement in PATCHES:
        result[offset] = replacement
    return bytes(result)
