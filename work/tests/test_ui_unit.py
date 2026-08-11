"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import unittest

from time_twist.ui import SourceVerifiedPatch, UiPatchError


class SourceVerifiedPatchTests(unittest.TestCase):
    """Verify source guards and size neutrality without proprietary inputs."""

    def setUp(self) -> None:
        """Create one representative two-byte component patch."""
        self.patch = SourceVerifiedPatch(
            component="SYNTH",
            file_offset=2,
            cpu_address=0x8002,
            expected=b"\x10\x20",
            replacement=b"\x30\x40",
            label="branch guard",
        )

    def test_matching_source_is_patched_in_place(self) -> None:
        """Apply a same-size replacement at its declared file offset."""
        data = bytearray(b"\x00\x01\x10\x20\x05")

        self.patch.apply_to(data)

        self.assertEqual(data, bytearray(b"\x00\x01\x30\x40\x05"))

    def test_source_mismatch_fails_without_mutation(self) -> None:
        """Reject an unexpected binary revision before changing bytes."""
        data = bytearray(b"\x00\x01\x10\x21\x05")
        original = bytes(data)

        with self.assertRaisesRegex(UiPatchError, "does not match source"):
            self.patch.apply_to(data)

        self.assertEqual(bytes(data), original)

    def test_size_changing_metadata_is_rejected(self) -> None:
        """Reject declarative metadata that would move following code."""
        patch = SourceVerifiedPatch(
            component="SYNTH",
            file_offset=0,
            cpu_address=0x8000,
            expected=b"\x10\x20",
            replacement=b"\x30",
            label="invalid",
        )

        with self.assertRaisesRegex(UiPatchError, "changed size"):
            patch.apply_to(bytearray(b"\x10\x20"))


if __name__ == "__main__":
    unittest.main()
