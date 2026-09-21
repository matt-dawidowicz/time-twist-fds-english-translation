"""Regression tests for the recovered v38 reproducibility bundle.

These checks require no copyrighted/private FDS input.  They prove that every
archived source payload still reconstructs to the exact file bytes recorded in
the v38 recovery manifest.  The ROM-level gate lives in
recovery/v38/repro_bundle/verify_v38.py and runs when the private v25 baseline
is supplied locally.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "recovery" / "v38" / "repro_bundle"
MANIFEST = BUNDLE / "manifest.json"
PAYLOAD = BUNDLE / "payload"

EXPECTED_ROM_SHA256 = (
    "62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400"
)
EXPECTED_ROM_SIZE = 262000


class V38RecoveredCheckpointTests(unittest.TestCase):
    """Protect the recovered v38 source bundle and canonical ROM identity."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the recovered v38 manifest once for all checkpoint tests."""
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_canonical_rom_gate_is_frozen(self) -> None:
        """Keep the approved v38 ROM size and SHA-256 immutable."""
        self.assertEqual(
            self.manifest["expected_rom_sha256"], EXPECTED_ROM_SHA256
        )
        self.assertEqual(self.manifest["expected_rom_size"], EXPECTED_ROM_SIZE)

    def test_all_recovered_payloads_are_exact(self) -> None:
        """Require every archived source payload to match its recorded digest."""
        files = self.manifest["files"]
        self.assertEqual(len(files), 17)
        for item in files:
            with self.subTest(path=item["path"]):
                encoded = (PAYLOAD / item["payload"]).read_text(
                    encoding="ascii"
                )
                raw = gzip.decompress(
                    base64.b64decode("".join(encoded.split()))
                )
                self.assertEqual(len(raw), item["bytes"])
                self.assertEqual(
                    hashlib.sha256(raw).hexdigest(), item["sha256"]
                )


if __name__ == "__main__":
    unittest.main()
