"""Private-overlay integration tests for the current title asset, layout, and runtime-patch contracts."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import time_twist.title as title
from PIL import Image

from tests.support.paths import WORK_ROOT
from tools.preview.rebuild_native_title_asset import build_native_titles

WORK_DIR = WORK_ROOT

NATIVE_FILE_SHA256 = (
    "B1F262770FB490E2A933B956D5857432C101EE378A0F765CCCFACD8EE5FBF9A8"
)
NATIVE_PIXELS_SHA256 = (
    "27EE6BA45E19778B80EBBEACEEDC763EF896CE6A0A942D0C080114AB2C02B208"
)
SLIDE_FILE_SHA256 = (
    "5B77F1E1080BC6A34AAB8B66420C2D53F025121285095ED142B481AD3C0C873C"
)
SLIDE_PIXELS_SHA256 = (
    "34FF7674E69C187BBF504C126F5F1F4ACBEF93823633C2EB00D5E4558FFC95BB"
)
FINAL_ATTRIBUTES_SHA256 = (
    "42869099B63ED98598904E2C1B959CA7A38A3749ED51712774549ED4F348926E"
)
SECOND_ATTRIBUTES_SHA256 = (
    "50B20CBF142A10729ED041C30EFAFFC52F4AD332B4729AE4E9B29A198AF066A3"
)


def _sha256(data: bytes) -> str:
    """Provide a deterministic helper for the current contract tests."""
    return hashlib.sha256(data).hexdigest().upper()


def _patterns(data: bytes) -> tuple[bytes, ...]:
    """Provide a deterministic helper for the current contract tests."""
    if len(data) % 16:
        raise AssertionError("CHR data is not tile aligned")
    return tuple(
        data[offset : offset + 16] for offset in range(0, len(data), 16)
    )


class TitlePatchTests(unittest.TestCase):
    """Group current regression tests by project contract."""

    @classmethod
    def setUpClass(cls) -> None:
        """Prepare shared fixtures for the current contract tests."""
        source = WORK_DIR / "build/NOV4_accented_font_ui.bin"
        if not source.exists():
            source = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        cls.source_path = source
        cls.native_path = (
            WORK_DIR / "title_assets/Time Twist approved native title.png"
        )
        cls.slide_path = (
            WORK_DIR / "title_assets/Time Twist approved native slide.png"
        )
        cls.opening_path = (
            WORK_DIR / "title_assets/Time Twist approved English opening.gif"
        )
        required = (
            cls.source_path,
            cls.native_path,
            cls.slide_path,
            cls.opening_path,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise AssertionError(f"title fixtures are unavailable: {missing}")
        cls.source = cls.source_path.read_bytes()
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

    def assert_legal_rle(self, encoded: bytes, expected: bytes) -> None:
        """Assert the current contract against the prepared test fixture."""
        decoded = bytearray()
        offset = 0
        while offset < len(encoded):
            marker = encoded[offset]
            offset += 1
            self.assertNotEqual(
                marker, 0xFF, "RLE fragment contains a terminator"
            )
            if marker >= 0xC0:
                self.assertLessEqual(marker, 0xFE)
                count = marker - 0xC0
                self.assertIn(count, range(1, 63))
                self.assertLess(
                    offset, len(encoded), "RLE run is missing its value"
                )
                decoded.extend((encoded[offset],) * count)
                offset += 1
            else:
                decoded.append(marker)
        self.assertEqual(bytes(decoded), expected)
        self.assertEqual(title.encode_title_rle(expected), encoded)

    def _layout(self) -> dict[str, int]:
        """Provide a deterministic helper for the current contract tests."""
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

    def test_recovered_title_boundaries_and_source_hashes(self) -> None:
        """Verify the current contract described by this regression test."""
        final, final_end = title.decode_title_rle(
            self.source, title.FINAL_NAMETABLE_START
        )
        second, second_end = title.decode_title_rle(
            self.source, title.SECOND_NAMETABLE_START
        )
        combined, combined_end = title.decode_title_stream(
            self.source, title.FINAL_NAMETABLE_START
        )
        self.assertEqual((len(final), len(second)), (1024, 1024))
        self.assertEqual(final_end, title.FINAL_NAMETABLE_END)
        self.assertEqual(second_end, title.SECOND_NAMETABLE_END)
        self.assertEqual(combined, final + second)
        self.assertEqual(combined_end, title.SECOND_NAMETABLE_END + 1)
        self.assertEqual(
            _sha256(
                self.source[title.CLOCK_SOURCE_OFFSET : title.CLOCK_SOURCE_END]
            ),
            title.CLOCK_SOURCE_SHA256,
        )
        self.assertEqual(
            _sha256(
                self.source[
                    title.CLOCK_METASPRITE_START : title.CLOCK_METASPRITE_END
                ]
            ),
            title.CLOCK_METASPRITE_SHA256,
        )

    def test_native_authority_regenerates_exactly_and_has_locked_geometry(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        regenerated, regenerated_slide = build_native_titles(self.opening_path)
        self.assertEqual(regenerated.mode, "P")
        self.assertEqual(regenerated.size, (256, 240))
        self.assertEqual(regenerated.tobytes(), self.native.tobytes())
        self.assertEqual(regenerated_slide.tobytes(), self.slide.tobytes())
        self.assertEqual(
            _sha256(self.native_path.read_bytes()), NATIVE_FILE_SHA256
        )
        self.assertEqual(_sha256(self.native.tobytes()), NATIVE_PIXELS_SHA256)
        self.assertEqual(
            _sha256(self.slide_path.read_bytes()), SLIDE_FILE_SHA256
        )
        self.assertEqual(_sha256(self.slide.tobytes()), SLIDE_PIXELS_SHA256)
        self.assertEqual(
            sum(pixel != 0 for pixel in self.native.get_flattened_data()),
            7982,
        )
        self.assertEqual(
            sum(pixel != 0 for pixel in self.slide.get_flattened_data()),
            5916,
        )
        self.assertEqual(set(self.native.get_flattened_data()), {0, 1, 2, 3})
        self.assertEqual(set(self.slide.get_flattened_data()), {0, 1})
        self.assertFalse(
            any(self.native.crop((0, 97, 256, 240)).get_flattened_data())
        )

    def test_completed_title_is_exact_and_lower_rom_art_is_unchanged(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        rendered = title._render_split_nametable(
            self.assets.final_nametable,
            self.assets.background_chr,
            self.assets.bottom_chr,
        )
        source_final, _ = title.decode_title_rle(
            self.source, title.FINAL_NAMETABLE_START
        )
        source_chr = self.source[
            title.TITLE_CHR_OFFSET : title.TITLE_CHR_OFFSET
            + title.TITLE_CHR_SIZE
        ]
        original = title._render_indexed_nametable(source_final, source_chr)

        self.assertEqual(
            rendered.crop((0, 0, 256, 97)).tobytes(),
            self.native.crop((0, 0, 256, 97)).tobytes(),
        )
        expected = original.copy()
        expected.paste(self.native.crop((0, 0, 256, 97)), (0, 0))
        expected.paste(0, (0, 97, 256, 112))
        subtitle_width = (
            sum(
                4 if character == " " else 6
                for character in title.DEFAULT_SUBTITLE
            )
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
        self.assertFalse(
            any(rendered.crop((0, 97, 256, 102)).get_flattened_data())
        )
        self.assertFalse(
            any(rendered.crop((0, 109, 256, 112)).get_flattened_data())
        )

    def test_exact_tile_budgets_phase_delta_and_completed_origin(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        final_top = _patterns(
            self.assets.background_chr[: title.TOP_TILE_COUNT * 16]
        )
        slide_top = _patterns(
            self.assets.slide_chr[: title.TOP_TILE_COUNT * 16]
        )
        delta = _patterns(self.assets.final_delta_chr)
        bottom = _patterns(self.assets.bottom_chr)
        nintendo = _patterns(self.assets.nintendo_chr)
        restore = _patterns(self.assets.restore_chr)
        self.assertEqual((len(final_top), len(set(final_top))), (236, 236))
        self.assertEqual((len(slide_top), len(set(slide_top))), (236, 236))
        self.assertEqual(
            (len(delta), len(set(delta))),
            (title.FINAL_DELTA_TILE_COUNT,) * 2,
        )
        self.assertEqual((len(bottom), len(set(bottom))), (55, 55))
        self.assertEqual((len(nintendo), len(set(nintendo))), (38, 38))
        self.assertEqual((len(restore), len(set(restore))), (38, 38))
        self.assertTrue(set(nintendo).isdisjoint(restore))
        self.assertEqual(
            self.assets.restore_chr,
            self.assets.slide_chr[
                title.NINTENDO_FIRST_TILE
                * 16 : (title.NINTENDO_FIRST_TILE + title.NINTENDO_TILE_COUNT)
                * 16
            ],
        )
        rebuilt_final = bytearray(self.assets.slide_chr)
        delta_start = self.assets.final_delta_first_tile * 16
        rebuilt_final[
            delta_start : delta_start + len(self.assets.final_delta_chr)
        ] = self.assets.final_delta_chr
        self.assertEqual(bytes(rebuilt_final), self.assets.background_chr)
        self.assertEqual(self.assets.slide_chr, self.assets.chr_data)
        self.assertNotEqual(self.assets.background_chr, self.assets.chr_data)
        self.assertEqual(self.assets.approximation_error, 0)

        final_tiles = self.assets.final_nametable
        slide_tiles = self.assets.second_nametable
        self.assertTrue(
            all(
                tile_id < title.TOP_TILE_COUNT
                for tile_id in final_tiles[: 16 * 32]
            )
        )
        self.assertTrue(
            all(
                tile_id < title.BOTTOM_TILE_COUNT
                for tile_id in final_tiles[16 * 32 : 960]
            )
        )
        self.assertTrue(
            all(
                tile_id < title.TOP_TILE_COUNT
                for tile_id in slide_tiles[: 12 * 32]
            )
        )
        self.assertTrue(
            all(
                title.NINTENDO_FIRST_TILE
                <= tile_id
                < title.NINTENDO_FIRST_TILE + title.NINTENDO_TILE_COUNT
                for tile_id in slide_tiles[12 * 32 : 960]
            )
        )

        final_logo = title._render_indexed_nametable(
            final_tiles, self.assets.background_chr
        ).crop((0, 0, 256, 96))
        slide_logo = title._render_indexed_nametable(
            slide_tiles, self.assets.slide_chr
        ).crop((0, 0, 256, 96))
        self.assertEqual(
            final_logo.tobytes(),
            self.native.crop((0, 0, 256, 96)).tobytes(),
        )
        self.assertEqual(
            slide_logo.tobytes(), self.slide.crop((0, 0, 256, 96)).tobytes()
        )

    def test_nintendo_overlay_and_pre_slide_restore_have_no_stale_logo_pixels(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        source_second, _ = title.decode_title_rle(
            self.source, title.SECOND_NAMETABLE_START
        )
        source_chr = self.source[
            title.TITLE_CHR_OFFSET : title.TITLE_CHR_OFFSET
            + title.TITLE_CHR_SIZE
        ]
        original = title._render_indexed_nametable(source_second, source_chr)
        first = title.NINTENDO_FIRST_TILE * 16
        end = first + title.NINTENDO_CHR_SIZE

        nintendo_phase_chr = bytearray(self.assets.slide_chr)
        nintendo_phase_chr[first:end] = self.assets.nintendo_chr
        nintendo_phase = title._render_indexed_nametable(
            self.assets.second_nametable, bytes(nintendo_phase_chr)
        )
        self.assertEqual(
            nintendo_phase.crop((0, 96, 256, 240)).tobytes(),
            original.crop((0, 96, 256, 240)).tobytes(),
        )

        nintendo_phase_chr[first:end] = self.assets.restore_chr
        self.assertEqual(bytes(nintendo_phase_chr), self.assets.slide_chr)
        restored = title._render_indexed_nametable(
            self.assets.second_nametable, bytes(nintendo_phase_chr)
        )
        self.assertEqual(
            restored.crop((0, 0, 256, 96)).tobytes(),
            self.slide.crop((0, 0, 256, 96)).tobytes(),
        )

    def test_native_slide_origins_wrap_and_representative_frames_are_locked(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        expected_origins = (
            0x1F0,
            0x01C,
            0x1D8,
            0x034,
            0x1C0,
            0x04C,
            0x1A8,
            0x064,
            0x190,
            0x07C,
            0x178,
            0x094,
            0x160,
            0x0AC,
            0x148,
            0x0C4,
            0x130,
            0x0DC,
            0x118,
            0x0F4,
            0x100,
        )
        self.assertEqual(title.SLIDE_SCROLL_ORIGINS, expected_origins)
        self.assertEqual(
            tuple(origin - 0x100 for origin in expected_origins),
            (
                240,
                -228,
                216,
                -204,
                192,
                -180,
                168,
                -156,
                144,
                -132,
                120,
                -108,
                96,
                -84,
                72,
                -60,
                48,
                -36,
                24,
                -12,
                0,
            ),
        )
        self.assertEqual(
            title.SLIDE_BACKGROUND_PALETTES,
            (
                (0x0F, 0x0F, 0x0F, 0x0F),
                (0x0F, 0x30, 0x30, 0x30),
                (0x0F, 0x0F, 0x0F, 0x0F),
                (0x0F, 0x0F, 0x0F, 0x0F),
            ),
        )
        self.assertEqual(title.SLIDE_WHITE_COLOR, 0x30)

        def masked_physical_nametable(nametable: bytes) -> Image.Image:
            """Independently model one map's state-3 attribute visibility."""
            unmasked = title._render_indexed_nametable(
                nametable, self.assets.slide_chr
            ).crop((0, 0, 256, 96))
            attributes = nametable[960:1024]
            source_pixels = unmasked.load()
            masked = Image.new("L", (256, 96), 0)
            masked_pixels = masked.load()
            for y in range(96):
                for x in range(256):
                    attribute = attributes[(y // 32) * 8 + (x // 32)]
                    quadrant_shift = ((y // 16) & 1) * 4 + ((x // 16) & 1) * 2
                    palette_id = (attribute >> quadrant_shift) & 3
                    pattern_index = source_pixels[x, y]
                    if palette_id == 1 and pattern_index in {1, 2, 3}:
                        masked_pixels[x, y] = pattern_index
            return masked

        final_physical = masked_physical_nametable(self.assets.final_nametable)
        slide_physical = masked_physical_nametable(
            self.assets.second_nametable
        )
        world = Image.new("L", (512, 96), 0)
        world.paste(final_physical, (0, 0))
        world.paste(slide_physical, (256, 0))
        for index, origin in enumerate(expected_origins):
            with self.subTest(index=index, origin=f"{origin:03X}"):
                # Mask each physical nametable before sampling the 512-pixel
                # world. This retains the NT1-to-NT0 wrap and the per-map
                # attribute state that reveals the oscillating logo strips.
                expected_raw = Image.new("L", (256, 96), 0)
                first_width = min(256, 512 - origin)
                expected_raw.paste(
                    world.crop((origin, 0, origin + first_width, 96)),
                    (0, 0),
                )
                if first_width < 256:
                    expected_raw.paste(
                        world.crop((0, 0, 256 - first_width, 96)),
                        (first_width, 0),
                    )
                raw = title.render_slide_logo_frame(self.assets, origin)
                self.assertEqual(raw.mode, "L")
                self.assertEqual(raw.size, (256, 96))
                self.assertEqual(raw.tobytes(), expected_raw.tobytes())

                # Only palette 1 maps native nonzero pattern indices to white.
                # The returned raw values preserve 1/2/3 so this projection
                # detects both lost outline pixels and hidden-part leakage.
                expected_monochrome = Image.new(
                    "RGB", (256, 240), title.TITLE_PALETTE[0]
                )
                raw_pixels = raw.load()
                expected_pixels = expected_monochrome.load()
                for y in range(96):
                    for x in range(256):
                        if raw_pixels[x, y]:
                            expected_pixels[x, y] = title.TITLE_PALETTE[1]
                monochrome = title.render_monochrome_slide_frame(
                    self.assets, origin
                )
                self.assertEqual(
                    monochrome.tobytes(), expected_monochrome.tobytes()
                )
                self.assertFalse(
                    any(
                        pixel != title.TITLE_PALETTE[0]
                        for pixel in monochrome.crop(
                            (0, 96, 256, 240)
                        ).get_flattened_data()
                    )
                )
        completed = title.render_slide_logo_frame(self.assets, 0x100)
        completed_source = self.slide.crop((0, 0, 256, 96))
        self.assertEqual(completed.tobytes(), completed_source.tobytes())
        self.assertEqual(
            sum(bool(pixel) for pixel in completed.get_flattened_data()),
            5916,
        )
        self.assertFalse(
            any(
                title.render_slide_logo_frame(
                    self.assets, 0x1F0
                ).get_flattened_data()
            )
        )
        for invalid in (-1, 0x200):
            with (
                self.subTest(invalid=invalid),
                self.assertRaises(title.TitlePatchError),
            ):
                title.render_slide_logo_frame(self.assets, invalid)

    def test_attribute_tables_and_runtime_palette_are_locked(self) -> None:
        """Verify the current contract described by this regression test."""
        source_final, _ = title.decode_title_rle(
            self.source, title.FINAL_NAMETABLE_START
        )
        source_second, _ = title.decode_title_rle(
            self.source, title.SECOND_NAMETABLE_START
        )
        final_attributes = self.assets.final_nametable[960:1024]
        second_attributes = self.assets.second_nametable[960:1024]
        self.assertEqual(final_attributes, source_final[960:1024])
        self.assertEqual(second_attributes, source_second[960:1024])
        self.assertEqual(_sha256(final_attributes), FINAL_ATTRIBUTES_SHA256)
        self.assertEqual(_sha256(second_attributes), SECOND_ATTRIBUTES_SHA256)
        self.assertEqual(final_attributes[:24], bytes(24))
        self.assertEqual(second_attributes[:24], bytes((0x55,)) * 24)

        cpu_capture = WORK_DIR / "runtime_capture/zenpen_title_cpu.dmp"
        if not cpu_capture.exists():
            self.fail("original title RAM capture is not available")
        palette_buffer = cpu_capture.read_bytes()[0x300:0x320]
        self.assertEqual(
            list(reversed(palette_buffer[28:32])),
            [0x0F, 0x30, 0x24, 0x04],
        )
        self.assertEqual(title.TITLE_PALETTE[1], (255, 254, 255))
        self.assertEqual(title.TITLE_PALETTE[2], (243, 106, 255))
        self.assertEqual(title.TITLE_PALETTE[3], (92, 0, 126))

    def test_rle_fragments_are_legal_exact_and_singly_terminated(self) -> None:
        """Verify the current contract described by this regression test."""
        self.assert_legal_rle(
            self.assets.encoded_final, self.assets.final_nametable
        )
        self.assert_legal_rle(
            self.assets.encoded_second, self.assets.second_nametable
        )

        stream = self._layout()["stream"]
        second_offset = stream + len(self.assets.encoded_final)
        terminator = second_offset + len(self.assets.encoded_second)
        self.assertEqual(
            self.patched[stream:second_offset], self.assets.encoded_final
        )
        self.assertEqual(
            self.patched[second_offset:terminator], self.assets.encoded_second
        )
        self.assertEqual(self.patched[terminator:], b"\xff")
        final, decoded_second_offset = title.decode_title_rle(
            self.patched, stream
        )
        second, decoded_terminator = title.decode_title_rle(
            self.patched, decoded_second_offset
        )
        combined, end = title.decode_title_stream(self.patched, stream)
        self.assertEqual(
            (final, second),
            (
                self.assets.final_nametable,
                self.assets.second_nametable,
            ),
        )
        self.assertEqual(decoded_terminator, terminator)
        self.assertEqual(combined, final + second)
        self.assertEqual(end, len(self.patched))

    def test_patch_layout_helpers_scope_memory_and_determinism(self) -> None:
        """Verify the current contract described by this regression test."""
        layout = self._layout()

        def address(offset: int) -> int:
            """Provide a deterministic helper for the current contract tests."""
            return title.NOV4_LOAD_ADDRESS + offset

        bottom_address = address(layout["bottom"])
        nintendo_address = address(layout["nintendo"])
        loader_address = address(layout["loader"])
        slide_prep_address = address(layout["slide_prep"])
        transition_address = address(layout["transition"])
        exit_address = address(layout["exit"])
        stream_address = address(layout["stream"])
        base_restore_address = address(
            title.TITLE_CHR_OFFSET + title.NINTENDO_FIRST_TILE * 16
        )

        self.assertEqual(
            self.patched[layout["bottom"] : layout["nintendo"]],
            self.assets.bottom_chr,
        )
        self.assertEqual(
            self.patched[layout["nintendo"] : layout["delta"]],
            self.assets.nintendo_chr,
        )
        self.assertEqual(
            self.patched[layout["delta"] : layout["loader"]],
            self.assets.final_delta_chr,
        )
        expected_loader = (
            bytes.fromhex("A0 1B A9 00 A2 26 20 AF EB")
            + nintendo_address.to_bytes(2, "little")
            + b"\x60"
        )
        self.assertEqual(
            self.patched[layout["loader"] : layout["slide_prep"]],
            expected_loader,
        )
        expected_slide_prep = title._pre_slide_restore_helper(
            base_restore_address
        )
        self.assertEqual(
            self.patched[layout["slide_prep"] : layout["transition"]],
            expected_slide_prep,
        )
        self.assertEqual(len(expected_slide_prep), title.SLIDE_PREP_SIZE)

        expected_transition = (
            bytes.fromhex(
                "A9 01 8D E1 07 20 E0 6F "
                "A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20 "
                f"A0 10 A9 00 A2 {title.FINAL_DELTA_TILE_COUNT:02X} 20 AF EB"
            )
            + address(layout["delta"]).to_bytes(2, "little")
            + bytes.fromhex("A0 00 A9 00 A2 37 20 AF EB")
            + bottom_address.to_bytes(2, "little")
            + bytes.fromhex(
                "68 85 FF 09 10 85 FF 8D 00 20 "
                "A9 00 85 4F 85 55 85 57 85 58 85 49 85 4A "
                "8D 70 07 8D 71 07 "
                "A9 FF 85 48 A9 10 85 56 "
                "A9 C0 8D 72 07 A9 3F 8D 73 07 "
                "A5 1C 8D 01 20 60"
            )
        )
        self.assertEqual(
            self.patched[layout["transition"] : layout["exit"]],
            expected_transition,
        )
        expected_exit = title.TITLE_EXIT_HELPER
        self.assertEqual(
            self.patched[layout["exit"] : layout["stream"]], expected_exit
        )

        self.assertEqual(
            self.patched[
                title.TITLE_POINTER_OFFSET : title.TITLE_POINTER_OFFSET + 4
            ],
            bytes((0xA9, stream_address & 0xFF, 0xA2, stream_address >> 8)),
        )
        self.assertEqual(
            self.patched[
                title.BACKGROUND_TAIL_UPLOAD_OFFSET : title.BACKGROUND_TAIL_UPLOAD_OFFSET
                + 11
            ],
            bytes((0x20, loader_address & 0xFF, loader_address >> 8))
            + b"\xea" * 8,
        )
        self.assertEqual(
            self.patched[
                title.SLIDE_PREP_CALL_OFFSET : title.SLIDE_PREP_CALL_OFFSET
                + len(title.SLIDE_PREP_CALL_SOURCE)
            ],
            bytes((0x20, slide_prep_address & 0xFF, slide_prep_address >> 8)),
        )
        self.assertEqual(
            self.patched[
                title.TITLE_TRANSITION_CALL_OFFSET : title.TITLE_TRANSITION_CALL_OFFSET
                + len(title.TITLE_TRANSITION_CALL_SOURCE)
            ],
            bytes((0x20, transition_address & 0xFF, transition_address >> 8))
            + b"\xea" * (len(title.TITLE_TRANSITION_CALL_SOURCE) - 3),
        )
        self.assertEqual(
            self.patched[
                title.TITLE_EXIT_OFFSET : title.TITLE_EXIT_OFFSET + 7
            ],
            bytes((0x4C, exit_address & 0xFF, exit_address >> 8))
            + b"\xea" * 4,
        )
        self.assertEqual(
            self.patched[
                title.PPUCTRL_INIT_OFFSET : title.PPUCTRL_INIT_OFFSET
                + len(title.PPUCTRL_INIT_SOURCE)
            ],
            self.source[
                title.PPUCTRL_INIT_OFFSET : title.PPUCTRL_INIT_OFFSET
                + len(title.PPUCTRL_INIT_SOURCE)
            ],
        )
        self.assertEqual(
            self.patched[
                title.PHASE_ZERO_UPLOAD_OFFSET : title.PHASE_ZERO_UPLOAD_OFFSET
                + len(title.PHASE_ZERO_UPLOAD_SOURCE)
            ],
            self.source[
                title.PHASE_ZERO_UPLOAD_OFFSET : title.PHASE_ZERO_UPLOAD_OFFSET
                + len(title.PHASE_ZERO_UPLOAD_SOURCE)
            ],
        )
        self.assertEqual(
            self.source[
                title.SLIDE_PALETTE_COLOR1_OFFSET : title.SLIDE_PALETTE_COLOR1_OFFSET
                + len(title.SLIDE_PALETTE_COLOR1_SOURCE)
            ],
            title.SLIDE_PALETTE_COLOR1_SOURCE,
        )
        self.assertEqual(
            self.patched[
                title.SLIDE_PALETTE_COLOR1_OFFSET : title.SLIDE_PALETTE_COLOR1_OFFSET
                + len(title.SLIDE_PALETTE_COLOR1_PATCH)
            ],
            title.SLIDE_PALETTE_COLOR1_PATCH,
        )

        allowed = set(
            range(title.TITLE_POINTER_OFFSET, title.TITLE_POINTER_OFFSET + 4)
        )
        for offset, size in (
            (title.TITLE_EXIT_OFFSET, len(title.TITLE_EXIT_SOURCE)),
            (title.BACKGROUND_TAIL_UPLOAD_OFFSET, 11),
            (title.SLIDE_PREP_CALL_OFFSET, len(title.SLIDE_PREP_CALL_SOURCE)),
            (
                title.TITLE_TRANSITION_CALL_OFFSET,
                len(title.TITLE_TRANSITION_CALL_SOURCE),
            ),
            (
                title.SLIDE_PALETTE_COLOR1_OFFSET,
                len(title.SLIDE_PALETTE_COLOR1_PATCH),
            ),
            (
                title.CLOCK_HAND_ORIGINS_OFFSET,
                len(title.CLOCK_HAND_ORIGINS_PATCH),
            ),
        ):
            allowed.update(range(offset, offset + size))
        allowed.update(
            range(title.TITLE_CHR_OFFSET, title.CLOCK_SOURCE_OFFSET)
        )
        actual = {
            index
            for index, (before, after) in enumerate(
                zip(
                    self.source,
                    self.patched[: len(self.source)],
                    strict=True,
                )
            )
            if before != after
        }
        self.assertLessEqual(actual, allowed)

        self.assertEqual(
            len(self.patched),
            self._layout()["stream"]
            + len(self.assets.encoded_final)
            + len(self.assets.encoded_second)
            + 1,
        )
        self.assertLess(address(len(self.patched)), title.NOV3_LOAD_ADDRESS)
        self.assertEqual(
            title.build_title_assets(self.source, self.native_path),
            self.assets,
        )
        self.assertEqual(
            title.patched_nov4_title(self.source, self.native_path),
            self.patched,
        )

    def test_clock_chr_metasprites_and_timing_stay_native_with_new_origin(
        self,
    ) -> None:
        """Verify the current contract described by this regression test."""
        source_clock = self.source[
            title.CLOCK_SOURCE_OFFSET : title.CLOCK_SOURCE_END
        ]
        patched_clock = self.patched[
            title.CLOCK_SOURCE_OFFSET : title.CLOCK_SOURCE_END
        ]
        self.assertEqual(patched_clock, source_clock)
        self.assertEqual(_sha256(patched_clock), title.CLOCK_SOURCE_SHA256)
        source_metasprites = self.source[
            title.CLOCK_METASPRITE_START : title.CLOCK_METASPRITE_END
        ]
        patched_metasprites = self.patched[
            title.CLOCK_METASPRITE_START : title.CLOCK_METASPRITE_END
        ]
        self.assertEqual(patched_metasprites, source_metasprites)
        self.assertEqual(
            _sha256(patched_metasprites), title.CLOCK_METASPRITE_SHA256
        )
        self.assertEqual(
            self.source[
                title.CLOCK_HAND_ORIGINS_OFFSET : title.CLOCK_HAND_ORIGINS_OFFSET
                + 7
            ],
            bytes.fromhex("78 00 37 04 80 00 3F"),
        )
        self.assertEqual(
            self.patched[
                title.CLOCK_HAND_ORIGINS_OFFSET : title.CLOCK_HAND_ORIGINS_OFFSET
                + 7
            ],
            bytes.fromhex("6A 00 3A 04 72 00 42"),
        )

        # Both metasprite origins move exactly -14 X and +3 Y. Their animation
        # records remain native while the shared elbow lands on the reviewed
        # clock center (approximately 127,78).
        old = title.CLOCK_HAND_ORIGINS_SOURCE
        new = title.CLOCK_HAND_ORIGINS_PATCH
        self.assertEqual((new[0] - old[0], new[2] - old[2]), (-14, 3))
        self.assertEqual((new[4] - old[4], new[6] - old[6]), (-14, 3))
        self.assertEqual(new[1], old[1])
        self.assertEqual(new[3], old[3])
        self.assertEqual(new[5], old[5])

    def test_source_and_native_asset_guards_fail_closed(self) -> None:
        """Verify the current contract described by this regression test."""
        damaged = bytearray(self.source)
        damaged[title.SLIDE_PREP_CALL_OFFSET] ^= 0x01
        with self.assertRaisesRegex(
            title.TitlePatchError, "pre-slide palette call"
        ):
            title.patched_nov4_title(bytes(damaged), self.native_path)

        damaged = bytearray(self.source)
        damaged[title.SLIDE_PALETTE_COLOR1_OFFSET] ^= 0x01
        with self.assertRaisesRegex(
            title.TitlePatchError, "slide palette color 1"
        ):
            title.patched_nov4_title(bytes(damaged), self.native_path)

        damaged = bytearray(self.source)
        damaged[title.CLOCK_SOURCE_OFFSET] ^= 0x01
        with self.assertRaisesRegex(title.TitlePatchError, "title CHR"):
            title.patched_nov4_title(bytes(damaged), self.native_path)

        damaged = bytearray(self.source)
        damaged[title.FINAL_NAMETABLE_START] ^= 0x01
        with self.assertRaises(title.TitlePatchError):
            title.patched_nov4_title(bytes(damaged), self.native_path)

        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            invalid_images = (
                ("wrong-size.png", Image.new("L", (255, 240), 0)),
                ("wrong-mode.png", Image.new("RGB", (256, 240), (0, 0, 0))),
            )
            for name, image in invalid_images:
                path = temporary_path / name
                image.save(path)
                with (
                    self.subTest(name=name),
                    self.assertRaises(title.TitlePatchError),
                ):
                    title._target_to_indices(path)

            bad_index = Image.new("L", (256, 240), 0)
            bad_index.putpixel((0, 0), 4)
            bad_index_path = temporary_path / "bad-index.png"
            bad_index.save(bad_index_path)
            with self.assertRaisesRegex(title.TitlePatchError, "outside 0-3"):
                title._target_to_indices(bad_index_path)

            bad_ownership = Image.new("L", (256, 240), 0)
            bad_ownership.putpixel((0, 97), 1)
            bad_ownership_path = temporary_path / "bad-ownership.png"
            bad_ownership.save(bad_ownership_path)
            with self.assertRaisesRegex(
                title.TitlePatchError, "below its approved rows"
            ):
                title._target_to_indices(bad_ownership_path)


if __name__ == "__main__":
    unittest.main()
