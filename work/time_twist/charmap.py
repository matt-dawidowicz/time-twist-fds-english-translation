"""Recovered character map for Time Twist's packed scenario text."""

from __future__ import annotations


# Common values are written as tile $C0 + value by NOV2.  Only 0-47 are
# representable by the common prefix; 46/47 are remapped to punctuation tiles.
COMMON_KANA = tuple(
    "あいうえおかきくけこ"
    "さしすせそたちつてと"
    "なにぬねのはひふへほ"
    "まみむめもやゆよらり"
    "るれろわをん"
)


def decode_common(value: int) -> str:
    if 0 <= value < len(COMMON_KANA):
        return COMMON_KANA[value]
    if value == 46:
        return "、"
    if value == 47:
        return "。"
    return f"{{COMMON:{value}}}"


_DAKUTEN = {
    5: "が",
    6: "ぎ",
    7: "ぐ",
    8: "げ",
    9: "ご",
    10: "ざ",
    11: "じ",
    12: "ず",
    13: "ぜ",
    14: "ぞ",
    15: "だ",
    16: "ぢ",
    17: "づ",
    18: "で",
    19: "ど",
    25: "ば",
    26: "び",
    27: "ぶ",
    28: "べ",
    29: "ぼ",
}

_HANDAKUTEN = {
    32: "ぱ",
    33: "ぴ",
    34: "ぷ",
    35: "ぺ",
    36: "ぽ",
}

_EXTENDED_GLYPHS = {
    1: "・",
    2: '"',
    37: "ぁ",
    38: "ぃ",
    39: "ぅ",
    40: "ぇ",
    41: "ぉ",
    42: "っ",
    43: "ゃ",
    44: "ゅ",
    45: "ょ",
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
    56: "ー",
    57: "／",
    58: "！",
    59: "」",
    60: "「",
    61: "…",
    62: "？",
    63: " ",
}


def decode_extended(value: int) -> str:
    if value in _DAKUTEN:
        return _DAKUTEN[value]
    if value in _HANDAKUTEN:
        return _HANDAKUTEN[value]
    if value in _EXTENDED_GLYPHS:
        return _EXTENDED_GLYPHS[value]
    return f"{{EXT:{value}}}"
