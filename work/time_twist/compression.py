"""Build compact dictionaries that the original scenario engine can decode.

The game offers 31 one-based dictionary references.  Each reference costs
nine bits, so a repeated literal sequence is useful only when the references
save more space than the packed dictionary entry consumes.  The compressor
uses deterministic greedy selection and creates flat entries containing only
literal common/extended symbols.

The result is not a general-purpose optimal compressor.  It is designed around
the game's fixed RAM reservation, native prefix tree, byte-aligned record
separators, and fixed tables that may require particular entries.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .textcodec import PackedSymbol, SymbolKind, pack_records


MAX_DICTIONARY_ENTRIES = 31
MAX_CANDIDATE_TOKENS = 32
MAX_CANDIDATES_TO_EVALUATE = 200


def symbol_bit_length(symbol: PackedSymbol) -> int:
    """Return the native encoded width of a record payload symbol.

    Args:
        symbol: Common, extended, dictionary, or ordinary control token.

    Returns:
        Encoded width in bits, excluding record alignment.

    Raises:
        ValueError: If ``symbol`` is a separator or has an unsupported kind.
    """

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
    """Measure the complete packed text and dictionary footprint.

    Args:
        groups: Scenario records grouped in pointer-table order.
        dictionary: Ordered, one-based dictionary entries.

    Returns:
        Total byte count after separators and per-record alignment are applied.

    The function deliberately repacks the data instead of summing token widths
    because separator alignment can change the true byte cost.
    """

    return sum(len(pack_records(group)) for group in groups) + len(
        pack_records(dictionary)
    )


def _record_packed_size(record: tuple[PackedSymbol, ...]) -> int:
    """Return exact aligned bytes for one payload plus its separator."""

    bits = sum(symbol_bit_length(symbol) for symbol in record) + 7
    return (bits + 7) // 8


def _symbol_key(symbol: PackedSymbol) -> int:
    """Map every native symbol kind/value to one collision-free byte."""

    if symbol.kind is SymbolKind.COMMON:
        return symbol.value
    if symbol.kind is SymbolKind.EXTENDED:
        return 0x40 + symbol.value
    if symbol.kind is SymbolKind.DICTIONARY:
        return 0x80 + symbol.value
    if symbol.kind is SymbolKind.CONTROL:
        return 0xC0 + symbol.value
    raise ValueError(f"unsupported record symbol {symbol.kind}")


def _prepared_records(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> tuple[tuple[bytes, int], ...]:
    """Cache byte-search keys and payload bit lengths for one iteration."""

    return tuple(
        (
            bytes(_symbol_key(symbol) for symbol in record),
            sum(symbol_bit_length(symbol) for symbol in record),
        )
        for group in groups
        for record in group
    )


def _non_overlapping_byte_occurrences(haystack: bytes, needle: bytes) -> int:
    """Count deterministic leftmost non-overlapping matches using C-level find."""

    count = 0
    position = 0
    while True:
        position = haystack.find(needle, position)
        if position < 0:
            return count
        count += 1
        position += len(needle)


def _candidate_packed_size(
    prepared_records: tuple[tuple[bytes, int], ...],
    dictionary_size: int,
    candidate: tuple[PackedSymbol, ...],
) -> int:
    """Measure a candidate exactly without rebuilding and repacking all groups."""

    candidate_key = bytes(_symbol_key(symbol) for symbol in candidate)
    literal_bits = sum(symbol_bit_length(symbol) for symbol in candidate)
    delta_bits = literal_bits - 9
    group_size = 0
    for record_key, old_bits in prepared_records:
        replacements = _non_overlapping_byte_occurrences(
            record_key, candidate_key
        )
        new_bits = old_bits - replacements * delta_bits
        group_size += (new_bits + 14) // 8
    return group_size + dictionary_size + _record_packed_size(candidate)


def _candidate_counts(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> Counter[tuple[PackedSymbol, ...]]:
    """Count repeated literal substrings that are legal flat entries.

    Args:
        groups: Current scenario groups, possibly already containing
            dictionary references selected during an earlier iteration.

    Returns:
        Occurrence counts for every two-to-32-token candidate.

    Existing references and control tokens split candidate regions. This
    prevents nested dictionaries and preserves control placement. Overlapping
    occurrences are counted for ranking; actual replacement is non-overlapping.
    """

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
    """Replace leftmost, non-overlapping candidate occurrences.

    Args:
        groups: Current scenario group structure.
        candidate: Literal token sequence to replace.
        reference: One-based dictionary symbol assigned to the candidate.

    Returns:
        A new immutable group structure. Input tuples and symbols are not
        modified.

    Replacement restarts after the full match, making the result deterministic
    even when a candidate overlaps with itself.
    """

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
    """Return compressed groups and a flat native-compatible dictionary.

    Args:
        groups: Fully encoded English scenario groups with no separators.
        required_entries: Literal entries that must occupy the first dictionary
            slots because fixed-address text outside the groups references
            them.

    Returns:
        A pair of compressed groups and the ordered flat dictionary.

    Raises:
        ValueError: If required entries exceed the 31-slot limit, are empty or
            duplicated, or contain non-literal tokens.

    ``required_entries`` lets a bank reserve dictionary slots for packed text
    outside its normal scenario groups.  Those entries are installed first,
    then the remaining slots are selected greedily from the scenario corpus.

    Candidate ranking starts with an inexpensive bit-saving estimate.  The
    best 200 candidates are then measured by repacking the complete groups and
    dictionary, which accounts for separator alignment.  Selection stops when
    no candidate reduces the final byte count or all 31 slots are occupied.

    The transformation is deterministic and side-effect free: identical input
    produces identical group symbols, dictionary order, and packed size.
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
        prepared_records = _prepared_records(compressed)
        dictionary_size = sum(
            _record_packed_size(entry) for entry in dictionary
        )
        for _, candidate in ranked[:MAX_CANDIDATES_TO_EVALUATE]:
            candidate_size = _candidate_packed_size(
                prepared_records, dictionary_size, candidate
            )
            if candidate_size < best_size:
                best_candidate = candidate
                best_size = candidate_size

        if best_candidate is not None:
            best_groups = _replace_candidate(
                compressed, best_candidate, reference
            )

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
    """Recursively expand references and reject out-of-range values or loops.

    Args:
        symbols: Record or dictionary-entry symbols to expand.
        dictionary: Ordered one-based dictionary entries.
        _stack: Internal recursion path used for cycle detection. Callers
            should leave this at its default.

    Returns:
        A flat symbol tuple with every dictionary reference expanded.

    Raises:
        ValueError: If a reference is zero, exceeds the dictionary, or creates
            a direct or indirect loop.

    English dictionaries are flat, but this accepts nested source dictionaries
    so verification can compare fully expanded symbols in either form. Inputs
    are not modified.
    """

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
