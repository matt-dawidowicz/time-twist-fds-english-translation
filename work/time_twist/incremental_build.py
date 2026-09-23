"""Fast bounded recompilation of already entropy-coded playtest images.

The incremental path deliberately does less than the release compiler. It keeps
the existing dictionary, group table, fixed code/data, UI patches, font, and
runtime patches in place. Fixed-position group streams may only shrink or stay
within their current byte spans. Only a contiguous group-stream suffix that
already reaches the end of a bank may resize.

If those constraints are insufficient, callers must use the full release
compiler/optimizer instead of silently relocating unknown data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .english import encode_english
from .entropy_codec import pack_entropy_stream, split_entropy_stream
from .entropy_compression import (
    expand_entropy_record,
    parse_entropy_record_with_expansions,
)
from .fds import FdsImage
from .production_translation import merged_translation_map
from .release_metadata import SCENARIO_LOCATIONS
from .scenario import (
    DICTIONARY_POINTER_OFFSET,
    GROUP_TABLE_POINTER_OFFSET,
    GROUP_ZERO_POINTER_OFFSET,
    LOAD_ADDRESS,
)
from .textcodec import PackedSymbol, SymbolKind

NOV3_LOAD_ADDRESS = 0xD7B5


class IncrementalBuildError(ValueError):
    """Report a candidate that cannot be changed without broader relocation."""


@dataclass(frozen=True)
class IncrementalBankResult:
    """Describe one bounded bank rebuild."""

    data: bytes
    changed_records: tuple[str, ...]


@dataclass(frozen=True)
class IncrementalImageResult:
    """Describe one incremental four-side image build."""

    data: bytes
    changed_banks: tuple[str, ...]
    changed_records: tuple[str, ...]


@dataclass(frozen=True)
class _Group:
    """Describe one decoded entropy group and its current physical span."""

    index: int
    address: int
    offset: int
    byte_length: int
    records: tuple[tuple[PackedSymbol, ...], ...]


def _read_word(data: bytes, offset: int) -> int:
    """Read one bounded little-endian pointer."""
    if offset < 0 or offset + 2 > len(data):
        raise IncrementalBuildError(
            f"word offset 0x{offset:04X} is outside entropy bank"
        )
    return int.from_bytes(data[offset : offset + 2], "little")


def _write_word(data: bytearray, offset: int, value: int) -> None:
    """Write one bounded little-endian pointer."""
    if not 0 <= value <= 0xFFFF:
        raise IncrementalBuildError(f"pointer 0x{value:X} exceeds 16 bits")
    if offset < 0 or offset + 2 > len(data):
        raise IncrementalBuildError(
            f"word offset 0x{offset:04X} is outside entropy bank"
        )
    data[offset : offset + 2] = value.to_bytes(2, "little")


def _used_bytes(start: int, byte_index: int, mask: int) -> int:
    """Return bytes touched by a bit-contiguous decoded stream."""
    end = byte_index if mask == 0x80 else byte_index + 1
    if end < start:
        raise IncrementalBuildError("entropy stream cursor moved backwards")
    return end - start


def _translation_topology(
    bank_name: str, translations: dict[str, str]
) -> tuple[tuple[int, ...], tuple[tuple[str, ...], ...]]:
    """Return contiguous per-group record counts and IDs."""
    pattern = re.compile(
        rf"^{re.escape(bank_name)}/g(\d+)/r(\d+)$"
    )
    grouped: dict[int, dict[int, str]] = {}
    for record_id in translations:
        match = pattern.match(record_id)
        if match is None:
            raise IncrementalBuildError(
                f"{bank_name}: malformed record ID {record_id!r}"
            )
        group = int(match.group(1))
        record = int(match.group(2))
        grouped.setdefault(group, {})[record] = record_id

    if not grouped or sorted(grouped) != list(range(len(grouped))):
        raise IncrementalBuildError(
            f"{bank_name}: group IDs are not contiguous from zero"
        )

    ids: list[tuple[str, ...]] = []
    for group in range(len(grouped)):
        records = grouped[group]
        if sorted(records) != list(range(len(records))):
            raise IncrementalBuildError(
                f"{bank_name}/g{group}: record IDs are not contiguous from zero"
            )
        ids.append(tuple(records[index] for index in range(len(records))))
    return tuple(map(len, ids)), tuple(ids)


def _decode_groups(
    data: bytes, record_counts: tuple[int, ...]
) -> tuple[tuple[_Group, ...], int]:
    """Decode every group stream using the current pointer table."""
    table_address = _read_word(data, GROUP_TABLE_POINTER_OFFSET)
    table_offset = table_address - LOAD_ADDRESS
    if not 0 <= table_offset <= len(data):
        raise IncrementalBuildError("group table is outside entropy bank")

    addresses = [_read_word(data, GROUP_ZERO_POINTER_OFFSET)]
    addresses.extend(
        _read_word(data, table_offset + 2 * index)
        for index in range(len(record_counts) - 1)
    )

    groups: list[_Group] = []
    for index, (address, count) in enumerate(
        zip(addresses, record_counts, strict=True)
    ):
        offset = address - LOAD_ADDRESS
        if not 0 <= offset < len(data):
            raise IncrementalBuildError(
                f"group {index} pointer 0x{address:04X} is outside bank"
            )
        records, byte_index, mask = split_entropy_stream(
            data,
            offset=offset,
            limit=count,
        )
        groups.append(
            _Group(
                index=index,
                address=address,
                offset=offset,
                byte_length=_used_bytes(offset, byte_index, mask),
                records=tuple(tuple(record) for record in records),
            )
        )
    return tuple(groups), table_offset


def _dictionary_references(
    records: tuple[tuple[PackedSymbol, ...], ...],
) -> set[int]:
    """Return one-based dictionary indexes referenced by records."""
    return {
        symbol.value
        for record in records
        for symbol in record
        if symbol.kind is SymbolKind.DICTIONARY
    }


def _reachable_expansions(
    data: bytes,
    groups: tuple[_Group, ...],
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode and recursively expand dictionary entries reachable from groups.

    Recovered v38 dictionaries may contain forward references, so this uses a
    graph resolver rather than the newer optimizer's backward-only helper.
    """
    required: set[int] = set()
    for group in groups:
        required.update(_dictionary_references(group.records))
    if not required:
        return ()

    dictionary_offset = _read_word(data, DICTIONARY_POINTER_OFFSET) - LOAD_ADDRESS
    if not 0 <= dictionary_offset < len(data):
        raise IncrementalBuildError("dictionary pointer is outside entropy bank")

    definitions: tuple[tuple[PackedSymbol, ...], ...] = ()
    while required:
        maximum = max(required)
        if maximum > 255:
            raise IncrementalBuildError(
                f"dictionary reference {maximum} exceeds entropy ABI"
            )
        if len(definitions) >= maximum:
            break
        decoded, _byte_index, _mask = split_entropy_stream(
            data,
            offset=dictionary_offset,
            limit=maximum,
        )
        definitions = tuple(tuple(record) for record in decoded)
        before = len(required)
        for definition in definitions:
            required.update(_dictionary_references((definition,)))
        if len(required) == before and len(definitions) < max(required):
            raise IncrementalBuildError("dictionary closure is incomplete")

    memo: dict[int, tuple[PackedSymbol, ...]] = {}
    visiting: set[int] = set()

    def expand(index: int) -> tuple[PackedSymbol, ...]:
        """Resolve one dictionary entry recursively with cycle detection."""
        if index in memo:
            return memo[index]
        if index in visiting:
            raise IncrementalBuildError(
                f"dictionary cycle reaches entry {index}"
            )
        if not 1 <= index <= len(definitions):
            raise IncrementalBuildError(
                f"dictionary reference {index} is unavailable"
            )
        visiting.add(index)
        output: list[PackedSymbol] = []
        for symbol in definitions[index - 1]:
            if symbol.kind is SymbolKind.DICTIONARY:
                output.extend(expand(symbol.value))
            else:
                output.append(symbol)
        visiting.remove(index)
        memo[index] = tuple(output)
        return memo[index]

    return tuple(expand(index) for index in range(1, len(definitions) + 1))


def _semantic(
    record: tuple[PackedSymbol, ...],
) -> tuple[tuple[object, int], ...]:
    """Drop decoder bit positions while retaining semantic symbols."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _terminal_group_indexes(
    data_length: int, groups: tuple[_Group, ...]
) -> frozenset[int]:
    """Return the contiguous physical group suffix that reaches file end."""
    ordered = sorted(groups, key=lambda group: group.offset)
    cursor = data_length
    terminal: list[int] = []
    for group in reversed(ordered):
        if group.offset + group.byte_length != cursor:
            break
        terminal.append(group.index)
        cursor = group.offset
    return frozenset(terminal)


def rebuild_entropy_bank(
    data: bytes,
    bank_name: str,
    translations: dict[str, str],
) -> IncrementalBankResult:
    """Rebuild changed records without moving dictionary or fixed bank data."""
    record_counts, record_ids = _translation_topology(
        bank_name, translations
    )
    groups, table_offset = _decode_groups(data, record_counts)
    expansions = _reachable_expansions(data, groups)

    changed: list[str] = []
    rebuilt_records: dict[int, tuple[tuple[PackedSymbol, ...], ...]] = {}
    for group in groups:
        output: list[tuple[PackedSymbol, ...]] = []
        for record_index, packed in enumerate(group.records):
            record_id = record_ids[group.index][record_index]
            target = encode_english(translations[record_id])
            current = expand_entropy_record(packed, expansions)
            if _semantic(current) == _semantic(target):
                output.append(packed)
                continue
            replacement = parse_entropy_record_with_expansions(
                target, expansions
            )
            if _semantic(expand_entropy_record(replacement, expansions)) != _semantic(
                target
            ):
                raise IncrementalBuildError(
                    f"{record_id}: fixed dictionary failed semantic round-trip"
                )
            output.append(replacement)
            changed.append(record_id)
        rebuilt_records[group.index] = tuple(output)

    if not changed:
        return IncrementalBankResult(data=data, changed_records=())

    terminal = _terminal_group_indexes(len(data), groups)
    result = bytearray(data)

    for group in groups:
        if group.index in terminal:
            continue
        blob = pack_entropy_stream(rebuilt_records[group.index])
        if len(blob) > group.byte_length:
            raise IncrementalBuildError(
                f"{bank_name}/g{group.index} grows from {group.byte_length} "
                f"to {len(blob)} bytes outside the resizable terminal suffix; "
                "run the full release optimizer"
            )
        result[group.offset : group.offset + group.byte_length] = (
            blob + bytes(group.byte_length - len(blob))
        )

    if terminal:
        ordered_terminal = sorted(
            (group for group in groups if group.index in terminal),
            key=lambda group: group.offset,
        )
        terminal_start = ordered_terminal[0].offset
        del result[terminal_start:]
        new_addresses: dict[int, int] = {}
        for group in ordered_terminal:
            new_addresses[group.index] = LOAD_ADDRESS + len(result)
            result.extend(pack_entropy_stream(rebuilt_records[group.index]))

        if LOAD_ADDRESS + len(result) > NOV3_LOAD_ADDRESS:
            raise IncrementalBuildError(
                f"{bank_name} incremental text reaches "
                f"0x{LOAD_ADDRESS + len(result):04X}; NOV3 begins at "
                f"0x{NOV3_LOAD_ADDRESS:04X}"
            )

        if 0 in new_addresses:
            _write_word(
                result,
                GROUP_ZERO_POINTER_OFFSET,
                new_addresses[0],
            )
        for group_index, address in new_addresses.items():
            if group_index == 0:
                continue
            _write_word(
                result,
                table_offset + 2 * (group_index - 1),
                address,
            )

    verified, _ = _decode_groups(bytes(result), record_counts)
    for group in verified:
        for record_index, packed in enumerate(group.records):
            target = encode_english(
                translations[record_ids[group.index][record_index]]
            )
            current = expand_entropy_record(packed, expansions)
            if _semantic(current) != _semantic(target):
                raise IncrementalBuildError(
                    f"{record_ids[group.index][record_index]} failed "
                    "post-build verification"
                )

    return IncrementalBankResult(
        data=bytes(result),
        changed_records=tuple(changed),
    )


def build_incremental_image(
    image_data: bytes,
    *,
    translations_directory: Path,
) -> IncrementalImageResult:
    """Rebuild only scenario banks whose decoded text differs from source."""
    image = FdsImage.from_bytes(image_data)
    changed_banks: list[str] = []
    changed_records: list[str] = []

    for bank_name, (part, local_side) in SCENARIO_LOCATIONS.items():
        side = local_side + (2 if part == "kouhen" else 0)
        entry = image.sides[side].find_file(bank_name)
        translations = merged_translation_map(
            bank_name,
            base_directory=translations_directory,
        )
        rebuilt = rebuild_entropy_bank(
            entry.data,
            bank_name,
            translations,
        )
        if rebuilt.changed_records:
            entry.data = rebuilt.data
            changed_banks.append(bank_name)
            changed_records.extend(rebuilt.changed_records)

    return IncrementalImageResult(
        data=image.to_bytes(),
        changed_banks=tuple(changed_banks),
        changed_records=tuple(changed_records),
    )
