"""Capacity-aware public facade for the native dictionary compressor."""

from __future__ import annotations

import sys
from threading import RLock

from . import _compression_core as _core
from .textcodec import PackedSymbol

for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)
del _name

MAX_DICTIONARY_ENTRIES = _core.MAX_DICTIONARY_ENTRIES
MAX_CANDIDATE_TOKENS = _core.MAX_CANDIDATE_TOKENS
MAX_CANDIDATES_TO_EVALUATE = _core.MAX_CANDIDATES_TO_EVALUATE
symbol_bit_length = _core.symbol_bit_length
packed_size = _core.packed_size
expand_dictionary_symbols = _core.expand_dictionary_symbols

_FALLBACK_LOCK = RLock()


def compress_english_groups(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
    max_bytes: int | None = None,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Compress text and widen candidate search only on a capacity miss.

    The normal deterministic top-200 greedy search remains the fast path. If a
    caller supplies ``max_bytes`` and that result exceeds the reservation, the
    same greedy algorithm is rerun with candidate pruning disabled. The smaller
    result is retained. This is a robustness fallback, not a claim of globally
    optimal compression.
    """
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")

    primary = _core.compress_english_groups(
        groups,
        required_entries=required_entries,
    )
    primary_size = packed_size(*primary)
    if max_bytes is None or primary_size <= max_bytes:
        return primary

    with _FALLBACK_LOCK:
        original_limit = _core.MAX_CANDIDATES_TO_EVALUATE
        try:
            _core.MAX_CANDIDATES_TO_EVALUATE = sys.maxsize
            fallback = _core.compress_english_groups(
                groups,
                required_entries=required_entries,
            )
        finally:
            _core.MAX_CANDIDATES_TO_EVALUATE = original_limit

    if packed_size(*fallback) < primary_size:
        return fallback
    return primary
