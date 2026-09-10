"""Dictionary optimization for the frozen Time Twist entropy grammar.

The search uses compact immutable ``(kind, value)`` tokens internally.  That is
intentional: the production corpus is large enough that constructing thousands
of ``PackedSymbol`` objects in the candidate loop roughly triples build time.
Only the public inputs/outputs use the project's semantic token class.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .textcodec import PackedSymbol, SymbolKind

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]
_Token = tuple[str, int]
_TRecord = tuple[_Token, ...]
_TGroups = tuple[tuple[_TRecord, ...], ...]


class EntropyCompressionError(ValueError):
    """Report an invalid grammar or dictionary-expanded input corpus."""


@dataclass(frozen=True)
class EntropyCompressionResult:
    """One dictionary grammar and the corpus parsed through it."""

    groups: ScenarioGroups
    menu: tuple[tuple[PackedSymbol, ...], ...]
    dictionary: ScenarioDictionary
    expansions: tuple[tuple[PackedSymbol, ...], ...]
    optimizer_bytes: int


def _to_token(symbol: PackedSymbol) -> _Token:
    if symbol.kind is SymbolKind.COMMON:
        return "C", symbol.value
    if symbol.kind is SymbolKind.DICTIONARY:
        return "D", symbol.value
    if symbol.kind is SymbolKind.EXTENDED:
        return "E", symbol.value
    if symbol.kind is SymbolKind.CONTROL:
        if symbol.value == 5:
            raise EntropyCompressionError("control 5 is a record separator")
        return "K", symbol.value
    raise EntropyCompressionError(
        f"record payload contains unsupported {symbol.kind}:{symbol.value}"
    )


def _from_token(token: _Token) -> PackedSymbol:
    kind, value = token
    semantic = {
        "C": SymbolKind.COMMON,
        "D": SymbolKind.DICTIONARY,
        "E": SymbolKind.EXTENDED,
        "K": SymbolKind.CONTROL,
    }[kind]
    return PackedSymbol(semantic, value, 0, 0)


def _to_groups(groups: ScenarioGroups) -> _TGroups:
    return tuple(
        tuple(
            tuple(_to_token(symbol) for symbol in record) for record in group
        )
        for group in groups
    )


def _to_records(
    records: Sequence[Sequence[PackedSymbol]],
) -> tuple[_TRecord, ...]:
    return tuple(
        tuple(_to_token(symbol) for symbol in record) for record in records
    )


def _public_groups(groups: _TGroups) -> ScenarioGroups:
    return tuple(
        tuple(
            tuple(_from_token(token) for token in record) for record in group
        )
        for group in groups
    )


def _public_records(
    records: Sequence[_TRecord],
) -> tuple[tuple[PackedSymbol, ...], ...]:
    return tuple(
        tuple(_from_token(token) for token in record) for record in records
    )


def _bits(token: _Token) -> int:
    kind, value = token
    if kind == "K":
        if value == 5:
            return 4
        if 0 <= value <= 7:
            return 8
    elif kind == "E" and 37 <= value <= 63:
        return 10
    elif kind == "C":
        if 0 <= value <= 7:
            return 5
        if value <= 15:
            return 6
        if value <= 23:
            return 7
        if value <= 47:
            return 8
    elif kind == "D":
        if 1 <= value <= 16:
            return 7
        if value <= 64:
            return 8
        if value <= 96:
            return 11
        if value <= 128:
            return 12
        if value <= 255:
            return 14
    raise EntropyCompressionError(f"unrepresentable entropy token {token}")


def _record_bytes(record: _TRecord) -> int:
    """Step-4 search metric with an independently aligned trial record."""
    return (sum(_bits(token) for token in record) + 4 + 7) // 8


def _total_bytes(
    groups: _TGroups,
    menu: Sequence[_TRecord],
    dictionary: Sequence[_TRecord],
) -> int:
    return sum(
        _record_bytes(record)
        for records in (*groups, tuple(menu), tuple(dictionary))
        for record in records
    )


def _expand_definitions(
    definitions: Sequence[_TRecord],
) -> tuple[_TRecord, ...]:
    expansions: list[_TRecord] = []
    for index, definition in enumerate(definitions, start=1):
        output: list[_Token] = []
        for token in definition:
            if token[0] == "D":
                if not 1 <= token[1] < index:
                    raise EntropyCompressionError(
                        f"entry {index} has non-backward reference {token[1]}"
                    )
                output.extend(expansions[token[1] - 1])
            else:
                output.append(token)
        expansions.append(tuple(output))
    return tuple(expansions)


def _expand_record(
    record: _TRecord, expansions: Sequence[_TRecord]
) -> _TRecord:
    output: list[_Token] = []
    for token in record:
        if token[0] == "D":
            if not 1 <= token[1] <= len(expansions):
                raise EntropyCompressionError(
                    f"dictionary reference {token[1]} is out of range"
                )
            output.extend(expansions[token[1] - 1])
        else:
            output.append(token)
    return tuple(output)


def _make_parser(expansions: Sequence[_TRecord]):
    by_first: dict[_Token, list[tuple[int, _TRecord]]] = {}
    for index, expansion in enumerate(expansions, start=1):
        if expansion:
            by_first.setdefault(expansion[0], []).append((index, expansion))
    for candidates in by_first.values():
        candidates.sort(key=lambda item: -len(item[1]))

    def parse(literal: _TRecord, maximum_index: int | None = None) -> _TRecord:
        length = len(literal)
        costs = [0] * (length + 1)
        parsed: list[_TRecord] = [()] * (length + 1)
        for position in range(length - 1, -1, -1):
            token = literal[position]
            best_cost = _bits(token) + costs[position + 1]
            best = (token, *parsed[position + 1])
            for index, expansion in by_first.get(token, ()):
                if maximum_index is not None and index > maximum_index:
                    continue
                end = position + len(expansion)
                if end > length or literal[position:end] != expansion:
                    continue
                reference = ("D", index)
                cost = _bits(reference) + costs[end]
                candidate = (reference, *parsed[end])
                if cost < best_cost or (
                    cost == best_cost
                    and (len(candidate), candidate) < (len(best), best)
                ):
                    best_cost = cost
                    best = candidate
            costs[position] = best_cost
            parsed[position] = best
        return parsed[0]

    return parse


def _rebuild_definitions(
    expansions: Sequence[_TRecord],
) -> tuple[_TRecord, ...]:
    parse = _make_parser(expansions)
    return tuple(
        parse(expansion, index - 1)
        for index, expansion in enumerate(expansions, start=1)
    )


def _parse_corpus(
    literal_groups: _TGroups,
    literal_menu: Sequence[_TRecord],
    expansions: Sequence[_TRecord],
) -> tuple[_TGroups, tuple[_TRecord, ...]]:
    parse = _make_parser(expansions)
    return (
        tuple(
            tuple(parse(record) for record in group)
            for group in literal_groups
        ),
        tuple(parse(record) for record in literal_menu),
    )


def _depths(definitions: Sequence[_TRecord]) -> tuple[int, ...]:
    depths: list[int] = []
    for definition in definitions:
        depths.append(
            1
            + max(
                (
                    depths[value - 1]
                    for kind, value in definition
                    if kind == "D"
                ),
                default=0,
            )
        )
    return tuple(depths)


def _candidate_counts(
    groups: _TGroups,
    menu: Sequence[_TRecord],
    maximum_tokens: int,
) -> Counter[_TRecord]:
    counts: Counter[_TRecord] = Counter()
    for records in (*groups, tuple(menu)):
        for record in records:
            segment: list[_Token] = []
            for token in (*record, None):
                if token is not None and token[0] != "K":
                    segment.append(token)
                    continue
                for start in range(len(segment)):
                    maximum = min(maximum_tokens, len(segment) - start)
                    for width in range(1, maximum + 1):
                        counts[tuple(segment[start : start + width])] += 1
                segment = []
    return counts


def _candidate_expansion(
    candidate: _TRecord,
    expansions: Sequence[_TRecord],
) -> _TRecord:
    return _expand_record(candidate, expansions)


def _candidate_depth(candidate: _TRecord, depths: Sequence[int]) -> int:
    return 1 + max(
        (depths[value - 1] for kind, value in candidate if kind == "D"),
        default=0,
    )


def _public_result(
    groups: _TGroups,
    menu: Sequence[_TRecord],
    definitions: Sequence[_TRecord],
    expansions: Sequence[_TRecord],
    optimizer_bytes: int,
) -> EntropyCompressionResult:
    return EntropyCompressionResult(
        groups=_public_groups(groups),
        menu=_public_records(menu),
        dictionary=_public_records(definitions),
        expansions=_public_records(expansions),
        optimizer_bytes=optimizer_bytes,
    )


def optimize_entropy_dictionary(
    literal_groups: ScenarioGroups,
    literal_menu: Sequence[Sequence[PackedSymbol]] = (),
    *,
    maximum_entries: int = 128,
    maximum_grammar_tokens: int = 12,
    maximum_nesting_depth: int = 4,
    trial_candidates: int = 8,
) -> EntropyCompressionResult:
    """Build the deterministic dictionary used by the frozen Step-4 codec."""
    groups_literal = _to_groups(literal_groups)
    menu_literal = _to_records(literal_menu)
    if any(
        token[0] == "D"
        for group in groups_literal
        for record in group
        for token in record
    ):
        raise EntropyCompressionError(
            "scenario input must be dictionary-expanded"
        )
    if any(token[0] == "D" for record in menu_literal for token in record):
        raise EntropyCompressionError("menu input must be dictionary-expanded")
    if not 0 <= maximum_entries <= 255:
        raise ValueError("maximum_entries must be between 0 and 255")

    expansions: tuple[_TRecord, ...] = ()
    definitions: tuple[_TRecord, ...] = ()
    groups = groups_literal
    menu = menu_literal
    current = _total_bytes(groups, menu, definitions)

    while len(expansions) < maximum_entries:
        index = len(expansions) + 1
        reference_bits = _bits(("D", index))
        candidates = _candidate_counts(groups, menu, maximum_grammar_tokens)
        depths = _depths(definitions)
        existing = set(expansions)
        parse = _make_parser(expansions)
        ranked = []
        for candidate, count in candidates.items():
            if count < 2:
                continue
            if _candidate_depth(candidate, depths) > maximum_nesting_depth:
                continue
            expansion = _candidate_expansion(candidate, expansions)
            if expansion in existing:
                continue
            candidate_bits = sum(_bits(token) for token in candidate)
            if candidate_bits <= reference_bits:
                continue
            definition = parse(expansion)
            estimate = (
                count * (candidate_bits - reference_bits)
                - _record_bytes(definition) * 8
            )
            if estimate > 0:
                ranked.append(
                    (estimate, count, candidate, expansion, definition)
                )
        if not ranked:
            break
        ranked.sort(
            key=lambda item: (item[0], item[1], len(item[2]), item[2]),
            reverse=True,
        )
        best = None
        for estimate, _count, _candidate, expansion, definition in ranked[
            :trial_candidates
        ]:
            next_expansions = (*expansions, expansion)
            next_definitions = (*definitions, definition)
            next_groups, next_menu = _parse_corpus(
                groups_literal, menu_literal, next_expansions
            )
            size = _total_bytes(next_groups, next_menu, next_definitions)
            key = (size, -estimate, expansion)
            if best is None or key < best[0]:
                best = (
                    key,
                    next_expansions,
                    next_definitions,
                    next_groups,
                    next_menu,
                )
        if best is None or best[0][0] >= current:
            break
        _, expansions, definitions, groups, menu = best
        current = best[0][0]

    return _public_result(groups, menu, definitions, expansions, current)


def _reference_counts_tokens(
    groups: _TGroups,
    menu: Sequence[_TRecord],
    definitions: Sequence[_TRecord],
    count: int,
) -> tuple[int, ...]:
    refs = [0] * count
    for records in (*groups, tuple(menu), tuple(definitions)):
        for record in records:
            for kind, value in record:
                if kind == "D":
                    refs[value - 1] += 1
    return tuple(refs)


def usage_pruned_entropy_variants(
    result: EntropyCompressionResult,
    literal_groups: ScenarioGroups,
    literal_menu: Sequence[Sequence[PackedSymbol]] = (),
    *,
    search_depth: int = 16,
) -> tuple[EntropyCompressionResult, ...]:
    """Move hot phrases into cheap tiers and prune low-value tail entries."""
    if not result.expansions:
        return (result,)
    literal_g = _to_groups(literal_groups)
    literal_m = _to_records(literal_menu)
    expansions = _to_records(result.expansions)
    definitions = _to_records(result.dictionary)
    groups = _to_groups(result.groups)
    menu = _to_records(result.menu)
    counts = _reference_counts_tokens(
        groups, menu, definitions, len(expansions)
    )
    ranked = sorted(
        range(len(expansions)),
        key=lambda item: (counts[item], len(expansions[item]), -item),
        reverse=True,
    )
    minimum = max(1, len(expansions) - search_depth)
    keep_counts = set(range(minimum, len(expansions) + 1))
    keep_counts.update(
        value
        for value in (64, 68, 80, 88, 96, 100, 102, 103, 104, 112, 120)
        if minimum <= value <= len(expansions)
    )
    variants = [result]
    seen = {expansions}
    for keep in sorted(keep_counts, reverse=True):
        candidate_expansions = tuple(
            expansions[item] for item in ranked[:keep]
        )
        if candidate_expansions in seen:
            continue
        seen.add(candidate_expansions)
        candidate_definitions = _rebuild_definitions(candidate_expansions)
        candidate_groups, candidate_menu = _parse_corpus(
            literal_g, literal_m, candidate_expansions
        )
        variants.append(
            _public_result(
                candidate_groups,
                candidate_menu,
                candidate_definitions,
                candidate_expansions,
                _total_bytes(
                    candidate_groups,
                    candidate_menu,
                    candidate_definitions,
                ),
            )
        )
    return tuple(variants)


def expand_entropy_dictionary(
    dictionary: ScenarioDictionary,
) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Expand a backward-only entropy dictionary into literal token records."""
    expansions: list[tuple[PackedSymbol, ...]] = []
    for index, definition in enumerate(dictionary, start=1):
        output: list[PackedSymbol] = []
        for symbol in definition:
            if symbol.kind is SymbolKind.DICTIONARY:
                if not 1 <= symbol.value < index:
                    raise EntropyCompressionError(
                        f"entry {index} has non-backward reference "
                        f"{symbol.value}"
                    )
                output.extend(expansions[symbol.value - 1])
            else:
                output.append(symbol)
        expansions.append(tuple(output))
    return tuple(expansions)


def expand_entropy_record(
    record: Sequence[PackedSymbol],
    expansions: Sequence[Sequence[PackedSymbol]],
) -> tuple[PackedSymbol, ...]:
    """Expand dictionary references in one packed record using literal entries."""
    output: list[PackedSymbol] = []
    for symbol in record:
        if symbol.kind is SymbolKind.DICTIONARY:
            if not 1 <= symbol.value <= len(expansions):
                raise EntropyCompressionError(
                    f"dictionary reference {symbol.value} is out of range"
                )
            output.extend(expansions[symbol.value - 1])
        else:
            output.append(symbol)
    return tuple(output)
