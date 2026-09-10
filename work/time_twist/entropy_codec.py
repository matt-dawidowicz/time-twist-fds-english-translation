"""Frozen entropy codec for production Time Twist scenario text.

The game still consumes the same semantic token classes as the recovered NOV2
text engine.  Production entropy mode changes only their binary representation.
A small fixed prefix chooses one of sixteen value ranges and a fixed-width
payload selects the value within that range.

Unlike the native format, record separators do *not* force byte alignment.
Scenario groups and dictionaries are bit-contiguous streams and are padded only
at the end of each independently addressed stream.  Fixed menu tables are
padded every 32 records because their page index stores byte addresses.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .textcodec import PackedSymbol, PackedTextError, SymbolKind


class EntropyCodecError(PackedTextError):
    """Report a malformed or unrepresentable production entropy stream."""


@dataclass(frozen=True)
class EntropyCategory:
    """One fixed prefix-code leaf and its semantic value range."""

    prefix: str
    payload_bits: int
    base: int
    kind: SymbolKind
    maximum: int


# This table is frozen from the full production corpus.  Category numbers are
# part of the NOV2 runtime ABI, so reorderings are binary-incompatible.
ENTROPY_CATEGORIES: tuple[EntropyCategory, ...] = (
    EntropyCategory("0111", 0, 5, SymbolKind.SEPARATOR, 5),
    EntropyCategory("11000", 3, 0, SymbolKind.CONTROL, 7),
    EntropyCategory("111", 2, 0, SymbolKind.COMMON, 3),
    EntropyCategory("001", 2, 4, SymbolKind.COMMON, 7),
    EntropyCategory("101", 3, 8, SymbolKind.COMMON, 15),
    EntropyCategory("1101", 3, 16, SymbolKind.COMMON, 23),
    EntropyCategory("00001", 3, 24, SymbolKind.COMMON, 31),
    EntropyCategory("1001", 4, 32, SymbolKind.COMMON, 47),
    EntropyCategory("0110", 3, 1, SymbolKind.DICTIONARY, 8),
    EntropyCategory("0001", 3, 9, SymbolKind.DICTIONARY, 16),
    EntropyCategory("1000", 4, 17, SymbolKind.DICTIONARY, 32),
    EntropyCategory("010", 5, 33, SymbolKind.DICTIONARY, 64),
    EntropyCategory("000001", 5, 65, SymbolKind.DICTIONARY, 96),
    EntropyCategory("0000001", 5, 97, SymbolKind.DICTIONARY, 128),
    EntropyCategory("0000000", 7, 129, SymbolKind.DICTIONARY, 255),
    EntropyCategory("11001", 5, 37, SymbolKind.EXTENDED, 63),
)

CATEGORY_PREFIXES = tuple(category.prefix for category in ENTROPY_CATEGORIES)
CATEGORY_PAYLOAD_BITS = tuple(
    category.payload_bits for category in ENTROPY_CATEGORIES
)
CATEGORY_BASES = tuple(category.base for category in ENTROPY_CATEGORIES)


class _BitWriter:
    """Represent BitWriter state and behavior."""

    def __init__(self) -> None:
        """Initialize the helper state."""
        self._data = bytearray()
        self.bit_position = 0

    def write_bits(self, value: int, width: int) -> None:
        """Write bits."""
        if width < 0 or value < 0 or value >= (1 << width):
            raise EntropyCodecError(
                f"value {value} does not fit in {width} bits"
            )
        for shift in range(width - 1, -1, -1):
            byte_index, within = divmod(self.bit_position, 8)
            if byte_index == len(self._data):
                self._data.append(0)
            self._data[byte_index] |= ((value >> shift) & 1) << (7 - within)
            self.bit_position += 1

    def write_prefix(self, prefix: str) -> None:
        """Write prefix."""
        for bit in prefix:
            self.write_bits(int(bit), 1)

    def align(self) -> None:
        """Support the align operation for this module."""
        remainder = self.bit_position & 7
        if remainder:
            self.bit_position += 8 - remainder

    def to_bytes(self) -> bytes:
        """Support the to bytes operation for this module."""
        return bytes(self._data)


class _BitReader:
    """Represent BitReader state and behavior."""

    def __init__(self, data: bytes, bit_position: int = 0) -> None:
        """Initialize the helper state."""
        if bit_position < 0 or bit_position > len(data) * 8:
            raise EntropyCodecError("bit position is outside entropy stream")
        self.data = data
        self.bit_position = bit_position

    def read_bit(self) -> int:
        """Read bit."""
        if self.bit_position >= len(self.data) * 8:
            raise EntropyCodecError("unexpected end of entropy stream")
        byte_index, within = divmod(self.bit_position, 8)
        self.bit_position += 1
        return (self.data[byte_index] >> (7 - within)) & 1

    def read_bits(self, width: int) -> int:
        """Read bits."""
        value = 0
        for _ in range(width):
            value = (value << 1) | self.read_bit()
        return value


def _category_index(symbol: PackedSymbol) -> int:
    """Support the category index operation for this module."""
    kind = symbol.kind
    value = symbol.value
    if kind is SymbolKind.SEPARATOR:
        if value != 5:
            raise EntropyCodecError(
                f"separator value {value} must be control 5"
            )
        return 0
    if kind is SymbolKind.CONTROL:
        if value == 5:
            raise EntropyCodecError(
                "control 5 must use the separator representation"
            )
        if 0 <= value <= 7:
            return 1
    elif kind is SymbolKind.COMMON:
        for index in range(2, 8):
            category = ENTROPY_CATEGORIES[index]
            if category.base <= value <= category.maximum:
                return index
    elif kind is SymbolKind.DICTIONARY:
        for index in range(8, 15):
            category = ENTROPY_CATEGORIES[index]
            if category.base <= value <= category.maximum:
                return index
    elif kind is SymbolKind.EXTENDED and 37 <= value <= 63:
        return 15
    raise EntropyCodecError(f"unsupported entropy symbol {kind}:{value}")


def entropy_symbol_bits(symbol: PackedSymbol) -> int:
    """Return the exact encoded bit width of one semantic symbol."""
    category = ENTROPY_CATEGORIES[_category_index(symbol)]
    return len(category.prefix) + category.payload_bits


def entropy_record_bits(record: Sequence[PackedSymbol]) -> int:
    """Return record payload bits plus the four-bit separator."""
    if any(symbol.kind is SymbolKind.SEPARATOR for symbol in record):
        raise EntropyCodecError("record payload contains a separator")
    return sum(entropy_symbol_bits(symbol) for symbol in record) + len(
        ENTROPY_CATEGORIES[0].prefix
    )


def entropy_stream_size(records: Iterable[Sequence[PackedSymbol]]) -> int:
    """Return bytes after padding once at the end of the complete stream."""
    materialized = tuple(tuple(record) for record in records)
    bits = sum(entropy_record_bits(record) for record in materialized)
    return (bits + 7) // 8


def _encode_symbol(writer: _BitWriter, symbol: PackedSymbol) -> None:
    """Encode symbol."""
    category = ENTROPY_CATEGORIES[_category_index(symbol)]
    writer.write_prefix(category.prefix)
    if category.payload_bits:
        writer.write_bits(symbol.value - category.base, category.payload_bits)


def pack_entropy_stream(
    records: Iterable[Sequence[PackedSymbol]],
) -> bytes:
    """Pack records contiguously and pad only after the final separator."""
    writer = _BitWriter()
    separator = PackedSymbol(SymbolKind.SEPARATOR, 5, 0, 0)
    for record in records:
        for symbol in record:
            if symbol.kind is SymbolKind.SEPARATOR:
                raise EntropyCodecError(
                    "record payload cannot contain a separator"
                )
            _encode_symbol(writer, symbol)
        _encode_symbol(writer, separator)
    writer.align()
    return writer.to_bytes()


def pack_entropy_pages(
    records: Sequence[Sequence[PackedSymbol]],
    *,
    records_per_page: int = 32,
) -> tuple[bytes, tuple[int, ...]]:
    """Pack byte-addressable record pages and return each page byte offset."""
    if records_per_page <= 0:
        raise ValueError("records_per_page must be positive")
    chunks: list[bytes] = []
    starts: list[int] = []
    cursor = 0
    for start in range(0, len(records), records_per_page):
        starts.append(cursor)
        chunk = pack_entropy_stream(records[start : start + records_per_page])
        chunks.append(chunk)
        cursor += len(chunk)
    return b"".join(chunks), tuple(starts)


def _build_decode_trie() -> dict[int | str, object]:
    """Build decode trie."""
    root: dict[int | str, object] = {}
    for index, category in enumerate(ENTROPY_CATEGORIES):
        node = root
        for bit_text in category.prefix:
            bit = int(bit_text)
            child = node.setdefault(bit, {})
            if not isinstance(child, dict):
                raise AssertionError("entropy prefix tree is malformed")
            node = child
        if node:
            raise AssertionError("entropy prefix is not a leaf")
        node["category"] = index
    return root


_DECODE_TRIE = _build_decode_trie()


def _decode_symbol(reader: _BitReader) -> PackedSymbol:
    """Decode symbol."""
    node: dict[int | str, object] = _DECODE_TRIE
    while "category" not in node:
        bit = reader.read_bit()
        child = node.get(bit)
        if not isinstance(child, dict):
            raise EntropyCodecError("invalid entropy prefix")
        node = child
    index = node["category"]
    if not isinstance(index, int):
        raise AssertionError("entropy category leaf is malformed")
    category = ENTROPY_CATEGORIES[index]
    value = category.base + reader.read_bits(category.payload_bits)
    if value > category.maximum:
        raise EntropyCodecError(
            f"noncanonical entropy category {index} payload {value}"
        )
    if category.kind is SymbolKind.CONTROL and value == 5:
        raise EntropyCodecError("noncanonical control-5 entropy token")
    return PackedSymbol(category.kind, value, 0, 0)


def split_entropy_stream(
    data: bytes,
    *,
    offset: int = 0,
    limit: int,
) -> tuple[list[list[PackedSymbol]], int, int]:
    """Decode records and return final byte index and one-hot bit mask.

    The mask mirrors NOV2 ``$6C``: ``0x80`` means the next unread bit is the
    first bit of the current byte, ``0x01`` means the last bit.  A record
    separator deliberately leaves this cursor untouched.
    """
    if offset < 0 or offset > len(data):
        raise ValueError("record offset is outside entropy stream")
    if limit < 0:
        raise ValueError("record limit cannot be negative")
    reader = _BitReader(data, offset * 8)
    records: list[list[PackedSymbol]] = []
    current: list[PackedSymbol] = []
    while len(records) < limit:
        symbol = _decode_symbol(reader)
        if symbol.kind is SymbolKind.SEPARATOR:
            records.append(current)
            current = []
        else:
            current.append(symbol)
    byte_index, within = divmod(reader.bit_position, 8)
    mask = 0x80 >> within if within else 0x80
    return records, byte_index, mask


def unpack_entropy_stream(
    data: bytes,
    *,
    record_count: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode one complete padded stream and reject nonzero trailing padding."""
    records, byte_index, mask = split_entropy_stream(
        data,
        offset=0,
        limit=record_count,
    )
    consumed_bits = byte_index * 8
    if mask != 0x80:
        consumed_bits += (mask.bit_length() - 1) ^ 7
    if consumed_bits > len(data) * 8:
        raise EntropyCodecError("entropy stream cursor exceeds payload")
    for bit_position in range(consumed_bits, len(data) * 8):
        byte, within = divmod(bit_position, 8)
        if data[byte] & (0x80 >> within):
            raise EntropyCodecError("entropy stream has nonzero end padding")
    return tuple(tuple(record) for record in records)
