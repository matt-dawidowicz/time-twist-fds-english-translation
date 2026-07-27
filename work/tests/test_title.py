from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from PIL import Image

import time_twist.title as title


class TitlePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = Path("work/build/NOV4_accented_font_ui.bin")
        if not source.exists():
            source = Path("work/extracted_zenpen/side0_08_NOV4_A200.bin")
        cls.source_path = source
        cls.target_path = Path(
            "work/title_assets/Time Twist full-screen logo reference.png"
        )

    def test_recovered_title_asset_boundaries(self) -> None:
        if not self.source_path.exists():
            self.skipTest("NOV4 fixture is not available")
        data = self.source_path.read_bytes()
        final, final_end = title.decode_title_rle(
            data, title.FINAL_NAMETABLE_START
        )
        second, second_end = title.decode_title_rle(
            data, title.SECOND_NAMETABLE_START
        )
        self.assertEqual(len(final), 1024)
        self.assertEqual(len(second), 1024)
        self.assertEqual(final_end, title.FINAL_NAMETABLE_END)
        self.assertEqual(second_end, title.SECOND_NAMETABLE_END)
        combined, combined_end = title.decode_title_stream(
            data, title.FINAL_NAMETABLE_START
        )
        self.assertEqual(combined, final + second)
        self.assertEqual(combined_end, title.SECOND_NAMETABLE_END + 1)
        self.assertEqual(
            hashlib.sha256(
                data[title.CLOCK_SOURCE_OFFSET:title.CLOCK_SOURCE_END]
            ).hexdigest().upper(),
            title.CLOCK_SOURCE_SHA256,
        )

    def test_english_title_keeps_white_edges_subtitle_and_reference_clock_face(self) -> None:
        if not self.source_path.exists() or not self.target_path.exists():
            self.skipTest("title fixtures are not available")
        data = self.source_path.read_bytes()
        assets = title.build_title_assets(data, self.target_path)
        patched = title._render_split_nametable(
            assets.final_nametable,
            assets.background_chr,
            assets.bottom_chr,
        )
        source_final, _ = title.decode_title_rle(
            data, title.FINAL_NAMETABLE_START
        )
        source_chr = data[
            title.TITLE_CHR_OFFSET:title.TITLE_CHR_OFFSET + title.TITLE_CHR_SIZE
        ]
        original = title._render_indexed_nametable(source_final, source_chr)

        expected = Image.new("L", (256, 240), 0)
        width = sum(
            4 if character == " " else 6
            for character in title.DEFAULT_SUBTITLE
        ) - 1
        title._draw_text(
            expected,
            title.DEFAULT_SUBTITLE,
            x=(256 - width) // 2,
            y=96,
            color=2,
        )
        self.assertEqual(
            patched.crop((0, 96, 256, 103)).tobytes(),
            expected.crop((0, 96, 256, 103)).tobytes(),
        )
        self.assertTrue(
            all(
                pixel == 0
                for pixel in patched.crop((0, 92, 256, 96)).get_flattened_data()
            )
        )

        expected_clock = title._target_to_indices(self.target_path)
        title._remove_full_reference_hand(expected_clock)
        expected_clock.paste(0, (0, 92, 256, 96))
        self.assertEqual(
            patched.crop((103, 40, 161, 96)).tobytes(),
            expected_clock.crop((103, 40, 161, 96)).tobytes(),
        )
        self.assertEqual(
            patched.crop((0, 0, 256, 96)).tobytes(),
            expected_clock.crop((0, 0, 256, 96)).tobytes(),
        )
        self.assertEqual(
            patched.crop((0, 136, 256, 192)).tobytes(),
            original.crop((0, 136, 256, 192)).tobytes(),
        )
        expected_full = original.copy()
        expected_full.paste(expected_clock.crop((0, 0, 256, 96)), (0, 0))
        expected_full.paste(0, (0, 92, 256, 106))
        title._draw_text(
            expected_full,
            title.DEFAULT_SUBTITLE,
            x=(256 - width) // 2,
            y=96,
            color=2,
        )
        self.assertEqual(patched.tobytes(), expected_full.tobytes())
        self.assertTrue(
            all(
                tile_id < title.TOP_TILE_COUNT
                for tile_id in assets.final_nametable[:960]
            )
        )
        self.assertTrue(
            all(
                tile_id < title.TOP_TILE_COUNT
                for tile_id in assets.second_nametable[:960]
            )
        )
        self.assertEqual(assets.background_chr, assets.chr_data)
        self.assertEqual(assets.approximation_error, 0)

    def test_nintendo_phase_is_clean_and_keeps_its_original_logo(self) -> None:
        if not self.source_path.exists() or not self.target_path.exists():
            self.skipTest("title fixtures are not available")
        source = self.source_path.read_bytes()
        assets = title.build_title_assets(source, self.target_path)
        source_second, _ = title.decode_title_rle(
            source, title.SECOND_NAMETABLE_START
        )
        source_chr = source[
            title.TITLE_CHR_OFFSET:title.TITLE_CHR_OFFSET + title.TITLE_CHR_SIZE
        ]
        original = title._render_indexed_nametable(source_second, source_chr)
        initial_chr = bytearray(assets.background_chr)
        first = title.NINTENDO_FIRST_TILE * 16
        initial_chr[first:first + title.NINTENDO_CHR_SIZE] = assets.nintendo_chr
        phase_zero = title._render_indexed_nametable(
            assets.second_nametable, bytes(initial_chr)
        )

        reserved_ids = set(range(
            title.NINTENDO_FIRST_TILE,
            title.NINTENDO_FIRST_TILE + title.NINTENDO_TILE_COUNT,
        ))
        self.assertTrue(reserved_ids.isdisjoint(assets.second_nametable[:384]))
        final_top = title._render_indexed_nametable(
            assets.final_nametable,
            assets.background_chr,
        )
        slide_right = title.SLIDE_TITLE_TILE_COLUMNS * 8
        self.assertEqual(
            phase_zero.crop((0, 0, slide_right, 96)).tobytes(),
            final_top.crop((0, 0, slide_right, 96)).tobytes(),
        )
        self.assertTrue(
            all(
                pixel == 0
                for pixel in phase_zero.crop((slide_right, 0, 256, 96)).get_flattened_data()
            )
        )
        self.assertEqual(
            phase_zero.crop((0, 96, 256, 240)).tobytes(),
            original.crop((0, 96, 256, 240)).tobytes(),
        )

    def test_runtime_title_palette_uses_white_pink_purple_index_order(self) -> None:
        cpu_capture = Path("work/mesen_capture/zenpen_title_cpu.dmp")
        if not cpu_capture.exists():
            self.skipTest("original title RAM capture is not available")
        palette_buffer = cpu_capture.read_bytes()[0x300:0x320]

        # The NMI uploads the 32-byte buffer from index 31 down to zero.
        # Its last stored group therefore becomes background palette zero.
        self.assertEqual(
            list(reversed(palette_buffer[28:32])),
            [0x0F, 0x30, 0x24, 0x04],
        )
        self.assertEqual(title.TITLE_PALETTE[1], (255, 254, 255))
        self.assertEqual(title.TITLE_PALETTE[2], (243, 106, 255))
        self.assertEqual(title.TITLE_PALETTE[3], (92, 0, 126))

    def test_title_patch_relocates_maps_and_centers_untouched_clock_frames(self) -> None:
        if not self.source_path.exists() or not self.target_path.exists():
            self.skipTest("title fixtures are not available")
        source = self.source_path.read_bytes()
        assets = title.build_title_assets(source, self.target_path)
        patched = title.patched_nov4_title(source, self.target_path)
        append_offset = len(source)
        title_stream_offset = append_offset + sum((
            title.BOTTOM_CHR_SIZE,
            title.NINTENDO_CHR_SIZE,
            title.NINTENDO_CHR_SIZE,
            title.INITIAL_CHR_LOADER_SIZE,
            title.TITLE_TRANSITION_SIZE,
            title.TITLE_EXIT_SIZE,
        ))
        title_stream_address = title.NOV4_LOAD_ADDRESS + title_stream_offset
        bottom_offset = append_offset
        nintendo_offset = bottom_offset + title.BOTTOM_CHR_SIZE
        restore_offset = nintendo_offset + title.NINTENDO_CHR_SIZE
        loader_offset = restore_offset + title.NINTENDO_CHR_SIZE
        transition_offset = loader_offset + title.INITIAL_CHR_LOADER_SIZE
        exit_offset = transition_offset + title.TITLE_TRANSITION_SIZE
        loader_address = title.NOV4_LOAD_ADDRESS + loader_offset
        transition_address = title.NOV4_LOAD_ADDRESS + transition_offset
        exit_address = title.NOV4_LOAD_ADDRESS + exit_offset
        bottom_address = title.NOV4_LOAD_ADDRESS + bottom_offset
        restore_address = title.NOV4_LOAD_ADDRESS + restore_offset

        self.assertEqual(
            patched[title.TITLE_EXIT_OFFSET:title.TITLE_EXIT_OFFSET + 7],
            bytes((0x4C, exit_address & 0xFF, exit_address >> 8)) + b"\xEA" * 4,
        )
        self.assertEqual(
            patched[
                title.TITLE_POINTER_OFFSET:title.TITLE_POINTER_OFFSET + 4
            ],
            bytes((
                0xA9,
                title_stream_address & 0xFF,
                0xA2,
                title_stream_address >> 8,
            )),
        )
        self.assertEqual(
            patched[title.PPUCTRL_INIT_OFFSET:title.PPUCTRL_INIT_OFFSET + 6],
            source[title.PPUCTRL_INIT_OFFSET:title.PPUCTRL_INIT_OFFSET + 6],
        )
        self.assertEqual(
            patched[
                title.BACKGROUND_TAIL_UPLOAD_OFFSET:
                title.BACKGROUND_TAIL_UPLOAD_OFFSET + 11
            ],
            bytes((0x20, loader_address & 0xFF, loader_address >> 8))
            + b"\xEA" * 8,
        )
        self.assertEqual(
            patched[
                title.PHASE_ZERO_UPLOAD_OFFSET:
                title.PHASE_ZERO_UPLOAD_OFFSET + 11
            ],
            source[
                title.PHASE_ZERO_UPLOAD_OFFSET:
                title.PHASE_ZERO_UPLOAD_OFFSET + 11
            ],
        )
        self.assertEqual(
            patched[
                title.TITLE_TRANSITION_CALL_OFFSET:
                title.TITLE_TRANSITION_CALL_OFFSET
                + len(title.TITLE_TRANSITION_CALL_SOURCE)
            ],
            bytes((0x20, transition_address & 0xFF, transition_address >> 8))
            + b"\xEA" * (len(title.TITLE_TRANSITION_CALL_SOURCE) - 3),
        )
        expected_transition = bytes.fromhex(
            "A9 01 8D E1 07 20 E0 6F "
            "A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20 "
            "A0 1B A9 00 A2 26 20 AF EB"
        ) + restore_address.to_bytes(2, "little") + bytes.fromhex(
            "A0 00 A9 00 A2 37 20 AF EB"
        ) + bottom_address.to_bytes(2, "little") + bytes.fromhex(
            "68 85 FF 09 10 85 FF 8D 00 20 "
            "A9 00 85 4F 85 55 85 57 85 58 85 49 85 4A "
            "8D 70 07 8D 71 07 "
            "A9 FF 85 48 A9 10 85 56 "
            "A9 C0 8D 72 07 A9 3F 8D 73 07 "
            "A5 1C 8D 01 20 60"
        )
        self.assertEqual(
            patched[transition_offset:exit_offset],
            expected_transition,
        )
        self.assertEqual(
            patched[exit_offset:title_stream_offset],
            bytes.fromhex(
                "A9 00 8D 22 40 85 48 85 4F 85 9C "
                "A5 FF 09 10 85 FF 8D 00 20 "
                "A9 02 A2 03 4C 19 61"
            ),
        )
        self.assertEqual(
            len(patched),
            title_stream_offset
            + len(assets.encoded_final)
            + len(assets.encoded_second)
            + 1,
        )
        final, second_offset = title.decode_title_rle(patched, title_stream_offset)
        second, terminator_offset = title.decode_title_rle(patched, second_offset)
        combined, end = title.decode_title_stream(patched, title_stream_offset)
        self.assertEqual(final, assets.final_nametable)
        self.assertEqual(second, assets.second_nametable)
        self.assertEqual(combined, final + second)
        self.assertEqual(patched[terminator_offset], 0xFF)
        self.assertEqual(end, len(patched))
        self.assertLess(
            title.NOV4_LOAD_ADDRESS + len(patched), title.NOV3_LOAD_ADDRESS
        )

        self.assertEqual(
            patched[title.CLOCK_SOURCE_OFFSET:title.CLOCK_SOURCE_END],
            source[title.CLOCK_SOURCE_OFFSET:title.CLOCK_SOURCE_END],
        )
        self.assertEqual(
            patched[
                title.CLOCK_METASPRITE_START:title.CLOCK_METASPRITE_END
            ],
            source[title.CLOCK_METASPRITE_START:title.CLOCK_METASPRITE_END],
        )
        self.assertEqual(
            patched[
                title.CLOCK_HAND_ORIGINS_OFFSET:
                title.CLOCK_HAND_ORIGINS_OFFSET
                + len(title.CLOCK_HAND_ORIGINS_PATCH)
            ],
            title.CLOCK_HAND_ORIGINS_PATCH,
        )
        allowed = set(
            range(title.TITLE_POINTER_OFFSET, title.TITLE_POINTER_OFFSET + 4)
        )
        for offset, size in (
            (title.TITLE_EXIT_OFFSET, len(title.TITLE_EXIT_SOURCE)),
            (title.BACKGROUND_TAIL_UPLOAD_OFFSET, 11),
            (
                title.TITLE_TRANSITION_CALL_OFFSET,
                len(title.TITLE_TRANSITION_CALL_SOURCE),
            ),
            (
                title.CLOCK_HAND_ORIGINS_OFFSET,
                len(title.CLOCK_HAND_ORIGINS_PATCH),
            ),
        ):
            allowed.update(range(offset, offset + size))
        allowed.update(range(title.TITLE_CHR_OFFSET, title.CLOCK_SOURCE_OFFSET))
        actual = {
            index
            for index, (before, after) in enumerate(zip(source, patched))
            if before != after
        }
        self.assertLessEqual(actual, allowed)

    def test_title_patch_rejects_unknown_source(self) -> None:
        if not self.source_path.exists() or not self.target_path.exists():
            self.skipTest("title fixtures are not available")
        damaged = bytearray(self.source_path.read_bytes())
        damaged[title.TITLE_CHR_OFFSET] ^= 0x01
        with self.assertRaises(title.TitlePatchError):
            title.patched_nov4_title(bytes(damaged), self.target_path)


if __name__ == "__main__":
    unittest.main()
