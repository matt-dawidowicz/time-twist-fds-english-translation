"""Safe final-layer 12-month Fortune Teller selector.

v64 proved that the historical September v4/v5 12-choice patch cannot be
transplanted literally onto the modern NOV2 runtime:

* $043B is live first-column-width state, so a width array at $0433-$043E
  collides with it at slot 8.
* the historical $821B helper jumped to $94AE, past the modern $22xx PPU
  address setup, allowing menu redraws to target $00xx CHR pattern RAM.

This implementation keeps the v63 <=8-choice renderer semantics, stores twelve
per-choice widths in the verified $0470-$047B gap, and adds only the geometry
needed for 9-12 visible choices.
"""

from __future__ import annotations


class MonthMenuPatchError(ValueError):
    """Raised when the expected candidate/runtime bytes have drifted."""


NOV2_LOAD_ADDRESS = 0x6000
TT1A_LOAD_ADDRESS = 0xA200
MENU_WIDTH_WORK_RAM_ADDRESS = 0x0470
MENU_WIDTH_WORK_RAM_END = 0x047B

MONTH_LABELS = (
    "Jan", "Feb", "Mar", "Apr",
    "May", "Jun", "Jul", "Aug",
    "Sep", "Oct", "Nov", "Dec",
)
MONTH_DESCRIPTOR = (5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17)
MONTH_GRID = (
    ("Jan", "May", "Sep"),
    ("Feb", "Jun", "Oct"),
    ("Mar", "Jul", "Nov"),
    ("Apr", "Aug", "Dec"),
)
MONTH_CURSOR_X = (0x20, 0x68, 0xB0)
MONTH_TEXT_BASE = (0x45, 0x4E, 0x57)

_NATIVE_DESCRIPTOR_BYTES = bytes.fromhex(
    "04 01 02 03 04 07 05 06 07 08 09 0A 0B "
    "06 0C 0D 0E 0F 10 11 02 12 13"
)
_FLAT_DESCRIPTOR_BYTES = bytes.fromhex(
    "04 01 02 03 04 0C 05 06 07 08 09 0A 0C "
    "0D 0E 0F 10 11 01 0B 02 12 13"
)
_CURSOR_REDIRECT_BEFORE = bytes.fromhex(
    "A4 32 C0 04 90 0A 98 29 03 A8 AD 3B 04 69 2F 60 A9 20 60"
)
_CURSOR_REDIRECT_AFTER = (
    bytes.fromhex("4C EC 88")
    + bytes.fromhex("98 4A 4A A8 B9 A7 88 60")
    + bytes([0xEA]) * 8
)
_CURSOR_DISPATCH_BEFORE = bytes.fromhex(
    "A4 32 C0 04 90 B2 AD 20 04 C9 09 90 03 4C 4A 81 "
    "98 29 03 A8 AD 3B 04 69 30 60"
)
_CURSOR_DISPATCH_AFTER = bytes.fromhex(
    "A4 32 C0 04 90 B2 AD 20 04 C9 09 B0 0A "
    "98 29 03 A8 AD 3B 04 69 30 60 4C 90 6D"
)
_TEXT_SPECIAL_BEFORE = bytes([0xEA]) * 11
_TEXT_SPECIAL_AFTER = bytes.fromhex(
    "8A 29 08 C9 08 69 4E 4C A4 94 EA"
)
_RENDERER_PREFIX_BEFORE = bytes.fromhex(
    "8A C9 04 90 0D 29 03 A8 AD 3B 04 4A 4A 4A 69 47 D0 02 A9 45"
)
_RENDERER_PREFIX_AFTER = bytes.fromhex(
    "A9 45 E0 04 90 0E A5 91 C9 09 B0 23 "
    "AD 3B 04 4A 4A 4A 69 47"
)
_RENDERER_TRAMPOLINES = bytes.fromhex("4C C2 94 4C 1B 82")


def _guarded(
    data: bytearray,
    *,
    load_address: int,
    cpu_address: int,
    expected: bytes,
    replacement: bytes,
    label: str,
) -> None:
    if len(expected) != len(replacement):
        raise MonthMenuPatchError(f"{label}: size mismatch")
    offset = cpu_address - load_address
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise MonthMenuPatchError(
            f"{label}: source mismatch at ${cpu_address:04X}: "
            f"{actual.hex(' ').upper()} != {expected.hex(' ').upper()}"
        )
    data[offset : offset + len(replacement)] = replacement


def parse_tt1a_primary_descriptors(
    data: bytes,
) -> tuple[tuple[int, ...], ...]:
    """Decode TT1A's compact primary-menu descriptor table."""
    start = int.from_bytes(data[0x10:0x12], "little") - TT1A_LOAD_ADDRESS
    end = int.from_bytes(data[0x12:0x14], "little") - TT1A_LOAD_ADDRESS
    if not 0 <= start <= end <= len(data):
        raise MonthMenuPatchError("TT1A primary-menu table is out of bounds")
    cursor = start
    descriptors: list[tuple[int, ...]] = []
    while cursor < end:
        count = data[cursor]
        record_end = cursor + 1 + count
        if count == 0 or record_end > end:
            raise MonthMenuPatchError(
                f"malformed TT1A descriptor at 0x{cursor:04X}"
            )
        descriptors.append(tuple(data[cursor + 1 : record_end]))
        cursor = record_end
    if cursor != end:
        raise MonthMenuPatchError("TT1A descriptor table end drifted")
    return tuple(descriptors)


def patch_tt1a_month_descriptor(data: bytes) -> bytes:
    """Flatten the retail two-stage month selector into twelve real choices."""
    result = bytearray(data)
    _guarded(
        result,
        load_address=TT1A_LOAD_ADDRESS,
        cpu_address=0xA4AB,
        expected=_NATIVE_DESCRIPTOR_BYTES,
        replacement=_FLAT_DESCRIPTOR_BYTES,
        label="TT1A 12-month primary-menu descriptor",
    )
    continuation = 0xA2F9 - TT1A_LOAD_ADDRESS
    if bytes(result[continuation : continuation + 5]) != bytes.fromhex(
        "28 02 50 05 A3"
    ):
        raise MonthMenuPatchError(
            "TT1A flattened month continuation is missing or changed"
        )
    expected = (
        (1, 2, 3, 4),
        MONTH_DESCRIPTOR,
        (11,),
        (18, 19),
    )
    actual = parse_tt1a_primary_descriptors(bytes(result))
    if actual != expected:
        raise MonthMenuPatchError(
            f"unexpected TT1A descriptors after flattening: {actual!r}"
        )
    return bytes(result)


def patch_nov2_twelve_choice_geometry(data: bytes) -> bytes:
    """Add safe 9-12-choice geometry without changing normal <=8 menus."""
    result = bytearray(data)

    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6DE8,
        expected=bytes.fromhex("99 2D 04"),
        replacement=bytes.fromhex("99 70 04"),
        label="relocate per-choice menu widths to $0470",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x813B,
        expected=bytes.fromhex("B9 2D 04"),
        replacement=bytes.fromhex("B9 70 04"),
        label="selection-span width lookup -> $0470",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6D8D,
        expected=_CURSOR_REDIRECT_BEFORE,
        replacement=_CURSOR_REDIRECT_AFTER,
        label="safe 2/3-column leading-cursor redirect",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x88EC,
        expected=_CURSOR_DISPATCH_BEFORE,
        replacement=_CURSOR_DISPATCH_AFTER,
        label="safe 2/3-column leading-cursor dispatcher",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x821B,
        expected=_TEXT_SPECIAL_BEFORE,
        replacement=_TEXT_SPECIAL_AFTER,
        label="safe 3-column text-base helper",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x9490,
        expected=_RENDERER_PREFIX_BEFORE,
        replacement=_RENDERER_PREFIX_AFTER,
        label="preserve <=8 renderer and branch >=9 safely",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x94AE,
        expected=bytes.fromhex("BD 2D 04"),
        replacement=bytes.fromhex("BD 70 04"),
        label="renderer draw-count width lookup -> $0470",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x94BC,
        expected=bytes([0xEA]) * 6,
        replacement=_RENDERER_TRAMPOLINES,
        label="normal/special renderer trampolines",
    )

    patched = bytes(result)

    if any(
        pattern in patched
        for pattern in (
            bytes.fromhex("99 2D 04"),
            bytes.fromhex("B9 2D 04"),
            bytes.fromhex("BD 2D 04"),
            bytes.fromhex("9D 2D 04"),
        )
    ):
        raise MonthMenuPatchError("stale indexed $042D width reference remains")

    relocated = sum(
        patched.count(bytes.fromhex(pattern))
        for pattern in ("99 70 04", "B9 70 04", "BD 70 04", "9D 70 04")
    )
    if relocated != 3:
        raise MonthMenuPatchError(
            f"expected three indexed $0470 width references, found {relocated}"
        )

    # The predicate scratch range ends at $046F and event flags start at $0480.
    if not (
        0x046F < MENU_WIDTH_WORK_RAM_ADDRESS
        and MENU_WIDTH_WORK_RAM_END < 0x0480
    ):
        raise MonthMenuPatchError("12-byte menu-width array escaped safe gap")

    # Modern first-column width state and parent Back guard must remain intact.
    if bytes.fromhex("CD 3B 04 90 03 8D 3B 04") not in patched:
        raise MonthMenuPatchError("live $043B max-width state was damaged")
    guard = 0x814A - NOV2_LOAD_ADDRESS
    if bytes(patched[guard : guard + 5]) != bytes.fromhex("84 9C 4C BB 6B"):
        raise MonthMenuPatchError("parent Back guard changed")

    # v65 deliberately keeps the canonical trailing-span call.
    trailing = 0x989F - NOV2_LOAD_ADDRESS
    if bytes(patched[trailing : trailing + 3]) != bytes.fromhex("20 37 81"):
        raise MonthMenuPatchError("canonical trailing-span call changed")

    return patched


def month_text_ppu_address(slot: int) -> int:
    """Return the exact nametable address used by one 4x3 month slot."""
    if not 0 <= slot < 12:
        raise ValueError(slot)
    row = slot & 3
    column = slot >> 2
    address = 0x2200 + MONTH_TEXT_BASE[column] + (row << 6)
    if not 0x2000 <= address <= 0x23BF:
        raise MonthMenuPatchError(f"slot {slot} escaped nametable space")
    return address


def twelve_month_navigation(slot: int, direction: str) -> int:
    """Mirror the native menu input handler for a twelve-choice descriptor."""
    if not 0 <= slot < 12:
        raise ValueError(slot)
    if direction == "down":
        return (slot + 1) % 12
    if direction == "up":
        return (slot - 1) % 12
    if direction == "left":
        return slot - 4 if slot >= 4 else slot
    if direction == "right":
        return slot + 4 if slot + 4 < 12 else slot
    raise ValueError(direction)
