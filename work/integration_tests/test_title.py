from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import time_twist.title as title
from PIL import Image
from rebuild_native_title_asset import build_native_title

WORK_DIR = Path(__file__).resolve().parents[1]

NATIVE_FILE_SHA256 = (
    "281FD547A893A27A8C744C3FDE8ADC6C98F4E2E97F5A32BCCCE2FFA270D5DA42"
)
NATIVE_PIXELS_SHA256 = (
    "C77D0A349D7BF98A4618E33F4C291C4A65052BB810132E635B159D4E958C8932"
)
LOGO_CROP_SHA256 = (
    "8F99A8550AFD72F86AAD11E23FDAFAE9EE4C97122258B683A9FA35A98E45C731"
)
CLOCK_CROP_SHA256 = (
    "3C16F7F08C456F26D60060356CD8D554B85101F8A876EB1E54286F47AA078E86"
)
FINAL_NAMETABLE_SHA256 = (
    "4B0AF1BE07B4DE5BDAE7BED62C3E83826658E72BC6ECCCBBAE2116741804BB89"
)
SECOND_NAMETABLE_SHA256 = (
    "ED26477E194FE7CF799B49FC065B0F49B2F1EB2235E88887C0892B1E6346458F"
)
BACKGROUND_CHR_SHA256 = (
    "869FF26DEA880C2350CA50DA011D11FB59D4F38EBC8FD1B3FE9D131B2492F16B"
)
BOTTOM_CHR_SHA256 = (
    "094DC4B019411BA7B40437FB9C3533DC4EB17C54889656D263DF7491EEF474E8"
)
NINTENDO_CHR_SHA256 = (
    "4867B9149645372FAA72E077252774721E854C6FDC6E6BBD5101DBA771B52AE0"
)
RESTORE_CHR_SHA256 = (
    "C9B3BC078BBE8CBF2712DE52A740D6D4938C667A8D51F9639DD74E713EE1713E"
)
ENCODED_FINAL_SHA256 = (
    "820671EC16B55DBF72C92CF8D8D346DA7F82B74EEF69B4CFE8AC1069B8BAE8E1"
)
ENCODED_SECOND_SHA256 = (
    "1DF3611DC0AAF1F3FEE8FD46F79623132F48D4D9421868EE895687DFCDF3C95C"
)
PATCHED_NOV4_SHA256 = (
    "6C66ACEE7FCFDDCA95153223764870F9797123F239F960381DA28860B1FB3EFE"
)
FINAL_ATTRIBUTES_SHA256 = (
    "42869099B63ED98598904E2C1B959CA7A38A3749ED51712774549ED4F348926E"
)
SECOND_ATTRIBUTES_SHA256 = (
    "50B20CBF142A10729ED041C30EFAFFC52F4AD332B4729AE4E9B29A198AF066A3"
)
SLIDE_RAW_SHA256 = {
    0: "DE676BAE28A480011D3D012DB14BEF539324E62A841A9627863C689BEA168AF3",
    2: "FAC907046579AF7AB099F2DD46F1CE8833A30D5B01B932D4438DB029924452BC",
    5: "3539DC8C2FEE3CC3F0EEF8B80EE5BF37F993944BF1123437D20020412C45D4E7",
    10: "6F3137A353B3FAE86D4602C0207EC9ADEC2415449B21158214D0127F01D67B30",
    15: "3418E214F9DC6A0928E400782058FE58CF6FBAFC1B92A472D2E6A446D6FB4FBC",
    19: "80CF6BDA05228FE9A3A01F4AAD043AC1F7A7495835E6B348928D1E87594449D7",
    20: "8F99A8550AFD72F86AAD11E23FDAFAE9EE4C97122258B683A9FA35A98E45C731",
}
SLIDE_MONOCHROME_SHA256 = {
    0: "DD493585BDE88D5307E760B29CDD3A721AD9FA8FA5CB16618C77889C0D6BE401",
    2: "986991C91B87117B28D2AF4BC92A70DB3EAAE448101ED2B81ADDE23BA8372688",
    5: "CB415D8024D851B698D40640D036B7A1208D7BB889DC2ACCEE2E4873AF1C3291",
    10: "335924BF63C8A1CBD9D6DE3AD390AF096760EA1D8AE0AD8178D18966218F4A9C",
    15: "0AFB109469A4CD2E5FEC7FC01224975DDA3763C0C242554239DCD1DDA30659C9",
    19: "8AE548C5D0082866F7A5F61B9F3D1C0E43ECFDD05EC57D1005E31001EE252099",
    20: "F9908D76CF3B60DC174174EAD6BCAE207F735E4759C57D142062C49B910A7FD0",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _patterns(data: bytes) -> tuple[bytes, ...]:
    if len(data) % 16:
        raise AssertionError("CHR data is not tile aligned")
    return tuple(
        data[offset : offset + 16] for offset in range(0, len(data), 16)
    )


class TitlePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = WORK_DIR / "build/NOV4_accented_font_ui.bin"
        if not source.exists():
            source = WORK_DIR / "extracted_zenpen/side0_08_NOV4_A200.bin"
        cls.source_path = source
        cls.native_path = (
            WORK_DIR / "title_assets/Time Twist approved native title.png"
        )
        cls.design_path = (
            WORK_DIR / "title_assets/Time Twist polished design reference.png"
        )
        cls.legacy_path = (
            WORK_DIR / "title_assets/Time Twist full-screen logo reference.png"
        )
        required = (
            cls.source_path,
            cls.native_path,
            cls.design_path,
            cls.legacy_path,
        )
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise AssertionError(f"title fixtures are unavailable: {missing}")
        cls.source = cls.source_path.read_bytes()
        cls.native = title._target_to_indices(cls.native_path)
        cls.assets = title.build_title_assets(cls.source, cls.native_path)
        cls.patched = title.patched_nov4_title(cls.source, cls.native_path)

    def assert_legal_rle(self, encoded: bytes, expected: bytes) -> None:
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
        bottom = len(self.source)
        nintendo = bottom + title.BOTTOM_CHR_SIZE
        restore = nintendo + title.NINTENDO_CHR_SIZE
        loader = restore + title.NINTENDO_CHR_SIZE
        slide_prep = loader + title.INITIAL_CHR_LOADER_SIZE
        transition = slide_prep + title.SLIDE_PREP_SIZE
        exit_helper = transition + title.TITLE_TRANSITION_SIZE
        stream = exit_helper + title.TITLE_EXIT_SIZE
        return {
            "bottom": bottom,
            "nintendo": nintendo,
            "restore": restore,
            "loader": loader,
            "slide_prep": slide_prep,
            "transition": transition,
            "exit": exit_helper,
            "stream": stream,
        }

    def test_recovered_title_boundaries_and_source_hashes(self) -> None:
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
        regenerated = build_native_title(self.design_path, self.legacy_path)
        self.assertEqual(regenerated.mode, "L")
        self.assertEqual(regenerated.size, (256, 240))
        self.assertEqual(regenerated.tobytes(), self.native.tobytes())
        self.assertEqual(
            _sha256(self.native_path.read_bytes()), NATIVE_FILE_SHA256
        )
        self.assertEqual(_sha256(self.native.tobytes()), NATIVE_PIXELS_SHA256)

        logo = self.native.crop((0, 0, 256, 96))
        clock = self.native.crop((100, 36, 152, 96))
        self.assertEqual(_sha256(logo.tobytes()), LOGO_CROP_SHA256)
        self.assertEqual(_sha256(clock.tobytes()), CLOCK_CROP_SHA256)
        self.assertEqual(
            sum(pixel != 0 for pixel in logo.get_flattened_data()), 9348
        )
        self.assertEqual(
            sum(pixel != 0 for pixel in clock.get_flattened_data()), 810
        )
        self.assertEqual(set(self.native.get_flattened_data()), {0, 1, 2, 3})
        self.assertFalse(
            any(self.native.crop((0, 96, 256, 240)).get_flattened_data())
        )

    def test_completed_title_is_exact_and_lower_rom_art_is_unchanged(
        self,
    ) -> None:
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
            rendered.crop((0, 0, 256, 96)).tobytes(),
            self.native.crop((0, 0, 256, 96)).tobytes(),
        )
        expected = original.copy()
        expected.paste(self.native.crop((0, 0, 256, 96)), (0, 0))
        expected.paste(0, (0, 92, 256, 106))
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
            y=96,
            color=2,
        )
        self.assertEqual(rendered.tobytes(), expected.tobytes())
        self.assertEqual(
            rendered.crop((0, 106, 256, 240)).tobytes(),
            original.crop((0, 106, 256, 240)).tobytes(),
        )
        self.assertFalse(
            any(rendered.crop((0, 92, 256, 96)).get_flattened_data())
        )
        self.assertFalse(
            any(rendered.crop((0, 103, 256, 106)).get_flattened_data())
        )

    def test_exact_tile_budgets_full_slide_identity_and_completed_origin(
        self,
    ) -> None:
        top = _patterns(
            self.assets.background_chr[: title.TOP_TILE_COUNT * 16]
        )
        bottom = _patterns(self.assets.bottom_chr)
        nintendo = _patterns(self.assets.nintendo_chr)
        restore = _patterns(self.assets.restore_chr)
        self.assertEqual((len(top), len(set(top))), (236, 236))
        self.assertEqual((len(bottom), len(set(bottom))), (55, 55))
        self.assertEqual((len(nintendo), len(set(nintendo))), (38, 38))
        self.assertEqual((len(restore), len(set(restore))), (38, 38))
        self.assertTrue(set(nintendo).isdisjoint(restore))
        self.assertEqual(
            self.assets.restore_chr,
            self.assets.background_chr[
                title.NINTENDO_FIRST_TILE
                * 16 : (title.NINTENDO_FIRST_TILE + title.NINTENDO_TILE_COUNT)
                * 16
            ],
        )
        self.assertEqual(self.assets.background_chr, self.assets.chr_data)
        self.assertEqual(self.assets.approximation_error, 0)

        final_tiles = self.assets.final_nametable
        slide_tiles = self.assets.second_nametable
        self.assertEqual(slide_tiles[: 12 * 32], final_tiles[: 12 * 32])
        self.assertEqual(
            set(final_tiles[: title.SPLIT_TILE_ROW * 32]),
            set(range(title.TOP_TILE_COUNT)),
        )
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
            slide_tiles, self.assets.background_chr
        ).crop((0, 0, 256, 96))
        self.assertEqual(slide_logo.tobytes(), final_logo.tobytes())
        self.assertEqual(
            slide_logo.tobytes(), self.native.crop((0, 0, 256, 96)).tobytes()
        )

        self.assertEqual(_sha256(final_tiles), FINAL_NAMETABLE_SHA256)
        self.assertEqual(_sha256(slide_tiles), SECOND_NAMETABLE_SHA256)
        self.assertEqual(
            _sha256(self.assets.background_chr), BACKGROUND_CHR_SHA256
        )
        self.assertEqual(_sha256(self.assets.bottom_chr), BOTTOM_CHR_SHA256)
        self.assertEqual(
            _sha256(self.assets.nintendo_chr), NINTENDO_CHR_SHA256
        )
        self.assertEqual(_sha256(self.assets.restore_chr), RESTORE_CHR_SHA256)

    def test_nintendo_overlay_and_pre_slide_restore_have_no_stale_logo_pixels(
        self,
    ) -> None:
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

        nintendo_phase_chr = bytearray(self.assets.background_chr)
        nintendo_phase_chr[first:end] = self.assets.nintendo_chr
        nintendo_phase = title._render_indexed_nametable(
            self.assets.second_nametable, bytes(nintendo_phase_chr)
        )
        self.assertEqual(
            nintendo_phase.crop((0, 96, 256, 240)).tobytes(),
            original.crop((0, 96, 256, 240)).tobytes(),
        )

        nintendo_phase_chr[first:end] = self.assets.restore_chr
        self.assertEqual(bytes(nintendo_phase_chr), self.assets.background_chr)
        restored = title._render_indexed_nametable(
            self.assets.second_nametable, bytes(nintendo_phase_chr)
        )
        self.assertEqual(
            restored.crop((0, 0, 256, 96)).tobytes(),
            self.native.crop((0, 0, 256, 96)).tobytes(),
        )

    def test_native_slide_origins_wrap_and_representative_frames_are_locked(
        self,
    ) -> None:
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
        expected_visible_counts = (
            0,
            95,
            232,
            1401,
            999,
            2764,
            2092,
            4058,
            3477,
            5025,
            4476,
            6020,
            5509,
            7536,
            6780,
            8474,
            8196,
            9172,
            9324,
            9348,
            9348,
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
                nametable, self.assets.background_chr
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
                self.assertEqual(
                    sum(bool(pixel) for pixel in raw.get_flattened_data()),
                    expected_visible_counts[index],
                )

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
                self.assertEqual(
                    sum(
                        pixel == title.TITLE_PALETTE[1]
                        for pixel in monochrome.get_flattened_data()
                    ),
                    expected_visible_counts[index],
                )
                self.assertFalse(
                    any(
                        pixel != title.TITLE_PALETTE[0]
                        for pixel in monochrome.crop(
                            (0, 96, 256, 240)
                        ).get_flattened_data()
                    )
                )
                if index in SLIDE_RAW_SHA256:
                    self.assertEqual(
                        _sha256(raw.tobytes()), SLIDE_RAW_SHA256[index]
                    )
                    self.assertEqual(
                        _sha256(monochrome.tobytes()),
                        SLIDE_MONOCHROME_SHA256[index],
                    )

        completed = title.render_slide_logo_frame(self.assets, 0x100)
        completed_source = self.native.crop((0, 0, 256, 96))
        self.assertEqual(completed.tobytes(), completed_source.tobytes())
        self.assertEqual(
            sum(bool(pixel) for pixel in completed.get_flattened_data()),
            9348,
        )
        self.assertEqual(_sha256(completed.tobytes()), SLIDE_RAW_SHA256[20])
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

        cpu_capture = WORK_DIR / "mesen_capture/zenpen_title_cpu.dmp"
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
        self.assertEqual(len(self.assets.encoded_final), 456)
        self.assertEqual(len(self.assets.encoded_second), 400)
        self.assertEqual(
            _sha256(self.assets.encoded_final), ENCODED_FINAL_SHA256
        )
        self.assertEqual(
            _sha256(self.assets.encoded_second), ENCODED_SECOND_SHA256
        )
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
        layout = self._layout()

        def address(offset: int) -> int:
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
            self.patched[layout["nintendo"] : layout["restore"]],
            self.assets.nintendo_chr,
        )
        self.assertEqual(
            self.patched[layout["restore"] : layout["loader"]],
            self.assets.restore_chr,
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
        expected_slide_prep = (
            bytes.fromhex(
                "20 74 AB A9 00 8D 01 20 A5 FF 48 29 7F 8D 00 20 "
                "A0 1B A9 00 A2 26 20 AF EB"
            )
            + base_restore_address.to_bytes(2, "little")
            + bytes.fromhex("68 85 FF 09 10 85 FF 8D 00 20 A5 1C 8D 01 20 60")
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
                "A0 1B A9 00 A2 26 20 AF EB"
            )
            + address(layout["restore"]).to_bytes(2, "little")
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
        expected_exit = bytes.fromhex(
            "A9 00 8D 22 40 85 48 85 4F 85 9C "
            "A5 FF 09 10 85 FF 8D 00 20 "
            "A9 02 A2 03 4C 19 61"
        )
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

        self.assertEqual(len(self.patched), 12209)
        self.assertEqual(address(len(self.patched)), 0xD1B1)
        self.assertEqual(
            title.NOV3_LOAD_ADDRESS - address(len(self.patched)), 0x604
        )
        self.assertLess(address(len(self.patched)), title.NOV3_LOAD_ADDRESS)
        self.assertEqual(_sha256(self.patched), PATCHED_NOV4_SHA256)
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
            bytes.fromhex("68 00 2F 04 70 00 37"),
        )

        # Both metasprite origins move exactly -16 X and -8 Y. Their animation
        # records remain native while the shared elbow lands on the reviewed
        # clock center (approximately 125,67).
        old = title.CLOCK_HAND_ORIGINS_SOURCE
        new = title.CLOCK_HAND_ORIGINS_PATCH
        self.assertEqual((new[0] - old[0], new[2] - old[2]), (-16, -8))
        self.assertEqual((new[4] - old[4], new[6] - old[6]), (-16, -8))
        self.assertEqual(new[1], old[1])
        self.assertEqual(new[3], old[3])
        self.assertEqual(new[5], old[5])

    def test_source_and_native_asset_guards_fail_closed(self) -> None:
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
            bad_ownership.putpixel((0, 96), 1)
            bad_ownership_path = temporary_path / "bad-ownership.png"
            bad_ownership.save(bad_ownership_path)
            with self.assertRaisesRegex(title.TitlePatchError, "rows 0-95"):
                title._target_to_indices(bad_ownership_path)


if __name__ == "__main__":
    unittest.main()
