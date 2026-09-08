"""Fixture-free invariants for the public title API and helper machine code."""

from __future__ import annotations

import unittest

from time_twist import title


class TitleAssetApiTests(unittest.TestCase):
    """Preserve caller compatibility through the public title facade."""

    def test_approximation_error_accepts_existing_constructor_forms(
        self,
    ) -> None:
        """Keep attribute access and legacy keyword/positional construction."""
        arguments = (b"", b"", b"", b"", 0, b"", b"", b"", b"", b"", b"", b"")
        self.assertEqual(title.TitleAssets(*arguments).approximation_error, 0)
        self.assertEqual(
            title.TitleAssets(
                *arguments, approximation_error=7
            ).approximation_error,
            7,
        )
        self.assertEqual(
            title.TitleAssets(*arguments, 7).approximation_error, 7
        )


class TitleHelperTests(unittest.TestCase):
    """Protect small injected title routines without private ROM fixtures."""

    def test_pre_slide_helper_restores_chr_before_queuing_palette(
        self,
    ) -> None:
        """Keep the BIOS upload from clobbering the staged slide palette."""
        helper = title._pre_slide_restore_helper(0xB6D2)
        save_mask = bytes.fromhex("A5 1C 48")
        clear_mask_and_ppu = bytes.fromhex("A9 00 85 1C 8D 01 20")
        disable_nmi = bytes.fromhex("A5 FF 48 29 7F 8D 00 20")
        chr_upload = bytes.fromhex("A0 1B A9 00 A2 26 20 AF EB D2 B6")
        restore_origin = bytes.fromhex("A9 01 85 58 A9 F0 85 57 85 4D")
        queue_palette = bytes.fromhex("20 74 AB")
        restore_ppuctrl = bytes.fromhex("68 85 FF 09 10 85 FF 8D 00 20")
        restore_mask_mirror_only = bytes.fromhex("68 85 1C EA EA EA 60")

        self.assertEqual(len(helper), title.SLIDE_PREP_SIZE)
        self.assertEqual(title.SLIDE_PREP_SIZE, 59)
        self.assertTrue(helper.startswith(save_mask))
        self.assertLess(
            helper.index(save_mask), helper.index(clear_mask_and_ppu)
        )
        self.assertLess(
            helper.index(clear_mask_and_ppu), helper.index(disable_nmi)
        )
        self.assertLess(helper.index(disable_nmi), helper.index(chr_upload))
        self.assertLess(helper.index(chr_upload), helper.index(restore_origin))
        self.assertLess(
            helper.index(restore_origin), helper.index(queue_palette)
        )
        self.assertLess(
            helper.index(queue_palette), helper.index(restore_ppuctrl)
        )
        self.assertLess(
            helper.index(restore_ppuctrl),
            helper.index(restore_mask_mirror_only),
        )
        self.assertTrue(helper.endswith(restore_mask_mirror_only))
        self.assertEqual(
            helper.count(bytes.fromhex("8D 01 20")),
            1,
            "pre-slide helper may blank $2001, but must not restore it; "
            "the next NMI must apply the new scroll before rendering returns",
        )

    def test_exit_helper_blanks_rendering_before_split_teardown(self) -> None:
        """Prevent lower title tiles from flashing as upper-logo fragments."""
        helper = title.TITLE_EXIT_HELPER
        clear_mask_mirror = bytes.fromhex("85 1C")
        blank_ppu = bytes.fromhex("8D 01 20")
        disable_timer = bytes.fromhex("8D 22 40")
        select_upper_chr = bytes.fromhex("8D 00 20")

        self.assertEqual(len(helper), title.TITLE_EXIT_SIZE)
        self.assertEqual(title.TITLE_EXIT_SIZE, 32)
        self.assertTrue(
            helper.startswith(b"\xa9\x00" + clear_mask_mirror + blank_ppu)
        )
        self.assertLess(helper.index(blank_ppu), helper.index(disable_timer))
        self.assertLess(
            helper.index(blank_ppu), helper.index(select_upper_chr)
        )
        self.assertTrue(helper.endswith(title.TITLE_EXIT_SOURCE))
