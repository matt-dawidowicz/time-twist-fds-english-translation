"""Fixture-free locks for the approved English opening GIF conversion."""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from PIL import Image
from rebuild_native_title_asset import (
    CLOCK_NUMERAL_BOXES,
    CLOCK_RIM_BRIDGE_PATCH,
    CLOCK_TRACE_CENTER_X,
    CLOCK_TRACE_COLORS,
    CLOCK_TRACE_ROWS,
    CLOCK_TRACE_Y_SUM,
    FINAL_OUTLINE_PATCH,
    FIRST_T_LOWER_BEVEL_X,
    FIRST_T_LOWER_BEVEL_Y,
    FIRST_T_TIP_BOX,
    S_ENTRY_PATCH,
    TM_CLEAR_BOX,
    TM_GLYPHS,
    TM_TOP,
    build_native_titles,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "work" / "title_assets"
OPENING = ASSET_ROOT / "Time Twist approved English opening.gif"
FINAL = ASSET_ROOT / "Time Twist approved native title.png"
SLIDE = ASSET_ROOT / "Time Twist approved native slide.png"


def _sha256(data: bytes) -> str:
    """Return an uppercase SHA-256 digest for regression assertions."""
    return hashlib.sha256(data).hexdigest().upper()


class TitleOpeningAssetTests(unittest.TestCase):
    """Lock the display-to-native conversion and both phase authorities."""

    def test_opening_regenerates_both_native_assets_exactly(self) -> None:
        """Prove the checked-in PNGs regenerate with reviewed polish."""
        final, slide = build_native_titles(OPENING)
        with Image.open(FINAL) as expected_final:
            self.assertEqual(final.mode, "P")
            self.assertEqual(final.size, (256, 240))
            self.assertEqual(final.tobytes(), expected_final.tobytes())
            self.assertEqual(
                expected_final.getpalette()[:12],
                [0, 0, 0, 255, 254, 255, 243, 106, 255, 92, 0, 126],
            )
        with Image.open(SLIDE) as expected_slide:
            self.assertEqual(slide.mode, "P")
            self.assertEqual(slide.size, (256, 240))
            self.assertEqual(slide.tobytes(), expected_slide.tobytes())
            self.assertEqual(
                expected_slide.getpalette()[:6],
                [0, 0, 0, 255, 254, 255],
            )

    def test_native_phase_geometry_is_pixel_locked_and_distinct(self) -> None:
        """Reject resampling drift or replacement with one shared wordmark."""
        with (
            Image.open(FINAL) as final_source,
            Image.open(SLIDE) as slide_source,
        ):
            final = final_source.copy()
            slide = slide_source.copy()
        self.assertEqual(final.getbbox(), (22, 22, 238, 97))
        self.assertEqual(slide.getbbox(), (24, 25, 236, 87))
        self.assertEqual(set(final.get_flattened_data()), {0, 1, 2, 3})
        self.assertEqual(set(slide.get_flattened_data()), {0, 1})
        self.assertEqual(
            _sha256(final.tobytes()),
            "27EE6BA45E19778B80EBBEACEEDC763EF896CE6A0A942D0C080114AB2C02B208",
        )
        self.assertEqual(
            _sha256(slide.tobytes()),
            "34FF7674E69C187BBF504C126F5F1F4ACBEF93823633C2EB00D5E4558FFC95BB",
        )
        self.assertNotEqual(final.tobytes(), slide.tobytes())

    def test_checked_in_asset_files_are_locked(self) -> None:
        """Keep source and encoded PNG files byte-identical across rebuilds."""
        self.assertEqual(
            _sha256(OPENING.read_bytes()),
            "56B1473C88D0F811F7C1DED2A45D51B248129D3D3C2937E8814D70C8D95C2273",
        )
        self.assertEqual(
            _sha256(FINAL.read_bytes()),
            "B1F262770FB490E2A933B956D5857432C101EE378A0F765CCCFACD8EE5FBF9A8",
        )
        self.assertEqual(
            _sha256(SLIDE.read_bytes()),
            "5B77F1E1080BC6A34AAB8B66420C2D53F025121285095ED142B481AD3C0C873C",
        )

    def test_one_pixel_clock_and_trademark_details_survive(self) -> None:
        """Keep the thin 12/9/3/6 and TM strokes from the display authority."""
        with Image.open(FINAL) as source:
            final = source.copy()

        def white_rows(
            box: tuple[int, int, int, int],
        ) -> tuple[str, ...]:
            """Encode one rectangular white-pixel mask as binary rows."""
            left, top, right, bottom = box
            return tuple(
                "".join(
                    "1" if final.getpixel((x, y)) == 1 else "0"
                    for x in range(left, right)
                )
                for y in range(top, bottom)
            )

        self.assertEqual(
            white_rows((124, 60, 131, 65)),
            ("1011110", "1010010", "1000100", "1011000", "1011110"),
        )
        self.assertEqual(
            white_rows((112, 74, 116, 80)),
            ("1111", "1001", "1001", "1111", "0001", "1111"),
        )
        self.assertEqual(
            white_rows((137, 74, 141, 80)),
            ("1111", "0001", "0110", "0001", "0001", "1111"),
        )
        self.assertEqual(
            white_rows((125, 89, 130, 94)),
            ("11110", "10000", "11110", "10010", "11110"),
        )
        self.assertEqual(
            white_rows((218, 23, 231, 31)),
            (
                "0111110010001",
                "0001000011011",
                "0001000010101",
                "0001000010101",
                "0001000010001",
                "0001000010001",
                "0001000010001",
                "0000000000000",
            ),
        )

    def test_letter_boundary_white_mask_is_pixel_locked(self) -> None:
        """Reject another one-pixel phase shift along the wordmark outline."""
        with Image.open(FINAL) as final:
            white_mask = bytearray()
            for y in range(22, 87):
                for x in range(22, 238):
                    in_clock = 108 <= x < 148 and 56 <= y < 87
                    in_trademark = 205 <= x < 238 and 22 <= y < 40
                    if not in_clock and not in_trademark:
                        white_mask.append(final.getpixel((x, y)) == 1)
        self.assertEqual(sum(white_mask), 1836)
        self.assertEqual(
            _sha256(bytes(white_mask)),
            "DCBAA57C8A6E9BA21F2CAD7010BE6FAE56EE75DB80F1FD2014C131CFFC86A9EB",
        )

    def test_reviewed_polish_repairs_all_reported_logo_details(self) -> None:
        """Lock the reviewed T, clock, W/I/S, and TM cleanup regions."""
        with Image.open(FINAL) as source:
            final = source.copy()

        self.assertTrue(
            all(
                final.getpixel((x, FIRST_T_LOWER_BEVEL_Y)) == 3
                for x in FIRST_T_LOWER_BEVEL_X
            )
        )
        left, top, right, bottom = FIRST_T_TIP_BOX
        self.assertEqual(
            tuple(
                "".join(
                    "0WPD"[final.getpixel((x, y))] for x in range(left, right)
                )
                for y in range(top, bottom)
            ),
            (
                "00000000WW",
                "000000WWWW",
                "0000WWWWWW",
                "00WWWWWDDW",
            ),
        )

        numeral_pixels = {
            (x, y)
            for left, top, right, bottom in CLOCK_NUMERAL_BOXES
            for y in range(top, bottom)
            for x in range(left, right)
            if final.getpixel((x, y)) == 1
        }
        for source_y, left, trace in CLOCK_TRACE_ROWS:
            self.assertEqual(len(trace), CLOCK_TRACE_CENTER_X - left + 1)
            for y in (source_y, CLOCK_TRACE_Y_SUM - source_y):
                for offset, symbol in enumerate(trace):
                    x = left + offset
                    for coordinate in (
                        (x, y),
                        (2 * CLOCK_TRACE_CENTER_X - x, y),
                    ):
                        expected = CLOCK_TRACE_COLORS[symbol]
                        if coordinate in CLOCK_RIM_BRIDGE_PATCH:
                            expected = CLOCK_RIM_BRIDGE_PATCH[coordinate]
                        if coordinate in numeral_pixels:
                            expected = 1
                        self.assertEqual(final.getpixel(coordinate), expected)

        for coordinate, expected in CLOCK_RIM_BRIDGE_PATCH.items():
            if coordinate not in numeral_pixels:
                self.assertEqual(final.getpixel(coordinate), expected)

        for value in (1, 2, 3):
            remaining = {
                (x, y)
                for y in range(55, 97)
                for x in range(109, 144)
                if final.getpixel((x, y)) == value
                and (
                    (x, y) in CLOCK_RIM_BRIDGE_PATCH
                    or any(
                        CLOCK_TRACE_COLORS[symbol] == value
                        and (x, y)
                        in {
                            (left + offset, trace_y),
                            (
                                2 * CLOCK_TRACE_CENTER_X - left - offset,
                                trace_y,
                            ),
                            (
                                left + offset,
                                CLOCK_TRACE_Y_SUM - trace_y,
                            ),
                            (
                                2 * CLOCK_TRACE_CENTER_X - left - offset,
                                CLOCK_TRACE_Y_SUM - trace_y,
                            ),
                        }
                        for trace_y, left, trace in CLOCK_TRACE_ROWS
                        for offset, symbol in enumerate(trace)
                    )
                )
            }
            pending = [remaining.pop()]
            while pending:
                x, y = pending.pop()
                for neighbor in (
                    (x - 1, y),
                    (x + 1, y),
                    (x, y - 1),
                    (x, y + 1),
                ):
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        pending.append(neighbor)
            self.assertFalse(
                remaining,
                f"clock rim color {value} is not a closed 4-neighbor contour",
            )

        for coordinate, expected in S_ENTRY_PATCH.items():
            if coordinate not in FINAL_OUTLINE_PATCH:
                self.assertEqual(final.getpixel(coordinate), expected)
        for coordinate, expected in FINAL_OUTLINE_PATCH.items():
            self.assertEqual(final.getpixel(coordinate), expected)

        left, top, right, bottom = TM_CLEAR_BOX
        expected_tm = set()
        for glyph, glyph_left in TM_GLYPHS:
            for row, source_row in enumerate(glyph):
                for column, value in enumerate(source_row):
                    if value == "1":
                        expected_tm.add((glyph_left + column, TM_TOP + row))
        actual_tm = {
            (x, y)
            for y in range(top, bottom)
            for x in range(left, right)
            if final.getpixel((x, y)) == 1
        }
        self.assertEqual(actual_tm, expected_tm)


if __name__ == "__main__":
    unittest.main()
