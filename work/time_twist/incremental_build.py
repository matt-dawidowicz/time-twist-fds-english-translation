"""Fast source-first recompilation of entropy-coded playtest images.

The incremental builder reads the current production entropy layout, reuses its
approved dictionary unchanged, and reallocates only the scenario text region.
It never runs dictionary optimization or reconstructs unrelated runtime assets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

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

GROUP_RECORD_COUNTS: dict[str, tuple[int, ...]] = {
    "TT1A": (32, 3),
    "TT1B": (32, 32, 32, 32, 9),
    "TT2": (32, 32, 32, 32, 32, 9),
    "T22": (32, 26),
    "TT3A": (32, 32, 32, 32, 24),
    "TT3B": (32, 26),
    "TT4": (32, 32, 32, 32, 32, 23),
    "TT5": (32, 32, 32, 27),
    "T25": (32, 32, 12),
    "TT6A": (32, 32, 32, 4),
    "TT6B": (32, 32, 30),
    "TT6C": (32, 32, 32, 10),
    "TT6D": (8,),
}

FIXED_TAIL_BOUNDARIES: dict[str, int] = {
    "TT1A": 2169,
    "TT1B": 7070,
    "TT2": 7471,
    "T22": 3938,
    "TT3A": 7128,
    "TT3B": 3045,
    "TT4": 8930,
    "TT5": 7236,
    "T25": 5247,
    "TT6A": 4550,
    "TT6B": 4167,
    "TT6C": 6388,
    "TT6D": 731,
}


class IncrementalBuildError(ValueError):
    """Report a compiled bank that cannot be safely rebuilt incrementally."""


@dataclass(frozen=True)
class IncrementalBankResult:
    """Describe one incremental scenario-bank rebuild."""

    data: bytes
    changed_records: tuple[str, ...]


@dataclass(frozen=True)
class IncrementalImageResult:
    """Describe one incremental four-side playtest image build."""

    data: bytes
    changed_banks: tuple[str, ...]
    changed_records: tuple[str, ...]


@dataclass(frozen=True)
class _SplitGroup:
    """Describe the one optional runtime split-stream thunk."""

    group_index: int
    first_record_count: int
    suffix_address: int


@dataclass(frozen=True)
class _EntropyBankState:
    """Decoded and byte-verified state of one compiled scenario bank."""

    bank_name: str
    data: bytes
    group_addresses: tuple[int, ...]
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
    dictionary: tuple[tuple[PackedSymbol, ...], ...]
    expansions: tuple[tuple[PackedSymbol, ...], ...]
    literal_groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
    fixed_tail_boundary: int
    split_group: _SplitGroup | None


def _read_word(data: bytes, offset: int) -> int:
    """Read one checked little-endian word."""
    if offset < 0 or offset + 2 > len(data):
        raise IncrementalBuildError(
            f"word offset 0x{offset:04X} is outside entropy bank"
        )
    return int.from_bytes(data[offset : offset + 2], "little")


def _write_word(data: bytearray, offset: int, value: int) -> None:
    """Write one checked little-endian word."""
    if not 0 <= value <= 0xFFFF:
        raise IncrementalBuildError(f"pointer 0x{value:X} exceeds 16 bits")
    if offset < 0 or offset + 2 > len(data):
        raise IncrementalBuildError(
            f"word offset 0x{offset:04X} is outside entropy bank"
        )
    data[offset : offset + 2] = value.to_bytes(2, "little")


def _offset(address: int, data: bytes) -> int:
    """Convert one loaded address to a checked bank offset."""
    offset = address - LOAD_ADDRESS
    if not 0 <= offset < len(data):
        raise IncrementalBuildError(
            f"address 0x{address:04X} is outside entropy bank"
        )
    return offset


def _semantic(
    record: tuple[PackedSymbol, ...],
) -> tuple[tuple[object, int], ...]:
    """Drop decoder bit positions while retaining semantic symbols."""
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _translation_topology(
    bank_name: str,
    translations: dict[str, str],
) -> tuple[tuple[int, ...], tuple[tuple[str, ...], ...]]:
    """Return contiguous per-group record counts and stable record IDs."""
    pattern = re.compile(rf"^{re.escape(bank_name)}/g(\d+)/r(\d+)$")
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
    counts = tuple(map(len, ids))
    expected = GROUP_RECORD_COUNTS.get(bank_name)
    if expected is None or counts != expected:
        raise IncrementalBuildError(
            f"{bank_name}: canonical record topology differs from compiled ABI"
        )
    return counts, tuple(ids)


def _group_addresses(data: bytes, group_count: int) -> tuple[int, ...]:
    """Read group zero and all remaining group pointers."""
    table_offset = _offset(_read_word(data, GROUP_TABLE_POINTER_OFFSET), data)
    addresses = (
        _read_word(data, GROUP_ZERO_POINTER_OFFSET),
        *(
            _read_word(data, table_offset + 2 * index)
            for index in range(group_count - 1)
        ),
    )
    for address in addresses:
        _offset(address, data)
    return addresses


def _split_group(data: bytes) -> _SplitGroup | None:
    """Decode the frozen 27-byte split-stream thunk when installed."""
    thunk_address = _read_word(data, 10)
    if thunk_address == 0:
        return None
    thunk_offset = _offset(thunk_address, data)
    thunk = data[thunk_offset : thunk_offset + 27]
    if len(thunk) != 27 or thunk[:3] != bytes.fromhex("a531c9"):
        raise IncrementalBuildError("compiled split-group thunk is malformed")
    split = _SplitGroup(
        group_index=thunk[3] >> 5,
        first_record_count=thunk[9],
        suffix_address=thunk[17] | (thunk[21] << 8),
    )
    _offset(split.suffix_address, data)
    return split


def _decode_verified_stream(
    data: bytes,
    *,
    address: int,
    record_count: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode one stream and prove canonical re-encoding matches its bytes."""
    start = _offset(address, data)
    decoded, _byte_index, _mask = split_entropy_stream(
        data,
        offset=start,
        limit=record_count,
    )
    records = tuple(tuple(record) for record in decoded)
    packed = pack_entropy_stream(records)
    if data[start : start + len(packed)] != packed:
        raise IncrementalBuildError(
            f"entropy stream at 0x{address:04X} does not round-trip byte-exactly"
        )
    return records


def _decode_dictionary(
    data: bytes,
    *,
    boundary: int,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Infer dictionary count by exact coverage of its packed byte region."""
    start = _offset(_read_word(data, DICTIONARY_POINTER_OFFSET), data)
    if not start <= boundary <= len(data):
        raise IncrementalBuildError(
            "dictionary/fixed-tail boundary is malformed"
        )
    raw = data[start:boundary]
    if not raw:
        return ()
    for count in range(1, 256):
        decoded, _byte_index, _mask = split_entropy_stream(
            data,
            offset=start,
            limit=count,
        )
        records = tuple(tuple(record) for record in decoded)
        if pack_entropy_stream(records) == raw:
            return records
    raise IncrementalBuildError(
        "dictionary stream does not terminate at the fixed-tail boundary"
    )


def _expand_dictionary(
    definitions: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Expand a recovered dictionary, including valid forward references."""
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


def _load_entropy_bank(data: bytes, bank_name: str) -> _EntropyBankState:
    """Load and byte-verify one compiled production scenario bank."""
    try:
        counts = GROUP_RECORD_COUNTS[bank_name]
        boundary = FIXED_TAIL_BOUNDARIES[bank_name]
    except KeyError as error:
        raise IncrementalBuildError(
            f"unknown scenario bank {bank_name!r}"
        ) from error
    if LOAD_ADDRESS + len(data) > NOV3_LOAD_ADDRESS:
        raise IncrementalBuildError(f"{bank_name} overlaps NOV3")

    addresses = _group_addresses(data, len(counts))
    split = _split_group(data)
    groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    for group_index, (address, count) in enumerate(
        zip(addresses, counts, strict=True)
    ):
        if split is None or split.group_index != group_index:
            groups.append(
                _decode_verified_stream(
                    data,
                    address=address,
                    record_count=count,
                )
            )
            continue
        if not 0 < split.first_record_count < count:
            raise IncrementalBuildError("split-group record count is invalid")
        prefix = _decode_verified_stream(
            data,
            address=address,
            record_count=split.first_record_count,
        )
        suffix = _decode_verified_stream(
            data,
            address=split.suffix_address,
            record_count=count - split.first_record_count,
        )
        groups.append(prefix + suffix)

    dictionary = (
        ()
        if bank_name == "TT1A"
        else _decode_dictionary(data, boundary=boundary)
    )
    expansions = _expand_dictionary(dictionary)
    literal_groups = tuple(
        tuple(expand_entropy_record(record, expansions) for record in group)
        for group in groups
    )
    return _EntropyBankState(
        bank_name=bank_name,
        data=data,
        group_addresses=addresses,
        groups=tuple(groups),
        dictionary=dictionary,
        expansions=expansions,
        literal_groups=literal_groups,
        fixed_tail_boundary=boundary,
        split_group=split,
    )


def _allocate_groups(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    dictionary_bytes: int,
    resident_capacity: int,
    tail_capacity: int,
) -> dict[str, object] | None:
    """Choose whole-group placement, falling back to one split group."""
    sizes = tuple(len(pack_entropy_stream(group)) for group in groups)
    count = len(groups)
    options: list[tuple[tuple[object, ...], dict[str, object]]] = []
    for mask in range(1 << count):
        resident = tuple(i for i in range(count) if mask & (1 << i))
        spill = tuple(i for i in range(count) if not mask & (1 << i))
        used = (
            sum(sizes[i] for i in resident)
            + 2 * (count - 1)
            + dictionary_bytes
        )
        spilled = sum(sizes[i] for i in spill)
        if used <= resident_capacity and spilled <= tail_capacity:
            options.append(
                (
                    (0, spilled, len(spill), -resident_capacity + used),
                    {
                        "resident": resident,
                        "spill": spill,
                        "split": None,
                    },
                )
            )
    if options:
        return min(options, key=lambda item: item[0])[1]

    for split_group, group in enumerate(groups):
        for first in range(1, len(group)):
            prefix = len(pack_entropy_stream(group[:first]))
            suffix = len(pack_entropy_stream(group[first:]))
            for mask in range(1 << count):
                if not mask & (1 << split_group):
                    continue
                resident = tuple(i for i in range(count) if mask & (1 << i))
                spill = tuple(i for i in range(count) if not mask & (1 << i))
                used = (
                    sum(
                        prefix if i == split_group else sizes[i]
                        for i in resident
                    )
                    + dictionary_bytes
                    + 2 * (count - 1)
                    + 27
                )
                spilled = sum(sizes[i] for i in spill) + suffix
                if used <= resident_capacity and spilled <= tail_capacity:
                    options.append(
                        (
                            (
                                1,
                                spilled,
                                len(spill),
                                -resident_capacity + used,
                                split_group,
                                first,
                            ),
                            {
                                "resident": resident,
                                "spill": spill,
                                "split": (split_group, first),
                            },
                        )
                    )
    return min(options, key=lambda item: item[0])[1] if options else None


def _thunk(
    group_index: int,
    first_record_count: int,
    suffix_address: int,
) -> bytes:
    """Build the frozen NOV2 split-stream thunk."""
    return bytes(
        [
            165,
            49,
            201,
            group_index << 5,
            208,
            18,
            165,
            194,
            201,
            first_record_count,
            144,
            12,
            233,
            first_record_count,
            133,
            194,
            169,
            suffix_address & 0xFF,
            133,
            106,
            169,
            suffix_address >> 8,
            133,
            107,
            76,
            36,
            129,
        ]
    )


def _compiled_base_end(state: _EntropyBankState) -> int:
    """Return preserved fixed-suffix end before current spill data begins."""
    boundary = state.fixed_tail_boundary
    spill_offsets = [
        address - LOAD_ADDRESS
        for address in state.group_addresses
        if address - LOAD_ADDRESS >= boundary
    ]
    if state.split_group is not None:
        suffix = state.split_group.suffix_address - LOAD_ADDRESS
        if suffix >= boundary:
            spill_offsets.append(suffix)
    return min(spill_offsets) if spill_offsets else len(state.data)


def _rebuild_loaded_bank(
    state: _EntropyBankState,
    literal_groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> bytes:
    """Reallocate scenario streams while keeping dictionary/fixed suffix stable."""
    if tuple(map(len, literal_groups)) != GROUP_RECORD_COUNTS[state.bank_name]:
        raise IncrementalBuildError("literal group topology changed")

    groups = tuple(
        tuple(
            parse_entropy_record_with_expansions(
                record,
                state.expansions,
            )
            for record in group
        )
        for group in literal_groups
    )

    if state.bank_name == "TT1A":
        start = min(state.group_addresses) - LOAD_ADDRESS
        output = bytearray(state.data[:start])
        addresses: list[int] = []
        for group in groups:
            addresses.append(LOAD_ADDRESS + len(output))
            output.extend(pack_entropy_stream(group))
        _write_word(output, GROUP_ZERO_POINTER_OFFSET, addresses[0])
        table = _read_word(output, GROUP_TABLE_POINTER_OFFSET) - LOAD_ADDRESS
        for index, address in enumerate(addresses[1:]):
            _write_word(output, table + 2 * index, address)
        if LOAD_ADDRESS + len(output) > NOV3_LOAD_ADDRESS - 16:
            raise IncrementalBuildError(
                "TT1A incremental rebuild overlaps NOV3 reserve"
            )
        return bytes(output)

    boundary = state.fixed_tail_boundary
    base_end = _compiled_base_end(state)
    resident_offsets = [
        address - LOAD_ADDRESS
        for address in state.group_addresses
        if address - LOAD_ADDRESS < boundary
    ]
    if not resident_offsets:
        raise IncrementalBuildError("compiled bank has no resident group")
    region_start = min(resident_offsets)
    dictionary_blob = pack_entropy_stream(state.dictionary)
    plan = _allocate_groups(
        groups,
        dictionary_bytes=len(dictionary_blob),
        resident_capacity=boundary - region_start,
        tail_capacity=NOV3_LOAD_ADDRESS - LOAD_ADDRESS - base_end,
    )
    if plan is None:
        raise IncrementalBuildError(
            f"{state.bank_name}: fixed dictionary cannot fit edited scenario"
        )

    output = bytearray(state.data[:base_end])
    output[region_start:boundary] = b"\x00" * (boundary - region_start)
    addresses = [0] * len(groups)
    split = cast(tuple[int, int] | None, plan["split"])
    resident = cast(tuple[int, ...], plan["resident"])
    spill = cast(tuple[int, ...], plan["spill"])
    split_group, first = split if split is not None else (None, None)
    cursor = region_start
    for group_index in resident:
        records = (
            groups[group_index][:first]
            if group_index == split_group and first is not None
            else groups[group_index]
        )
        blob = pack_entropy_stream(records)
        addresses[group_index] = LOAD_ADDRESS + cursor
        output[cursor : cursor + len(blob)] = blob
        cursor += len(blob)
    for group_index in spill:
        addresses[group_index] = LOAD_ADDRESS + len(output)
        output.extend(pack_entropy_stream(groups[group_index]))

    suffix_address = None
    if split_group is not None and first is not None:
        suffix_address = LOAD_ADDRESS + len(output)
        output.extend(pack_entropy_stream(groups[split_group][first:]))

    dictionary_offset = boundary - len(dictionary_blob)
    table_offset = dictionary_offset - 2 * (len(groups) - 1)
    thunk_offset = table_offset - (27 if split is not None else 0)
    if cursor > thunk_offset:
        raise IncrementalBuildError(
            "resident streams overlap pointer/dictionary block"
        )
    output[dictionary_offset:boundary] = dictionary_blob
    for index, address in enumerate(addresses[1:]):
        _write_word(output, table_offset + 2 * index, address)
    _write_word(
        output,
        DICTIONARY_POINTER_OFFSET,
        LOAD_ADDRESS + dictionary_offset,
    )
    _write_word(
        output,
        GROUP_TABLE_POINTER_OFFSET,
        LOAD_ADDRESS + table_offset,
    )
    _write_word(output, GROUP_ZERO_POINTER_OFFSET, addresses[0])
    if split is None:
        _write_word(output, 10, 0)
    else:
        assert split_group is not None
        assert first is not None
        assert suffix_address is not None
        _write_word(output, 10, LOAD_ADDRESS + thunk_offset)
        output[thunk_offset:table_offset] = _thunk(
            split_group,
            first,
            suffix_address,
        )
    if state.data[boundary:base_end] != bytes(output[boundary:base_end]):
        raise IncrementalBuildError("fixed suffix changed")
    if LOAD_ADDRESS + len(output) > NOV3_LOAD_ADDRESS:
        raise IncrementalBuildError("incremental rebuild overlaps NOV3")
    return bytes(output)


def rebuild_entropy_bank(
    data: bytes,
    bank_name: str,
    translations: dict[str, str],
) -> IncrementalBankResult:
    """Rebuild one compiled bank against canonical English using its dictionary."""
    record_counts, record_ids = _translation_topology(
        bank_name,
        translations,
    )
    state = _load_entropy_bank(data, bank_name)
    if record_counts != tuple(map(len, state.groups)):
        raise IncrementalBuildError(
            "compiled group topology differs from source"
        )

    desired = tuple(
        tuple(
            encode_english(translations[record_ids[group_index][record_index]])
            for record_index in range(record_count)
        )
        for group_index, record_count in enumerate(record_counts)
    )
    changed = tuple(
        record_ids[group_index][record_index]
        for group_index, (before_group, after_group) in enumerate(
            zip(state.literal_groups, desired, strict=True)
        )
        for record_index, (before, after) in enumerate(
            zip(before_group, after_group, strict=True)
        )
        if _semantic(before) != _semantic(after)
    )
    if not changed:
        return IncrementalBankResult(data=data, changed_records=())

    rebuilt = _rebuild_loaded_bank(state, desired)
    verified = _load_entropy_bank(rebuilt, bank_name)
    for group_index, (actual_group, expected_group) in enumerate(
        zip(verified.literal_groups, desired, strict=True)
    ):
        for record_index, (actual, expected) in enumerate(
            zip(actual_group, expected_group, strict=True)
        ):
            if _semantic(actual) != _semantic(expected):
                record_id = record_ids[group_index][record_index]
                raise IncrementalBuildError(
                    f"{record_id} failed post-build verification"
                )
    return IncrementalBankResult(
        data=rebuilt,
        changed_records=changed,
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
        data=image_data if not changed_banks else image.to_bytes(),
        changed_banks=tuple(changed_banks),
        changed_records=tuple(changed_records),
    )
