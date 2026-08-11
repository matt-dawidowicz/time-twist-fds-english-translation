"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.ui import (
    COMPONENT_LOAD_ADDRESSES,
    NOV2_OPAQUE_CLEAR_PATCHES,
    NOV2_SINGLE_CHOICE_B_PATCHES,
    SourceVerifiedPatch,
    UiPatchError,
)


class SourceVerifiedPatchTests(unittest.TestCase):
    """Verify source guards and size neutrality without proprietary inputs."""

    def setUp(self) -> None:
        """Create one representative two-byte component patch."""
        self.patch = SourceVerifiedPatch(
            component="NOV2",
            file_offset=2,
            cpu_address=0x6002,
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
        with self.assertRaisesRegex(UiPatchError, "changed size"):
            SourceVerifiedPatch(
                component="NOV2",
                file_offset=0,
                cpu_address=0x6000,
                expected=b"\x10\x20",
                replacement=b"\x30",
                label="invalid",
            )

    def test_cpu_address_must_match_verified_component_load(self) -> None:
        """Reject a descriptive CPU address that disagrees with the file offset."""
        with self.assertRaisesRegex(UiPatchError, "expected \\$6002"):
            SourceVerifiedPatch(
                component="NOV2",
                file_offset=2,
                cpu_address=0x8002,
                expected=b"\x10",
                replacement=b"\x20",
                label="bad address",
            )

    def test_unknown_component_load_mapping_is_rejected(self) -> None:
        """Avoid inventing generic mappings for unverified components."""
        with self.assertRaisesRegex(UiPatchError, "no verified component"):
            SourceVerifiedPatch(
                component="SYNTH",
                file_offset=0,
                cpu_address=0x8000,
                expected=b"\x10",
                replacement=b"\x20",
                label="unknown load",
            )

    def test_all_declared_patch_addresses_match_the_verified_load(
        self,
    ) -> None:
        """Audit every production record through its established load mapping."""
        patches = (
            *NOV2_OPAQUE_CLEAR_PATCHES,
            *NOV2_SINGLE_CHOICE_B_PATCHES,
        )
        for patch in patches:
            with self.subTest(label=patch.label):
                self.assertEqual(
                    patch.cpu_address,
                    COMPONENT_LOAD_ADDRESSES[patch.component]
                    + patch.file_offset,
                )

    def test_documented_patch_offsets_match_declarative_records(self) -> None:
        """Keep the implementation guide's file/CPU pairs auditable."""
        project_root = Path(__file__).resolve().parents[2]
        documentation = (
            project_root / "docs" / "BUG_FIXES_AND_TITLE_IMPLEMENTATION.md"
        ).read_text(encoding="utf-8")
        patches = (
            *NOV2_OPAQUE_CLEAR_PATCHES,
            *NOV2_SINGLE_CHOICE_B_PATCHES,
        )
        for patch in patches:
            with self.subTest(label=patch.label):
                row_pair = (
                    f"| `${patch.file_offset:04X}` | "
                    f"`${patch.cpu_address:04X}` |"
                )
                self.assertIn(row_pair, documentation)


if __name__ == "__main__":
    unittest.main()
