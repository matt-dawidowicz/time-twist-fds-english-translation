"""Encode and validate English text for Time Twist's native renderer.

Visible text is represented with the game's common/extended packed symbols.
Structural controls are written in JSON as ``{CTRL:n}`` and become native
seven-bit control symbols.  The module also enforces the 24-tile dialogue-row
limit that prevents wrapped characters from being overwritten by the next
control transition.

This is the patch-facing character map.  The Japanese decode-only map lives in
:mod:`time_twist.charmap`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .textcodec import PackedSymbol, SymbolKind

# Common codes cost six bits.  They contain space, every lowercase letter,
# the 19 most frequent uppercase letters, and the two most common marks.
COMMON_CHARACTERS = " " "etaoinshrdlucmfwypvbgkjqxz" "ETAOINSHRDLUCMFWYPV" ",."

# Extended codes 37-63 cost nine bits and use the engine's existing lookup
# table.  Keeping digits and punctuation on their original tile IDs avoids
# disrupting hard-coded numeric and punctuation displays elsewhere.
EXTENDED_CHARACTERS: dict[int, str] = {
    37: "B",
    38: "G",
    39: "K",
    40: "Q",
    41: "J",
    42: "X",
    43: "Z",
    # Code 44 previously held an unused opening parenthesis in the English
    # map.  The current script needs an accented e for "consommé", while no
    # translated record uses parentheses.  Reusing the same existing lookup
    # slot keeps NOV2's table and every loaded file exactly the same size.
    44: "é",
    45: ")",
    46: "1",
    47: "2",
    48: "3",
    49: "4",
    50: "5",
    51: "6",
    52: "7",
    53: "8",
    54: "9",
    55: "0",
    56: "-",
    57: "/",
    58: "!",
    59: '"',
    60: "'",
    61: ":",
    62: "?",
    63: " ",
}

CONTROL_PATTERN = re.compile(r"\{CTRL:([0-7])\}")
DISPLAY_COLUMNS = 24


class EnglishTextError(ValueError):
    """Report English text that the native font or renderer cannot use safely.

    This error identifies unsupported characters, malformed control syntax, or
    display-width violations discovered before bytes are inserted into a bank.
    Callers should revise the translation or control layout rather than suppress
    the exception, because replacement characters would conceal ROM corruption.
    """


def _character_symbols() -> dict[str, PackedSymbol]:
    """Build the canonical visible-character-to-symbol map.

    Returns:
        A new mapping for every character supported by the English font.

    Common codes are installed first because they cost six bits. Extended
    duplicates, currently only space, use :meth:`dict.setdefault` and cannot
    replace the cheaper representation.
    """
    result = {
        char: PackedSymbol(SymbolKind.COMMON, value, 0, 0)
        for value, char in enumerate(COMMON_CHARACTERS)
    }
    for value, char in EXTENDED_CHARACTERS.items():
        # Space intentionally uses the shorter common code.
        result.setdefault(char, PackedSymbol(SymbolKind.EXTENDED, value, 0, 0))
    return result


CHARACTER_SYMBOLS = _character_symbols()


def encode_english(text: str) -> tuple[PackedSymbol, ...]:
    """Encode supported dialogue characters plus explicit ``{CTRL:n}`` tags.

    Args:
        text: Patch-facing English containing only supported glyphs and
            complete ``{CTRL:0}`` through ``{CTRL:7}`` tags.

    Returns:
        An immutable symbol tuple suitable for compression or packing.

    Raises:
        EnglishTextError: If a tag is malformed, a visible character is not in
            the English font, or control 5 is used inside a record.

    Control 5 is rejected because the packed-text codec owns it as the
    byte-aligned record separator. Unsupported characters and malformed tags
    fail with their character position so translation JSON can be corrected
    before any ROM is rebuilt.
    """
    symbols: list[PackedSymbol] = []
    position = 0
    while position < len(text):
        if text[position] == "{":
            match = CONTROL_PATTERN.match(text, position)
            if not match:
                raise EnglishTextError(
                    f"invalid tag at character {position}: {text[position:position + 16]!r}"
                )
            value = int(match.group(1))
            if value == 5:
                raise EnglishTextError(
                    "control 5 is reserved for record separators"
                )
            symbols.append(PackedSymbol(SymbolKind.CONTROL, value, 0, 0))
            position = match.end()
            continue
        char = text[position]
        try:
            symbols.append(CHARACTER_SYMBOLS[char])
        except KeyError as error:
            raise EnglishTextError(
                f"unsupported English character {char!r} at character {position}"
            ) from error
        position += 1
    return tuple(symbols)


def render_english(symbols: Iterable[PackedSymbol]) -> str:
    """Render English symbols and diagnostic tokens for verification.

    Args:
        symbols: Ordered native symbols, normally produced by
            :func:`encode_english` or dictionary expansion.

    Returns:
        Visible English plus explicit control tags. Unknown symbol/value pairs
        remain visible as diagnostic tokens rather than being discarded.

    This function does not expand dictionary references. Call
    :func:`time_twist.compression.expand_dictionary_symbols` first when
    verifying compressed scenario text.
    """
    common = {value: char for value, char in enumerate(COMMON_CHARACTERS)}
    rendered: list[str] = []
    for symbol in symbols:
        if symbol.kind is SymbolKind.COMMON and symbol.value in common:
            rendered.append(common[symbol.value])
        elif (
            symbol.kind is SymbolKind.EXTENDED
            and symbol.value in EXTENDED_CHARACTERS
        ):
            rendered.append(EXTENDED_CHARACTERS[symbol.value])
        elif symbol.kind is SymbolKind.CONTROL:
            rendered.append(f"{{CTRL:{symbol.value}}}")
        else:
            rendered.append(f"{{{symbol.kind.value.upper()}:{symbol.value}}}")
    return "".join(rendered)


def control_values(text: str) -> tuple[int, ...]:
    """Extract recognized control values in textual order.

    Args:
        text: Source or translated text containing explicit control tags.

    Returns:
        An immutable tuple of integer control values. Malformed text outside
        recognized tags is ignored; full validation belongs to
        :func:`encode_english`.
    """
    return tuple(
        int(match.group(1)) for match in CONTROL_PATTERN.finditer(text)
    )


def validate_display_width(
    text: str,
    columns: int = DISPLAY_COLUMNS,
    *,
    allow_wrap: bool = False,
) -> None:
    """Validate text chunks against the renderer's fixed row width.

    Args:
        text: English text with optional control tags.
        columns: Visible tile width of one renderer row.
        allow_wrap: Permit segments longer than one row only when every
            automatic wrap lands on safe word-padding boundaries.

    Raises:
        EnglishTextError: If a segment exceeds ``columns`` when wrapping is
            disabled, or if an enabled wrap would split a word or begin the
            next row with padding.

    Time Twist's dialogue row is 24 tiles wide. A chunk that overruns it is
    automatically wrapped by the renderer, but the following control code can
    immediately reuse that row and overwrite the wrapped characters. Selected
    records may intentionally wrap when padding places every new word exactly
    at a row boundary.

    The function performs validation only and has no side effects. Control
    tags delimit independently measured display segments and do not consume
    columns.
    """
    start = 0
    segment = 0
    for match in (*CONTROL_PATTERN.finditer(text), None):
        end = len(text) if match is None else match.start()
        chunk = text[start:end]
        width = len(chunk)
        if width > columns:
            if not allow_wrap:
                raise EnglishTextError(
                    f"segment {segment} is {width} columns; maximum is {columns}"
                )
            for boundary in range(columns, width, columns):
                if chunk[boundary - 1] != " " or chunk[boundary] == " ":
                    raise EnglishTextError(
                        f"segment {segment} has an unsafe wrap at column {boundary}"
                    )
        if match is not None:
            start = match.end()
            segment += 1
