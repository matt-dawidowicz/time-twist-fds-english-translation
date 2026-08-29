"""Keep the private integration boundary small and source-oriented."""

from __future__ import annotations

import json
import unittest
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = PROJECT_ROOT / "work" / "integration_fixtures.json"
EXPECTED_SCHEMA = "Time Twist private integration fixtures v2"
EXPECTED_PRIVATE_INPUTS = {
    "work/baseline/time_twist_kouhen_japan.fds",
    "work/baseline/time_twist_zenpen_japan.fds",
    "work/runtime_capture/zenpen_opening_chr.dmp",
    "work/runtime_capture/zenpen_opening_cpu.dmp",
    "work/runtime_capture/zenpen_title_chr.dmp",
    "work/runtime_capture/zenpen_title_cpu.dmp",
}
FORBIDDEN_GENERATED_PARTS = {
    "build",
    "translated_banks",
    "extracted_zenpen",
    "extracted_kouhen",
    "outputs",
}


class PrivateFixtureContractTests(unittest.TestCase):
    """Prevent generated binaries from becoming permanent private oracles."""

    def test_manifest_contains_only_irreducible_private_inputs(self) -> None:
        """Lock the private boundary to baselines plus runtime captures."""
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("schema"), EXPECTED_SCHEMA)
        files = payload.get("files")
        self.assertIsInstance(files, dict)
        assert isinstance(files, dict)
        self.assertEqual(set(files), EXPECTED_PRIVATE_INPUTS)

        for relative, record in files.items():
            with self.subTest(path=relative):
                path = PurePosixPath(relative)
                self.assertFalse(set(path.parts) & FORBIDDEN_GENERATED_PARTS)
                self.assertIsInstance(record, dict)
                assert isinstance(record, dict)
                self.assertEqual(set(record), {"sha256", "bytes"})
                digest = record["sha256"]
                size = record["bytes"]
                self.assertIsInstance(digest, str)
                self.assertEqual(len(digest), 64)
                self.assertTrue(
                    all(char in "0123456789ABCDEF" for char in digest)
                )
                self.assertIs(type(size), int)
                self.assertGreater(size, 0)


if __name__ == "__main__":
    unittest.main()
