"""Fixture-free locks for the definitive IPS-derived title authorities."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from time_twist.title_assets import _target_to_indices
from time_twist.title_authority import (
    DEFINITIVE_FINAL_PIXEL_SHA256,
    DEFINITIVE_IPS_AUTHORITY_NAME,
    DEFINITIVE_SLIDE_PIXEL_SHA256,
    _sha256,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "work" / "title_assets"
FINAL = ASSET_ROOT / "Time Twist approved native title.png"
SLIDE = ASSET_ROOT / "Time Twist approved native slide.png"
AUTHORITY = ASSET_ROOT / DEFINITIVE_IPS_AUTHORITY_NAME


class TitleOpeningAssetTests(unittest.TestCase):
    """Lock the IPS-derived final wordmark and matching swipe silhouette."""

    def test_authority_locks_source_patch_and_pixel_hash(self) -> None:
        """Bind the maintained pixels to the exact Japanese image and IPS."""
        payload = json.loads(AUTHORITY.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["schema"], "Time Twist definitive IPS logo v1"
        )
        self.assertEqual(
            payload["base_zenpen_sha256"],
            "B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916",
        )
        self.assertEqual(
            payload["ips_sha256"],
            "915C0ED3600F5E560F9F588DC2100FE59772B5F7570E4F183565FBA9C77C6BA2",
        )
        self.assertEqual(
            payload["final_pixel_sha256"], DEFINITIVE_FINAL_PIXEL_SHA256
        )

    def test_final_logo_uses_exact_ips_geometry_and_palette(self) -> None:
        """Lock the definitive logo's native bounds, indices, and pixel count."""
        final = _target_to_indices(FINAL)
        self.assertEqual(final.getbbox(), (9, 23, 246, 97))
        self.assertEqual(set(final.get_flattened_data()), {0, 1, 2, 3})
        self.assertEqual(
            _sha256(final.tobytes()), DEFINITIVE_FINAL_PIXEL_SHA256
        )
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
        self.assertEqual(
            _sha256(slide.tobytes()), DEFINITIVE_SLIDE_PIXEL_SHA256
        )
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
