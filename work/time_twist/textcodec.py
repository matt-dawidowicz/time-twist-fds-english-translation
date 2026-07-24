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
    """Identify the five token classes in the native prefix tree.

    The enum inherits from :class:`str` so extracted symbols serialize cleanly
    to JSON. ``SEPARATOR`` is represented separately from ``CONTROL`` even
    though both use the control-code branch; value 5 has record-boundary
    semantics and cannot appear inside a record.
    """

    COMMON = "common"
    EXTENDED = "extended"
    DICTIONARY = "dictionary"
    CONTROL = "control"
    SEPARATOR = "separator"


@dataclass(frozen=True)
class PackedSymbol:
    """One decoded or to-be-encoded native text token.

    Attributes:
        kind: Prefix-tree branch used to encode the token.
        value: Numeric payload within that branch.
        start_bit: Inclusive source bit offset recorded by the decoder.
        end_bit: Exclusive source bit offset recorded by the decoder.

    Encoders normally construct symbols with zero source positions. The writer
    determines physical positions from output order rather than modifying the
    frozen object.
    """

    kind: SymbolKind
    value: int
    start_bit: int
    end_bit: int


class PackedTextError(ValueError):
    """Report malformed, truncated, or unrepresentable packed text.

    Decoders raise this exception when a stream ends mid-symbol or contains an
    impossible code.  Encoders raise it when a symbol or record violates the
    packed format.  The shared type lets CLI callers reject unsafe data without
    confusing format failures with unrelated file-system errors.
    """


class BitReader:
    """Read an MSB-first bitstream while tracking an absolute bit position.

    The reader holds an immutable byte string and mutates only
    :attr:`bit_position`. It does not interpret symbols or validate padding;
    those responsibilities belong to the codec routines.
    """

    def __init__(self, data: bytes, bit_position: int = 0) -> None:
        """Initialize a reader at an absolute bit offset.

        Args:
            data: Complete byte stream to read.
            bit_position: Initial offset from the first byte's most-significant
                bit. The default begins at bit zero.

        Raises:
            ValueError: If ``bit_position`` lies outside ``data``.
        """

        if bit_position < 0 or bit_position > len(data) * 8:
            raise ValueError("bit position is outside the stream")
        self.data = data
        self.bit_position = bit_position

    @property
    def byte_position(self) -> int:
        """Return the byte containing the next unread bit.

        This is the floor of the absolute bit position. A reader at the end of
        a byte-aligned stream therefore returns ``len(data)``.
        """

        return self.bit_position // 8

    @property
    def at_byte_boundary(self) -> bool:
        """Return whether the next unread bit begins a byte."""

        return self.bit_position % 8 == 0

    def read_bit(self) -> int:
        """Read and return the next bit.

        Bits are consumed from bit 7 through bit 0 in each byte, matching the
        6502 decoder.

        Returns:
            The integer ``0`` or ``1``.

        Raises:
            PackedTextError: If no unread bit remains.

        Side Effects:
            Advances :attr:`bit_position` by one on success.
        """

        if self.bit_position >= len(self.data) * 8:
            raise PackedTextError("unexpected end of packed-text stream")
        byte_index, within_byte = divmod(self.bit_position, 8)
        self.bit_position += 1
        return (self.data[byte_index] >> (7 - within_byte)) & 1

    def read_bits(self, count: int) -> int:
        """Read several bits as one unsigned, big-endian integer.

        Args:
            count: Number of bits to consume. Zero returns zero.

        Returns:
            The accumulated integer value.

        Raises:
            ValueError: If ``count`` is negative.
            PackedTextError: If the requested range crosses the stream end.

        Side Effects:
            Advances :attr:`bit_position` by ``count`` on success.
        """

        if count < 0:
            raise ValueError("bit count cannot be negative")
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read_bit()
        return value

    def align_to_next_byte(self) -> None:
        """Advance past unread padding in the current byte.

        No padding-value check is performed because the original decoder also
        discards these bits after a record separator.
        """

        remainder = self.bit_position % 8
        if remainder:
            self.bit_position += 8 - remainder


class BitWriter:
    """Accumulate an MSB-first packed-text stream.

    Newly allocated bytes start at zero, so alignment leaves deterministic
    zero padding. The writer does not insert record separators automatically.
    """

    def __init__(self) -> None:
        """Create an empty writer positioned at bit zero.

        Side Effects:
            Initializes a private mutable byte buffer.  No external objects or
            files are modified.
        """

        self._bytes = bytearray()
        self.bit_position = 0

    def write_bits(self, value: int, count: int) -> None:
        """Append an unsigned value using an exact bit width.

        Args:
            value: Non-negative integer to encode.
            count: Exact number of bits to emit.

        Raises:
            ValueError: If ``count`` is negative or ``value`` cannot be
                represented in the requested width.

        Side Effects:
            Extends the internal byte buffer and advances ``bit_position``.
        """

        if count < 0 or value < 0 or value >= (1 << count):
            raise ValueError(f"value {value} does not fit in {count} bits")
        for shift in range(count - 1, -1, -1):
            byte_index, within_byte = divmod(self.bit_position, 8)
            if byte_index == len(self._bytes):
                self._bytes.append(0)
            self._bytes[byte_index] |= ((value >> shift) & 1) << (7 - within_byte)
            self.bit_position += 1

    def align_to_next_byte(self) -> None:
        """Advance to the next byte, retaining zero-valued padding bits.

        Side Effects:
            Resets the in-byte bit position to zero when the current output byte
            is partially filled.  The existing unused bits remain zero.
        """

        remainder = self.bit_position % 8
        if remainder:
            self.bit_position += 8 - remainder

    def to_bytes(self) -> bytes:
        """Return an immutable snapshot of the current output buffer.

        Returns:
            All bytes written so far, including the final partially filled byte
            and its zero-valued padding bits.
        """

        return bytes(self._bytes)


def decode_symbol(reader: BitReader) -> PackedSymbol:
    """Decode one symbol exactly as the NOV2 prefix tree does.

    Prefix layout::

        0xxxxx / 10xxxx   common glyph (six bits total)
        110xxxxxx         extended glyph
        1110xxxxx         dictionary entry
        1111xxx           control code

    Args:
        reader: Bit reader positioned at the first prefix bit.

    Returns:
        A symbol containing the decoded kind, payload, and exact source bit
        interval.

    Raises:
        PackedTextError: If the stream ends before the complete prefix or
            payload can be read.

    Side Effects:
        Advances ``reader`` by six, seven, or nine bits.

    Control value 5 is returned as :attr:`SymbolKind.SEPARATOR`; callers are
    responsible for applying the engine's following byte alignment.
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
    """Append one symbol using NOV2's native prefix tree.

    Args:
        writer: Destination bitstream.
        symbol: Token whose ``kind`` and ``value`` should be encoded. Source
            position fields are ignored.

    Raises:
        PackedTextError: If the kind is unsupported, a payload is outside its
            native range, or control value 5 is supplied as an ordinary
            control.

    Side Effects:
        Appends bits to ``writer``. It does not perform byte alignment after a
        separator.
    """

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


def pack_records(
    records: list[tuple[PackedSymbol, ...]]
    | tuple[tuple[PackedSymbol, ...], ...],
) -> bytes:
    """Pack records with control-5 separators and byte-aligned starts.

    Args:
        records: Ordered record payloads without separator tokens.

    Returns:
        Native packed bytes, including one separator and any alignment padding
        after every record.

    Raises:
        PackedTextError: If a payload contains a separator or any symbol is
            invalid for :func:`encode_symbol`.

    Record payloads cannot contain a separator themselves. The writer emits
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

    Args:
        data: Complete packed byte stream.
        offset: Byte offset of the first record.
        limit: Exact number of records to decode.

    Returns:
        A pair containing mutable symbol lists and the byte offset immediately
        after the final aligned separator.

    Raises:
        ValueError: If ``offset`` is outside ``data``.
        PackedTextError: If fewer than ``limit`` complete records are present.

    A zero limit returns no records and the original offset. This mirrors
    ``$8126-$8137``, which discards the rest of the separator byte before
    beginning the next record.
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
