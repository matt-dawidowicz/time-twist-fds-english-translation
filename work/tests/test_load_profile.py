"""Tests for the source-verified FDS load profiler."""

from __future__ import annotations

import unittest

from time_twist.fds import FdsFile, FdsImage, FdsSide
from time_twist.load_profile import (
    DYNAMIC_LOAD_TABLE,
    DYNAMIC_LOAD_TABLE_ENTRY_SIZE,
    PRIMARY_LOAD_CALL,
    SECONDARY_LOAD_CALL,
    dynamic_load_entries,
    scan_load_files_calls,
)


def _file(
    name: str,
    *,
    file_id: int,
    number: int,
    load_address: int,
    data: bytes,
    data_offset: int,
) -> FdsFile:
    header = bytearray(16)
    header[0] = 0x03
    header[1] = number
    header[2] = file_id
    header[3:11] = name.encode("ascii").ljust(8, b"\0")
    header[11:13] = load_address.to_bytes(2, "little")
    header[13:15] = len(data).to_bytes(2, "little")
    return FdsFile(
        index=number,
        header=header,
        data=data,
        header_offset=max(0, data_offset - 17),
        data_offset=data_offset,
    )


def _side(game: bytes, files: list[FdsFile], parsed_length: int) -> FdsSide:
    disk_info = bytearray(56)
    disk_info[0] = 0x01
    disk_info[16:20] = game
    return FdsSide(
        index=0,
        disk_info=bytes(disk_info),
        file_count_block=bytearray((0x02, len(files))),
        files=files,
        parsed_length=parsed_length,
    )


class LoadProfileTests(unittest.TestCase):
    """Exercise direct-call decoding and the Time Twist NOV2 source guard."""

    def test_scan_decodes_inline_file_list(self) -> None:
        data = bytearray(0x80)
        data[8:15] = bytes.fromhex("20 F8 E1 40 60 50 60")
        data[0x50:0x53] = bytes((0x41, 0x51, 0xFF))
        entry = _file(
            "NOV2",
            file_id=1,
            number=0,
            load_address=0x6000,
            data=bytes(data),
            data_offset=75,
        )
        image = FdsImage(header=b"", sides=[_side(b"TT1 ", [entry], 256)])

        calls = scan_load_files_calls(image)

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].cpu_address, 0x6008)
        self.assertEqual(calls[0].disk_id_pointer, 0x6040)
        self.assertEqual(calls[0].file_list_pointer, 0x6050)
        self.assertEqual(calls[0].static_file_ids, (0x41, 0x51))

    def test_dynamic_table_maps_tt3_prefix(self) -> None:
        data = bytearray(0x1C00)
        primary = PRIMARY_LOAD_CALL - 0x6000
        secondary = SECONDARY_LOAD_CALL - 0x6000
        data[primary : primary + 7] = bytes.fromhex("20 F8 E1 CB 60 DF 60")
        data[secondary : secondary + 7] = bytes.fromhex("20 F8 E1 CB 60 E4 60")
        copy = 0x7A3D - 0x6000
        data[copy : copy + 24] = bytes.fromhex(
            "BD A5 7B 8D DF 60 BD A6 7B 8D E0 60 "
            "BD A7 7B 8D E1 60 BD A8 7B 8D E2 60"
        )
        table = DYNAMIC_LOAD_TABLE - 0x6000
        data[table : table + 15 * DYNAMIC_LOAD_TABLE_ENTRY_SIZE] = bytes(
            [0xFF] * (15 * DYNAMIC_LOAD_TABLE_ENTRY_SIZE)
        )
        row5 = table + 5 * DYNAMIC_LOAD_TABLE_ENTRY_SIZE
        data[row5 : row5 + 4] = bytes((0x45, 0x55, 0xFF, 0xFF))

        nov2 = _file(
            "NOV2",
            file_id=1,
            number=0,
            load_address=0x6000,
            data=bytes(data),
            data_offset=75,
        )
        tt3a = _file(
            "TT3A",
            file_id=0x45,
            number=1,
            load_address=0xA200,
            data=b"A" * 16,
            data_offset=500,
        )
        ob3 = _file(
            "OB3",
            file_id=0x55,
            number=2,
            load_address=0,
            data=b"B" * 16,
            data_offset=700,
        )
        bg3 = _file(
            "BG3",
            file_id=0x55,
            number=3,
            load_address=0x1100,
            data=b"C" * 16,
            data_offset=900,
        )
        zenpen = FdsImage(
            header=b"",
            sides=[_side(b"TT1 ", [nov2, tt3a, ob3, bg3], 1200)],
        )
        kouhen = FdsImage(header=b"", sides=[_side(b"TT2 ", [], 100)])

        row = dynamic_load_entries(zenpen, kouhen)[5]

        self.assertEqual(row.raw_ids, (0x45, 0x55, 0xFF, 0xFF))
        self.assertEqual(len(row.targets), 1)
        self.assertEqual(row.targets[0].files, ("TT3A", "OB3", "BG3"))
        self.assertEqual(row.targets[0].prefix_bytes, 916)
        self.assertEqual(row.targets[0].avoidable_archival_bytes, 284)


if __name__ == "__main__":
    unittest.main()
