"""Fixture-free locks for the definitive IPS-derived title authorities."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from time_twist.title_assets import _target_to_indices

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "work" / "title_assets"
FINAL = ASSET_ROOT / "Time Twist approved native title.png"
SLIDE = ASSET_ROOT / "Time Twist approved native slide.png"
FINAL_FILE_SHA256 = (
    "220E1755BEBFCEFCA408D5E18A323FC6AE9EDEB03C3B01CA22B30163A2E0016F"
)
FINAL_PIXEL_SHA256 = (
    "EA50A1888635F7A8FE863C61EB6D728CE260D281FABF3259E2FED700BC75CBA8"
)
SLIDE_FILE_SHA256 = (
    "5218681DB3BC8F7631DC69BFB0B6A3C242B55B8018D3319CF9EC94C14DF10CA8"
)
SLIDE_PIXEL_SHA256 = (
    "7FA164F34514B568560F5FC4BE7186719A692EB1013E7B00A26DE9FAE61080AB"
)


def _sha256(data: bytes) -> str:
    """Return an uppercase SHA-256 digest."""
    return hashlib.sha256(data).hexdigest().upper()


class TitleOpeningAssetTests(unittest.TestCase):
    """Lock the exact IPS-derived final wordmark and swipe silhouette."""

    def test_checked_in_authorities_are_exact_canonical_pngs(self) -> None:
        """Bind production directly to the deterministic IPS-derived PNG files."""
        self.assertEqual(_sha256(FINAL.read_bytes()), FINAL_FILE_SHA256)
        self.assertEqual(_sha256(SLIDE.read_bytes()), SLIDE_FILE_SHA256)

    def test_final_logo_uses_exact_ips_geometry_and_palette(self) -> None:
        """Lock the definitive logo's native bounds, indices, and pixel count."""
        final = _target_to_indices(FINAL)
        self.assertEqual(final.getbbox(), (9, 23, 246, 97))
        self.assertEqual(set(final.get_flattened_data()), {0, 1, 2, 3})
        self.assertEqual(_sha256(final.tobytes()), FINAL_PIXEL_SHA256)
        self.assertEqual(
            sum(pixel != 0 for pixel in final.get_flattened_data()),
            7998,
        )
        self.assertFalse(
            any(final.crop((0, 97, 256, 240)).get_flattened_data())
        )

    def test_slide_is_the_same_logo_silhouette_down_to_the_pixel(self) -> None:
        """Require the completed swipe to be the definitive logo in white."""
        final = _target_to_indices(FINAL)
        slide = _target_to_indices(SLIDE, last_owned_row=95)
        self.assertEqual(slide.getbbox(), (9, 23, 246, 96))
        self.assertEqual(set(slide.get_flattened_data()), {0, 1})
        self.assertEqual(_sha256(slide.tobytes()), SLIDE_PIXEL_SHA256)
        self.assertEqual(
            sum(pixel != 0 for pixel in slide.get_flattened_data()),
            7982,
        )
        final_pixels = final.load()
        slide_pixels = slide.load()
        self.assertIsNotNone(final_pixels)
        self.assertIsNotNone(slide_pixels)
        assert final_pixels is not None and slide_pixels is not None
        for y in range(96):
            for x in range(256):
                self.assertEqual(
                    bool(slide_pixels[x, y]),
                    bool(final_pixels[x, y]),
                    f"slide/final silhouette differs at ({x},{y})",
                )
        self.assertFalse(
            any(slide.crop((0, 96, 256, 240)).get_flattened_data())
        )

    def test_slide_first_t_top_matches_final_outline(self) -> None:
        """Lock the first T's upper staircase to the final-logo silhouette."""
        final = _target_to_indices(FINAL)
        slide = _target_to_indices(SLIDE, last_owned_row=95)
        first_t_top = (9, 23, 57, 45)
        final_region = final.crop(first_t_top)
        slide_region = slide.crop(first_t_top)
        self.assertEqual(
            tuple(bool(pixel) for pixel in slide_region.get_flattened_data()),
            tuple(bool(pixel) for pixel in final_region.get_flattened_data()),
        )
        expected_staircase = {
            27: (55, 56),
            28: (53, 56),
            29: (51, 56),
            30: (49, 56),
            31: (47, 56),
            32: (45, 56),
            33: (43, 56),
            34: (41, 56),
            35: (39, 56),
            36: (37, 56),
            37: (35, 56),
            38: (33, 56),
            39: (31, 56),
            40: (29, 56),
            41: (27, 56),
        }
        for y, (left, right) in expected_staircase.items():
            with self.subTest(y=y):
                active = tuple(
                    x for x in range(9, 57) if slide.getpixel((x, y)) != 0
                )
                self.assertEqual(active, tuple(range(left, right + 1)))

    def test_ips_clock_and_trademark_details_are_retained(self) -> None:
        """Lock representative one-pixel details from the definitive patch."""
        final = _target_to_indices(FINAL)
        probes = {
            (108, 30): 1,
            (127, 32): 1,
            (131, 34): 1,
            (225, 24): 1,
            (236, 26): 1,
            (238, 31): 1,
        }
        for coordinate, expected in probes.items():
            self.assertEqual(final.getpixel(coordinate), expected)


if __name__ == "__main__":
    unittest.main()
