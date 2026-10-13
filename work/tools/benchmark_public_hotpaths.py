"""Benchmark ROM-free translation hot paths against a frozen synthetic corpus.

Timings are diagnostic, not pass/fail performance thresholds: hardware and
Python versions vary. Exact encoded output hashes ARE checked for correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work"))

from time_twist.entropy_codec import pack_entropy_stream  # noqa: E402
from time_twist.entropy_compression import (  # noqa: E402
    optimize_entropy_dictionary,
)
from time_twist.release_metadata import sha256_file  # noqa: E402
from time_twist.textcodec import PackedSymbol, SymbolKind  # noqa: E402

EXPECTED_80_RECORD_PACKED_SHA256 = (
    "9C58D5F731997F1B69EE2DDD9F28176FBFBFB0FEDC41D00DAC3757FF157B3AC3"
)


def _measure(workload, repetitions: int) -> dict[str, object]:
    """Measure repeated calls with warmup, median time, and peak memory."""
    workload()
    times: list[float] = []
    tracemalloc.start()
    try:
        for _ in range(repetitions):
            start = time.perf_counter()
            workload()
            times.append(time.perf_counter() - start)
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return {
        "median_ms": round(statistics.median(times) * 1000, 3),
        "peak_traced_bytes": peak,
        "repetitions": repetitions,
    }


def run_benchmarks(repetitions: int, hash_megabytes: int) -> dict[str, object]:
    """Measure fixed synthetic dictionary and file-hashing work."""

    def common(value: int) -> PackedSymbol:
        """Create an ordinary immutable codec symbol."""
        return PackedSymbol(SymbolKind.COMMON, value, 0, 0)

    phrase = (common(1), common(2), common(3), common(4))
    records = tuple(
        (*phrase, common(index % 8), *phrase) for index in range(80)
    )

    def optimize():
        """Build a grammar from repeated synthetic dialogue records."""
        return optimize_entropy_dictionary(
            (records,), maximum_entries=24, trial_candidates=6
        )

    result = optimize()
    packed_hash = hashlib.sha256(
        pack_entropy_stream(result.groups[0])
    ).hexdigest().upper()
    if packed_hash != EXPECTED_80_RECORD_PACKED_SHA256:
        raise RuntimeError("optimizer bytes changed from the frozen baseline")
    optimizer = _measure(optimize, repetitions)
    optimizer["packed_sha256"] = packed_hash

    with tempfile.TemporaryDirectory(prefix="time-twist-benchmark-") as tmp:
        source = Path(tmp) / "synthetic.bin"
        block = bytes(range(256)) * 4096
        with source.open("wb") as stream:
            for _ in range(hash_megabytes):
                stream.write(block)
        expected = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        if sha256_file(source) != expected:
            raise RuntimeError("streaming hash differs from the baseline")
        hashing = _measure(lambda: sha256_file(source), repetitions)
        hashing["input_bytes"] = source.stat().st_size
        hashing["sha256"] = expected

    return {
        "schema": "Time Twist synthetic performance v1",
        "optimizer": optimizer,
        "hashing": hashing,
    }


def main() -> None:
    """Print machine-readable measurements without reading retail ROMs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=7)
    parser.add_argument("--hash-megabytes", type=int, default=28)
    args = parser.parse_args()
    if not 1 <= args.repetitions <= 100:
        parser.error("repetitions must be between 1 and 100")
    if not 1 <= args.hash_megabytes <= 256:
        parser.error("hash-megabytes must be between 1 and 256")
    result = run_benchmarks(args.repetitions, args.hash_megabytes)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
