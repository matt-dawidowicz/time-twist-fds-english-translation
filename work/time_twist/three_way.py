"""Decode auditable Japanese/current/competitor scenario coordinates.

The public project cannot distribute retail FDS images or another patch
author's translated script.  This module therefore contains only structural
facts and deterministic decoders.  A maintainer supplies their own images and
competitor IPS file to the companion ``generate_three_way_comparison.py``
script, which writes its extracted review corpus beneath the ignored private
runtime-capture directory.

The competitor release uses a different English font map, a different
extended-dictionary escape, and non-monotonic group placement.  None of those
choices is treated as a model for this project's patch.  They are decoded only
to align the same Japanese record coordinates for editorial comparison.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from .charmap import decode_common, decode_extended
from .english import COMMON_CHARACTERS, EXTENDED_CHARACTERS
from .fds import FdsFile
from .textcodec import PackedSymbol, SymbolKind, split_records

SCENARIO_HEADER_DICTIONARY_POINTER: Final = 0x16
SCENARIO_HEADER_GROUP_TABLE_POINTER: Final = 0x24
SCENARIO_HEADER_GROUP_ZERO_POINTER: Final = 0x26


@dataclass(frozen=True)
class ScenarioSpec:
    """Locate one scenario file and preserve its known logical record counts."""

    name: str
    half: str
    side: int
    record_counts: tuple[int, ...]


SCENARIO_SPECS: Final = (
    ScenarioSpec("TT1A", "zenpen", 1, (32, 3)),
    ScenarioSpec("TT1B", "zenpen", 1, (32, 32, 32, 32, 9)),
    ScenarioSpec("TT2", "zenpen", 1, (32, 32, 32, 32, 32, 9)),
    ScenarioSpec("T22", "zenpen", 1, (32, 26)),
    ScenarioSpec("TT3A", "zenpen", 0, (32, 32, 32, 32, 24)),
    ScenarioSpec("TT3B", "zenpen", 0, (32, 26)),
    ScenarioSpec("TT4", "kouhen", 1, (32, 32, 32, 32, 32, 23)),
    ScenarioSpec("TT5", "kouhen", 1, (32, 32, 32, 27)),
    ScenarioSpec("T25", "kouhen", 1, (32, 32, 12)),
    ScenarioSpec("TT6A", "kouhen", 0, (32, 32, 32, 4)),
    ScenarioSpec("TT6B", "kouhen", 0, (32, 32, 30)),
    ScenarioSpec("TT6C", "kouhen", 0, (32, 32, 32, 10)),
    ScenarioSpec("TT6D", "kouhen", 0, (8,)),
)


class TextDialect(str, Enum):
    """Select the Japanese, project-English, or competitor-English codec."""

    JAPANESE = "japanese"
    CURRENT_ENGLISH = "current-english"
    COMPETITOR_ENGLISH = "competitor-english"


@dataclass(frozen=True)
class IpsRecord:
    """Represent one literal or already-expanded RLE record from an IPS file."""

    offset: int
    data: bytes


@dataclass(frozen=True)
class IpsPatch:
    """Store parsed IPS writes plus an optional post-patch truncation size."""

    records: tuple[IpsRecord, ...]
    truncate_size: int | None


@dataclass(frozen=True)
class DecodedRecord:
    """Store rendered text and its exact byte-aligned packed source interval."""

    group: int
    record: int
    text: str
    packed_bytes: int
    source_range: tuple[int, int]


@dataclass(frozen=True)
class DecodedBank:
    """Store all stable records plus ranges consumed to decode one bank."""

    records: tuple[DecodedRecord, ...]
    dictionary_entries: int
    dictionary_range: tuple[int, int] | None
    pointer_ranges: tuple[tuple[int, int], ...]

    @property
    def text_ranges(self) -> tuple[tuple[int, int], ...]:
        """Return every packed record interval plus the used dictionary."""

        ranges = tuple(record.source_range for record in self.records)
        if self.dictionary_range is None:
            return ranges
        return (*ranges, self.dictionary_range)


# Recovered directly from the competitor NOV4 glyph rows selected by NOV2's
# common-code lookup.  The order is packed-symbol value order, not alphabetic
# order.  Keeping this private decoder separate avoids contaminating the
# project's authoritative English character map.
COMPETITOR_COMMON_CHARACTERS: Final = (
    " eoat.nirhsldum:ygcwpf!,b"
    "MkTv'A?"
    "ISGHWDNBC-"
    "OJPREY"
)
assert len(COMPETITOR_COMMON_CHARACTERS) == 48

# Values 4-36 are not glyphs in this release; its patched NOV2 decoder turns
# them into dictionary references 32-64 by adding 28.  Only literal extended
# values actually observed in the complete 1,299-record scenario corpus are
# assigned here.  Unknown values remain explicit diagnostics.
COMPETITOR_EXTENDED_CHARACTERS: Final = {
    1: "j",
    2: "F",
    37: "x",
    38: "z",
    39: "q",
    40: ";",
    41: "V",
    42: "Q",
    43: '"',
    44: "Z",
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
    59: "Y",
    60: "L",
    61: "U",
    63: " ",
}


def parse_ips(data: bytes) -> IpsPatch:
    """Parse IPS without applying instructions embedded in surrounding files.

    Args:
        data: Complete IPS payload beginning with ``PATCH``.

    Returns:
        Expanded patch records and the optional three-byte truncate extension.

    Raises:
        ValueError: If the signature, a record, RLE data, EOF marker, or
            truncate extension is malformed.
    """

    if not data.startswith(b"PATCH"):
        raise ValueError("IPS payload does not begin with PATCH")
    position = 5
    records: list[IpsRecord] = []
    while True:
        if position + 3 > len(data):
            raise ValueError("IPS payload has no complete EOF marker")
        marker = data[position : position + 3]
        position += 3
        if marker == b"EOF":
            break
        if position + 2 > len(data):
            raise ValueError("IPS literal/RLE size is truncated")
        offset = int.from_bytes(marker, "big")
        size = int.from_bytes(data[position : position + 2], "big")
        position += 2
        if size:
            end = position + size
            if end > len(data):
                raise ValueError("IPS literal record is truncated")
            payload = data[position:end]
            position = end
        else:
            if position + 3 > len(data):
                raise ValueError("IPS RLE record is truncated")
            repeat = int.from_bytes(data[position : position + 2], "big")
            if repeat == 0:
                raise ValueError("IPS RLE record has a zero repeat count")
            payload = bytes((data[position + 2],)) * repeat
            position += 3
        records.append(IpsRecord(offset, payload))

    remaining = len(data) - position
    if remaining not in (0, 3):
        raise ValueError("IPS EOF is followed by an invalid extension")
    truncate_size = (
        int.from_bytes(data[position : position + 3], "big")
        if remaining == 3
        else None
    )
    return IpsPatch(tuple(records), truncate_size)


def apply_ips(source: bytes, patch: IpsPatch) -> tuple[bytes, bytes]:
    """Apply an IPS patch and return both output and explicit-write mask.

    Args:
        source: Base bytes supplied by the maintainer.
        patch: Parsed IPS records.

    Returns:
        Patched bytes and a same-size mask whose nonzero bytes were explicitly
        supplied by IPS records.  The mask lets callers distinguish patch
        authority from potentially mismatched base-image bytes.
    """

    result = bytearray(source)
    written = bytearray(len(source))
    for record in patch.records:
        end = record.offset + len(record.data)
        if record.offset > len(result):
            padding = record.offset - len(result)
            result.extend(b"\0" * padding)
            written.extend(b"\0" * padding)
        if end > len(result):
            growth = end - len(result)
            result.extend(b"\0" * growth)
            written.extend(b"\0" * growth)
        result[record.offset:end] = record.data
        written[record.offset:end] = b"\1" * len(record.data)
    if patch.truncate_size is not None:
        del result[patch.truncate_size :]
        del written[patch.truncate_size :]
    return bytes(result), bytes(written)


def _read_pointer(data: bytes, offset: int, load_address: int) -> int:
    """Read and validate one loaded-address pointer as a file offset."""

    if offset < 0 or offset + 2 > len(data):
        raise ValueError(f"pointer field ${offset:04X} is outside the bank")
    address = int.from_bytes(data[offset : offset + 2], "little")
    result = address - load_address
    if result < 0 or result > len(data):
        raise ValueError(
            f"pointer ${address:04X} is outside the loaded scenario bank"
        )
    return result


def _competitor_symbols(
    symbols: tuple[PackedSymbol, ...] | list[PackedSymbol],
) -> tuple[PackedSymbol, ...]:
    """Apply the competitor's narrower extended-dictionary escape mapping."""

    return tuple(
        PackedSymbol(
            SymbolKind.DICTIONARY,
            symbol.value + 28,
            symbol.start_bit,
            symbol.end_bit,
        )
        if symbol.kind is SymbolKind.EXTENDED and 4 <= symbol.value <= 36
        else symbol
        for symbol in symbols
    )


def _maximum_dictionary_reference(
    records: tuple[tuple[PackedSymbol, ...], ...]
    | list[tuple[PackedSymbol, ...]],
) -> int:
    """Return the greatest one-based dictionary reference in packed records."""

    return max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )


def _render_english(
    symbols: tuple[PackedSymbol, ...],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    *,
    common_characters: str,
    extended_characters: dict[int, str],
    stack: tuple[int, ...] = (),
) -> str:
    """Render one English dialect while exposing every invalid token."""

    rendered: list[str] = []
    for symbol in symbols:
        if symbol.kind is SymbolKind.COMMON:
            if 0 <= symbol.value < len(common_characters):
                rendered.append(common_characters[symbol.value])
            else:
                rendered.append(f"{{COMMON:{symbol.value}}}")
        elif symbol.kind is SymbolKind.EXTENDED:
            rendered.append(
                extended_characters.get(
                    symbol.value, f"{{EXT:{symbol.value}}}"
                )
            )
        elif symbol.kind is SymbolKind.DICTIONARY:
            index = symbol.value - 1
            if index < 0 or index >= len(dictionary):
                rendered.append(f"{{DICT:{symbol.value}}}")
            elif index in stack:
                rendered.append(f"{{DICT-LOOP:{symbol.value}}}")
            else:
                rendered.append(
                    _render_english(
                        dictionary[index],
                        dictionary,
                        common_characters=common_characters,
                        extended_characters=extended_characters,
                        stack=(*stack, index),
                    )
                )
        elif symbol.kind is SymbolKind.CONTROL:
            rendered.append(f"{{CTRL:{symbol.value}}}")
        elif symbol.kind is SymbolKind.SEPARATOR:
            rendered.append("{END}")
    return "".join(rendered)


def _decode_one_record(
    data: bytes,
    offset: int,
    dialect: TextDialect,
) -> tuple[tuple[PackedSymbol, ...], int]:
    """Decode one aligned record and return its transformed symbols and end."""

    extended_dictionary = dialect is TextDialect.CURRENT_ENGLISH
    records, end = split_records(
        data,
        offset=offset,
        limit=1,
        extended_dictionary=extended_dictionary,
    )
    symbols = tuple(records[0])
    if dialect is TextDialect.COMPETITOR_ENGLISH:
        symbols = _competitor_symbols(symbols)
    return symbols, end


def _decode_dictionary(
    data: bytes,
    offset: int,
    seed_records: tuple[tuple[PackedSymbol, ...], ...],
    dialect: TextDialect,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], int]:
    """Decode the transitively referenced dictionary for one text dialect."""

    required = _maximum_dictionary_reference(seed_records)
    maximum = {
        TextDialect.JAPANESE: 31,
        TextDialect.CURRENT_ENGLISH: 68,
        TextDialect.COMPETITOR_ENGLISH: 64,
    }[dialect]
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    end = offset
    while len(dictionary) < required:
        if required > maximum:
            raise ValueError(
                f"{dialect.value} dictionary reference {required} exceeds "
                f"the recovered maximum {maximum}"
            )
        raw, end = split_records(
            data,
            offset=offset,
            limit=required,
            extended_dictionary=(dialect is TextDialect.CURRENT_ENGLISH),
        )
        if dialect is TextDialect.COMPETITOR_ENGLISH:
            dictionary = tuple(_competitor_symbols(record) for record in raw)
        else:
            dictionary = tuple(tuple(record) for record in raw)
        required = max(
            required, _maximum_dictionary_reference(dictionary)
        )
    return dictionary, end


def _render_record(
    symbols: tuple[PackedSymbol, ...],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    dialect: TextDialect,
) -> str:
    """Render one record with the explicitly selected character mapping."""

    if dialect is TextDialect.JAPANESE:
        rendered: list[str] = []

        def render_japanese(
            values: tuple[PackedSymbol, ...], stack: tuple[int, ...] = ()
        ) -> None:
            """Expand Japanese symbols into the enclosing rendered buffer."""

            for symbol in values:
                if symbol.kind is SymbolKind.COMMON:
                    rendered.append(decode_common(symbol.value))
                elif symbol.kind is SymbolKind.EXTENDED:
                    rendered.append(decode_extended(symbol.value))
                elif symbol.kind is SymbolKind.DICTIONARY:
                    index = symbol.value - 1
                    if index < 0 or index >= len(dictionary):
                        rendered.append(f"{{DICT:{symbol.value}}}")
                    elif index in stack:
                        rendered.append(f"{{DICT-LOOP:{symbol.value}}}")
                    else:
                        render_japanese(dictionary[index], (*stack, index))
                elif symbol.kind is SymbolKind.CONTROL:
                    rendered.append(f"{{CTRL:{symbol.value}}}")
                elif symbol.kind is SymbolKind.SEPARATOR:
                    rendered.append("{END}")

        render_japanese(symbols)
        return "".join(rendered)
    if dialect is TextDialect.CURRENT_ENGLISH:
        return _render_english(
            symbols,
            dictionary,
            common_characters=COMMON_CHARACTERS,
            extended_characters=EXTENDED_CHARACTERS,
        )
    return _render_english(
        symbols,
        dictionary,
        common_characters=COMPETITOR_COMMON_CHARACTERS,
        extended_characters=COMPETITOR_EXTENDED_CHARACTERS,
    )


def decode_scenario_file(
    entry: FdsFile,
    record_counts: tuple[int, ...],
    dialect: TextDialect,
) -> DecodedBank:
    """Decode one Time Twist scenario file by stable logical coordinates.

    Args:
        entry: Parsed FDS file with its native ``$A200`` load address.
        record_counts: Known record count for each logical group.
        dialect: Character and extended-dictionary interpretation.

    Returns:
        Rendered records, physical packed sizes, dictionary evidence, and the
        exact ranges consumed from the file.

    Raises:
        ValueError: If pointers leave the file, a dictionary exceeds its
            recovered dialect limit, or any decoded diagnostic token remains.

    The competitor stores logical groups out of address order, so record
    counts—not pointer sorting or adjacent-address boundaries—define alignment.
    This does not relax the canonical project's stricter rebuild parser.
    """

    data = entry.data
    dictionary_offset = _read_pointer(
        data, SCENARIO_HEADER_DICTIONARY_POINTER, entry.load_address
    )
    table_offset = _read_pointer(
        data, SCENARIO_HEADER_GROUP_TABLE_POINTER, entry.load_address
    )
    group_offsets = [
        _read_pointer(
            data, SCENARIO_HEADER_GROUP_ZERO_POINTER, entry.load_address
        )
    ]
    group_offsets.extend(
        _read_pointer(data, table_offset + index * 2, entry.load_address)
        for index in range(len(record_counts) - 1)
    )

    packed_records: list[tuple[int, int, tuple[PackedSymbol, ...], int, int]] = []
    for group_index, (start, count) in enumerate(
        zip(group_offsets, record_counts, strict=True)
    ):
        cursor = start
        for record_index in range(count):
            symbols, end = _decode_one_record(data, cursor, dialect)
            packed_records.append(
                (group_index, record_index, symbols, cursor, end)
            )
            cursor = end

    seed = tuple(record[2] for record in packed_records)
    dictionary, dictionary_end = _decode_dictionary(
        data, dictionary_offset, seed, dialect
    )
    rendered = tuple(
        DecodedRecord(
            group=group,
            record=record,
            text=_render_record(symbols, dictionary, dialect),
            packed_bytes=end - start,
            source_range=(start, end),
        )
        for group, record, symbols, start, end in packed_records
    )
    diagnostics = (
        "{COMMON:",
        "{EXT:",
        "{DICT:",
        "{DICT-LOOP:",
        "{END}",
    )
    failures = [
        f"g{record.group}/r{record.record}: {record.text}"
        for record in rendered
        if any(token in record.text for token in diagnostics)
    ]
    if failures:
        raise ValueError(
            f"{entry.name} has unresolved {dialect.value} symbols: "
            + "; ".join(failures[:3])
        )

    pointer_ranges = (
        (
            SCENARIO_HEADER_DICTIONARY_POINTER,
            SCENARIO_HEADER_DICTIONARY_POINTER + 2,
        ),
        (
            SCENARIO_HEADER_GROUP_TABLE_POINTER,
            SCENARIO_HEADER_GROUP_ZERO_POINTER + 2,
        ),
        (table_offset, table_offset + 2 * (len(record_counts) - 1)),
    )
    return DecodedBank(
        records=rendered,
        dictionary_entries=len(dictionary),
        dictionary_range=(
            (dictionary_offset, dictionary_end) if dictionary else None
        ),
        pointer_ranges=pointer_ranges,
    )
