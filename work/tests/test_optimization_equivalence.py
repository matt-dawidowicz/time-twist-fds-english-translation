"""Protect exact encoded output and SHA-256 identities during optimization."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from time_twist.entropy_codec import pack_entropy_stream
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
    optimize_entropy_dictionary,
)
from time_twist.release_metadata import sha256_file
from time_twist.textcodec import PackedSymbol, SymbolKind


class OptimizationEquivalenceTests(unittest.TestCase):
    """Verify optimizations against immutable pre-change results."""

    def test_file_hash_streams_and_matches_one_shot_sha256(self) -> None:
        """Preserve the SHA-256 digest, including at buffer boundaries."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.bin"
            lengths = (
                0,
                1,
                1024 * 1024 - 1,
                1024 * 1024,
                1024 * 1024 + 1,
            )
            for length in lengths:
                payload = (bytes(range(256)) * (length // 256 + 1))[:length]
                path.write_bytes(payload)
                expected = hashlib.sha256(payload).hexdigest().upper()
                with mock.patch.object(
                    Path,
                    "read_bytes",
                    side_effect=AssertionError("not streamed"),
                ):
                    self.assertEqual(sha256_file(path), expected)

    def test_entropy_optimizer_preserves_frozen_packed_bytes(self) -> None:
        """Compare an actual encoded stream with its pre-change golden hash."""

        def common(value: int) -> PackedSymbol:
            """Construct one ordinary text symbol."""
            return PackedSymbol(SymbolKind.COMMON, value, 0, 0)

        phrase = (common(1), common(2), common(3), common(4))
        rows = tuple(
            (*phrase, common(index % 8), *phrase) for index in range(80)
        )
        optimized = optimize_entropy_dictionary(
            (rows,),
            maximum_entries=24,
            trial_candidates=6,
        )
        self.assertEqual(optimized.optimizer_bytes, 187)
        self.assertEqual(len(optimized.dictionary), 9)
        encoded = pack_entropy_stream(optimized.groups[0])
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest().upper(),
            "9C58D5F731997F1B69EE2DDD9F28176FBFBFB0FEDC41D00DAC3757FF157B3AC3",
        )

        expansions = expand_entropy_dictionary(optimized.dictionary)
        for result, original in zip(optimized.groups[0], rows, strict=True):
            restored = expand_entropy_record(result, expansions)
            self.assertEqual(
                tuple((symbol.kind, symbol.value) for symbol in restored),
                tuple((symbol.kind, symbol.value) for symbol in original),
            )


if __name__ == "__main__":
    unittest.main()
