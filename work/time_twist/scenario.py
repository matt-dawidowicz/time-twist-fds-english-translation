"""Parse and render Time Twist scenario-bank text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .charmap import decode_common, decode_extended
from .textcodec import BitReader, PackedSymbol, SymbolKind, decode_symbol, pack_records


LOAD_ADDRESS = 0xA200
DICTIONARY_POINTER_OFFSET = 0x16
GROUP_TABLE_POINTER_OFFSET = 0x24
GROUP_ZERO_POINTER_OFFSET = 0x26
MAX_DICTIONARY_ENTRY_COUNT = 31


@dataclass(frozen=True)
class ScenarioRecord:
    group_index: int
    record_index: int
    symbols: tuple[PackedSymbol, ...]


@dataclass(frozen=True)
class ScenarioBank:
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
    """Raised when a scenario bank's pointers or record boundaries are invalid."""


def _read_word(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ScenarioError(f"word offset ${offset:04X} is outside the bank")
    return int.from_bytes(data[offset : offset + 2], "little")


def _to_offset(address: int, load_address: int, size: int) -> int:
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
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], int]:
    required_count = _maximum_dictionary_reference(text_records)
    if required_count > MAX_DICTIONARY_ENTRY_COUNT:
        raise ScenarioError(f"dictionary reference {required_count} is out of range")
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    end_offset = start_offset
    while len(dictionary) < required_count:
        dictionary, end_offset = _decode_fixed_records(
            data, start_offset, required_count
        )
        nested_count = _maximum_dictionary_reference(dictionary)
        if nested_count > MAX_DICTIONARY_ENTRY_COUNT:
            raise ScenarioError(f"dictionary reference {nested_count} is out of range")
        required_count = max(required_count, nested_count)
    return dictionary, end_offset


def parse_scenario_bank(
    path: Path,
    *,
    load_address: int = LOAD_ADDRESS,
) -> ScenarioBank:
    data = path.read_bytes()
    dictionary_address = _read_word(data, DICTIONARY_POINTER_OFFSET)
    group_table_address = _read_word(data, GROUP_TABLE_POINTER_OFFSET)
    group_zero_address = _read_word(data, GROUP_ZERO_POINTER_OFFSET)

    dictionary_offset = _to_offset(dictionary_address, load_address, len(data))
    group_table_offset = _to_offset(group_table_address, load_address, len(data))
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
    if tuple(sorted(group_addresses)) != group_addresses:
        raise ScenarioError("text-group pointers are not strictly ordered")

    group_offsets = tuple(
        _to_offset(address, load_address, len(data)) for address in group_addresses
    )
    group_end_offsets = (*group_offsets[1:], group_table_offset)
    if group_zero_offset != group_offsets[0]:
        raise ScenarioError("group-zero pointer conversion is inconsistent")

    records: list[ScenarioRecord] = []
    for group_index, (start, end) in enumerate(zip(group_offsets, group_end_offsets)):
        group_records = _decode_records_to_end(data, start, end)
        records.extend(
            ScenarioRecord(group_index, record_index, symbols)
            for record_index, symbols in enumerate(group_records)
        )

    dictionary, dictionary_end_offset = _decode_referenced_dictionary(
        data,
        dictionary_offset,
        (record.symbols for record in records),
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
    """Rebuild a bank while preserving code/data outside its text region."""

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
            raise ScenarioError("rebuilt group pointer exceeds the 16-bit address space")
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
        raise ScenarioError("rebuilt scenario data exceeds the 16-bit address space")

    prefix[DICTIONARY_POINTER_OFFSET : DICTIONARY_POINTER_OFFSET + 2] = (
        dictionary_address.to_bytes(2, "little")
    )
    prefix[GROUP_TABLE_POINTER_OFFSET : GROUP_TABLE_POINTER_OFFSET + 2] = (
        group_table_address.to_bytes(2, "little")
    )
    prefix[GROUP_ZERO_POINTER_OFFSET : GROUP_ZERO_POINTER_OFFSET + 2] = (
        group_addresses[0].to_bytes(2, "little")
    )
    rebuilt_text = bytes(prefix + group_stream + group_table + dictionary_stream)
    if preserve_memory_footprint:
        if len(rebuilt_text) > bank.dictionary_end_offset:
            overrun = len(rebuilt_text) - bank.dictionary_end_offset
            raise ScenarioError(
                f"rebuilt text exceeds the original RAM footprint by {overrun} bytes"
            )
        # Keep the original tail at its original CPU address.  Besides keeping
        # the FDS file size fixed, this prevents a translated overlay from
        # moving fixed-address data or overwriting the resident NOV4 program.
        rebuilt_text += bank.data[len(rebuilt_text) : bank.dictionary_end_offset]
    suffix = bank.data[bank.dictionary_end_offset :]
    return rebuilt_text + suffix


def render_symbols(
    symbols: Iterable[PackedSymbol],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    *,
    _stack: tuple[int, ...] = (),
) -> str:
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
