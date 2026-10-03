"""Unit contracts for the private definitive title IPS and subtitle uploader."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from time_twist.exact_ips_title import (
    _FINAL_LOGO_TILE_CORRECTIONS,
    DEFINITIVE_IPS_ENV,
    _definitive_ips,
    _definitive_ips_path,
    _install_subtitle,
)
from time_twist.title_layout import TitlePatchError


class ExactIpsTitleContractTests(unittest.TestCase):
    """Keep private-patch provenance and zero-glyph handling fail-closed."""

    def test_explicit_private_ips_path_is_honored(self) -> None:
        """Use the explicitly configured private IPS path when present."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "maintainer-title.ips"
            with patch.dict(os.environ, {DEFINITIVE_IPS_ENV: str(path)}):
                self.assertEqual(_definitive_ips_path(), path.resolve())

    def test_missing_private_ips_is_rejected(self) -> None:
        """Fail closed when the required private IPS file is missing."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.ips"
            with (
                patch.dict(os.environ, {DEFINITIVE_IPS_ENV: str(path)}),
                self.assertRaisesRegex(TitlePatchError, "IPS is missing"),
            ):
                _definitive_ips()

    def test_wrong_private_ips_hash_is_rejected(self) -> None:
        """Reject a private IPS whose bytes do not match the reviewed hash."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.ips"
            path.write_bytes(b"PATCHEOF")
            with (
                patch.dict(os.environ, {DEFINITIVE_IPS_ENV: str(path)}),
                self.assertRaisesRegex(TitlePatchError, "hash does not match"),
            ):
                _definitive_ips()

    def test_final_playtest_logo_corrections_are_exact_and_narrow(
        self,
    ) -> None:
        """Lock the six final-phase-only wordmark tile corrections."""
        self.assertEqual(
            [
                (cell, tile)
                for cell, tile, _source, _target in _FINAL_LOGO_TILE_CORRECTIONS
            ],
            [
                (0x066, 0x03),
                (0x0D6, 0x04),
                (0x0D7, 0x33),
                (0x0F1, 0x14),
                (0x123, 0x08),
                (0x12B, 0x16),
            ],
        )
        for _cell, _tile, source, target in _FINAL_LOGO_TILE_CORRECTIONS:
            with self.subTest(cell=_cell):
                self.assertEqual(len(source), 16)
                self.assertEqual(len(target), 16)
                self.assertNotEqual(source, target)

    @patch("time_twist.exact_ips_title.decode_title_rle")
    def test_space_only_subtitle_is_rejected_before_chr_upload(
        self, decode
    ) -> None:
        """Reject a subtitle with no drawable glyphs before CHR upload setup."""
        final = bytes(1024)
        second = bytes(1024)
        decode.side_effect = [(final, 100), (second, 200)]
        data = bytearray(256)
        data[200] = 0xFF
        with self.assertRaisesRegex(TitlePatchError, "no drawable glyphs"):
            _install_subtitle(bytes(data), "    ")
        self.assertEqual(decode.call_count, 2)


if __name__ == "__main__":
    unittest.main()
