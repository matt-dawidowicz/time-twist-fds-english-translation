"""Safe scenario-bank placement for bit-contiguous production entropy text."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .entropy_codec import (
    pack_entropy_pages,
    pack_entropy_stream,
    unpack_entropy_stream,
)
from .entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from .scenario import (
    DICTIONARY_POINTER_OFFSET,
    GROUP_TABLE_POINTER_OFFSET,
    GROUP_ZERO_POINTER_OFFSET,
    ScenarioBank,
)
from .textcodec import PackedSymbol
from .ui import (
    FIXED_RECORD_FOLLOWING_POINTER_OFFSETS,
    FIXED_RECORD_PAGE_POINTER_OFFSET,
    FIXED_RECORD_TABLE_POINTER_OFFSET,
    FIXED_RECORD_TABLE_SPECS,
    FIXED_RECORDS_PER_PAGE,
    UiPatchError,
    fixed_record_table_page_pointer_bytes,
)

NOV3_LOAD_ADDRESS = 0xD7B5
ENTROPY_SCENARIO_LOAD_ADDRESS = 0xA200

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]


class EntropyScenarioError(ValueError):
    """Report an unsafe layout, pointer mismatch, or failed round trip."""


@dataclass(frozen=True)
class EntropyScenarioLayout:
    """Describe one entropy-coded overlay and its resident/spill placement."""

    data: bytes
    load_address: int
    group_addresses: tuple[int, ...]
    group_bytes: tuple[int, ...]
    group_table_address: int
    dictionary_address: int
    dictionary_bytes: int
    resident_groups: tuple[int, ...]
    spilled_groups: tuple[int, ...]
    resident_bytes: int
    spill_bytes: int
    source_bytes: int

    @property
    def loaded_end(self) -> int:
        """Return the exclusive loaded CPU address of the patched bank."""
        return self.load_address + len(self.data)


def _read_word(data: bytes, offset: int) -> int:
    """Read one little-endian word from the supplied buffer."""
    if offset < 0 or offset + 2 > len(data):
        raise EntropyScenarioError(
            f"word offset 0x{offset:04X} is outside bank"
        )
    return int.from_bytes(data[offset : offset + 2], "little")


def _write_word(data: bytearray, offset: int, value: int) -> None:
    """Write one little-endian word into the supplied buffer."""
    if not 0 <= value <= 0xFFFF:
        raise EntropyScenarioError(f"pointer ${value:05X} exceeds 16 bits")
    if offset < 0 or offset + 2 > len(data):
        raise EntropyScenarioError(
            f"word offset 0x{offset:04X} is outside bank"
        )
    data[offset : offset + 2] = value.to_bytes(2, "little")


def _source_record_counts(bank: ScenarioBank) -> tuple[int, ...]:
    """Support the source record counts operation for this module."""
    return tuple(
        sum(record.group_index == group for record in bank.records)
        for group in range(len(bank.group_addresses))
    )


def _semantic_record(
    record: tuple[PackedSymbol, ...] | list[PackedSymbol],
) -> tuple[tuple[object, int], ...]:
    """Support the semantic record operation for this module."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _literal_groups(
    groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
) -> ScenarioGroups:
    """Support the literal groups operation for this module."""
    expansions = expand_entropy_dictionary(dictionary)
    return tuple(
        tuple(expand_entropy_record(record, expansions) for record in group)
        for group in groups
    )


def _best_resident_subset(
    group_sizes: tuple[int, ...], capacity: int
) -> tuple[int, ...]:
    """Choose whole groups that consume the most old-reservation bytes."""
    if capacity < 0:
        raise EntropyScenarioError(
            "entropy dictionary and pointer table exceed old text space"
        )
    best_bytes = -1
    best: tuple[int, ...] = ()
    for mask in range(1 << len(group_sizes)):
        selected = tuple(
            index for index in range(len(group_sizes)) if mask & (1 << index)
        )
        used = sum(group_sizes[index] for index in selected)
        if used > capacity:
            continue
        if used > best_bytes or (used == best_bytes and selected < best):
            best_bytes = used
            best = selected
    if best_bytes < 0:
        raise EntropyScenarioError("no valid resident-group subset")
    return best


def _source_record_starts(data: bytes, count: int) -> tuple[int, ...]:
    """Return source-native byte starts for page-index verification."""
    from .textcodec import split_records

    starts: list[int] = []
    offset = 0
    for _ in range(count):
        starts.append(offset)
        _, offset = split_records(data, offset=offset, limit=1)
    return tuple(starts)


def relocate_entropy_fixed_record_table(
    data: bytes,
    *,
    bank_name: str,
    load_address: int,
    group_zero_offset: int,
    records: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[bytes, int]:
    """Repack one fixed menu table into byte-addressable 32-record pages."""
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    if len(records) != len(spec.records):
        raise UiPatchError(
            f"{bank_name} expected {len(spec.records)} fixed records, "
            f"got {len(records)}"
        )
    source = data[spec.start : spec.end]
    if len(source) != spec.end - spec.start:
        raise UiPatchError(
            f"{bank_name} is too short for its fixed text table"
        )
    if hashlib.sha256(source).hexdigest().upper() != spec.source_sha256:
        raise UiPatchError(
            f"{bank_name} fixed text table does not match source"
        )

    def header_offset(pointer_offset: int) -> int:
        """Support the header offset operation for this module."""
        return _read_word(data, pointer_offset) - load_address

    if header_offset(FIXED_RECORD_TABLE_POINTER_OFFSET) != spec.start:
        raise UiPatchError(f"{bank_name} fixed-table base pointer changed")
    if header_offset(FIXED_RECORD_PAGE_POINTER_OFFSET) != spec.end:
        raise UiPatchError(f"{bank_name} fixed-table page pointer changed")

    page_pointer_bytes = fixed_record_table_page_pointer_bytes(bank_name)
    old_following_offset = header_offset(
        FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[0]
    )
    if old_following_offset != spec.end + page_pointer_bytes:
        raise UiPatchError(
            f"{bank_name} fixed-table page index has unexpected size"
        )
    second_following = header_offset(FIXED_RECORD_FOLLOWING_POINTER_OFFSETS[1])
    if not old_following_offset <= second_following < group_zero_offset:
        raise UiPatchError(
            f"{bank_name} secondary table pointer is outside recovered block"
        )

    original_starts = _source_record_starts(source, len(spec.records))
    expected_pages = b"".join(
        (load_address + spec.start + original_starts[index]).to_bytes(
            2, "little"
        )
        for index in range(
            FIXED_RECORDS_PER_PAGE,
            len(records),
            FIXED_RECORDS_PER_PAGE,
        )
    )
    if data[spec.end : old_following_offset] != expected_pages:
        raise UiPatchError(f"{bank_name} fixed-table page index changed")

    secondary_low = load_address + old_following_offset
    secondary_high = load_address + group_zero_offset
    if any(
        secondary_low
        <= int.from_bytes(data[offset : offset + 2], "little")
        < secondary_high
        for offset in range(old_following_offset, group_zero_offset - 1)
    ):
        raise UiPatchError(
            f"{bank_name} secondary prefix contains an unrelocated pointer"
        )

    packed, page_starts = pack_entropy_pages(
        records, records_per_page=FIXED_RECORDS_PER_PAGE
    )
    new_page_offset = spec.start + len(packed)
    new_pages = b"".join(
        (load_address + spec.start + start).to_bytes(2, "little")
        for start in page_starts[1:]
    )
    if len(new_pages) != page_pointer_bytes:
        raise UiPatchError(f"{bank_name} rebuilt page index changed size")

    new_following_offset = new_page_offset + len(new_pages)
    delta = new_following_offset - old_following_offset
    new_group_zero_offset = group_zero_offset + delta
    if new_group_zero_offset <= new_following_offset:
        raise UiPatchError(f"{bank_name} relocated prefix is malformed")

    prefix = bytearray(data[: spec.start])
    prefix.extend(packed)
    prefix.extend(new_pages)
    prefix.extend(data[old_following_offset:group_zero_offset])
    if len(prefix) != new_group_zero_offset:
        raise UiPatchError(
            f"{bank_name} relocated prefix size is inconsistent"
        )

    _write_word(
        prefix,
        FIXED_RECORD_PAGE_POINTER_OFFSET,
        load_address + new_page_offset,
    )
    for pointer_offset in FIXED_RECORD_FOLLOWING_POINTER_OFFSETS:
        _write_word(
            prefix,
            pointer_offset,
            _read_word(data, pointer_offset) + delta,
        )
    if len(prefix) > len(data):
        raise UiPatchError(f"{bank_name} relocated prefix exceeds the bank")
    relocated = bytes(prefix) + data[len(prefix) :]
    if len(relocated) != len(data):
        raise UiPatchError(f"{bank_name} relocation changed bank size")
    return relocated, new_group_zero_offset


def build_entropy_scenario_bank(
    bank: ScenarioBank,
    groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
    *,
    base_data: bytes | None = None,
    old_region_start: int | None = None,
    prg_ram_end: int = NOV3_LOAD_ADDRESS,
) -> EntropyScenarioLayout:
    """Place continuous entropy streams while preserving the fixed source tail."""
    if bank.load_address != ENTROPY_SCENARIO_LOAD_ADDRESS:
        raise EntropyScenarioError(
            f"entropy runtime requires load ${ENTROPY_SCENARIO_LOAD_ADDRESS:04X}"
        )
    counts = _source_record_counts(bank)
    if len(groups) != len(counts):
        raise EntropyScenarioError(
            f"expected {len(counts)} groups, got {len(groups)}"
        )
    for index, (group, expected) in enumerate(
        zip(groups, counts, strict=True)
    ):
        if len(group) != expected:
            raise EntropyScenarioError(
                f"group {index} expected {expected} records, got {len(group)}"
            )

    expected_groups = _literal_groups(groups, dictionary)
    source = bank.data if base_data is None else base_data
    if len(source) != len(bank.data):
        raise EntropyScenarioError(
            "base_data must retain original overlay size"
        )
    region_start = (
        bank.group_addresses[0] - bank.load_address
        if old_region_start is None
        else old_region_start
    )
    if not 0 <= region_start < bank.dictionary_end_offset <= len(source):
        raise EntropyScenarioError("old scenario reservation is malformed")

    group_blobs = tuple(pack_entropy_stream(group) for group in groups)
    dictionary_blob = pack_entropy_stream(dictionary)
    group_sizes = tuple(map(len, group_blobs))
    table_size = 2 * (len(groups) - 1)
    resident_capacity = (
        bank.dictionary_end_offset
        - region_start
        - table_size
        - len(dictionary_blob)
    )
    resident = _best_resident_subset(group_sizes, resident_capacity)
    resident_set = set(resident)
    spilled = tuple(
        index for index in range(len(groups)) if index not in resident_set
    )

    output = bytearray(source)
    output[region_start : bank.dictionary_end_offset] = b"\x00" * (
        bank.dictionary_end_offset - region_start
    )
    addresses = [0] * len(groups)
    cursor = region_start
    for index in resident:
        blob = group_blobs[index]
        output[cursor : cursor + len(blob)] = blob
        addresses[index] = bank.load_address + cursor
        cursor += len(blob)

    group_table_offset = cursor
    cursor += table_size
    dictionary_address = bank.load_address + cursor
    output[cursor : cursor + len(dictionary_blob)] = dictionary_blob
    cursor += len(dictionary_blob)
    if cursor > bank.dictionary_end_offset:
        raise EntropyScenarioError(
            "resident entropy data overrun fixed-tail boundary"
        )

    high_cursor = len(bank.data)
    for index in spilled:
        blob = group_blobs[index]
        addresses[index] = bank.load_address + high_cursor
        output.extend(blob)
        high_cursor += len(blob)
    loaded_end = bank.load_address + high_cursor
    if loaded_end > prg_ram_end:
        raise EntropyScenarioError(
            f"entropy text reaches ${loaded_end:04X}; NOV3 begins at ${prg_ram_end:04X}"
        )

    table = b"".join(
        address.to_bytes(2, "little") for address in addresses[1:]
    )
    output[group_table_offset : group_table_offset + len(table)] = table
    group_table_address = bank.load_address + group_table_offset
    _write_word(output, DICTIONARY_POINTER_OFFSET, dictionary_address)
    _write_word(output, GROUP_TABLE_POINTER_OFFSET, group_table_address)
    _write_word(output, GROUP_ZERO_POINTER_OFFSET, addresses[0])

    if (
        output[bank.dictionary_end_offset : len(bank.data)]
        != source[bank.dictionary_end_offset :]
    ):
        raise EntropyScenarioError("fixed source tail moved or changed")

    layout = EntropyScenarioLayout(
        data=bytes(output),
        load_address=bank.load_address,
        group_addresses=tuple(addresses),
        group_bytes=group_sizes,
        group_table_address=group_table_address,
        dictionary_address=dictionary_address,
        dictionary_bytes=len(dictionary_blob),
        resident_groups=resident,
        spilled_groups=spilled,
        resident_bytes=(
            sum(group_sizes[index] for index in resident)
            + table_size
            + len(dictionary_blob)
        ),
        spill_bytes=sum(group_sizes[index] for index in spilled),
        source_bytes=len(bank.data),
    )
    validate_entropy_scenario_bank(bank, expected_groups, dictionary, layout)
    return layout


def validate_entropy_scenario_bank(
    source_bank: ScenarioBank,
    literal_groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
    layout: EntropyScenarioLayout,
) -> None:
    """Decode every independently addressed stream and prove semantic equality."""
    data = layout.data
    load = source_bank.load_address
    if (
        _read_word(data, DICTIONARY_POINTER_OFFSET)
        != layout.dictionary_address
    ):
        raise EntropyScenarioError("dictionary header pointer mismatch")
    if (
        _read_word(data, GROUP_TABLE_POINTER_OFFSET)
        != layout.group_table_address
    ):
        raise EntropyScenarioError("group-table header pointer mismatch")
    if (
        _read_word(data, GROUP_ZERO_POINTER_OFFSET)
        != layout.group_addresses[0]
    ):
        raise EntropyScenarioError("group-zero header pointer mismatch")

    table_offset = layout.group_table_address - load
    table_addresses = tuple(
        _read_word(data, table_offset + 2 * index)
        for index in range(len(layout.group_addresses) - 1)
    )
    if table_addresses != layout.group_addresses[1:]:
        raise EntropyScenarioError("group-pointer table mismatch")

    counts = _source_record_counts(source_bank)
    decoded_groups = []
    for address, size, count in zip(
        layout.group_addresses, layout.group_bytes, counts, strict=True
    ):
        offset = address - load
        blob = data[offset : offset + size]
        decoded_groups.append(unpack_entropy_stream(blob, record_count=count))

    dictionary_offset = layout.dictionary_address - load
    dictionary_blob = data[
        dictionary_offset : dictionary_offset + layout.dictionary_bytes
    ]
    decoded_dictionary = unpack_entropy_stream(
        dictionary_blob, record_count=len(dictionary)
    )
    if tuple(map(_semantic_record, decoded_dictionary)) != tuple(
        map(_semantic_record, dictionary)
    ):
        raise EntropyScenarioError("dictionary round-trip mismatch")

    expansions = expand_entropy_dictionary(decoded_dictionary)
    for group_index, (decoded, expected) in enumerate(
        zip(decoded_groups, literal_groups, strict=True)
    ):
        for record_index, (packed, literal) in enumerate(
            zip(decoded, expected, strict=True)
        ):
            expanded = expand_entropy_record(packed, expansions)
            if _semantic_record(expanded) != _semantic_record(literal):
                raise EntropyScenarioError(
                    f"group {group_index} record {record_index} failed round-trip"
                )

    if (
        data[source_bank.dictionary_end_offset : len(source_bank.data)]
        != source_bank.data[source_bank.dictionary_end_offset :]
    ):
        raise EntropyScenarioError("fixed source tail differs from source")
