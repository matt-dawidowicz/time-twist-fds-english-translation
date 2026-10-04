"""Final-layer 12-month Fortune Teller selector for the English release.

The retail TT1A birth-month UI uses a seven-choice Jan-Jun/Jul-Dec menu whose
Jul-Dec entry opens a second six-choice menu.  The English release intentionally
flattens that presentation into one 4x3 Jan-Dec menu.  Birth month remains
mechanically irrelevant to the personality result; this module changes only
selection presentation and the shared NOV2 geometry needed for 9-12 choices.

The geometry is recovered from the runtime-tested September v4/v5 implementation,
adapted to coexist with the later parent-menu Back/Cancel guard.
"""

from __future__ import annotations


class MonthMenuPatchError(ValueError):
    """Raised when the expected candidate/runtime bytes have drifted."""


NOV2_LOAD_ADDRESS = 0x6000
TT1A_LOAD_ADDRESS = 0xA200
MONTH_LABELS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
MONTH_DESCRIPTOR = (5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17)
MONTH_GRID = (
    ("Jan", "May", "Sep"),
    ("Feb", "Jun", "Oct"),
    ("Mar", "Jul", "Nov"),
    ("Apr", "Aug", "Dec"),
)

_NATIVE_DESCRIPTOR_BYTES = bytes.fromhex(
    "04 01 02 03 04 07 05 06 07 08 09 0A 0B "
    "06 0C 0D 0E 0F 10 11 02 12 13"
)
_FLAT_DESCRIPTOR_BYTES = bytes.fromhex(
    "04 01 02 03 04 0C 05 06 07 08 09 0A 0C "
    "0D 0E 0F 10 11 01 0B 02 12 13"
)
_PARENT_TRAMPOLINE_BEFORE = bytes.fromhex("4C 4A 81 BB 6B EA")
_PARENT_TRAMPOLINE_AFTER = bytes.fromhex("84 9C 4C BB 6B EA")
_CURSOR_REDIRECT_BEFORE = bytes.fromhex(
    "A4 32 C0 04 90 0A 98 29 03 A8 AD 3B 04 69 2F 60 A9 20 60"
)
_CURSOR_REDIRECT_AFTER = bytes.fromhex("4C EC 88") + bytes([0xEA]) * 16
_CURSOR_CONSTANTS = bytes.fromhex("A9 20 60 20 68 B0 EA")
_THREE_COLUMN_CURSOR_HELPER_BEFORE = bytes.fromhex(
    "84 9C 4C BB 6B EA EA EA EA EA"
)
_THREE_COLUMN_CURSOR_HELPER_AFTER = bytes.fromhex(
    "98 4A 4A A8 B9 A7 88 60 EA EA"
)
_THREE_COLUMN_TEXT_HELPER_BEFORE = bytes([0xEA]) * 11
_THREE_COLUMN_TEXT_HELPER_AFTER = bytes.fromhex(
    "E0 08 A9 4E 90 02 A9 57 4C AE 94"
)
_CURSOR_DISPATCH_BEFORE = bytes.fromhex(
    "A4 32 C0 04 90 B2 AD 20 04 C9 09 90 03 4C 4A 81 "
    "98 29 03 A8 AD 3B 04 69 30 60"
)
_CURSOR_DISPATCH_AFTER = bytes.fromhex(
    "A4 32 C0 04 90 B2 AD 20 04 C9 09 90 03 4C 1B 82 "
    "98 29 03 A8 B9 33 04 69 28 60"
)
_RENDERER_BEFORE = bytes.fromhex(
    "8A C9 04 90 0D 29 03 A8 AD 3B 04 4A 4A 4A 69 47 D0 02 A9 45 "
    "65 3C 85 3C A9 22 65 3D 85 3D BD 2D 04 4A 4A 4A D0 02 A9 06 "
    "85 31 A2 00 EA EA EA EA EA EA"
)
_RENDERER_AFTER = bytes.fromhex(
    "8A C9 04 90 17 A5 91 C9 09 90 03 4C 1B 82 8A 29 03 A8 "
    "B9 33 04 4A 4A 4A 69 46 D0 02 A9 45 65 3C 85 3C A9 22 "
    "65 3D 85 3D BD 33 04 4A 4A 4A 85 31 A2 00"
)
_TRAILING_ARROW_HELPER = bytes.fromhex(
    "20 37 81 48 A5 A8 C9 08 68 90 03 18 69 08 60"
)


def _guarded(
    data: bytearray,
    *,
    load_address: int,
    cpu_address: int,
    expected: bytes,
    replacement: bytes,
    label: str,
) -> None:
    """Apply one size-neutral patch only to its known source bytes."""
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
    """Flatten TT1A's retail two-stage month selector into 12 real choices."""
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
    """Restore the runtime-tested 9-12-choice 4x3 NOV2 menu geometry."""
    result = bytearray(data)
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6DE8,
        expected=bytes.fromhex("99 2D 04"),
        replacement=bytes.fromhex("99 33 04"),
        label="relocate menu-width recorder",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x813B,
        expected=bytes.fromhex("B9 2D 04"),
        replacement=bytes.fromhex("B9 33 04"),
        label="relocate trailing-width lookup",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6D8D,
        expected=_CURSOR_REDIRECT_BEFORE,
        replacement=_CURSOR_REDIRECT_AFTER,
        label="route cursor-X through 2/3-column dispatcher",
    )
    constants = 0x88A4 - NOV2_LOAD_ADDRESS
    if bytes(result[constants : constants + 7]) != _CURSOR_CONSTANTS:
        raise MonthMenuPatchError("NOV2 three-column cursor constants drifted")

    # v63 reached the five-byte parent Back guard through an otherwise redundant
    # trampoline. Inline the same semantics there so the historical $814A cave
    # can again host the 3-column cursor helper.
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6B70,
        expected=_PARENT_TRAMPOLINE_BEFORE,
        replacement=_PARENT_TRAMPOLINE_AFTER,
        label="inline parent Back guard",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x814A,
        expected=_THREE_COLUMN_CURSOR_HELPER_BEFORE,
        replacement=_THREE_COLUMN_CURSOR_HELPER_AFTER,
        label="install three-column leading-cursor helper",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x821B,
        expected=_THREE_COLUMN_TEXT_HELPER_BEFORE,
        replacement=_THREE_COLUMN_TEXT_HELPER_AFTER,
        label="install three-column text helper",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x88EC,
        expected=_CURSOR_DISPATCH_BEFORE,
        replacement=_CURSOR_DISPATCH_AFTER,
        label="install two/three-column cursor dispatcher",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x9490,
        expected=_RENDERER_BEFORE,
        replacement=_RENDERER_AFTER,
        label="install 4x3 text renderer path",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x6D90,
        expected=bytes([0xEA]) * len(_TRAILING_ARROW_HELPER),
        replacement=_TRAILING_ARROW_HELPER,
        label="install third-column trailing-arrow correction",
    )
    _guarded(
        result,
        load_address=NOV2_LOAD_ADDRESS,
        cpu_address=0x989F,
        expected=bytes.fromhex("20 37 81"),
        replacement=bytes.fromhex("20 90 6D"),
        label="route trailing cursor through v5 wrapper",
    )

    patched = bytes(result)
    for pattern in (
        "B9 2D 04",
        "BD 2D 04",
        "99 2D 04",
        "9D 2D 04",
        "AD 3B 04",
    ):
        if bytes.fromhex(pattern) in patched:
            raise MonthMenuPatchError(
                f"stale menu-width reference remains: {pattern}"
            )
    relocated = sum(
        patched.count(bytes.fromhex(pattern))
        for pattern in ("B9 33 04", "BD 33 04", "99 33 04", "9D 33 04")
    )
    if relocated != 5:
        raise MonthMenuPatchError(
            f"expected five indexed $0433 width references, found {relocated}"
        )

    guard = 0x6B70 - NOV2_LOAD_ADDRESS
    if bytes(patched[guard : guard + 5]) != bytes.fromhex(
        "84 9C 4C BB 6B"
    ):
        raise MonthMenuPatchError("parent Back guard semantics were damaged")
    return patched


def twelve_month_navigation(slot: int, direction: str) -> int:
    """Return the 4x3 grid destination for one directional input."""
    if not 0 <= slot < 12:
        raise ValueError(slot)
    if direction == "up":
        return (slot & ~3) | ((slot - 1) & 3)
    if direction == "down":
        return (slot & ~3) | ((slot + 1) & 3)
    if direction == "left":
        return slot - 4 if slot >= 4 else slot
    if direction == "right":
        return slot + 4 if slot + 4 < 12 else slot
    raise ValueError(direction)
