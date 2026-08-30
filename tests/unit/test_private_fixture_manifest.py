"""Validate public metadata for the separately distributed private fixtures."""

from __future__ import annotations

import json
import unittest

from tests.support.paths import FIXTURE_MANIFEST


class PrivateFixtureManifestTests(unittest.TestCase):
    """Keep private runtime-evidence metadata portable and emulator-neutral."""

    def test_capture_paths_are_emulator_neutral(self) -> None:
        """Avoid embedding an emulator brand into the private overlay contract."""
        fixture_paths = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))[
            "files"
        ]
        capture_paths = [
            path
            for path in fixture_paths
            if path.endswith(("_chr.dmp", "_cpu.dmp"))
        ]
        self.assertEqual(len(capture_paths), 4)
        self.assertTrue(
            all(
                path.startswith("work/runtime_capture/")
                for path in capture_paths
            )
        )


if __name__ == "__main__":
    unittest.main()
