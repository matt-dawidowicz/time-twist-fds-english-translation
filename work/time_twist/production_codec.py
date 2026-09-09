"""Production-only packed-text extension for the unrestricted English script.

The certified release codec deliberately stops at 68 dictionary entries because
it reclaims otherwise-unused nine-bit extended-glyph codes without changing the
shape of the native prefix tree.  The production retranslation is substantially
larger, so this module adds one further, backward-compatible escape while
leaving the established 1-68 encodings unchanged.

Production dictionary references are encoded as follows::

    1..31    1110xxxxx                  9 bits (native)
    32..68   110xxxxxx                  9 bits (existing English escape)
    69..255  111000000 iiiiiiii        17 bits

Native dictionary index zero is invalid in ordinary text, so ``111000000`` is
available as an unambiguous escape.  The following byte stores the actual
one-based dictionary index.  High entries are therefore used only when their
longer phrases save more space than a 17-bit reference costs.

The production compressor also permits dictionary entries to reference earlier
entries.  Those backward-only references form an acyclic grammar and mirror a
capability already present in source Japanese dictionaries.  Dialogue records
are parsed with dynamic programming so overlapping phrases are chosen by total
encoded bit cost instead of replacement order.

This module is intentionally isolated from :mod:`time_twist.textcodec` and the
68-entry release compressor until the production decoder patch has runtime
coverage.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .compression import compress_english_groups
from .textcodec import (
    BitReader,
    BitWriter,
    EXTENDED_DICTIONARY_ENTRY_COUNT,
    EXTENDED_DICTIONARY_LITERAL_LIMIT,
    NATIVE_DICTIONARY_ENTRY_COUNT,
    PackedSymbol,
    PackedTextError,
    SymbolKind,
    encode_symbol,
)

PRODUCTION_DICTIONARY_ENTRY_COUNT = 255
HIGH_DICTIONARY_FIRST = EXTENDED_DICTIONARY_ENTRY_COUNT + 1
HIGH_DICTIONARY_ESCAPE = 0
DEFAULT_MAX_GRAMMAR_TOKENS = 12
DEFAULT_MAX_NESTING_DEPTH = 4
DEFAULT_TRIAL_CANDIDATES = 6

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]


def production_symbol_bit_length(symbol: PackedSymbol) -> int:
    """Return the encoded width of one production symbol in bits."""
    if symbol.kind is SymbolKind.DICTIONARY:
        if not 1 <= symbol.value <= PRODUCTION_DICTIONARY_ENTRY_COUNT:
            raise PackedTextError(
                f"dictionary value {symbol.value} is out of production range"
            )
        return 9 if symbol.value <= EXTENDED_DICTIONARY_ENTRY_COUNT else 17
    if symbol.kind is SymbolKind.COMMON:
        return 6
    if symbol.kind is SymbolKind.EXTENDED:
        return 9
    if symbol.kind in (SymbolKind.CONTROL, SymbolKind.SEPARATOR):
        return 7
    raise PackedTextError(f"unsupported symbol kind {symbol.kind}")


def encode_production_symbol(writer: BitWriter, symbol: PackedSymbol) -> None:
    """Encode one symbol using the 255-entry production dictionary format."""
    if symbol.kind is not SymbolKind.DICTIONARY:
        encode_symbol(writer, symbol)
        return
    if not 1 <= symbol.value <= PRODUCTION_DICTIONARY_ENTRY_COUNT:
        raise PackedTextError(
            f"dictionary value {symbol.value} is out of production range"
        )
    if symbol.value <= EXTENDED_DICTIONARY_ENTRY_COUNT:
        encode_symbol(writer, symbol)
        return

    # Native dictionary index zero (1110 + 00000) is otherwise invalid.  It is
    # therefore an unambiguous production escape followed by an eight-bit
    # one-based dictionary index.
    writer.write_bits(0b1110, 4)
    writer.write_bits(HIGH_DICTIONARY_ESCAPE, 5)
    writer.write_bits(symbol.value, 8)


def decode_production_symbol(reader: BitReader) -> PackedSymbol:
    """Decode one symbol from the 255-entry production prefix tree."""
    start = reader.bit_position
    first = reader.read_bit()
    second = reader.read_bit()
    if first == 0 or second == 0:
        value = (first << 5) | (second << 4) | reader.read_bits(4)
        kind = SymbolKind.COMMON
    else:
        third = reader.read_bit()
        if third == 0:
            value = reader.read_bits(6)
            if value <= EXTENDED_DICTIONARY_LITERAL_LIMIT:
                kind = SymbolKind.DICTIONARY
                value += 32
            else:
                kind = SymbolKind.EXTENDED
        else:
            fourth = reader.read_bit()
            if fourth == 0:
                value = reader.read_bits(5)
                if value == HIGH_DICTIONARY_ESCAPE:
                    value = reader.read_bits(8)
                    if value < HIGH_DICTIONARY_FIRST:
                        raise PackedTextError(
                            "noncanonical high dictionary reference "
                            f"{value}; expected {HIGH_DICTIONARY_FIRST}..255"
                        )
                kind = SymbolKind.DICTIONARY
            else:
                value = reader.read_bits(3)
                kind = (
                    SymbolKind.SEPARATOR
                    if value == 5
                    else SymbolKind.CONTROL
                )
    return PackedSymbol(kind, value, start, reader.bit_position)


def pack_production_records(
    records: Iterable[tuple[PackedSymbol, ...]],
) -> bytes:
    """Pack records with production dictionary escapes and native alignment."""
    writer = BitWriter()
    separator = PackedSymbol(SymbolKind.SEPARATOR, 5, 0, 0)
    for record in records:
        for symbol in record:
            if symbol.kind is SymbolKind.SEPARATOR:
                raise PackedTextError(
                    "record payload cannot contain a separator"
                )
            encode_production_symbol(writer, symbol)
        encode_production_symbol(writer, separator)
        writer.align_to_next_byte()
    return writer.to_bytes()


def split_production_records(
    data: bytes,
    *,
    offset: int = 0,
    limit: int,
) -> tuple[list[list[PackedSymbol]], int]:
    """Decode an exact number of byte-aligned production records."""
    if offset < 0 or offset > len(data):
        raise ValueError("record offset is outside the stream")
    if limit < 0:
        raise ValueError("record limit cannot be negative")
    reader = BitReader(data, offset * 8)
    records: list[list[PackedSymbol]] = []
    current: list[PackedSymbol] = []
    while len(records) < limit:
        symbol = decode_production_symbol(reader)
        if symbol.kind is SymbolKind.SEPARATOR:
            records.append(current)
            current = []
            reader.align_to_next_byte()
        else:
            current.append(symbol)
    return records, reader.byte_position


def production_packed_size(
    groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
) -> int:
    """Return exact byte size of production groups plus dictionary."""
    return sum(len(pack_production_records(group)) for group in groups) + len(
        pack_production_records(dictionary)
    )


def _validate_dictionary(dictionary: ScenarioDictionary) -> None:
    """Require an acyclic backward-only production dictionary."""
    if len(dictionary) > PRODUCTION_DICTIONARY_ENTRY_COUNT:
        raise ValueError(
            f"dictionary has {len(dictionary)} entries; production maximum is "
            f"{PRODUCTION_DICTIONARY_ENTRY_COUNT}"
        )
    for entry_index, entry in enumerate(dictionary, start=1):
        if not entry:
            raise ValueError(f"dictionary entry {entry_index} is empty")
        for symbol in entry:
            if symbol.kind in (SymbolKind.CONTROL, SymbolKind.SEPARATOR):
                raise ValueError(
                    f"dictionary entry {entry_index} contains control data"
                )
            if symbol.kind is SymbolKind.DICTIONARY:
                if not 1 <= symbol.value < entry_index:
                    raise ValueError(
                        f"dictionary entry {entry_index} references "
                        f"non-earlier entry {symbol.value}"
                    )


def _dictionary_expansions(
    dictionary: ScenarioDictionary,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Expand a validated backward-only dictionary to literal sequences."""
    _validate_dictionary(dictionary)
    expanded: list[tuple[PackedSymbol, ...]] = []
    for entry_index, entry in enumerate(dictionary, start=1):
        output: list[PackedSymbol] = []
        for symbol in entry:
            if symbol.kind is SymbolKind.DICTIONARY:
                output.extend(expanded[symbol.value - 1])
            elif symbol.kind in (SymbolKind.COMMON, SymbolKind.EXTENDED):
                output.append(symbol)
            else:  # pragma: no cover - guarded by _validate_dictionary.
                raise ValueError(
                    f"dictionary entry {entry_index} contains unsupported data"
                )
        expanded.append(tuple(output))
    return tuple(expanded)


def _dictionary_depths(dictionary: ScenarioDictionary) -> tuple[int, ...]:
    """Return one-based grammar depth for every validated dictionary entry."""
    _validate_dictionary(dictionary)
    depths: list[int] = []
    for entry in dictionary:
        referenced = [
            depths[symbol.value - 1]
            for symbol in entry
            if symbol.kind is SymbolKind.DICTIONARY
        ]
        depths.append(1 + max(referenced, default=0))
    return tuple(depths)


def _optimal_parse_record(
    record: tuple[PackedSymbol, ...],
    dictionary: ScenarioDictionary,
    expansions: tuple[tuple[PackedSymbol, ...], ...] | None = None,
) -> tuple[PackedSymbol, ...]:
    """Choose the lowest-bit literal/reference parse for one source record."""
    if any(symbol.kind is SymbolKind.DICTIONARY for symbol in record):
        raise ValueError("optimal parser expects uncompressed source records")
    if expansions is None:
        expansions = _dictionary_expansions(dictionary)

    by_first: dict[PackedSymbol, list[tuple[int, tuple[PackedSymbol, ...]]]] = {}
    for index, expansion in enumerate(expansions, start=1):
        if not expansion:
            continue
        by_first.setdefault(expansion[0], []).append((index, expansion))

    length = len(record)
    best_bits = [0] * (length + 1)
    best_tokens: list[tuple[PackedSymbol, ...]] = [()] * (length + 1)
    for position in range(length - 1, -1, -1):
        symbol = record[position]
        literal_bits = production_symbol_bit_length(symbol) + best_bits[position + 1]
        chosen_bits = literal_bits
        chosen = (symbol, *best_tokens[position + 1])

        if symbol.kind in (SymbolKind.COMMON, SymbolKind.EXTENDED):
            for index, expansion in by_first.get(symbol, ()):  # type: ignore[arg-type]
                end = position + len(expansion)
                if end > length or tuple(record[position:end]) != expansion:
                    continue
                reference = PackedSymbol(SymbolKind.DICTIONARY, index, 0, 0)
                bits = production_symbol_bit_length(reference) + best_bits[end]
                trial = (reference, *best_tokens[end])
                if bits < chosen_bits or (
                    bits == chosen_bits and len(trial) < len(chosen)
                ):
                    chosen_bits = bits
                    chosen = trial

        best_bits[position] = chosen_bits
        best_tokens[position] = chosen
    return best_tokens[0]


def optimal_parse_groups(
    groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
) -> ScenarioGroups:
    """Reparse literal source groups optimally against one dictionary."""
    expansions = _dictionary_expansions(dictionary)
    return tuple(
        tuple(
            _optimal_parse_record(record, dictionary, expansions)
            for record in group
        )
        for group in groups
    )


def _candidate_counts(
    groups: ScenarioGroups,
    *,
    maximum_tokens: int,
) -> Counter[tuple[PackedSymbol, ...]]:
    """Count repeated substrings in the currently optimal token stream."""
    counts: Counter[tuple[PackedSymbol, ...]] = Counter()
    for group in groups:
        for record in group:
            segment: list[PackedSymbol] = []
            for symbol in (*record, None):
                if symbol is not None and symbol.kind is not SymbolKind.CONTROL:
                    segment.append(symbol)
                    continue
                for start in range(len(segment)):
                    maximum = min(maximum_tokens, len(segment) - start)
                    for size in range(2, maximum + 1):
                        counts[tuple(segment[start : start + size])] += 1
                segment = []
    return counts


def _candidate_depth(
    candidate: tuple[PackedSymbol, ...],
    depths: tuple[int, ...],
) -> int:
    referenced = [
        depths[symbol.value - 1]
        for symbol in candidate
        if symbol.kind is SymbolKind.DICTIONARY
    ]
    return 1 + max(referenced, default=0)


def _candidate_expansion(
    candidate: tuple[PackedSymbol, ...],
    expansions: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[PackedSymbol, ...]:
    output: list[PackedSymbol] = []
    for symbol in candidate:
        if symbol.kind is SymbolKind.DICTIONARY:
            output.extend(expansions[symbol.value - 1])
        else:
            output.append(symbol)
    return tuple(output)


def _rank_grammar_candidates(
    parsed_groups: ScenarioGroups,
    dictionary: ScenarioDictionary,
    *,
    next_index: int,
    maximum_tokens: int,
    maximum_depth: int,
) -> list[tuple[int, tuple[PackedSymbol, ...]]]:
    """Rank nested grammar entries by conservative estimated bit saving."""
    counts = _candidate_counts(parsed_groups, maximum_tokens=maximum_tokens)
    depths = _dictionary_depths(dictionary)
    expansions = _dictionary_expansions(dictionary)
    existing_expansions = set(expansions)
    reference = PackedSymbol(SymbolKind.DICTIONARY, next_index, 0, 0)
    reference_bits = production_symbol_bit_length(reference)
    ranked: list[tuple[int, tuple[PackedSymbol, ...]]] = []

    for candidate, count in counts.items():
        if count < 2:
            continue
        if _candidate_depth(candidate, depths) > maximum_depth:
            continue
        expanded = _candidate_expansion(candidate, expansions)
        if expanded in existing_expansions:
            continue
        candidate_bits = sum(production_symbol_bit_length(s) for s in candidate)
        if candidate_bits <= reference_bits:
            continue
        entry_bits = len(pack_production_records((candidate,))) * 8
        estimated = count * (candidate_bits - reference_bits) - entry_bits
        if estimated > 0:
            ranked.append((estimated, candidate))

    ranked.sort(
        key=lambda item: (
            item[0],
            len(item[1]),
            tuple((symbol.kind.value, symbol.value) for symbol in item[1]),
        ),
        reverse=True,
    )
    return ranked


def compress_production_groups(
    groups: ScenarioGroups,
    *,
    required_entries: ScenarioDictionary = (),
    maximum_entries: int = PRODUCTION_DICTIONARY_ENTRY_COUNT,
    maximum_grammar_tokens: int = DEFAULT_MAX_GRAMMAR_TOKENS,
    maximum_nesting_depth: int = DEFAULT_MAX_NESTING_DEPTH,
    trial_candidates: int = DEFAULT_TRIAL_CANDIDATES,
) -> tuple[ScenarioGroups, ScenarioDictionary]:
    """Compress English with 68 cheap slots plus profitable 69-255 grammar slots.

    The first stage reuses the established flat English compressor for at most
    68 entries.  The source records are then reparsed optimally against that
    dictionary.  Additional entries are selected from repeated sequences in
    the optimal token stream; they may reference earlier dictionary entries,
    but never controls or later entries.  A proposed high entry is retained
    only when an exact repack of groups plus dictionary becomes smaller.
    """
    if not 1 <= maximum_entries <= PRODUCTION_DICTIONARY_ENTRY_COUNT:
        raise ValueError("maximum production dictionary entries is out of range")
    if maximum_grammar_tokens < 2:
        raise ValueError("maximum_grammar_tokens must be at least two")
    if maximum_nesting_depth < 1:
        raise ValueError("maximum_nesting_depth must be positive")
    if trial_candidates < 1:
        raise ValueError("trial_candidates must be positive")
    if any(
        symbol.kind is SymbolKind.DICTIONARY
        for group in groups
        for record in group
        for symbol in record
    ):
        raise ValueError("production compressor expects literal source groups")

    low_limit = min(maximum_entries, EXTENDED_DICTIONARY_ENTRY_COUNT)
    _, low_dictionary = compress_english_groups(
        groups,
        required_entries=required_entries,
        maximum_entries=low_limit,
        optimize=False,
    )
    dictionary: ScenarioDictionary = low_dictionary
    _validate_dictionary(dictionary)
    parsed = optimal_parse_groups(groups, dictionary)
    current_size = production_packed_size(parsed, dictionary)

    while len(dictionary) < maximum_entries:
        next_index = len(dictionary) + 1
        ranked = _rank_grammar_candidates(
            parsed,
            dictionary,
            next_index=next_index,
            maximum_tokens=maximum_grammar_tokens,
            maximum_depth=maximum_nesting_depth,
        )
        if not ranked:
            break

        best_size = current_size
        best_dictionary: ScenarioDictionary | None = None
        best_parsed: ScenarioGroups | None = None
        for _, candidate in ranked[:trial_candidates]:
            trial_dictionary = (*dictionary, candidate)
            trial_parsed = optimal_parse_groups(groups, trial_dictionary)
            trial_size = production_packed_size(trial_parsed, trial_dictionary)
            if trial_size < best_size:
                best_size = trial_size
                best_dictionary = trial_dictionary
                best_parsed = trial_parsed

        if best_dictionary is None or best_parsed is None:
            break
        dictionary = best_dictionary
        parsed = best_parsed
        current_size = best_size

    return parsed, dictionary
