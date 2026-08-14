"""Fixture-free tests for declarative fixed-address patch metadata."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist import ui
from time_twist.english import encode_english, render_english
from time_twist.textcodec import pack_records, split_records
from time_twist.ui import (
    COMPONENT_LOAD_ADDRESSES,
    ENGLISH_LOAD_PROMPT,
    ENGLISH_NOV4_LOAD_PROMPT,
    ENGLISH_SAVE_PROMPT,
    ENGLISH_START_PROMPT,
    LOAD_PROMPT_OFFSET,
    NOV2_OPAQUE_CLEAR_PATCHES,
    NOV2_SINGLE_CHOICE_B_PATCHES,
    NOV4_LOAD_PROMPT_OFFSET,
    ORIGINAL_LOAD_PROMPT,
    ORIGINAL_NOV4_LOAD_PROMPT,
    ORIGINAL_SAVE_PROMPT,
    SAVE_PROMPT_OFFSET,
    SourceVerifiedPatch,
    UiPatchError,
    _patched_load_prompt,
    _patched_nov4_load_prompt,
    _patched_save_prompt,
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


class FixedPromptTests(unittest.TestCase):
    """Verify fixed packed UI records without proprietary fixtures."""

    def test_title_menu_prompts_use_title_case_without_growing(self) -> None:
        """Keep the live Start and Load choices readable and size-neutral."""
        self.assertEqual(ENGLISH_START_PROMPT.hex().upper(), "8420C9080FA0")
        self.assertEqual(ENGLISH_LOAD_PROMPT.hex().upper(), "9440CAFA")
        self.assertEqual(
            ENGLISH_NOV4_LOAD_PROMPT.hex().upper(), "9440CA000FA0"
        )

    def test_nov4_load_prompt_replaces_the_visible_saved_game_choice(
        self,
    ) -> None:
        """Render Load in NOV4's six-byte title-menu saved-game slot."""
        data = bytearray(
            NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT) + 1
        )
        data[
            NOV4_LOAD_PROMPT_OFFSET : NOV4_LOAD_PROMPT_OFFSET
            + len(ORIGINAL_NOV4_LOAD_PROMPT)
        ] = ORIGINAL_NOV4_LOAD_PROMPT

        patched = _patched_nov4_load_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(
            patched[
                NOV4_LOAD_PROMPT_OFFSET : NOV4_LOAD_PROMPT_OFFSET
                + len(ENGLISH_NOV4_LOAD_PROMPT)
            ],
            ENGLISH_NOV4_LOAD_PROMPT,
        )

    def test_nov4_load_prompt_rejects_an_unknown_source(self) -> None:
        """Reject an unknown title-overlay revision without altering it."""
        data = bytes(NOV4_LOAD_PROMPT_OFFSET + len(ORIGINAL_NOV4_LOAD_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "NOV4 load prompt"):
            _patched_nov4_load_prompt(data)

    def test_load_prompt_replaces_only_its_verified_four_byte_slot(
        self,
    ) -> None:
        """Render Load after Start without moving following NOV2 data."""
        data = bytearray(LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT) + 1)
        data[
            LOAD_PROMPT_OFFSET : LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT)
        ] = ORIGINAL_LOAD_PROMPT

        patched = _patched_load_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(ENGLISH_LOAD_PROMPT.hex().upper(), "9440CAFA")
        self.assertEqual(
            patched[
                LOAD_PROMPT_OFFSET : LOAD_PROMPT_OFFSET
                + len(ENGLISH_LOAD_PROMPT)
            ],
            ENGLISH_LOAD_PROMPT,
        )

    def test_save_prompt_replaces_only_its_verified_four_byte_slot(
        self,
    ) -> None:
        """Render Save in NOV2's visible system-menu command slot."""
        data = bytearray(SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT) + 1)
        data[
            SAVE_PROMPT_OFFSET : SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT)
        ] = ORIGINAL_SAVE_PROMPT

        patched = _patched_save_prompt(bytes(data))

        self.assertEqual(len(patched), len(data))
        self.assertEqual(ENGLISH_SAVE_PROMPT.hex().upper(), "8434C1FA")
        self.assertEqual(
            patched[
                SAVE_PROMPT_OFFSET : SAVE_PROMPT_OFFSET
                + len(ENGLISH_SAVE_PROMPT)
            ],
            ENGLISH_SAVE_PROMPT,
        )

    def test_save_prompt_rejects_an_unknown_source(self) -> None:
        """Fail closed instead of writing Save onto an unknown revision."""
        data = bytes(SAVE_PROMPT_OFFSET + len(ORIGINAL_SAVE_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "save prompt"):
            _patched_save_prompt(data)

    def test_load_prompt_rejects_an_unknown_source(self) -> None:
        """Fail closed instead of writing Load onto an unverified revision."""
        data = bytes(LOAD_PROMPT_OFFSET + len(ORIGINAL_LOAD_PROMPT))

        with self.assertRaisesRegex(UiPatchError, "load prompt"):
            _patched_load_prompt(data)

    def test_disk_set_error_record_is_translated_in_place(self) -> None:
        """Replace the byte-aligned double-swap retry heading."""
        source = ui.DISK_SET_ERROR_SOURCE
        start = ui.DISK_SET_ERROR_OFFSET
        data = bytearray(start + len(source) + 1)
        data[start : start + len(source)] = source

        patched = ui._patched_disk_set_error_message(bytes(data))

        self.assertEqual(len(patched), len(data))
        expected = pack_records([encode_english(ui.DISK_SET_ERROR_ENGLISH)])
        self.assertEqual(len(expected), len(source))
        self.assertEqual(patched[start : start + len(source)], expected)
        self.assertEqual(patched[:start], data[:start])
        self.assertEqual(
            patched[start + len(source) :], data[start + len(source) :]
        )
        symbols = split_records(patched, offset=start, limit=1)[0][0]
        self.assertEqual(render_english(symbols), ui.DISK_SET_ERROR_ENGLISH)

    def test_disk_set_error_record_rejects_unknown_source(self) -> None:
        """Guard the recovered source bytes before changing them."""
        data = bytes(ui.DISK_SET_ERROR_OFFSET + len(ui.DISK_SET_ERROR_SOURCE))

        with self.assertRaisesRegex(UiPatchError, "disk-set error"):
            ui._patched_disk_set_error_message(data)


if __name__ == "__main__":
    unittest.main()
