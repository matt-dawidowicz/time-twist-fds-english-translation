from __future__ import annotations

import sys
import unittest
from pathlib import Path

WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from time_twist.fds import SIDE_SIZE, FdsImage, combine_images  # noqa: E402

BASELINE_DIR = WORK_DIR / "baseline"
ZENPEN = BASELINE_DIR / "time_twist_zenpen_japan.fds"
KOUHEN = BASELINE_DIR / "time_twist_kouhen_japan.fds"


class FdsRoundTripTests(unittest.TestCase):
    def test_baselines_round_trip_byte_identically(self) -> None:
        for path in (ZENPEN, KOUHEN):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                image = FdsImage.from_bytes(original, path)
                self.assertEqual(image.to_bytes(), original)

    def test_expected_time_twist_layout(self) -> None:
        zenpen = FdsImage.read(ZENPEN)
        kouhen = FdsImage.read(KOUHEN)
        self.assertEqual(
            [side.game_code for side in zenpen.sides], ["TT1", "TT1"]
        )
        self.assertEqual(
            [side.game_code for side in kouhen.sides], ["TT2", "TT2"]
        )
        self.assertEqual([len(side.files) for side in zenpen.sides], [10, 10])
        self.assertEqual([len(side.files) for side in kouhen.sides], [14, 9])
        self.assertEqual(len(zenpen.to_bytes()), 2 * SIDE_SIZE)
        self.assertEqual(len(kouhen.to_bytes()), 2 * SIDE_SIZE)

    def test_combine_preserves_all_four_sides_in_order(self) -> None:
        zenpen = FdsImage.read(ZENPEN)
        kouhen = FdsImage.read(KOUHEN)
        combined = combine_images([zenpen, kouhen])

        self.assertEqual(len(combined.sides), 4)
        self.assertEqual(
            [side.game_code for side in combined.sides],
            ["TT1", "TT1", "TT2", "TT2"],
        )
        self.assertEqual(
            combined.to_bytes(), zenpen.to_bytes() + kouhen.to_bytes()
        )
        self.assertEqual(
            [side.index for side in combined.sides],
            [0, 1, 2, 3],
        )

    def test_file_growth_updates_header_and_consumes_padding(self) -> None:
        image = FdsImage.read(ZENPEN)
        side = image.sides[1]
        entry = side.find_file("TT1B")
        old_size = entry.size
        old_padding = len(side.padding)
        entry.data += b"\xa5"

        rebuilt = image.to_bytes()
        reparsed = FdsImage.from_bytes(rebuilt)
        changed = reparsed.sides[1].find_file("TT1B")
        self.assertEqual(changed.size, old_size + 1)
        self.assertEqual(changed.data[-1], 0xA5)
        self.assertEqual(len(reparsed.sides[1].padding), old_padding - 1)

    def test_zenpen_output_changes_only_the_eight_english_files(self) -> None:
        output = (
            WORK_DIR.parent
            / "outputs"
            / "Time Twist Zenpen - complete English playtest.fds"
        )
        translated_banks = {
            name: WORK_DIR / "translated_banks" / f"{name}_fixed_footprint.bin"
            for name in ("TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B")
        }
        title_bank = WORK_DIR / "build" / "NOV4_english_title_v17.bin"
        nov2_bank = WORK_DIR / "build" / "NOV2_english_ui_v9.bin"
        if (
            not output.exists()
            or not all(path.exists() for path in translated_banks.values())
            or not title_bank.exists()
            or not nov2_bank.exists()
        ):
            self.fail("combined Zenpen fixture is not available")

        expected_changed = {
            (0, "TT3A"),
            (0, "TT3B"),
            (0, "NOV2"),
            (0, "NOV4"),
            (1, "TT1B"),
            (1, "TT1A"),
            (1, "TT2"),
            (1, "T22"),
        }
        actual_changed: set[tuple[int, str]] = set()
        original = FdsImage.read(ZENPEN)
        translated = FdsImage.read(output)
        self.assertEqual(len(translated.sides), len(original.sides))
        for side_index, (source_side, translated_side) in enumerate(
            zip(original.sides, translated.sides, strict=True)
        ):
            self.assertEqual(translated_side.disk_info, source_side.disk_info)
            self.assertEqual(
                translated_side.file_count_block, source_side.file_count_block
            )
            self.assertEqual(
                len(translated_side.files), len(source_side.files)
            )
            for source_file, translated_file in zip(
                source_side.files, translated_side.files, strict=True
            ):
                if side_index == 0 and source_file.name == "NOV4":
                    self.assertEqual(
                        translated_file.header[:13], source_file.header[:13]
                    )
                    self.assertEqual(
                        translated_file.header[15:], source_file.header[15:]
                    )
                    self.assertEqual(
                        translated_file.data, title_bank.read_bytes()
                    )
                else:
                    self.assertEqual(
                        translated_file.header, source_file.header
                    )
                if translated_file.data != source_file.data:
                    actual_changed.add((side_index, source_file.name))
                if side_index == 0 and source_file.name == "NOV2":
                    self.assertEqual(
                        translated_file.data, nov2_bank.read_bytes()
                    )
                if source_file.name in translated_banks:
                    self.assertEqual(
                        translated_file.data,
                        translated_banks[source_file.name].read_bytes(),
                    )
            expected_padding = (
                len(source_side.padding)
                - (
                    len(title_bank.read_bytes())
                    - source_side.find_file("NOV4").size
                )
                if side_index == 0
                else len(source_side.padding)
            )
            self.assertEqual(len(translated_side.padding), expected_padding)
            self.assertEqual(
                translated_side.padding,
                source_side.padding[:expected_padding],
            )
        self.assertEqual(actual_changed, expected_changed)

    def test_kouhen_output_changes_only_the_eight_english_files(self) -> None:
        output = (
            WORK_DIR.parent
            / "outputs"
            / "Time Twist Kouhen - complete English playtest.fds"
        )
        translated_banks = {
            name: WORK_DIR / "translated_banks" / f"{name}_fixed_footprint.bin"
            for name in ("TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D")
        }
        translated_files = {
            **translated_banks,
            "SON-KOUH": WORK_DIR / "build" / "SON-KOUH_english.bin",
        }
        if not output.exists() or not all(
            path.exists() for path in translated_files.values()
        ):
            self.fail("combined Kouhen fixture is not available")

        original = FdsImage.read(KOUHEN)
        translated = FdsImage.read(output)
        self.assertEqual(len(translated.sides), len(original.sides))
        for _side_index, (source_side, translated_side) in enumerate(
            zip(original.sides, translated.sides, strict=True)
        ):
            self.assertEqual(translated_side.disk_info, source_side.disk_info)
            self.assertEqual(
                translated_side.file_count_block, source_side.file_count_block
            )
            self.assertEqual(
                len(translated_side.files), len(source_side.files)
            )
            for source_file, translated_file in zip(
                source_side.files, translated_side.files, strict=True
            ):
                self.assertEqual(translated_file.header, source_file.header)
                if source_file.name in translated_files:
                    self.assertEqual(
                        translated_file.data,
                        translated_files[source_file.name].read_bytes(),
                    )
                else:
                    self.assertEqual(translated_file.data, source_file.data)
            self.assertEqual(translated_side.padding, source_side.padding)


if __name__ == "__main__":
    unittest.main()
