"""Parse, render, and rebuild Time Twist scenario overlay text.

Scenario overlays normally load at ``$A200``.  Header pointers identify group
streams, a pointer table, and a referenced dictionary.  The parser keeps the
complete source bank so a rebuild can replace only the variable text region
and leave the fixed tail at its original loaded address.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from .charmap import decode_common, decode_extended
from .textcodec import (
    BitReader,
    PackedSymbol,
    SymbolKind,
    decode_symbol,
    pack_records,
)

LOAD_ADDRESS = 0xA200
DICTIONARY_POINTER_OFFSET = 0x16
GROUP_TABLE_POINTER_OFFSET = 0x24
GROUP_ZERO_POINTER_OFFSET = 0x26
MAX_DICTIONARY_ENTRY_COUNT = 31


@dataclass(frozen=True)
class ScenarioRecord:
    """Store one packed record and its stable group-local coordinates.

    Attributes:
        group_index: Zero-based scenario group selected by the pointer table.
        record_index: Zero-based record position within that group.
        symbols: Payload tokens without the terminating separator.
    """

    group_index: int
    record_index: int
    symbols: tuple[PackedSymbol, ...]


@dataclass(frozen=True)
class ScenarioBank:
    """Parsed scenario layout plus immutable source bytes.

    Attributes:
        path: Source bank path used for provenance and stable naming.
        data: Complete immutable source bytes.
        load_address: CPU address corresponding to file offset zero.
        minimum_dictionary_entries: Source dictionary entries that must be
            included even when ordinary scenario records do not reference
            them directly.
        dictionary_address: Loaded address of the dictionary stream.
        group_table_address: Loaded address of group pointers 1 through n.
        group_addresses: Loaded addresses for every group, including group 0.
        dictionary: Decoded reachable entries in one-based reference order.
        dictionary_end_offset: First source byte after the decoded dictionary.
        records: Flattened records retaining their group-local coordinates.

    ``dictionary_end_offset`` is the critical fixed-memory boundary. Bytes at
    and after that offset may be code or data referenced by absolute address.
    """

    path: Path
    data: bytes
    load_address: int
    dictionary_address: int
    group_table_address: int
    group_addresses: tuple[int, ...]
    dictionary: tuple[tuple[PackedSymbol, ...], ...]
    dictionary_end_offset: int
    records: tuple[ScenarioRecord, ...]


class ScenarioError(ValueError):
    """Report invalid pointers, streams, capacity, or rebuilt scenario layout.

    The exception covers both malformed source banks and proposed translations
    that cannot preserve native structural constraints.  Rebuild operations
    validate into temporary buffers first, so a raised error does not mutate the
    caller's original bank bytes.
    """


def _read_word(data: bytes, offset: int) -> int:
    """Read one bounded little-endian 16-bit word.

    Args:
        data: Complete scenario bank.
        offset: File-relative offset of the low byte.

    Returns:
        Unsigned 16-bit value.

    Raises:
        ScenarioError: If either byte lies outside ``data``.
    """
    if offset < 0 or offset + 2 > len(data):
        raise ScenarioError(f"word offset ${offset:04X} is outside the bank")
    return int.from_bytes(data[offset : offset + 2], "little")


def _to_offset(address: int, load_address: int, size: int) -> int:
    """Convert a loaded address to a validated file-relative offset.

    Args:
        address: Absolute CPU address stored in the bank.
        load_address: CPU address corresponding to file offset zero.
        size: Complete bank length in bytes.

    Returns:
        ``address - load_address``. A pointer exactly one byte beyond the bank
        is accepted as an end boundary.

    Raises:
        ScenarioError: If the result is negative or greater than ``size``.
    """
    offset = address - load_address
    if offset < 0 or offset > size:
        raise ScenarioError(
            f"pointer ${address:04X} is outside ${load_address:04X}-${load_address + size:04X}"
        )
    return offset


def _decode_records_to_end(
    data: bytes,
    start_offset: int,
    end_offset: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode byte-aligned records up to an exact stream boundary.

    Args:
        data: Complete scenario bank.
        start_offset: File offset of the first record.
        end_offset: Required byte offset immediately after the last record.

    Returns:
        Immutable record payloads without separator tokens.

    Raises:
        ScenarioError: If offsets are reversed or record alignment crosses or
            fails to reach ``end_offset`` exactly.
        PackedTextError: If a symbol is truncated.
    """
    if start_offset > end_offset:
        raise ScenarioError("record stream starts after its end")
    reader = BitReader(data, start_offset * 8)
    records: list[tuple[PackedSymbol, ...]] = []
    while reader.byte_position < end_offset:
        record: list[PackedSymbol] = []
        while True:
            symbol = decode_symbol(reader)
            if symbol.kind is SymbolKind.SEPARATOR:
                reader.align_to_next_byte()
                records.append(tuple(record))
                break
            record.append(symbol)
        if reader.byte_position > end_offset:
            raise ScenarioError(
                f"record crosses stream boundary ${end_offset:04X}"
            )
    if reader.byte_position != end_offset:
        raise ScenarioError(
            f"record stream ended at ${reader.byte_position:04X}, expected ${end_offset:04X}"
        )
    return tuple(records)


def _decode_fixed_records(
    data: bytes,
    start_offset: int,
    count: int,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], int]:
    """Decode a known number of aligned records from one byte offset.

    Args:
        data: Complete scenario bank.
        start_offset: File offset of the first record.
        count: Number of separators/records to consume.

    Returns:
        A pair of immutable record payloads and the byte offset after the final
        separator alignment.

    Raises:
        PackedTextError: If the stream ends before ``count`` records.
    """
    reader = BitReader(data, start_offset * 8)
    records: list[tuple[PackedSymbol, ...]] = []
    for _ in range(count):
        record: list[PackedSymbol] = []
        while True:
            symbol = decode_symbol(reader)
            if symbol.kind is SymbolKind.SEPARATOR:
                reader.align_to_next_byte()
                records.append(tuple(record))
                break
            record.append(symbol)
    return tuple(records), reader.byte_position


def _maximum_dictionary_reference(
    records: Iterable[Iterable[PackedSymbol]],
) -> int:
    """Return the largest one-based dictionary reference in nested records.

    Args:
        records: Any iterable of symbol iterables.

    Returns:
        Maximum dictionary payload, or zero when no reference exists.
    """
    return max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )


def _decode_referenced_dictionary(
    data: bytes,
    start_offset: int,
    text_records: Iterable[Iterable[PackedSymbol]],
    *,
    minimum_entry_count: int = 0,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], int]:
    """Decode the transitive closure of dictionary references.

    Args:
        data: Complete scenario bank.
        start_offset: File offset of dictionary entry 1.
        text_records: Scenario records that seed the reachable entry count.
        minimum_entry_count: Explicit source entries required by packed text
            outside the ordinary scenario groups.

    Returns:
        Reachable dictionary entries and the byte offset after the final entry.

    Raises:
        ScenarioError: If a direct or nested reference exceeds the native
            31-entry limit.
        PackedTextError: If the required dictionary stream is truncated.

    The dictionary is reparsed when a decoded entry references a later entry.
    This avoids assuming that source dictionaries are flat.
    """
    if not 0 <= minimum_entry_count <= MAX_DICTIONARY_ENTRY_COUNT:
        raise ScenarioError(
            f"dictionary minimum {minimum_entry_count} is out of range"
        )
    required_count = max(
        minimum_entry_count,
        _maximum_dictionary_reference(text_records),
    )
    if required_count > MAX_DICTIONARY_ENTRY_COUNT:
        raise ScenarioError(
            f"dictionary reference {required_count} is out of range"
        )
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    end_offset = start_offset
    while len(dictionary) < required_count:
        dictionary, end_offset = _decode_fixed_records(
            data, start_offset, required_count
        )
        nested_count = _maximum_dictionary_reference(dictionary)
        if nested_count > MAX_DICTIONARY_ENTRY_COUNT:
            raise ScenarioError(
                f"dictionary reference {nested_count} is out of range"
            )
        required_count = max(required_count, nested_count)
    return dictionary, end_offset


def parse_scenario_bank(
    path: Path,
    *,
    load_address: int = LOAD_ADDRESS,
    minimum_dictionary_entries: int = 0,
) -> ScenarioBank:
    """Parse group pointers, byte-aligned records, and referenced dictionary.

    Args:
        path: Extracted scenario/program bank to read.
        load_address: CPU address corresponding to file offset zero.

    Returns:
        Parsed layout, source bytes, records, and reachable dictionary.

    Raises:
        OSError: If ``path`` cannot be read.
        ScenarioError: If pointers, table size, ordering, group boundaries, or
            dictionary references are invalid.
        PackedTextError: If a packed symbol is truncated.

    The pointer table stores groups 1..n; group zero has its own header pointer.
    Group addresses must be ordered, and each group must end exactly at the
    next group or the pointer table. Dictionary decoding includes both the
    explicit minimum and every entry reachable from scenario/nested source
    references.

    The function reads the filesystem but never mutates the bank.
    """
    data = path.read_bytes()
    dictionary_address = _read_word(data, DICTIONARY_POINTER_OFFSET)
    group_table_address = _read_word(data, GROUP_TABLE_POINTER_OFFSET)
    group_zero_address = _read_word(data, GROUP_ZERO_POINTER_OFFSET)

    dictionary_offset = _to_offset(dictionary_address, load_address, len(data))
    group_table_offset = _to_offset(
        group_table_address, load_address, len(data)
    )
    group_zero_offset = _to_offset(group_zero_address, load_address, len(data))
    if dictionary_offset < group_table_offset:
        raise ScenarioError("dictionary precedes the group-pointer table")
    table_size = dictionary_offset - group_table_offset
    if table_size % 2:
        raise ScenarioError("group-pointer table has an odd byte length")

    extra_group_addresses = tuple(
        _read_word(data, group_table_offset + offset)
        for offset in range(0, table_size, 2)
    )
    group_addresses = (group_zero_address, *extra_group_addresses)
    if any(first >= second for first, second in pairwise(group_addresses)):
        raise ScenarioError("text-group pointers are not strictly ordered")

    group_offsets = tuple(
        _to_offset(address, load_address, len(data))
        for address in group_addresses
    )
    group_end_offsets = (*group_offsets[1:], group_table_offset)
    if group_zero_offset != group_offsets[0]:
        raise ScenarioError("group-zero pointer conversion is inconsistent")

    records: list[ScenarioRecord] = []
    for group_index, (start, end) in enumerate(
        zip(group_offsets, group_end_offsets, strict=True)
    ):
        group_records = _decode_records_to_end(data, start, end)
        records.extend(
            ScenarioRecord(group_index, record_index, symbols)
            for record_index, symbols in enumerate(group_records)
        )

    dictionary, dictionary_end_offset = _decode_referenced_dictionary(
        data,
        dictionary_offset,
        (record.symbols for record in records),
        minimum_entry_count=minimum_dictionary_entries,
    )
    return ScenarioBank(
        path=path,
        data=data,
        load_address=load_address,
        dictionary_address=dictionary_address,
        group_table_address=group_table_address,
        group_addresses=group_addresses,
        dictionary=dictionary,
        dictionary_end_offset=dictionary_end_offset,
        records=tuple(records),
    )


def rebuild_scenario_bank(
    bank: ScenarioBank,
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = (),
    preserve_memory_footprint: bool = False,
) -> bytes:
    """Rebuild text and pointers while preserving non-text source bytes.

    Args:
        bank: Parsed source layout and immutable bytes.
        groups: Replacement records in original group order.
        dictionary: Replacement one-based dictionary entries.
        preserve_memory_footprint: Keep the original fixed tail at its loaded
            address and reject any text-region overrun.

    Returns:
        Rebuilt bank bytes with updated group/dictionary pointers.

    Raises:
        ScenarioError: If the group count changes, a loaded pointer exceeds
            16 bits, total scenario data exceeds address space, or a preserved
            footprint is too small.
        PackedTextError: If any replacement token cannot be packed.

    ``groups`` must match the original group count. When
    ``preserve_memory_footprint`` is true, the rebuilt group/table/dictionary
    area cannot cross the original ``dictionary_end_offset`` and any unused
    bytes before that boundary are copied from the source. The suffix begins
    at the same file offset and therefore the same loaded CPU address.

    The function is side-effect free and does not modify ``bank``.
    """
    if len(groups) != len(bank.group_addresses):
        raise ScenarioError(
            f"expected {len(bank.group_addresses)} groups, got {len(groups)}"
        )

    old_group_zero_offset = bank.group_addresses[0] - bank.load_address
    prefix = bytearray(bank.data[:old_group_zero_offset])
    group_addresses: list[int] = []
    group_stream = bytearray()
    for records in groups:
        address = bank.load_address + len(prefix) + len(group_stream)
        if address > 0xFFFF:
            raise ScenarioError(
                "rebuilt group pointer exceeds the 16-bit address space"
            )
        group_addresses.append(address)
        group_stream.extend(pack_records(records))

    group_table_address = bank.load_address + len(prefix) + len(group_stream)
    group_table = b"".join(
        address.to_bytes(2, "little") for address in group_addresses[1:]
    )
    dictionary_address = group_table_address + len(group_table)
    dictionary_stream = pack_records(dictionary)
    end_address = dictionary_address + len(dictionary_stream)
    if end_address > 0x10000:
        raise ScenarioError(
            "rebuilt scenario data exceeds the 16-bit address space"
        )

    prefix[DICTIONARY_POINTER_OFFSET : DICTIONARY_POINTER_OFFSET + 2] = (
        dictionary_address.to_bytes(2, "little")
    )
    prefix[GROUP_TABLE_POINTER_OFFSET : GROUP_TABLE_POINTER_OFFSET + 2] = (
        group_table_address.to_bytes(2, "little")
    )
    prefix[GROUP_ZERO_POINTER_OFFSET : GROUP_ZERO_POINTER_OFFSET + 2] = (
        group_addresses[0].to_bytes(2, "little")
    )
    rebuilt_text = bytes(
        prefix + group_stream + group_table + dictionary_stream
    )
    if preserve_memory_footprint:
        if len(rebuilt_text) > bank.dictionary_end_offset:
            overrun = len(rebuilt_text) - bank.dictionary_end_offset
            raise ScenarioError(
                f"rebuilt text exceeds the original RAM footprint by {overrun} bytes"
            )
        # Keep the original tail at its original CPU address.  Besides keeping
        # the FDS file size fixed, this prevents a translated overlay from
        # moving fixed-address data or overwriting the resident NOV4 program.
        rebuilt_text += bank.data[
            len(rebuilt_text) : bank.dictionary_end_offset
        ]
    suffix = bank.data[bank.dictionary_end_offset :]
    return rebuilt_text + suffix


def render_symbols(
    symbols: Iterable[PackedSymbol],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    *,
    _stack: tuple[int, ...] = (),
) -> str:
    """Render Japanese glyphs, recursively expanded dictionary text, and tags.

    Args:
        symbols: Record or dictionary-entry tokens to render.
        dictionary: Ordered one-based source dictionary.
        _stack: Internal recursion path for loop detection. Callers should use
            the default.

    Returns:
        Exact decoded Japanese where known, plus explicit tags for controls,
        separators, unknown glyphs, invalid references, or loops.

    Invalid references and loops remain visible as diagnostic tokens rather
    than disappearing from the extracted source. Rendering never mutates the
    symbols or dictionary and never raises for a bad reference.
    """
    rendered: list[str] = []
    for symbol in symbols:
        if symbol.kind is SymbolKind.COMMON:
            rendered.append(decode_common(symbol.value))
        elif symbol.kind is SymbolKind.EXTENDED:
            rendered.append(decode_extended(symbol.value))
        elif symbol.kind is SymbolKind.DICTIONARY:
            dictionary_index = symbol.value - 1
            if dictionary_index < 0 or dictionary_index >= len(dictionary):
                rendered.append(f"{{DICT:{symbol.value}}}")
            elif dictionary_index in _stack:
                rendered.append(f"{{DICT-LOOP:{symbol.value}}}")
            else:
                rendered.append(
                    render_symbols(
                        dictionary[dictionary_index],
                        dictionary,
                        _stack=(*_stack, dictionary_index),
                    )
                )
        elif symbol.kind is SymbolKind.CONTROL:
            rendered.append(f"{{CTRL:{symbol.value}}}")
        elif symbol.kind is SymbolKind.SEPARATOR:
            rendered.append("{END}")
    return "".join(rendered)
