"""Private integration tests for the original Time Twist FDS containers."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.fds import SIDE_SIZE, FdsImage, combine_images

WORK_DIR = Path(__file__).resolve().parents[1]
BASELINE_DIR = WORK_DIR / "baseline"
ZENPEN = BASELINE_DIR / "time_twist_zenpen_japan.fds"
KOUHEN = BASELINE_DIR / "time_twist_kouhen_japan.fds"


class FdsRoundTripTests(unittest.TestCase):
    """Protect source container layout independently of generated releases."""

    def test_baselines_round_trip_byte_identically(self) -> None:
        """Parse and serialize both approved baselines without changing bytes."""
        for path in (ZENPEN, KOUHEN):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                image = FdsImage.from_bytes(original, path)
                self.assertEqual(image.to_bytes(), original)

    def test_expected_time_twist_layout(self) -> None:
        """Lock the recovered side and file-count structure of both halves."""
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
        """Build the canonical four-side source layout without reordering."""
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
        self.assertEqual([side.index for side in combined.sides], [0, 1, 2, 3])

    def test_file_growth_updates_header_and_consumes_padding(self) -> None:
        """Grow one file and prove FDS size metadata/padding are rebuilt safely."""
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


if __name__ == "__main__":
    unittest.main()
