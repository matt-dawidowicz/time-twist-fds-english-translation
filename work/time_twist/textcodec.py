"""Decoder primitives for Time Twist's packed scenario text.

The routines at $80B1/$815E in NOV2 read the stream most-significant bit
first.  This module deliberately models the on-disk symbols before assigning
Japanese characters to them; keeping those two concerns separate makes the
binary parser testable while the character map is still being recovered.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SymbolKind(str, Enum):
    """Kinds selected by the native packed-text prefix tree."""

    COMMON = "common"
    EXTENDED = "extended"
    DICTIONARY = "dictionary"
    CONTROL = "control"
    SEPARATOR = "separator"


@dataclass(frozen=True)
class PackedSymbol:
    """One decoded or to-be-encoded native text token.

    ``start_bit`` and ``end_bit`` retain source positions during decoding.
    Encoders construct symbols with zero positions; the final writer assigns
    physical positions implicitly as it emits the stream.
    """

    kind: SymbolKind
    value: int
    start_bit: int
    end_bit: int


class PackedTextError(ValueError):
    """Raised when a packed-text stream ends in the middle of a symbol."""


class BitReader:
    """Read an MSB-first bitstream and expose its absolute bit position."""

    def __init__(self, data: bytes, bit_position: int = 0) -> None:
        if bit_position < 0 or bit_position > len(data) * 8:
            raise ValueError("bit position is outside the stream")
        self.data = data
        self.bit_position = bit_position

    @property
    def byte_position(self) -> int:
        """Current whole-byte offset (floor of the absolute bit position)."""

        return self.bit_position // 8

    @property
    def at_byte_boundary(self) -> bool:
        """Whether the next bit begins a new byte."""

        return self.bit_position % 8 == 0

    def read_bit(self) -> int:
        """Read one bit, advancing from bit 7 toward bit 0 in each byte."""

        if self.bit_position >= len(self.data) * 8:
            raise PackedTextError("unexpected end of packed-text stream")
        byte_index, within_byte = divmod(self.bit_position, 8)
        self.bit_position += 1
        return (self.data[byte_index] >> (7 - within_byte)) & 1

    def read_bits(self, count: int) -> int:
        """Read ``count`` bits as one big-endian integer."""

        if count < 0:
            raise ValueError("bit count cannot be negative")
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value

    def align_to_next_byte(self) -> None:
        """Discard unread padding bits in the current record-separator byte."""

        remainder = self.bit_position % 8
        if remainder:
            self.bit_position += 8 - remainder


class BitWriter:
    """Write the packed text stream most-significant bit first."""

    def __init__(self) -> None:
        self._bytes = bytearray()
        self.bit_position = 0

    def write_bits(self, value: int, count: int) -> None:
        """Write ``value`` in exactly ``count`` bits, most-significant first."""

        if count < 0 or value < 0 or value >= (1 << count):
            raise ValueError(f"value {value} does not fit in {count} bits")
        for shift in range(count - 1, -1, -1):
            byte_index, within_byte = divmod(self.bit_position, 8)
            if byte_index == len(self._bytes):
                self._bytes.append(0)
            self._bytes[byte_index] |= ((value >> shift) & 1) << (7 - within_byte)
            self.bit_position += 1

    def align_to_next_byte(self) -> None:
        """Leave the rest of the current byte as zero padding."""

        remainder = self.bit_position % 8
        if remainder:
            self.bit_position += 8 - remainder

    def to_bytes(self) -> bytes:
        """Return an immutable copy of the emitted bytes."""

        return bytes(self._bytes)


def decode_symbol(reader: BitReader) -> PackedSymbol:
    """Decode one symbol exactly as the NOV2 prefix tree does.

    Prefix layout::

        0xxxxx / 10xxxx   common glyph (six bits total)
        110xxxxxx         extended glyph
        1110xxxxx         dictionary entry
        1111xxx           control code

    Control value 5 is the byte-aligned record separator used by the engine's
    text lookup routine.
    """

    start = reader.bit_position
    first = reader.read_bit()
    second = reader.read_bit()
    if first == 0 or second == 0:
        value = (first << 5) | (second << 4) | reader.read_bits(4)
        kind = SymbolKind.COMMON
    else:
        third = reader.read_bit()
        if third == 0:
            kind = SymbolKind.EXTENDED
            value = reader.read_bits(6)
        else:
            fourth = reader.read_bit()
            if fourth == 0:
                kind = SymbolKind.DICTIONARY
                value = reader.read_bits(5)
            else:
                value = reader.read_bits(3)
                kind = SymbolKind.SEPARATOR if value == 5 else SymbolKind.CONTROL
    return PackedSymbol(kind, value, start, reader.bit_position)


def encode_symbol(writer: BitWriter, symbol: PackedSymbol) -> None:
    """Encode one symbol using NOV2's native prefix tree."""

    if symbol.kind is SymbolKind.COMMON:
        if not 0 <= symbol.value <= 47:
            raise PackedTextError(f"common value {symbol.value} is out of range")
        writer.write_bits(symbol.value, 6)
    elif symbol.kind is SymbolKind.EXTENDED:
        if not 0 <= symbol.value <= 63:
            raise PackedTextError(f"extended value {symbol.value} is out of range")
        writer.write_bits(0b110, 3)
        writer.write_bits(symbol.value, 6)
    elif symbol.kind is SymbolKind.DICTIONARY:
        if not 0 <= symbol.value <= 31:
            raise PackedTextError(f"dictionary value {symbol.value} is out of range")
        writer.write_bits(0b1110, 4)
        writer.write_bits(symbol.value, 5)
    elif symbol.kind in (SymbolKind.CONTROL, SymbolKind.SEPARATOR):
        value = 5 if symbol.kind is SymbolKind.SEPARATOR else symbol.value
        if not 0 <= value <= 7:
            raise PackedTextError(f"control value {value} is out of range")
        if symbol.kind is SymbolKind.CONTROL and value == 5:
            raise PackedTextError("control value 5 is reserved for record separators")
        writer.write_bits(0b1111, 4)
        writer.write_bits(value, 3)
    else:
        raise PackedTextError(f"unsupported symbol kind {symbol.kind}")


def pack_records(records: list[tuple[PackedSymbol, ...]] | tuple[tuple[PackedSymbol, ...], ...]) -> bytes:
    """Pack records with control-5 separators and byte-aligned starts.

    Record payloads cannot contain a separator themselves.  The writer emits
    exactly one separator after each record and pads to the next byte exactly
    as the game's lookup routine does.
    """

    writer = BitWriter()
    separator = PackedSymbol(SymbolKind.SEPARATOR, 5, 0, 0)
    for record in records:
        for symbol in record:
            if symbol.kind is SymbolKind.SEPARATOR:
                raise PackedTextError("record payload cannot contain a separator")
            encode_symbol(writer, symbol)
        encode_symbol(writer, separator)
        writer.align_to_next_byte()
    return writer.to_bytes()


def split_records(
    data: bytes,
    *,
    offset: int = 0,
    limit: int = 32,
) -> tuple[list[list[PackedSymbol]], int]:
    """Split byte-aligned packed records at control-code 5 separators.

    Returns the decoded records and the byte offset immediately after the last
    separator.  This mirrors $8126-$8137, which discards the rest of the byte
    after a separator before beginning the next record.
    """

    if offset < 0 or offset > len(data):
        raise ValueError("record offset is outside the stream")
    reader = BitReader(data, offset * 8)
    records: list[list[PackedSymbol]] = []
    current: list[PackedSymbol] = []
    while len(records) < limit:
        symbol = decode_symbol(reader)
        if symbol.kind is SymbolKind.SEPARATOR:
            records.append(current)
            current = []
            reader.align_to_next_byte()
        else:
            current.append(symbol)
    return records, reader.byte_position
