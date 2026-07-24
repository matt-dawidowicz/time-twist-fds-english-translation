from __future__ import annotations

import sys
import unittest
from pathlib import Path


WORK_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK_DIR))

from time_twist.fds import FdsImage, SIDE_SIZE, combine_images  # noqa: E402


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
        self.assertEqual([side.game_code for side in zenpen.sides], ["TT1", "TT1"])
        self.assertEqual([side.game_code for side in kouhen.sides], ["TT2", "TT2"])
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
        self.assertEqual(combined.to_bytes(), zenpen.to_bytes() + kouhen.to_bytes())
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
        entry.data += b"\xA5"

        rebuilt = image.to_bytes()
        reparsed = FdsImage.from_bytes(rebuilt)
        changed = reparsed.sides[1].find_file("TT1B")
        self.assertEqual(changed.size, old_size + 1)
        self.assertEqual(changed.data[-1], 0xA5)
        self.assertEqual(len(reparsed.sides[1].padding), old_padding - 1)

    def test_zenpen_output_changes_only_the_eight_english_files(self) -> None:
        output = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - complete English playtest.fds"
        )
        translated_banks = {
            name: WORK_DIR / "translated_banks" / f"{name}_fixed_footprint.bin"
            for name in ("TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B")
        }
        title_bank = WORK_DIR / "build" / "NOV4_english_title_v17.bin"
        nov2_bank = WORK_DIR / "build" / "NOV2_english_ui_v9.bin"
        if not output.exists() or not all(
            path.exists() for path in translated_banks.values()
        ) or not title_bank.exists() or not nov2_bank.exists():
            self.skipTest("combined Zenpen fixture is not available")

        expected_changed = {
            (0, "TT3A"), (0, "TT3B"), (0, "NOV2"), (0, "NOV4"),
            (1, "TT1B"), (1, "TT1A"), (1, "TT2"), (1, "T22"),
        }
        actual_changed: set[tuple[int, str]] = set()
        original = FdsImage.read(ZENPEN)
        translated = FdsImage.read(output)
        self.assertEqual(len(translated.sides), len(original.sides))
        for side_index, (source_side, translated_side) in enumerate(
            zip(original.sides, translated.sides)
        ):
            self.assertEqual(translated_side.disk_info, source_side.disk_info)
            self.assertEqual(
                translated_side.file_count_block, source_side.file_count_block
            )
            self.assertEqual(len(translated_side.files), len(source_side.files))
            for source_file, translated_file in zip(
                source_side.files, translated_side.files
            ):
                if side_index == 0 and source_file.name == "NOV4":
                    self.assertEqual(
                        translated_file.header[:13], source_file.header[:13]
                    )
                    self.assertEqual(
                        translated_file.header[15:], source_file.header[15:]
                    )
                    self.assertEqual(translated_file.data, title_bank.read_bytes())
                else:
                    self.assertEqual(translated_file.header, source_file.header)
                if translated_file.data != source_file.data:
                    actual_changed.add((side_index, source_file.name))
                if side_index == 0 and source_file.name == "NOV2":
                    self.assertEqual(translated_file.data, nov2_bank.read_bytes())
                if source_file.name in translated_banks:
                    self.assertEqual(
                        translated_file.data,
                        translated_banks[source_file.name].read_bytes(),
                    )
            expected_padding = (
                len(source_side.padding) -
                (len(title_bank.read_bytes()) - source_side.find_file("NOV4").size)
                if side_index == 0 else len(source_side.padding)
            )
            self.assertEqual(len(translated_side.padding), expected_padding)
            self.assertEqual(
                translated_side.padding,
                source_side.padding[:expected_padding],
            )
        self.assertEqual(actual_changed, expected_changed)

    def test_exact_reference_title_output_changes_only_nov4_and_consumes_padding(self) -> None:
        translated_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - complete English menus test.fds"
        )
        titled_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - clock and time machine fix test.fds"
        )
        title_bank = WORK_DIR / "build" / "NOV4_english_title_v12.bin"
        if not all(path.exists() for path in (
            translated_path, titled_path, title_bank
        )):
            self.skipTest("English title-card fixtures are not available")

        translated = FdsImage.read(translated_path)
        titled = FdsImage.read(titled_path)
        expected_title = title_bank.read_bytes()
        self.assertEqual(titled.to_bytes(), titled_path.read_bytes())
        old_nov4 = translated.sides[0].find_file("NOV4")
        new_nov4 = titled.sides[0].find_file("NOV4")
        growth = len(expected_title) - old_nov4.size

        self.assertEqual(new_nov4.data, expected_title)
        self.assertEqual(growth, 2341)
        self.assertEqual(len(titled.sides), len(translated.sides))
        for side_index, (old_side, new_side) in enumerate(
            zip(translated.sides, titled.sides)
        ):
            self.assertEqual(new_side.disk_info, old_side.disk_info)
            self.assertEqual(new_side.file_count_block, old_side.file_count_block)
            self.assertEqual(len(new_side.files), len(old_side.files))
            for old_file, new_file in zip(old_side.files, new_side.files):
                self.assertEqual(new_file.name, old_file.name)
                if side_index == 0 and old_file.name == "NOV4":
                    self.assertEqual(new_file.header[:13], old_file.header[:13])
                    self.assertEqual(new_file.header[15:], old_file.header[15:])
                    self.assertEqual(new_file.size, old_file.size + growth)
                else:
                    self.assertEqual(new_file.header, old_file.header)
                    self.assertEqual(new_file.data, old_file.data)

            expected_padding = (
                len(old_side.padding) - growth
                if side_index == 0 else len(old_side.padding)
            )
            self.assertEqual(len(new_side.padding), expected_padding)
            self.assertEqual(
                new_side.padding,
                old_side.padding[:expected_padding],
            )

    def test_dialogue_line_restore_changes_only_nov2(self) -> None:
        previous_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - clock and time machine fix test.fds"
        )
        restored_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - dialogue line restore test.fds"
        )
        nov2_path = WORK_DIR / "build" / "NOV2_english_ui_v8.bin"
        if not all(path.exists() for path in (
            previous_path, restored_path, nov2_path
        )):
            self.skipTest("dialogue-line restoration fixtures are not available")

        previous = FdsImage.read(previous_path)
        restored = FdsImage.read(restored_path)
        expected_nov2 = nov2_path.read_bytes()
        actual_changes: set[tuple[int, str]] = set()

        self.assertEqual(len(restored.sides), len(previous.sides))
        for side_index, (old_side, new_side) in enumerate(
            zip(previous.sides, restored.sides)
        ):
            self.assertEqual(new_side.disk_info, old_side.disk_info)
            self.assertEqual(new_side.file_count_block, old_side.file_count_block)
            self.assertEqual(len(new_side.files), len(old_side.files))
            self.assertEqual(new_side.padding, old_side.padding)
            for old_file, new_file in zip(old_side.files, new_side.files):
                self.assertEqual(new_file.header, old_file.header)
                if new_file.data != old_file.data:
                    actual_changes.add((side_index, old_file.name))

        self.assertEqual(actual_changes, {(0, "NOV2")})
        self.assertEqual(restored.sides[0].find_file("NOV2").data, expected_nov2)
        self.assertEqual(
            restored.sides[0].find_file("NOV4").data,
            previous.sides[0].find_file("NOV4").data,
        )

    def test_museum_and_accent_fix_changes_only_nov4_and_tt1b(self) -> None:
        previous_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - dialogue line restore test.fds"
        )
        fixed_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - museum directions and accent fix test.fds"
        )
        expected_files = {
            (0, "NOV4"): WORK_DIR / "build" / "NOV4_english_title_v13.bin",
            (1, "TT1B"): (
                WORK_DIR / "translated_banks" / "TT1B_fixed_footprint_v2.bin"
            ),
        }
        if not all(path.exists() for path in (
            previous_path, fixed_path, *expected_files.values()
        )):
            self.skipTest("museum/accent fixtures are not available")

        previous = FdsImage.read(previous_path)
        fixed = FdsImage.read(fixed_path)
        actual_changes: set[tuple[int, str]] = set()

        self.assertEqual(fixed.to_bytes(), fixed_path.read_bytes())
        for side_index, (old_side, new_side) in enumerate(
            zip(previous.sides, fixed.sides)
        ):
            self.assertEqual(new_side.disk_info, old_side.disk_info)
            self.assertEqual(new_side.file_count_block, old_side.file_count_block)
            self.assertEqual(new_side.padding, old_side.padding)
            for old_file, new_file in zip(old_side.files, new_side.files):
                self.assertEqual(new_file.header, old_file.header)
                key = (side_index, old_file.name)
                if new_file.data != old_file.data:
                    actual_changes.add(key)
                if key in expected_files:
                    self.assertEqual(new_file.data, expected_files[key].read_bytes())

        self.assertEqual(actual_changes, set(expected_files))

    def test_forest_and_church_wording_fix_changes_only_tt1b(self) -> None:
        previous_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - museum directions and accent fix test.fds"
        )
        fixed_path = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Zenpen - forest and church wording fix test.fds"
        )
        tt1b_path = WORK_DIR / "translated_banks" / "TT1B_fixed_footprint.bin"
        if not all(path.exists() for path in (
            previous_path, fixed_path, tt1b_path
        )):
            self.skipTest("forest/church wording fixtures are not available")

        previous = FdsImage.read(previous_path)
        fixed = FdsImage.read(fixed_path)
        actual_changes: set[tuple[int, str]] = set()

        self.assertEqual(fixed.to_bytes(), fixed_path.read_bytes())
        for side_index, (old_side, new_side) in enumerate(
            zip(previous.sides, fixed.sides)
        ):
            self.assertEqual(new_side.disk_info, old_side.disk_info)
            self.assertEqual(new_side.file_count_block, old_side.file_count_block)
            self.assertEqual(new_side.padding, old_side.padding)
            for old_file, new_file in zip(old_side.files, new_side.files):
                self.assertEqual(new_file.header, old_file.header)
                if new_file.data != old_file.data:
                    actual_changes.add((side_index, old_file.name))

        self.assertEqual(actual_changes, {(1, "TT1B")})
        self.assertEqual(
            fixed.sides[1].find_file("TT1B").data,
            tt1b_path.read_bytes(),
        )

    def test_kouhen_output_changes_only_the_eight_english_files(self) -> None:
        output = (
            WORK_DIR.parent / "outputs" /
            "Time Twist Kouhen - complete English playtest.fds"
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
            self.skipTest("combined Kouhen fixture is not available")

        original = FdsImage.read(KOUHEN)
        translated = FdsImage.read(output)
        self.assertEqual(len(translated.sides), len(original.sides))
        for side_index, (source_side, translated_side) in enumerate(
            zip(original.sides, translated.sides)
        ):
            self.assertEqual(translated_side.disk_info, source_side.disk_info)
            self.assertEqual(
                translated_side.file_count_block, source_side.file_count_block
            )
            self.assertEqual(len(translated_side.files), len(source_side.files))
            for source_file, translated_file in zip(
                source_side.files, translated_side.files
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
