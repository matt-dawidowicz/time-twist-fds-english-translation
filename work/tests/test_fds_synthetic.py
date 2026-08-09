from __future__ import annotations

import unittest

from time_twist.fds import (
    FDS_HEADER_SIZE,
    SIDE_SIZE,
    FdsFormatError,
    FdsImage,
    combine_images,
)


def make_side(*, code: bytes = b"TEST", payload: bytes = b"abc") -> bytes:
    disk_info = bytearray(56)
    disk_info[0] = 0x01
    disk_info[16:20] = code
    disk_info[20] = 1
    disk_info[21] = 0
    disk_info[22] = 0
    file_header = bytearray(16)
    file_header[0] = 0x03
    file_header[1] = 0
    file_header[2] = 7
    file_header[3:11] = b"DATA    "
    file_header[11:13] = (0x6000).to_bytes(2, "little")
    file_header[13:15] = len(payload).to_bytes(2, "little")
    file_header[15] = 0
    raw = (
        bytes(disk_info) + b"\x02\x01" + bytes(file_header) + b"\x04" + payload
    )
    return raw + b"\x00" * (SIDE_SIZE - len(raw))


class SyntheticFdsTests(unittest.TestCase):
    def test_raw_round_trip_and_manifest(self) -> None:
        raw = make_side()
        image = FdsImage.from_bytes(raw)
        self.assertEqual(image.to_bytes(), raw)
        self.assertEqual(image.sides[0].game_code, "TEST")
        self.assertEqual(image.sides[0].find_file("DATA").data, b"abc")

    def test_headered_round_trip(self) -> None:
        header = bytearray(FDS_HEADER_SIZE)
        header[:4] = b"FDS\x1a"
        header[4] = 1
        raw = bytes(header) + make_side()
        image = FdsImage.from_bytes(raw)
        self.assertEqual(image.to_bytes(), raw)

    def test_growth_refreshes_size_and_consumes_padding(self) -> None:
        image = FdsImage.from_bytes(make_side(payload=b"x"))
        entry = image.sides[0].find_file("DATA")
        old_padding = len(image.sides[0].padding)
        entry.data = b"expanded"
        rebuilt = FdsImage.from_bytes(image.to_bytes())
        self.assertEqual(rebuilt.sides[0].find_file("DATA").data, b"expanded")
        self.assertEqual(len(rebuilt.sides[0].padding), old_padding - 7)

    def test_combine_keeps_side_order(self) -> None:
        first = FdsImage.from_bytes(make_side(code=b"ONE "))
        second = FdsImage.from_bytes(make_side(code=b"TWO "))
        combined = combine_images([first, second])
        self.assertEqual(
            [side.game_code for side in combined.sides], ["ONE", "TWO"]
        )
        self.assertEqual(
            combined.to_bytes(), first.to_bytes() + second.to_bytes()
        )

    def test_rejects_bad_block_marker_and_capacity_overflow(self) -> None:
        malformed = bytearray(make_side())
        malformed[0] = 0
        with self.assertRaises(FdsFormatError):
            FdsImage.from_bytes(bytes(malformed))

        image = FdsImage.from_bytes(make_side())
        image.sides[0].find_file("DATA").data = b"x" * SIDE_SIZE
        with self.assertRaises(FdsFormatError):
            image.to_bytes()


if __name__ == "__main__":
    unittest.main()
