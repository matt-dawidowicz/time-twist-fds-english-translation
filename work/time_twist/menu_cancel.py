"""Finalize Back/Cancel semantics after the frozen v38 compiler."""

from __future__ import annotations

from .release_metadata import ReleaseBuildError

# The frozen compiler already installs the no-parent setup route:
# descriptor bit 3 clear -> $6B70 -> $814A, where STY $9C clears the saved
# Back destination before normal setup resumes. That is the authoritative
# no-parent marker.
MENU_SETUP_OFFSET = 0x0BA3
MENU_SETUP_EXPECTED = bytes.fromhex(
    "A0 00 B1 C5 29 08 F0 C5 A5 C5 85 9B A5 C6 85 9C "
    "A5 9D 85 9F A5 9E 85 A0"
)
NO_PARENT_TRAMPOLINE_OFFSET = 0x0B70
NO_PARENT_TRAMPOLINE_EXPECTED = bytes.fromhex("4C 4A 81")
NO_PARENT_STUB_OFFSET = 0x214A
NO_PARENT_STUB_EXPECTED = bytes.fromhex("84 9C 4C BB 6B")

# The frozen compiler still carries an older post-menu dispatcher plus a
# "self-parent" helper. Runtime evidence from TT3B's one-choice Charm submenu
# proves that a valid saved parent can equal the still-frozen current script
# PC ($9B/$9C == $C5/$C6). Equality therefore cannot mean "no parent".
BACK_DISPATCH_OFFSET = 0x39DC
BACK_DISPATCH_EXPECTED = bytes.fromhex(
    "A5 9C F0 FB 20 2E 6A F0 F6 A9 04 4C B6 7D"
)
BACK_DISPATCH_REPLACEMENT = bytes.fromhex(
    "A5 9C D0 01 60 A9 04 85 A1 A9 22 4C 09 61"
)

SELF_PARENT_GUARD_OFFSET = 0x0A2E
SELF_PARENT_GUARD_EXPECTED = bytes.fromhex(
    "A5 9C C5 C6 D0 04 A5 9B C5 C5 60 EA"
)
SELF_PARENT_GUARD_REPLACEMENT = bytes.fromhex(
    "4C 01 61 4C 01 61 4C 01 61 4C DB 89"
)

FINAL_MENU_CANCEL_SURFACES = (
    (
        BACK_DISPATCH_OFFSET,
        BACK_DISPATCH_REPLACEMENT,
        "parent-only Back/Cancel dispatcher",
    ),
    (
        SELF_PARENT_GUARD_OFFSET,
        SELF_PARENT_GUARD_REPLACEMENT,
        "retired self-parent special case",
    ),
)


def patch_menu_cancel(nov2: bytes) -> bytes:
    """Make Back depend only on the explicit saved-parent marker.

    The frozen compiler has already arranged for root/no-parent menu setup to
    clear $9C. Child/resumable menus preserve a nonzero $9C, even when the
    saved parent PC happens to equal the current frozen script PC.

    Replace the obsolete equality-based helper and dispatcher with the native
    parent-only path:

    - $9C == 0: B is ignored at a root menu;
    - $9C != 0: B enters normal Back/Cancel, regardless of visible choice count
      or whether $9B/$9C equals $C5/$C6.
    """
    for offset, expected in (
        (MENU_SETUP_OFFSET, MENU_SETUP_EXPECTED),
        (NO_PARENT_TRAMPOLINE_OFFSET, NO_PARENT_TRAMPOLINE_EXPECTED),
        (NO_PARENT_STUB_OFFSET, NO_PARENT_STUB_EXPECTED),
        (BACK_DISPATCH_OFFSET, BACK_DISPATCH_EXPECTED),
        (SELF_PARENT_GUARD_OFFSET, SELF_PARENT_GUARD_EXPECTED),
    ):
        if nov2[offset : offset + len(expected)] != expected:
            raise ReleaseBuildError(
                f"menu cancel source mismatch at ${offset + 0x6000:04X}"
            )

    result = bytearray(nov2)
    result[
        BACK_DISPATCH_OFFSET : BACK_DISPATCH_OFFSET
        + len(BACK_DISPATCH_REPLACEMENT)
    ] = BACK_DISPATCH_REPLACEMENT
    result[
        SELF_PARENT_GUARD_OFFSET : SELF_PARENT_GUARD_OFFSET
        + len(SELF_PARENT_GUARD_REPLACEMENT)
    ] = SELF_PARENT_GUARD_REPLACEMENT
    return bytes(result)
