"""Generate and install the translated 8x8 dialogue font in NOV4.

The game expands inverse one-bit glyph rows stored in NOV4.  Each deterministic
5x7 pattern is inset one pixel inside an 8x8 tile, avoiding desktop-font
antialiasing and ensuring the same binary output on every machine.

Tile IDs are derived from the common/extended runtime lookup tables used by
the packed text renderer.  Updating a character map therefore also requires a
matching glyph and regression coverage here.
"""

from __future__ import annotations

from .english import COMMON_CHARACTERS, EXTENDED_CHARACTERS


NOV4_FONT_BASE_OFFSET = 0x1B7D

# A deterministic 5x7 pixel alphabet.  The previous milestone rasterized an
# antialiased desktop font at only eight pixels high, leaving broken diagonals
# and one-pixel fragments on real game screens.  Uppercase and lowercase codes
# have distinct glyphs so dialogue can use natural mixed case while menu and
# disk-change strings remain deliberately uppercase.
PIXEL_FONT_5X7 = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "10110", "11001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10001", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01101", "10011", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "é": (
        "00100",
        "00010",
        "01110",
        "10001",
        "11111",
        "10000",
        "01110",
    ),
    "f": ("00110", "01001", "01000", "11100", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "10110", "11001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "10010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "10110", "11001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "11110", "10001", "10001", "11110", "10000", "10000"),
    "q": ("00000", "01111", "10001", "10001", "01111", "00001", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01001", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10001", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "10001", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ",": ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    "'": ("00100", "00100", "00010", "00000", "00000", "00000", "00000"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
}

# Runtime tile IDs used by extended codes 37-63.  These are NOV2's original
# lookup-table values at $835E-$8378; retaining them also retains the original
# digit and punctuation semantics for non-scenario displays.
EXTENDED_TILE_IDS = {
    37: 0xF2,
    38: 0xF3,
    39: 0xF4,
    40: 0xF5,
    41: 0xF6,
    42: 0xF7,
    43: 0xF8,
    44: 0xF9,
    45: 0xFA,
    46: 0xB6,
    47: 0xB7,
    48: 0xB8,
    49: 0xB9,
    50: 0xBA,
    51: 0xBB,
    52: 0xBC,
    53: 0xBD,
    54: 0xBE,
    55: 0xBF,
    56: 0xFB,
    57: 0xFC,
    58: 0xFD,
    59: 0xB3,
    60: 0xB2,
    61: 0xB4,
    62: 0xFE,
    63: 0xAC,
}


class FontPatchError(ValueError):
    """Raised when a NOV4 font patch cannot be applied safely."""


def common_tile_id(value: int) -> int:
    """Map a common packed value to the tile selected by NOV2."""

    if 0 <= value <= 45:
        return 0xC0 + value
    if value == 46:
        return 0xF0
    if value == 47:
        return 0xF1
    raise FontPatchError(f"common code {value} has no runtime tile")


def render_glyph(char: str) -> bytes:
    """Render one crisp glyph in the inverse 1bpp format expanded by NOV4.

    A blank stored row is ``$FF``.  Every ``1`` in the human-readable 5x7
    pattern clears the corresponding stored bit, producing an ink pixel when
    NOV4 expands the table into NES CHR.
    """

    if len(char) != 1:
        raise FontPatchError(f"expected one character, got {char!r}")
    if char == " ":
        return b"\xFF" * 8
    key = char
    try:
        pattern = PIXEL_FONT_5X7[key]
    except KeyError as error:
        raise FontPatchError(f"pixel font has no glyph for {char!r}") from error
    rows = bytearray(b"\xFF" * 8)
    for y, source_row in enumerate(pattern):
        for x, pixel in enumerate(source_row, start=1):
            if pixel == "1":
                rows[y] &= ~(1 << (7 - x))
    return bytes(rows)


def patched_nov4_font(
    data: bytes,
) -> bytes:
    """Return a size-identical NOV4 with every translated glyph installed.

    Only recovered font-table rows are changed.  A short/unknown NOV4 is
    rejected instead of being partially patched.
    """

    if len(data) < NOV4_FONT_BASE_OFFSET + (0xFE + 1) * 8:
        raise FontPatchError("NOV4 is too short for its recovered font table")
    result = bytearray(data)

    tile_characters: dict[int, str] = {}
    for value, char in enumerate(COMMON_CHARACTERS):
        tile_characters[common_tile_id(value)] = char
    for value, char in EXTENDED_CHARACTERS.items():
        tile_characters[EXTENDED_TILE_IDS[value]] = char

    for tile_id, char in tile_characters.items():
        offset = NOV4_FONT_BASE_OFFSET + tile_id * 8
        result[offset : offset + 8] = render_glyph(char)
    return bytes(result)
