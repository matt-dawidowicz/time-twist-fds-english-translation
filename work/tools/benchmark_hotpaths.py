"""Measure safe hot-path changes against the preserved pre-cleanup methods.

This is an optional, ROM-free developer benchmark, not a CI performance gate.
Timings are machine-dependent and must not be treated as release guarantees.
Execute it after installing the project requirements:

    python work/tools/benchmark_hotpaths.py
"""

from __future__ import annotations

import sys
import timeit
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK))
sys.path.insert(0, str(WORK / "tests"))

from test_incremental_build import _reference_allocate_groups  # noqa: E402
from test_native_compression_scan import _legacy_occurrences  # noqa: E402
from time_twist.compression import (  # noqa: E402
    _non_overlapping_byte_occurrences,
)
from time_twist.english import encode_english  # noqa: E402
from time_twist.entropy_codec import (  # noqa: E402
    CATEGORY_PREFIXES,
    _BitWriter,
    pack_entropy_stream,
)
from time_twist.incremental_build import _allocate_groups  # noqa: E402


class _OriginalPrefixWriter(_BitWriter):
    """Preserve the original per-bit category prefix loop for comparison."""

    def write_prefix(self, prefix: str) -> None:
        """Append each prefix bit separately, as the pre-cleanup code did."""
        for bit in prefix:
            self.write_bits(int(bit), 1)


def _measure(label: str, original, optimized, *, number: int) -> None:
    """Verify parity and report the best per-call timing of five trials."""
    if original() != optimized():
        raise AssertionError(f"{label}: optimized output differs")
    old = min(timeit.repeat(original, number=number, repeat=5)) / number
    new = min(timeit.repeat(optimized, number=number, repeat=5)) / number
    print(
        f"{label}: original {old * 1e3:.3f} ms/call; "
        f"optimized {new * 1e3:.3f} ms/call; "
        f"speedup {old / new:.2f}x"
    )


def _prefix_bytes(writer_type: type[_BitWriter]) -> tuple[bytes, int]:
    """Pack a fixed sample spanning all 16 frozen entropy categories."""
    writer = writer_type()
    writer.write_bits(0b101, 3)
    for prefix in CATEGORY_PREFIXES * 50:
        writer.write_prefix(prefix)
    return writer.to_bytes(), writer.bit_position


def main() -> None:
    """Compare isolated operations; never read, modify, or emit game images."""
    haystack = b"ABCabcABCDEFGHabc" * 300
    needle = b"abc"
    _measure(
        "native substring count",
        lambda: _legacy_occurrences(haystack, needle),
        lambda: _non_overlapping_byte_occurrences(haystack, needle),
        number=250,
    )
    _measure(
        "entropy prefix writer",
        lambda: _prefix_bytes(_OriginalPrefixWriter),
        lambda: _prefix_bytes(_BitWriter),
        number=100,
    )

    groups = tuple(
        tuple(
            encode_english("A" * (8 + (group + record) % 9))
            for record in range(10)
        )
        for group in range(5)
    )
    total = sum(len(pack_entropy_stream(group)) for group in groups)
    capacities = tuple(
        (
            (total * fraction) // 10 + extra,
            total - (total * fraction) // 10 + extra,
        )
        for fraction in (2, 3, 4, 5, 6, 7, 8)
        for extra in (-35, 0, 45)
    )

    def allocate(allocator) -> tuple[str, ...]:
        """Serialize all placement decisions for exact reference comparison."""
        return tuple(
            repr(
                allocator(
                    groups,
                    dictionary_bytes=12,
                    resident_capacity=resident,
                    tail_capacity=tail,
                )
            )
            for resident, tail in capacities
        )

    _measure(
        "scenario group placement batch",
        lambda: allocate(_reference_allocate_groups),
        lambda: allocate(_allocate_groups),
        number=4,
    )


if __name__ == "__main__":
    main()
