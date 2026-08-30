"""Decode and align an external Time Twist English patch for comparison only.

This module is deliberately separate from the production scenario parser. It
models quirks observed in a public third-party patch so maintainers can compare
translations record-by-record without weakening native format invariants or
copying third-party script text into the repository.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SIDE_SIZE = 65_500
LOAD_ADDRESS = 0xA200
PATCH_GAP = 5
MAX_SYMBOLS_PER_RECORD = 4096

# Recovered third-party common table. Entries are packed-code values, not tile
# IDs.
COMMON = (
    " ", "e", "o", "a", "t", ".", "n", "i", "r", "h", "s", "l", "d", "u", "m", ":",
    "y", "g", "c", "w", "p", "f", "!", ",", "b", "M", "k", "T", "v", "'", "A", "?",
    "I", "S", "G", "H", "W", "D", "N", "B", "C", "-", "O", "J", "P", "R", "E", "Y",
)

# The patch uses some extended codes as multi-character output tokens.
EXTENDED = {
    1: "j", 2: "F", 32: "s", 33: "ac", 34: "I ", 35: "Me", 36: "'", 37: "x",
    38: "z", 39: "q", 40: ";", 41: "V", 42: "Q", 43: '"', 44: "Z", 46: "1",
    47: "2", 48: "3", 49: "4", 50: "5", 51: "6", 52: "7", 53: "8", 54: "9",
    55: "0", 59: "K", 60: "L", 61: "U", 63: " ",
}


@dataclass(frozen=True)
class Symbol:
    """Represent one decoded third-party packed-text token."""

    kind: str
    value: int


class BitReader:
    """Read third-party packed text most-significant bit first."""

    def __init__(self, data: bytes, bit_position: int = 0) -> None:
        """Initialize a bounded reader over ``data``."""
        if bit_position < 0 or bit_position > len(data) * 8:
            raise ValueError("bit position is outside the stream")
        self.data = data
        self.bit_position = bit_position

    def read_bit(self) -> int:
        """Return the next packed bit and advance one position."""
        if self.bit_position >= len(self.data) * 8:
            raise EOFError("packed stream ended")
        byte_index, bit_index = divmod(self.bit_position, 8)
        self.bit_position += 1
        return (self.data[byte_index] >> (7 - bit_index)) & 1

    def read_bits(self, count: int) -> int:
        """Return ``count`` packed bits as one unsigned integer."""
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value

    def align(self) -> None:
        """Advance to the next byte boundary after a separator."""
        self.bit_position = (self.bit_position + 7) // 8 * 8

    @property
    def byte_position(self) -> int:
        """Return the byte containing the next unread bit."""
        return self.bit_position // 8


def decode_symbol(reader: BitReader) -> Symbol:
    """Decode one symbol using third-party NOV2 prefix-tree behavior."""
    first = reader.read_bit()
    second = reader.read_bit()
    if first == 0 or second == 0:
        value = (first << 5) | (second << 4) | reader.read_bits(4)
        return Symbol("common", value)
    third = reader.read_bit()
    if third == 0:
        value = reader.read_bits(6)
        if 4 <= value <= 31:
            return Symbol("dictionary", value + 28)
        return Symbol("extended", value)
    fourth = reader.read_bit()
    if fourth == 0:
        return Symbol("dictionary", reader.read_bits(5))
    value = reader.read_bits(3)
    if value == 5:
        return Symbol("separator", value)
    return Symbol("control", value)


def decode_fixed_records(
    data: bytes, offset: int, count: int
) -> tuple[list[list[Symbol]], int]:
    """Decode exactly ``count`` records beginning at byte ``offset``."""
    if offset < 0 or offset >= len(data):
        raise ValueError(f"record offset outside bank: {offset}")
    reader = BitReader(data, offset * 8)
    records: list[list[Symbol]] = []
    for record_index in range(count):
        record: list[Symbol] = []
        for _ in range(MAX_SYMBOLS_PER_RECORD):
            symbol = decode_symbol(reader)
            if symbol.kind == "separator":
                reader.align()
                break
            record.append(symbol)
        else:
            message = f"record {record_index} exceeded symbol limit"
            raise ValueError(message)
        records.append(record)
    return records, reader.byte_position


def decode_external_bank(
    data: bytes, group_counts: Iterable[int]
) -> tuple[list[list[list[Symbol]]], list[list[Symbol]]]:
    """Decode external groups using source record counts as truth."""
    counts = list(group_counts)
    if not counts:
        raise ValueError("at least one source group count is required")

    def word(offset: int) -> int:
        """Read one bounded little-endian pointer from the external bank."""
        if offset < 0 or offset + 2 > len(data):
            raise ValueError(f"pointer read outside bank: {offset}")
        return int.from_bytes(data[offset : offset + 2], "little")

    dictionary_offset = word(0x16) - LOAD_ADDRESS
    table_offset = word(0x24) - LOAD_ADDRESS
    if not 0 <= dictionary_offset < len(data):
        message = f"dictionary pointer outside bank: {dictionary_offset}"
        raise ValueError(message)
    if not 0 <= table_offset < len(data):
        raise ValueError(f"group table pointer outside bank: {table_offset}")

    addresses = [word(0x26)]
    addresses.extend(
        word(table_offset + index * 2) for index in range(len(counts) - 1)
    )

    groups: list[list[list[Symbol]]] = []
    for address, count in zip(addresses, counts, strict=True):
        offset = address - LOAD_ADDRESS
        records, _ = decode_fixed_records(data, offset, count)
        groups.append(records)

    max_dictionary_index = max(
        (
            symbol.value
            for group in groups
            for record in group
            for symbol in record
            if symbol.kind == "dictionary"
        ),
        default=0,
    )
    if max_dictionary_index == 0:
        return groups, []
    if max_dictionary_index > 59:
        message = f"unsupported dictionary index: {max_dictionary_index}"
        raise ValueError(message)

    dictionary, _ = decode_fixed_records(
        data, dictionary_offset, max_dictionary_index
    )
    nested_max = max(
        (
            symbol.value
            for record in dictionary
            for symbol in record
            if symbol.kind == "dictionary"
        ),
        default=0,
    )
    if nested_max > len(dictionary):
        if nested_max > 59:
            raise ValueError(
                f"unsupported nested dictionary index: {nested_max}"
            )
        dictionary, _ = decode_fixed_records(
            data, dictionary_offset, nested_max
        )
    return groups, dictionary


def render_record(
    record: list[Symbol],
    dictionary: list[list[Symbol]],
    *,
    stack: tuple[int, ...] = (),
) -> str:
    """Render one external record without discarding unknown tokens."""
    rendered: list[str] = []
    for symbol in record:
        if symbol.kind == "common":
            try:
                rendered.append(COMMON[symbol.value])
            except IndexError as error:
                message = f"unknown common code: {symbol.value}"
                raise ValueError(message) from error
        elif symbol.kind == "extended":
            token = EXTENDED.get(symbol.value, f"<E{symbol.value}>")
            rendered.append(token)
        elif symbol.kind == "control":
            rendered.append(f"{{CTRL:{symbol.value}}}")
        elif symbol.kind == "dictionary":
            index = symbol.value - 1
            if not 0 <= index < len(dictionary):
                rendered.append(f"<D{symbol.value}>")
                continue
            if index in stack:
                message = f"recursive dictionary reference: {symbol.value}"
                raise ValueError(message)
            expanded = render_record(
                dictionary[index], dictionary, stack=(*stack, index)
            )
            rendered.append(expanded)
        else:
            message = f"unexpected symbol kind in record: {symbol.kind}"
            raise ValueError(message)
    return "".join(rendered)


def patch_spans(
    payload: bytes, *, max_gap: int = PATCH_GAP
) -> list[tuple[int, int]]:
    """Infer coalesced write spans from a sparse absolute-offset payload.

    The observed patch writer coalesces non-zero changed bytes when no more
    than five bytes lie between them. Returning full spans preserves
    intentional zero writes inside each hunk.
    """
    nonzero = [index for index, value in enumerate(payload) if value]
    if not nonzero:
        return []
    spans: list[tuple[int, int]] = []
    start = previous = nonzero[0]
    for index in nonzero[1:]:
        if index - previous - 1 <= max_gap:
            previous = index
            continue
        spans.append((start, previous + 1))
        start = previous = index
    spans.append((start, previous + 1))
    return spans


def overlay_sparse_payload(
    base: bytes, payload: bytes, *, max_gap: int = PATCH_GAP
) -> bytes:
    """Overlay inferred external patch hunks onto a clean base."""
    if len(payload) > len(base):
        raise ValueError("payload is larger than reconstruction base")
    rebuilt = bytearray(base)
    for start, end in patch_spans(payload, max_gap=max_gap):
        rebuilt[start:end] = payload[start:end]
    return bytes(rebuilt)


def extract_raw_fds_file(path: Path, name: str) -> bytes:
    """Return one named file from a raw side-aligned FDS image."""
    raw = path.read_bytes()
    if len(raw) < SIDE_SIZE or len(raw) % SIDE_SIZE:
        raise ValueError(f"not a raw side-aligned FDS image: {path}")
    for side_index in range(len(raw) // SIDE_SIZE):
        start = side_index * SIDE_SIZE
        side = raw[start : start + SIDE_SIZE]
        if side[0] != 1 or side[56] != 2:
            continue
        position = 58
        for _ in range(side[57]):
            header = side[position : position + 16]
            if len(header) != 16 or header[0] != 3:
                message = (
                    f"invalid file header on side {side_index} at "
                    f"{position}"
                )
                raise ValueError(message)
            file_name = header[3:11].decode("ascii", "replace")
            file_name = file_name.rstrip("\0 ")
            size = int.from_bytes(header[13:15], "little")
            position += 16
            if position >= len(side) or side[position] != 4:
                message = (
                    f"missing data block on side {side_index} at "
                    f"{position}"
                )
                raise ValueError(message)
            start = position + 1
            data = side[start : start + size]
            position += 1 + size
            if file_name == name:
                return data
    raise KeyError(name)
