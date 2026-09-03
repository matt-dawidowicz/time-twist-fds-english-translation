"""Choose release compression without paying optimizer cost unnecessarily."""

from __future__ import annotations

from collections.abc import Callable

from .compression import compress_english_groups, packed_size
from .textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT, PackedSymbol

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]
CompressionResult = tuple[ScenarioGroups, ScenarioDictionary]
CompressionFunction = Callable[..., CompressionResult]
MeasureFunction = Callable[[ScenarioGroups, ScenarioDictionary], int]
CandidateValidator = Callable[[ScenarioGroups, ScenarioDictionary], bool]


def compress_release_groups(
    groups: ScenarioGroups,
    *,
    max_bytes: int,
    required_entries: ScenarioDictionary = (),
    maximum_entries: int = EXTENDED_DICTIONARY_ENTRY_COUNT,
    candidate_validator: CandidateValidator | None = None,
    compressor: CompressionFunction | None = None,
    measure: MeasureFunction | None = None,
    maximize_headroom: bool = False,
) -> CompressionResult:
    """Return a fitting result under either fast or editorial policy.

    Normal release builds favor turnaround time. The greedy compressor already
    widens to exhaustive candidate evaluation when its first result exceeds
    ``max_bytes``, so a fitting deterministic result is accepted immediately.
    The substantially more expensive beam search and dictionary-order hill
    climb remain a fallback for a genuinely tight or incompatible bank.

    Editorial optimization has a different objective: recover as much spare
    space as practical so natural English does not have to be shortened merely
    because an earlier draft already happened to fit. With
    ``maximize_headroom=True`` the fast-accept shortcut is disabled and the
    strongest deterministic optimizer is run unconditionally. The same
    ``max_bytes`` and compatibility predicates remain hard constraints.

    ``compressor`` and ``measure`` preserve the release facade's established
    test/embedding seams: callers can inject the facade-local functions while
    the selection policy remains isolated in this module.

    Args:
        groups: Encoded scenario groups to compress.
        max_bytes: Maximum packed groups-plus-dictionary footprint.
        required_entries: Fixed dictionary prefix required by external UI.
        maximum_entries: Dictionary slots supported by the target decoder.
        candidate_validator: Optional release compatibility predicate.
        compressor: Optional compression implementation supplied by the facade.
        measure: Optional packed-size implementation supplied by the facade.
        maximize_headroom: Always run optimized search instead of accepting the
            first fitting greedy result. Intended for editorial audits and
            final prose optimization, not routine development builds.

    Returns:
        Compressed groups and their ordered flat dictionary.
    """
    compress = (
        compressor if compressor is not None else compress_english_groups
    )
    size_of = measure if measure is not None else packed_size

    if maximize_headroom:
        return compress(
            groups,
            required_entries=required_entries,
            max_bytes=max_bytes,
            optimize=True,
            maximum_entries=maximum_entries,
            candidate_validator=candidate_validator,
        )

    fast = compress(
        groups,
        required_entries=required_entries,
        max_bytes=max_bytes,
        optimize=False,
        maximum_entries=maximum_entries,
    )
    fast_is_valid = candidate_validator is None or candidate_validator(*fast)
    if size_of(*fast) <= max_bytes and fast_is_valid:
        return fast
    return compress(
        groups,
        required_entries=required_entries,
        max_bytes=max_bytes,
        optimize=True,
        maximum_entries=maximum_entries,
        candidate_validator=candidate_validator,
    )
