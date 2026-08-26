"""Build compact dictionaries that the original scenario engine can decode.

The game offers 31 one-based dictionary references.  Each reference costs
nine bits, so a repeated literal sequence is useful only when the references
save more space than the packed dictionary entry consumes.  The fast path uses
deterministic greedy selection.  Release builds additionally compare bounded
beam search and fixed-prefix-safe dictionary reordering, keeping the smallest
exact result.  Every path creates flat entries containing only literal
common/extended symbols.

The result is not a general-purpose optimal compressor.  It is designed around
the game's fixed RAM reservation, native prefix tree, byte-aligned record
separators, and fixed tables that may require particular entries.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable

from .textcodec import (
    EXTENDED_DICTIONARY_ENTRY_COUNT,
    NATIVE_DICTIONARY_ENTRY_COUNT,
    PackedSymbol,
    SymbolKind,
    pack_records,
)

MAX_DICTIONARY_ENTRIES = NATIVE_DICTIONARY_ENTRY_COUNT
MAX_CANDIDATE_TOKENS = 32
MAX_CANDIDATES_TO_EVALUATE = 200
DEFAULT_BEAM_WIDTH = 4
DEFAULT_BEAM_BRANCH_FACTOR = 4
EXTENDED_BEAM_WIDTH = 12
EXTENDED_BEAM_BRANCH_FACTOR = 8
EXTENDED_BEAM_HEADROOM_BYTES = 16


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
                if (
                    tuple(record[position : position + candidate_length])
                    == candidate
                ):
                    rebuilt.append(reference)
                    position += candidate_length
                else:
                    rebuilt.append(record[position])
                    position += 1
            rebuilt_records.append(tuple(rebuilt))
        rebuilt_groups.append(tuple(rebuilt_records))
    return tuple(rebuilt_groups)


def _validate_required_entries(
    required_entries: tuple[tuple[PackedSymbol, ...], ...],
    *,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
) -> None:
    """Reject required dictionary entries that the native format cannot use."""
    if len(required_entries) > maximum_entries:
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
        raise ValueError(
            "required dictionary entries must contain literal glyphs"
        )


def _install_required_entries(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    required_entries: tuple[tuple[PackedSymbol, ...], ...],
    *,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Install fixed-UI dictionary entries before optional compression."""
    _validate_required_entries(
        required_entries,
        maximum_entries=maximum_entries,
    )
    compressed = groups
    dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    for candidate in required_entries:
        reference = PackedSymbol(
            SymbolKind.DICTIONARY, len(dictionary) + 1, 0, 0
        )
        compressed = _replace_candidate(compressed, candidate, reference)
        dictionary = (*dictionary, candidate)
    return compressed, dictionary


def _rank_candidates(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
) -> list[tuple[int, tuple[PackedSymbol, ...]]]:
    """Rank legal flat dictionary candidates by estimated bit savings."""
    ranked: list[tuple[int, tuple[PackedSymbol, ...]]] = []
    for candidate, count in _candidate_counts(groups).items():
        if count < 2:
            continue
        literal_bits = sum(symbol_bit_length(symbol) for symbol in candidate)
        entry_bits = len(pack_records((candidate,))) * 8
        estimated_saving = count * (literal_bits - 9) - entry_bits
        if estimated_saving > 0:
            ranked.append((estimated_saving, candidate))
    # Counter preserves deterministic traversal order for equal estimates.
    # Retain the established greedy tie behavior so introducing alternative
    # searches does not silently change the baseline release output.
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked


def _dictionary_key(
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[bytes, ...]:
    """Return a deterministic sortable identity for one dictionary."""
    return tuple(
        bytes(_symbol_key(symbol) for symbol in entry) for entry in dictionary
    )


def _compression_result_key(
    result: tuple[
        tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
        tuple[tuple[PackedSymbol, ...], ...],
    ],
) -> tuple[int, int, tuple[bytes, ...]]:
    """Sort compression results by bytes, entry count, then exact identity."""
    groups, dictionary = result
    return (
        packed_size(groups, dictionary),
        len(dictionary),
        _dictionary_key(dictionary),
    )


def _compress_english_groups_beam(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
    beam_width: int = DEFAULT_BEAM_WIDTH,
    branch_factor: int = DEFAULT_BEAM_BRANCH_FACTOR,
    candidate_limit: int | None = MAX_CANDIDATES_TO_EVALUATE,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Search several dictionary-selection paths and return the smallest.

    Greedy compression commits permanently to the best immediate candidate.
    That can miss a smaller final dictionary when two individually attractive
    substrings overlap.  This bounded beam keeps several exact-size successors
    at every dictionary depth while retaining the native flat-entry contract.

    The search is deterministic.  ``beam_width`` bounds the number of states
    retained at each depth, ``branch_factor`` bounds successors per state, and
    ``candidate_limit`` bounds the estimated candidate shortlist evaluated
    with the exact byte-aligned size model.
    """
    if beam_width < 1:
        raise ValueError("beam_width must be positive")
    if branch_factor < 1:
        raise ValueError("branch_factor must be positive")
    if candidate_limit is not None and candidate_limit < 1:
        raise ValueError("candidate_limit must be positive or None")

    initial_groups, initial_dictionary = _install_required_entries(
        groups,
        required_entries,
        maximum_entries=maximum_entries,
    )
    initial_size = packed_size(initial_groups, initial_dictionary)
    beam = [(initial_size, initial_groups, initial_dictionary)]
    best = beam[0]

    while beam and len(beam[0][2]) < maximum_entries:
        successors: list[
            tuple[
                int,
                tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
                tuple[tuple[PackedSymbol, ...], ...],
            ]
        ] = []
        for current_size, compressed, dictionary in beam:
            ranked = _rank_candidates(compressed)
            if candidate_limit is not None:
                ranked = ranked[:candidate_limit]
            prepared_records = _prepared_records(compressed)
            dictionary_size = sum(
                _record_packed_size(entry) for entry in dictionary
            )
            evaluated: list[tuple[int, bytes, tuple[PackedSymbol, ...]]] = []
            for _, candidate in ranked:
                candidate_size = _candidate_packed_size(
                    prepared_records, dictionary_size, candidate
                )
                if candidate_size < current_size:
                    evaluated.append(
                        (
                            candidate_size,
                            bytes(_symbol_key(symbol) for symbol in candidate),
                            candidate,
                        )
                    )
            evaluated.sort(key=lambda item: (item[0], item[1]))
            reference = PackedSymbol(
                SymbolKind.DICTIONARY, len(dictionary) + 1, 0, 0
            )
            for candidate_size, _, candidate in evaluated[:branch_factor]:
                next_groups = _replace_candidate(
                    compressed, candidate, reference
                )
                successors.append(
                    (
                        candidate_size,
                        next_groups,
                        (*dictionary, candidate),
                    )
                )

        if not successors:
            break
        unique: dict[
            tuple[bytes, ...],
            tuple[
                int,
                tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
                tuple[tuple[PackedSymbol, ...], ...],
            ],
        ] = {}
        for state in successors:
            key = _dictionary_key(state[2])
            previous = unique.get(key)
            if previous is None or state[0] < previous[0]:
                unique[key] = state
        beam = sorted(
            unique.values(),
            key=lambda state: (state[0], _dictionary_key(state[2])),
        )[:beam_width]
        if (beam[0][0], _dictionary_key(beam[0][2])) < (
            best[0],
            _dictionary_key(best[2]),
        ):
            best = beam[0]

    return best[1], best[2]


def _reapply_dictionary(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Apply one complete flat dictionary to uncompressed groups in order."""
    compressed = groups
    rebuilt_dictionary: tuple[tuple[PackedSymbol, ...], ...] = ()
    for candidate in dictionary:
        reference = PackedSymbol(
            SymbolKind.DICTIONARY, len(rebuilt_dictionary) + 1, 0, 0
        )
        compressed = _replace_candidate(compressed, candidate, reference)
        rebuilt_dictionary = (*rebuilt_dictionary, candidate)
    return compressed, rebuilt_dictionary


def _improve_dictionary_order(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    *,
    required_entry_count: int = 0,
    max_passes: int = 5,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Hill-climb optional entry order without changing fixed-UI indices.

    Flat dictionary entries can overlap.  Reordering two optional entries can
    therefore change which literal occurrences are replaced even though the
    dictionary contains the same text.  Required entries remain an immutable
    prefix because fixed-address UI records reference their exact indices.
    """
    if required_entry_count < 0 or required_entry_count > len(dictionary):
        raise ValueError("required_entry_count is outside the dictionary")
    if max_passes < 1:
        raise ValueError("max_passes must be positive")
    _validate_required_entries(dictionary)

    order = list(dictionary)
    best = _reapply_dictionary(groups, tuple(order))
    best_size = packed_size(*best)
    for _ in range(max_passes):
        improved = False
        for left in range(required_entry_count, len(order)):
            for right in range(left + 1, len(order)):
                trial_order = order.copy()
                trial_order[left], trial_order[right] = (
                    trial_order[right],
                    trial_order[left],
                )
                trial = _reapply_dictionary(groups, tuple(trial_order))
                trial_size = packed_size(*trial)
                if trial_size < best_size:
                    order = trial_order
                    best = trial
                    best_size = trial_size
                    improved = True
        if not improved:
            break
    return best


def _compress_english_groups_greedy(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
    candidate_limit: int | None = MAX_CANDIDATES_TO_EVALUATE,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
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
        candidate_limit: Maximum estimated candidates measured per greedy
            iteration, or ``None`` for exhaustive positive-saving evaluation.
        maximum_entries: Dictionary limit supported by the target decoder.

    Returns:
        A pair of compressed groups and the ordered flat dictionary.

    Raises:
        ValueError: If required entries exceed ``maximum_entries``, are empty
            or duplicated, or contain non-literal tokens.

    ``required_entries`` lets a bank reserve dictionary slots for packed text
    outside its normal scenario groups.  Those entries are installed first,
    then the remaining slots are selected greedily from the scenario corpus.

    Candidate ranking starts with an inexpensive bit-saving estimate.  The
    best 200 candidates are then measured by repacking the complete groups and
    dictionary, which accounts for separator alignment.  Selection stops when
    no candidate reduces the final byte count or all requested slots are
    occupied.

    The transformation is deterministic and side-effect free: identical input
    produces identical group symbols, dictionary order, and packed size.
    """
    compressed, dictionary = _install_required_entries(
        groups,
        required_entries,
        maximum_entries=maximum_entries,
    )
    current_size = packed_size(compressed, dictionary)

    while len(dictionary) < maximum_entries:
        ranked = _rank_candidates(compressed)

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
        candidates = (
            ranked if candidate_limit is None else ranked[:candidate_limit]
        )
        for _, candidate in candidates:
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


def compress_english_groups(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
    max_bytes: int | None = None,
    optimize: bool = False,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
    candidate_validator: (
        Callable[
            [
                tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
                tuple[tuple[PackedSymbol, ...], ...],
            ],
            bool,
        ]
        | None
    ) = None,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Compress groups, widening search on capacity or dictionary-count failure.

    Args:
        groups: Fully encoded English scenario groups with no separators.
        required_entries: Literal entries reserved for fixed-address text. A
            project-supplied tuple may additionally require all 31 slots so a
            fixed-address UI patch never decodes beyond the generated dictionary.
        max_bytes: Optional packed groups-plus-dictionary byte reservation.
        optimize: Compare the established greedy result with deterministic
            beam search and fixed-prefix-safe dictionary-order hill climbing.
            Release and complete-scenario build paths enable this explicitly;
            generic and property-test callers retain the fast greedy default.
        maximum_entries: Maximum dictionary entries accepted by the target
            decoder. The native format supports 31; the guarded English NOV2
            extension supports up to 68.
        candidate_validator: Optional release-level compatibility check for
            optimized candidates. Results that return false are excluded
            before the exact-size minimum is selected.

    Returns:
        Compressed groups and ordered flat dictionary.

    Raises:
        ValueError: If ``max_bytes`` is negative, required entries are invalid,
            or a full-dictionary caller cannot populate ``maximum_entries``.

    The normal pass evaluates only the top estimated candidates for each greedy
    step. If that result exceeds ``max_bytes`` or a fixed-UI caller requires
    every requested entry but the fast pass stops early, a deterministic
    fallback reruns
    greedy selection while evaluating every positive-saving candidate. For a
    full-dictionary request the exhaustive result must contain every requested
    entry;
    otherwise the build fails closed instead of letting a later UI patch read
    following code/data as dictionary records.

    With ``optimize=True``, the valid greedy result is also compared against a
    bounded beam and dictionary-order hill climb. Tight reservations receive a
    wider beam. The smallest exact result wins; an alternative path can never
    make a release bank larger than the established greedy result.
    """
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")
    if not 1 <= maximum_entries <= EXTENDED_DICTIONARY_ENTRY_COUNT:
        raise ValueError("maximum dictionary entries is out of range")
    requires_full_dictionary = bool(
        getattr(required_entries, "requires_full_dictionary", False)
    )
    if optimize:
        baseline = compress_english_groups(
            groups,
            required_entries=required_entries,
            max_bytes=max_bytes,
            optimize=False,
            maximum_entries=maximum_entries,
        )
        candidates = [
            baseline,
            _compress_english_groups_beam(
                groups,
                required_entries=required_entries,
                maximum_entries=maximum_entries,
            ),
            _improve_dictionary_order(
                groups,
                baseline[1],
                required_entry_count=len(required_entries),
            ),
        ]
        baseline_size = packed_size(*baseline)
        headroom = None if max_bytes is None else max_bytes - baseline_size
        if headroom is not None and headroom <= EXTENDED_BEAM_HEADROOM_BYTES:
            candidates.append(
                _compress_english_groups_beam(
                    groups,
                    required_entries=required_entries,
                    beam_width=EXTENDED_BEAM_WIDTH,
                    branch_factor=EXTENDED_BEAM_BRANCH_FACTOR,
                    maximum_entries=maximum_entries,
                )
            )
        if requires_full_dictionary:
            candidates = [
                result
                for result in candidates
                if len(result[1]) == maximum_entries
            ]
        if candidate_validator is not None:
            candidates = [
                result for result in candidates if candidate_validator(*result)
            ]
        if not candidates:
            raise ValueError(
                "no compression candidate satisfies the release constraints"
            )
        return min(candidates, key=_compression_result_key)

    primary = _compress_english_groups_greedy(
        groups,
        required_entries=required_entries,
        candidate_limit=MAX_CANDIDATES_TO_EVALUATE,
        maximum_entries=maximum_entries,
    )
    primary_size = packed_size(*primary)
    primary_complete = (
        not requires_full_dictionary
        or len(primary[1]) == maximum_entries
    )
    if (max_bytes is None or primary_size <= max_bytes) and primary_complete:
        return primary

    fallback = _compress_english_groups_greedy(
        groups,
        required_entries=required_entries,
        candidate_limit=None,
        maximum_entries=maximum_entries,
    )
    fallback_size = packed_size(*fallback)
    if requires_full_dictionary:
        if len(fallback[1]) != maximum_entries:
            raise ValueError(
                f"fixed-address UI requires exactly {maximum_entries} "
                "dictionary entries; "
                f"compressor produced {len(fallback[1])}"
            )
        return fallback
    if fallback_size < primary_size:
        return fallback
    return primary


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
            raise ValueError(
                f"dictionary reference {symbol.value} is out of range"
            )
        if index in _stack:
            raise ValueError(f"dictionary loop at reference {symbol.value}")
        expanded.extend(
            expand_dictionary_symbols(
                dictionary[index], dictionary, _stack=(*_stack, index)
            )
        )
    return tuple(expanded)
