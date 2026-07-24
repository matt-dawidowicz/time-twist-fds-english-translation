"""Build compact native dictionaries for fully translated scenario banks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .textcodec import PackedSymbol, SymbolKind, pack_records


MAX_DICTIONARY_ENTRIES = 31
MAX_CANDIDATE_TOKENS = 32
MAX_CANDIDATES_TO_EVALUATE = 200


def symbol_bit_length(symbol: PackedSymbol) -> int:
    if symbol.kind is SymbolKind.COMMON:
        return 6
    if symbol.kind in (SymbolKind.EXTENDED, SymbolKind.DICTIONARY):
        return 9
    if symbol.kind is SymbolKind.CONTROL:
        return 7
    raise ValueError(f"unsupported record symbol {symbol.kind}")


def packed_size(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
) -> int:
    return sum(len(pack_records(group)) for group in groups) + len(
        pack_records(dictionary)
    )


def _candidate_counts(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> Counter[tuple[PackedSymbol, ...]]:
    counts: Counter[tuple[PackedSymbol, ...]] = Counter()
    for group in groups:
        for record in group:
            segment: list[PackedSymbol] = []
            for symbol in (*record, None):
                # Original Time Twist banks only use literal glyphs inside
                # dictionary entries. Treat references and controls as hard
                # boundaries so newly selected entries stay flat as well.
                if symbol is not None and symbol.kind in (
                    SymbolKind.COMMON,
                    SymbolKind.EXTENDED,
                ):
                    segment.append(symbol)
                    continue
                for start in range(len(segment)):
                    maximum = min(MAX_CANDIDATE_TOKENS, len(segment) - start)
                    for length in range(2, maximum + 1):
                        counts[tuple(segment[start : start + length])] += 1
                segment = []
    return counts


def _replace_candidate(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    candidate: tuple[PackedSymbol, ...],
    reference: PackedSymbol,
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    candidate_length = len(candidate)
    rebuilt_groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    for group in groups:
        rebuilt_records: list[tuple[PackedSymbol, ...]] = []
        for record in group:
            rebuilt: list[PackedSymbol] = []
            position = 0
            while position < len(record):
                if tuple(record[position : position + candidate_length]) == candidate:
                    rebuilt.append(reference)
                    position += candidate_length
                else:
                    rebuilt.append(record[position])
                    position += 1
            rebuilt_records.append(tuple(rebuilt))
        rebuilt_groups.append(tuple(rebuilt_records))
    return tuple(rebuilt_groups)


def compress_english_groups(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Return groups and a flat native-compatible dictionary, chosen greedily.

    ``required_entries`` lets a bank reserve dictionary slots for packed text
    outside its normal scenario groups.  Those entries are installed first,
    then the remaining slots are selected with the ordinary scenario corpus.
    """

    if len(required_entries) > MAX_DICTIONARY_ENTRIES:
        raise ValueError("too many required dictionary entries")
    if len(set(required_entries)) != len(required_entries):
        raise ValueError("required dictionary entries must be unique")
    if any(not entry for entry in required_entries):
        raise ValueError("required dictionary entries must be nonempty")
    if any(
        symbol.kind not in (SymbolKind.COMMON, SymbolKind.EXTENDED)
        for entry in required_entries
        for symbol in entry
    ):
        raise ValueError("required dictionary entries must contain literal glyphs")

    compressed = groups
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    for candidate in required_entries:
        reference = PackedSymbol(
            SymbolKind.DICTIONARY, len(dictionary) + 1, 0, 0
        )
        compressed = _replace_candidate(compressed, candidate, reference)
        dictionary = (*dictionary, candidate)
    current_size = packed_size(compressed, dictionary)

    while len(dictionary) < MAX_DICTIONARY_ENTRIES:
        counts = _candidate_counts(compressed)
        ranked: list[tuple[int, tuple[PackedSymbol, ...]]] = []
        for candidate, count in counts.items():
            if count < 2:
                continue
            literal_bits = sum(symbol_bit_length(symbol) for symbol in candidate)
            entry_bits = len(pack_records((candidate,))) * 8
            estimated_saving = count * (literal_bits - 9) - entry_bits
            if estimated_saving > 0:
                ranked.append((estimated_saving, candidate))
        ranked.sort(key=lambda item: item[0], reverse=True)

        best_groups = None
        best_candidate = None
        best_size = current_size
        reference = PackedSymbol(
            SymbolKind.DICTIONARY, len(dictionary) + 1, 0, 0
        )
        for _, candidate in ranked[:MAX_CANDIDATES_TO_EVALUATE]:
            candidate_groups = _replace_candidate(compressed, candidate, reference)
            candidate_dictionary = (*dictionary, candidate)
            candidate_size = packed_size(candidate_groups, candidate_dictionary)
            if candidate_size < best_size:
                best_groups = candidate_groups
                best_candidate = candidate
                best_size = candidate_size

        if best_groups is None or best_candidate is None:
            break
        compressed = best_groups
        dictionary = (*dictionary, best_candidate)
        current_size = best_size

    return compressed, dictionary


def expand_dictionary_symbols(
    symbols: Iterable[PackedSymbol],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    *,
    _stack: tuple[int, ...] = (),
) -> tuple[PackedSymbol, ...]:
    """Expand nested dictionary references for encoder verification."""

    expanded: list[PackedSymbol] = []
    for symbol in symbols:
        if symbol.kind is not SymbolKind.DICTIONARY:
            expanded.append(symbol)
            continue
        index = symbol.value - 1
        if index < 0 or index >= len(dictionary):
            raise ValueError(f"dictionary reference {symbol.value} is out of range")
        if index in _stack:
            raise ValueError(f"dictionary loop at reference {symbol.value}")
        expanded.extend(
            expand_dictionary_symbols(
                dictionary[index], dictionary, _stack=(*_stack, index)
            )
        )
    return tuple(expanded)
