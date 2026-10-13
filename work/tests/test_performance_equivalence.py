"""Byte-identity regressions for performance-only entropy and SHA-256 changes."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from time_twist.entropy_codec import pack_entropy_stream
from time_twist.entropy_compression import optimize_entropy_dictionary
from time_twist.release_metadata import sha256_file
from time_twist.textcodec import PackedSymbol, SymbolKind

EXPECTED_PACKED_SHA256 = (
    "9C58D5F731997F1B69EE2DDD9F28176FBFBFB0FEDC41D00DAC3757FF157B3AC3"
)


class PerformanceEquivalenceTests(unittest.TestCase):
    """Prove byte identity rather than accepting merely equivalent text."""

    def test_optimizer_frozen_packed_output(self) -> None:
        """Caching must never alter the encoded result or dictionary choices."""
        def common(value: int) -> PackedSymbol:
            return PackedSymbol(SymbolKind.COMMON, value, 0, 0)

        phrase = (common(1), common(2), common(3), common(4))
        records = tuple(
            (*phrase, common(index % 8), *phrase)
            for index in range(80)
        )
        result = optimize_entropy_dictionary(
            (records,), maximum_entries=24, trial_candidates=6
        )
        actual = hashlib.sha256(
            pack_entropy_stream(result.groups[0])
        ).hexdigest().upper()
        self.assertEqual(actual, EXPECTED_PACKED_SHA256)

    def test_streamed_sha256_equals_in_memory_digest(self) -> None:
        """Hash non-aligned data including empty files without extra memory."""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.bin"
            for size in (0, 1, 8193, 1024 * 1024 + 19):
                payload = (bytes(range(256)) * ((size + 255) // 256))[:size]
                path.write_bytes(payload)
                self.assertEqual(
                    sha256_file(path),
                    hashlib.sha256(payload).hexdigest().upper(),
                )


if __name__ == "__main__":
    unittest.main()
