"""Failure-path tests for atomic release publication without retail ROMs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from time_twist.release import _atomic_publish_file


class ReleasePublicationSafetyTests(unittest.TestCase):
    """Guarantee previously published bytes survive failed staging writes."""

    def test_failed_copy_removes_temporary_and_keeps_existing_file(self) -> None:
        """A write failure must not leak a partial file or touch the target."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "staged.bin"
            target = root / "release.bin"
            source.write_bytes(b"new release payload")
            target.write_bytes(b"existing release payload")

            def interrupted_copy(_source, destination) -> None:
                """Simulate a disk-full error after a partial copy."""
                destination.write(b"partial")
                raise OSError("simulated copy failure")

            with (
                mock.patch(
                    "time_twist.release.shutil.copyfileobj",
                    side_effect=interrupted_copy,
                ),
                self.assertRaisesRegex(OSError, "simulated copy failure"),
            ):
                _atomic_publish_file(source, target)

            self.assertEqual(target.read_bytes(), b"existing release payload")
            self.assertEqual(sorted(p.name for p in root.iterdir()),
                             ["release.bin", "staged.bin"])

    def test_failed_fsync_cleans_temporary_and_keeps_existing_file(self) -> None:
        """Failure during durability verification also cleans partial output."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "staged.bin"
            target = root / "release.bin"
            source.write_bytes(b"new release payload")
            target.write_bytes(b"existing release payload")

            with (
                mock.patch(
                    "time_twist.release.os.fsync",
                    side_effect=OSError("simulated fsync failure"),
                ),
                self.assertRaisesRegex(OSError, "simulated fsync failure"),
            ):
                _atomic_publish_file(source, target)

            self.assertEqual(target.read_bytes(), b"existing release payload")
            self.assertEqual(sorted(p.name for p in root.iterdir()),
                             ["release.bin", "staged.bin"])


if __name__ == "__main__":
    unittest.main()
