"""Private-overlay integration tests for the definitive IPS-derived title."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import time_twist.title as title
from PIL import Image
from time_twist.font import patched_nov4_font
from time_twist.ui import patched_nov4_ui

WORK_DIR = Path(__file__).resolve().parents[1]

NATIVE_FILE_SHA256 = (
    "220E1755BEBFCEFCA408D5E18A323FC6AE9EDEB03C3B01CA22B30163A2E0016F"
)
NATIVE_PIXELS_SHA256 = (
    "EA50A1888635F7A8FE863C61EB6D728CE260D281FABF3259E2FED700BC75CBA8"
)
SLIDE_FILE_SHA256 = (
    "5218681DB3BC8F7631DC69BFB0B6A3C242B55B8018D3319CF9EC94C14DF10CA8"
)
SLIDE_PIXELS_SHA256 = (
    "7FA164F34514B568560F5FC4BE7186719A692EB1013E7B00A26DE9FAE61080AB"
)
FINAL_ATTRIBUTES_SHA256 = (
    "42869099B63ED98598904E2C1B959CA7A38A3749ED51712774549ED4F348926E"
)
SECOND_ATTRIBUTES_SHA256 = (
    "50B20CBF142A10729ED041C30EFAFFC52F4AD332B4729AE4E9B29A198AF066A3"
)


def _sha256(data: bytes) -> str:
    """Return an uppercase SHA-256 digest."""
    return hashlib.sha256(data).hexdigest().upper()


class TitlePatchTests(unittest.TestCase):
    """Lock the exact final/swipe artwork and the runtime that installs it."""

    @classmethod
    def setUpClass(cls) -> None:
        """Build the title once from the maintained private Japanese NOV4."""
        cls.source_path = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        cls.native_path = (
            WORK_DIR / "title_assets/Time Twist approved native title.png"
        )
        cls.slide_path = (
            WORK_DIR / "title_assets/Time Twist approved native slide.png"
        )
        missing = [
            str(path)
            for path in (cls.source_path, cls.native_path, cls.slide_path)
            if not path.exists()
        ]
        if missing:
            raise AssertionError(f"title fixtures are unavailable: {missing}")
        cls.source = patched_nov4_font(
            patched_nov4_ui(cls.source_path.read_bytes())
        )
        cls.native = title._target_to_indices(cls.native_path)
        cls.slide = title._target_to_indices(cls.slide_path, last_owned_row=95)
        cls.assets = title.build_title_assets(
            cls.source,
            cls.native_path,
            slide_target=cls.slide_path,
        )
        cls.patched = title.patched_nov4_title(
            cls.source,
            cls.native_path,
            slide_target=cls.slide_path,
        )

    def _layout(self) -> dict[str, int]:
        """Return deterministic offsets of all appended title payloads."""
        bottom = len(self.source)
        nintendo = bottom + title.BOTTOM_CHR_SIZE
        delta = nintendo + title.NINTENDO_CHR_SIZE
        loader = delta + len(self.assets.final_delta_chr)
        slide_prep = loader + title.INITIAL_CHR_LOADER_SIZE
        transition = slide_prep + title.SLIDE_PREP_SIZE
        exit_helper = transition + title.TITLE_TRANSITION_SIZE
        stream = exit_helper + title.TITLE_EXIT_SIZE
        return {
            "bottom": bottom,
            "nintendo": nintendo,
            "delta": delta,
            "loader": loader,
            "slide_prep": slide_prep,
            "transition": transition,
            "exit": exit_helper,
            "stream": stream,
        }

    def test_definitive_authorities_are_exact(self) -> None:
        """Lock the checked-in IPS-derived final and monochrome authorities."""
        self.assertEqual(_sha256(self.native_path.read_bytes()), NATIVE_FILE_SHA256)
        self.assertEqual(_sha256(self.slide_path.read_bytes()), SLIDE_FILE_SHA256)
        self.assertEqual(_sha256(self.native.tobytes()), NATIVE_PIXELS_SHA256)
        self.assertEqual(_sha256(self.slide.tobytes()), SLIDE_PIXELS_SHA256)
        self.assertEqual(
            sum(pixel != 0 for pixel in self.native.get_flattened_data()), 7998
        )
        self.assertEqual(
            sum(pixel != 0 for pixel in self.slide.get_flattened_data()), 7982
        )
        final_pixels = self.native.load()
        slide_pixels = self.slide.load()
        self.assertIsNotNone(final_pixels)
        self.assertIsNotNone(slide_pixels)
        assert final_pixels is not None and slide_pixels is not None
        for y in range(96):
            for x in range(256):
                self.assertEqual(bool(slide_pixels[x, y]), bool(final_pixels[x, y]))

    def test_completed_title_is_pixel_exact_and_keeps_existing_subtitle(self) -> None:
        """Require IPS art above the unchanged subtitle and native lower art."""
        rendered = title._render_split_nametable(
            self.assets.final_nametable,
            self.assets.background_chr,
            self.assets.bottom_chr,
        )
        source_final, _ = title.decode_title_rle(
            self.source, title.FINAL_NAMETABLE_START
        )
        source_chr = self.source[
            title.TITLE_CHR_OFFSET : title.TITLE_CHR_OFFSET + title.TITLE_CHR_SIZE
        ]
        original = title._render_indexed_nametable(source_final, source_chr)
        expected = original.copy()
        expected.paste(self.native.crop((0, 0, 256, 97)), (0, 0))
        expected.paste(0, (0, 97, 256, 112))
        subtitle_width = (
            sum(4 if character == " " else 6 for character in title.DEFAULT_SUBTITLE)
            - 1
        )
        title._draw_text(
            expected,
            title.DEFAULT_SUBTITLE,
            x=(256 - subtitle_width) // 2,
            y=102,
            color=2,
        )
        self.assertEqual(rendered.tobytes(), expected.tobytes())
        self.assertEqual(
            rendered.crop((0, 112, 256, 240)).tobytes(),
            original.crop((0, 112, 256, 240)).tobytes(),
        )

    def test_three_tile_phase_delta_reconstructs_final_exactly(self) -> None:
        """Lock the compact temporal CHR swap enabled by the shared silhouette."""
        self.assertEqual(title.FINAL_DELTA_TILE_COUNT, 3)
        self.assertEqual(len(self.assets.final_delta_chr), 3 * 16)
        rebuilt = bytearray(self.assets.slide_chr)
        start = self.assets.final_delta_first_tile * 16
        rebuilt[start : start + len(self.assets.final_delta_chr)] = (
            self.assets.final_delta_chr
        )
        self.assertEqual(bytes(rebuilt), self.assets.background_chr)
        final_logo = title._render_indexed_nametable(
            self.assets.final_nametable, self.assets.background_chr
        ).crop((0, 0, 256, 96))
        slide_logo = title._render_indexed_nametable(
            self.assets.second_nametable, self.assets.slide_chr
        ).crop((0, 0, 256, 96))
        self.assertEqual(
            final_logo.tobytes(), self.native.crop((0, 0, 256, 96)).tobytes()
        )
        self.assertEqual(
            slide_logo.tobytes(), self.slide.crop((0, 0, 256, 96)).tobytes()
        )

    def test_slide_runtime_finishes_on_exact_logo(self) -> None:
        """Preserve the native oscillating scroll while ending on the IPS logo."""
        self.assertEqual(len(title.SLIDE_SCROLL_ORIGINS), 21)
        self.assertEqual(title.SLIDE_SCROLL_ORIGINS[-1], 0x100)
        self.assertFalse(
            any(title.render_slide_logo_frame(self.assets, 0x1F0).get_flattened_data())
        )
        completed = title.render_slide_logo_frame(self.assets, 0x100)
        self.assertEqual(
            completed.tobytes(), self.slide.crop((0, 0, 256, 96)).tobytes()
        )
        self.assertEqual(
            sum(bool(pixel) for pixel in completed.get_flattened_data()), 7982
        )
        for origin in title.SLIDE_SCROLL_ORIGINS:
            frame = title.render_monochrome_slide_frame(self.assets, origin)
            self.assertEqual(frame.size, (256, 240))
            self.assertFalse(
                any(
                    pixel != title.TITLE_PALETTE[0]
                    for pixel in frame.crop((0, 96, 256, 240)).get_flattened_data()
                )
            )

    def test_source_attribute_tables_and_clock_animation_are_preserved(self) -> None:
        """Change logo geometry without rewriting native title control data."""
        source_final, _ = title.decode_title_rle(
            self.source, title.FINAL_NAMETABLE_START
        )
        source_second, _ = title.decode_title_rle(
            self.source, title.SECOND_NAMETABLE_START
        )
        self.assertEqual(self.assets.final_nametable[960:], source_final[960:])
        self.assertEqual(self.assets.second_nametable[960:], source_second[960:])
        self.assertEqual(
            _sha256(self.assets.final_nametable[960:]), FINAL_ATTRIBUTES_SHA256
        )
        self.assertEqual(
            _sha256(self.assets.second_nametable[960:]), SECOND_ATTRIBUTES_SHA256
        )
        self.assertEqual(
            self.patched[title.CLOCK_SOURCE_OFFSET : title.CLOCK_SOURCE_END],
            self.source[title.CLOCK_SOURCE_OFFSET : title.CLOCK_SOURCE_END],
        )
        self.assertEqual(
            self.patched[title.CLOCK_METASPRITE_START : title.CLOCK_METASPRITE_END],
            self.source[title.CLOCK_METASPRITE_START : title.CLOCK_METASPRITE_END],
        )

    def test_clock_origin_matches_definitive_ips(self) -> None:
        """Use the historical patch's exact hand placement for this clock face."""
        self.assertEqual(
            title.CLOCK_HAND_ORIGINS_SOURCE,
            bytes.fromhex("78 00 37 04 80 00 3F"),
        )
        self.assertEqual(
            title.CLOCK_HAND_ORIGINS_PATCH,
            bytes.fromhex("68 00 39 04 70 00 41"),
        )
        self.assertEqual(
            self.patched[
                title.CLOCK_HAND_ORIGINS_OFFSET : title.CLOCK_HAND_ORIGINS_OFFSET + 7
            ],
            title.CLOCK_HAND_ORIGINS_PATCH,
        )
        old = title.CLOCK_HAND_ORIGINS_SOURCE
        new = title.CLOCK_HAND_ORIGINS_PATCH
        self.assertEqual((new[0] - old[0], new[2] - old[2]), (-16, 2))
        self.assertEqual((new[4] - old[4], new[6] - old[6]), (-16, 2))

    def test_relocated_stream_is_exact_legal_and_within_nov4_memory(self) -> None:
        """Lock deterministic RLE framing and the resident NOV3 boundary."""
        layout = self._layout()
        stream = layout["stream"]
        final, second_start = title.decode_title_rle(self.patched, stream)
        second, terminator = title.decode_title_rle(self.patched, second_start)
        combined, end = title.decode_title_stream(self.patched, stream)
        self.assertEqual(final, self.assets.final_nametable)
        self.assertEqual(second, self.assets.second_nametable)
        self.assertEqual(combined, final + second)
        self.assertEqual(self.patched[terminator], 0xFF)
        self.assertEqual(end, len(self.patched))
        self.assertLess(
            title.NOV4_LOAD_ADDRESS + len(self.patched), title.NOV3_LOAD_ADDRESS
        )
        self.assertEqual(
            title.build_title_assets(
                self.source, self.native_path, slide_target=self.slide_path
            ),
            self.assets,
        )
        self.assertEqual(
            title.patched_nov4_title(
                self.source, self.native_path, slide_target=self.slide_path
            ),
            self.patched,
        )

    def test_source_and_native_asset_guards_fail_closed(self) -> None:
        """Reject unknown source bytes and malformed pixel authorities."""
        damaged = bytearray(self.source)
        damaged[title.FINAL_NAMETABLE_START] ^= 1
        with self.assertRaises(title.TitlePatchError):
            title.patched_nov4_title(bytes(damaged), self.native_path)
        damaged = bytearray(self.source)
        damaged[title.CLOCK_SOURCE_OFFSET] ^= 1
        with self.assertRaises(title.TitlePatchError):
            title.patched_nov4_title(bytes(damaged), self.native_path)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.png"
            Image.new("L", (255, 240), 0).save(path)
            with self.assertRaises(title.TitlePatchError):
                title._target_to_indices(path)


if __name__ == "__main__":
    unittest.main()
