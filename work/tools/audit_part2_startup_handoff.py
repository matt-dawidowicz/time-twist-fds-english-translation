#!/usr/bin/env python3
"""Audit the retail Zenpen-to-Kouhen title/startup handoff.

The audit consumes maintainer-supplied original Japanese Zenpen and Kouhen FDS
images. It does not modify or redistribute them. It verifies the native SAVE
layout, title-menu eligibility gate, explicit Part 2 transition, target scene,
and Kouhen direct-boot guard.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from time_twist.fds import FdsFile, FdsImage
from time_twist.part2_startup import (
    CURRENT_SCENE_INDEX_ZP,
    SAVE_PART2_MARKER_ADDRESS,
    SAVE_PART2_MARKER_VALUE,
    SAVE_SCENE_INDEX_ADDRESS,
    TITLE_MAIN_MENU_INDEX,
    TITLE_MAIN_MENU_RECORD_IDS,
    TITLE_PART2_SCENE_FILE_IDS,
    TITLE_PART2_SCENE_INDEX,
    TITLE_PART2_TRANSITION_ADDRESS,
    TITLE_PART2_TRANSITION_OPERAND,
    part2_is_available,
    save_address_for_zero_page,
)
from time_twist.scene_transitions import decode_fds_scene_transition_operand

NOV2_LOAD = 0x6000
NOV4_LOAD = 0xA200
OVERLAY_LOAD = 0xA200
SCENE_TABLE = 0x7BA5
SCENE_WIDTH = 4

NOV2_GUARDS = {
    0x6990: bytes.fromhex(
        "A9 01 8D C4 69 20 76 9D 90 0D A9 E3 85 8D 20 CE 9B "
        "A9 00 AA 4C AD 69 AD DD 03 AE DE 03 85 D2 86 D3"
    ),
    0x7B25: bytes.fromhex(
        "20 76 9D 90 03 20 5E 9D A5 CE C9 0B D0 05 A9 AA 8D "
        "DE 03 A9 55 8D DD 03 20 6A 9D 20 76 9D 4C 00 7B"
    ),
    0x7E89: bytes.fromhex("A9 B4 A2 7E 4C 6E 7A"),
    0x7EB4: bytes.fromhex(
        "64 EA E4 0C D2 00 A5 05 E1 0F 06 64 EA E4 E1 54 C7 7E 53"
    ),
    0x9CBA: bytes.fromhex(
        "A9 90 85 3C A9 03 85 3D A0 1F B9 80 04 91 3C 88 10 F8 "
        "A9 B0 85 3C A9 03 85 3D A0 0B B9 B3 07 91 3C 88 10 "
        "F8 A5 DC 85 CF A5 DD 85 D0 A9 D0 85 3C A9 03 85 3D "
        "A0 0F B9 C5 00 91 3C 88 10 F8 20 76 9D 60"
    ),
    0x9D16: bytes.fromhex(
        "A9 90 85 3C A9 03 85 3D A0 1F B1 3C 99 80 04 88 10 F8 "
        "A9 B0 85 3C A9 03 85 3D A0 0B B1 3C 99 B3 07 88 10 "
        "F8 A9 D0 85 3C A9 03 85 3D A0 0F B1 3C 99 C5 00 88 "
        "10 F8 60"
    ),
    0x9D76: bytes.fromhex(
        "AD CD 03 85 3C AD CE 03 85 3D AD CF 03 85 31 A9 00 8D "
        "CD 03 8D CE 03 8D D5 9D 8D D6 9D A9 A5 8D CF 03"
    ),
}

NOV4_GUARDS = {
    0xA200: bytes.fromhex(
        "51 A2 C3 A5 22 A6 4C A2 98 A7 32 A2 32 A2 51 A2 5C A2 "
        "7C A2 85 A2 97 C0 B3 C0 0B A3 40 A8 32 A2"
    ),
    0xA251: bytes.fromhex(
        "08 74 77 00 00 01 02 03 "
        "03 01 01 03 "
        "04 07 08 09 0A "
        "03 04 05 06 "
        "02 0B 0C "
        "06 0D 0E 0F 10 11 12 "
        "08 13 14 15 16 17 18 19 1A "
        "09 00 91 E3 92 01 E3 E4 00"
    ),
    0xBFE8: bytes.fromhex(
        "18 02 03 0C D2 00 00 07 61 E4 61 EA 29 03 01 30 "
        "FE BF 51 C0 59 C0"
    ),
    0xC059: bytes.fromhex("E0 C7"),
}

SCENE6_END_GUARD = bytes.fromhex("B2 10 39 A1 78 10 3A 0F 05")
TT4_ENTRY_GUARD = bytes.fromhex(
    "0E 03 DC 00 67 DD 00 D2 CE 00 07"
)
SON_KOUH_ENTRY_GUARD = bytes.fromhex(
    "A9 FF 85 DF AA 9A A9 27 8D 25 40 A9 00 8D 02 01 8D 03 "
    "01 A9 00 8D 01 20"
)


class Part2StartupAuditError(ValueError):
    """Report drift in the recovered Part 2 startup contract."""


def _guard(data: bytes, load: int, address: int, expected: bytes, label: str) -> None:
    """Require one native byte sequence at an exact loaded address."""
    offset = address - load
    actual = data[offset : offset + len(expected)]
    if actual != expected:
        raise Part2StartupAuditError(
            f"{label} drifted at ${address:04X}: "
            f"{actual.hex().upper()} != {expected.hex().upper()}"
        )


def _files_by_id(
    images: tuple[FdsImage, ...],
) -> dict[int, tuple[tuple[int, int, FdsFile], ...]]:
    """Index all files by ID together with physical disk/side location."""
    result: defaultdict[int, list[tuple[int, int, FdsFile]]] = defaultdict(list)
    for disk_index, image in enumerate(images):
        for side in image.sides:
            for file in side.files:
                result[file.file_id].append((disk_index, side.index, file))
    return {file_id: tuple(rows) for file_id, rows in result.items()}


def _find_named_file(image: FdsImage, name: str) -> tuple[int, FdsFile]:
    """Return side index and named file from one FDS image."""
    for side in image.sides:
        for file in side.files:
            if file.name == name:
                return side.index, file
    raise Part2StartupAuditError(f"missing FDS file {name}")


def _scene_ids(nov2: bytes, index: int) -> tuple[int, ...]:
    """Read one four-file NOV2 scene-load row."""
    start = SCENE_TABLE - NOV2_LOAD + index * SCENE_WIDTH
    return tuple(nov2[start : start + SCENE_WIDTH])


def _compose_program_scene(
    ids: tuple[int, ...],
    files_by_id: dict[int, tuple[tuple[int, int, FdsFile], ...]],
) -> tuple[bytes, tuple[str, ...]]:
    """Compose same-address gameplay program overlays in scene-row order."""
    memory = bytearray(0xD7B5 - OVERLAY_LOAD)
    programs: list[str] = []
    for file_id in ids:
        if file_id in (0x00, 0xFF):
            continue
        for _disk, _side, file in files_by_id.get(file_id, ()):
            if file.kind != 0 or file.load_address != OVERLAY_LOAD:
                continue
            memory[: file.size] = file.data
            programs.append(file.name)
    if not programs:
        raise Part2StartupAuditError("scene row has no gameplay program")
    return bytes(memory), tuple(programs)


def _parse_length_prefixed_menus(
    data: bytes, start: int, count: int
) -> tuple[tuple[int, ...], ...]:
    """Decode NOV4's compact count-plus-record-ID menu definitions."""
    cursor = start
    result: list[tuple[int, ...]] = []
    for _ in range(count):
        item_count = data[cursor]
        cursor += 1
        result.append(tuple(data[cursor : cursor + item_count]))
        cursor += item_count
    return tuple(result)


def audit(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Audit retail originals and return a JSON-serializable handoff summary."""
    images = (FdsImage.read(zenpen), FdsImage.read(kouhen))
    zenpen_image, kouhen_image = images

    zenpen_nov2_side, nov2_file = _find_named_file(zenpen_image, "NOV2")
    zenpen_nov4_side, nov4_file = _find_named_file(zenpen_image, "NOV4")
    zenpen_save_side, save_file = _find_named_file(zenpen_image, "SAVE")
    kouhen_guard_side, son_kouh = _find_named_file(kouhen_image, "SON-KOUH")

    if (zenpen_nov2_side, zenpen_nov4_side, zenpen_save_side) != (0, 0, 0):
        raise Part2StartupAuditError("Zenpen resident/title/SAVE files moved sides")
    if kouhen_guard_side != 0 or son_kouh.load_address != 0xDD1D:
        raise Part2StartupAuditError("Kouhen direct-boot guard moved")
    if save_file.load_address != 0x0390 or save_file.size != 0x50:
        raise Part2StartupAuditError("SAVE file layout changed")
    if save_file.data != bytes(0x50):
        raise Part2StartupAuditError("pristine retail SAVE file is no longer zeroed")

    nov2 = nov2_file.data
    nov4 = nov4_file.data

    for address, expected in NOV2_GUARDS.items():
        _guard(nov2, NOV2_LOAD, address, expected, "NOV2")
    for address, expected in NOV4_GUARDS.items():
        _guard(nov4, NOV4_LOAD, address, expected, "NOV4")

    if save_address_for_zero_page(CURRENT_SCENE_INDEX_ZP) != SAVE_SCENE_INDEX_ADDRESS:
        raise Part2StartupAuditError("scene-index SAVE mapping changed")
    if SAVE_SCENE_INDEX_ADDRESS != 0x03D9:
        raise Part2StartupAuditError("scene index no longer persists at $03D9")
    if SAVE_PART2_MARKER_ADDRESS != 0x03DD:
        raise Part2StartupAuditError("Part 2 marker address changed")
    if not part2_is_available(
        save_valid=True, persisted_marker=SAVE_PART2_MARKER_VALUE
    ):
        raise Part2StartupAuditError("verified Part 2 marker no longer enables Part 2")

    # Header words: $A20E predicates, $A210 menus, $A212 secondary filters.
    header_words = {
        "predicate_table": int.from_bytes(nov4[0x0E:0x10], "little"),
        "menu_table": int.from_bytes(nov4[0x10:0x12], "little"),
        "secondary_filter_table": int.from_bytes(nov4[0x12:0x14], "little"),
        "menu_text": int.from_bytes(nov4[0x14:0x16], "little"),
        "label_table": int.from_bytes(nov4[0x20:0x22], "little"),
        "entry": int.from_bytes(nov4[0x22:0x24], "little"),
    }
    expected_header = {
        "predicate_table": 0xA251,
        "menu_table": 0xA25C,
        "secondary_filter_table": 0xA27C,
        "menu_text": 0xA285,
        "label_table": 0xA30B,
        "entry": 0xA30F,
    }
    if header_words != expected_header:
        raise Part2StartupAuditError(
            f"NOV4 title header drifted: {header_words!r}"
        )

    menus = _parse_length_prefixed_menus(nov4, 0xA25C - NOV4_LOAD, 6)
    if menus[TITLE_MAIN_MENU_INDEX - 1] != TITLE_MAIN_MENU_RECORD_IDS:
        raise Part2StartupAuditError(
            f"title menu 3 drifted: {menus[TITLE_MAIN_MENU_INDEX - 1]!r}"
        )

    secondary_filter = nov4[0xA27C - NOV4_LOAD : 0xA285 - NOV4_LOAD]
    expected_filter = bytes.fromhex("09 00 91 E3 92 01 E3 E4 00")
    if secondary_filter != expected_filter:
        raise Part2StartupAuditError("Start/Load/Part 2 filter drifted")

    target = decode_fds_scene_transition_operand(TITLE_PART2_TRANSITION_OPERAND)
    if (
        target.disk_name,
        target.side_name,
        target.scene_index,
    ) != ("Kouhen", "B", TITLE_PART2_SCENE_INDEX):
        raise Part2StartupAuditError("NOV4 E0 C7 target semantics changed")

    scene7 = _scene_ids(nov2, TITLE_PART2_SCENE_INDEX)
    if scene7 != TITLE_PART2_SCENE_FILE_IDS:
        raise Part2StartupAuditError(f"scene 7 load row drifted: {scene7!r}")

    files_by_id = _files_by_id(images)
    target_files: list[dict[str, object]] = []
    for file_id in scene7:
        if file_id in (0x00, 0xFF):
            continue
        rows = files_by_id.get(file_id, ())
        locations = {(disk, side) for disk, side, _file in rows}
        if locations != {(1, 1)}:
            raise Part2StartupAuditError(
                f"scene-7 file ID ${file_id:02X} moved from Kouhen Side B"
            )
        target_files.append(
            {
                "file_id": f"{file_id:02X}",
                "names": sorted({file.name for _disk, _side, file in rows}),
            }
        )

    scene6_data, scene6_programs = _compose_program_scene(
        _scene_ids(nov2, 6), files_by_id
    )
    _guard(
        scene6_data,
        OVERLAY_LOAD,
        0xA60C,
        SCENE6_END_GUARD,
        "scene 6 ending",
    )

    scene7_data, scene7_programs = _compose_program_scene(scene7, files_by_id)
    _guard(
        scene7_data,
        OVERLAY_LOAD,
        0xA232,
        TT4_ENTRY_GUARD,
        "TT4 scene-index entry",
    )

    if son_kouh.data[: len(SON_KOUH_ENTRY_GUARD)] != SON_KOUH_ENTRY_GUARD:
        raise Part2StartupAuditError("SON-KOUH direct-boot guard entry drifted")

    return {
        "save": {
            "file_address": "0x0390",
            "file_size": 0x50,
            "scene_index_zero_page": "0xCE",
            "scene_index_save_address": "0x03D9",
            "part2_marker_address": "0x03DD",
            "part2_marker_written_value": "0x55",
            "checksum_marker_address": "0x03CF",
            "checksum_marker_value": "0xA5",
        },
        "title": {
            "header": {key: f"0x{value:04X}" for key, value in header_words.items()},
            "menus": [list(menu) for menu in menus],
            "main_menu_index": TITLE_MAIN_MENU_INDEX,
            "main_menu_record_ids": list(TITLE_MAIN_MENU_RECORD_IDS),
            "secondary_filter_hex": secondary_filter.hex().upper(),
            "eligibility_rule": "valid SAVE and $03DD != 0",
            "part2_transition_address": f"0x{TITLE_PART2_TRANSITION_ADDRESS:04X}",
            "part2_transition_operand": f"0x{TITLE_PART2_TRANSITION_OPERAND:02X}",
        },
        "ending": {
            "scene": 6,
            "program_chain": list(scene6_programs),
            "tail_address": "0xA60C",
            "tail_hex": SCENE6_END_GUARD.hex().upper(),
            "system_sequence": 5,
            "resident_sequence_address": "0x7EB4",
        },
        "part2_target": {
            "disk": target.disk_name,
            "side": target.side_name,
            "scene": target.scene_index,
            "scene_file_ids": [f"{value:02X}" for value in scene7],
            "scene_files": target_files,
            "program_chain": list(scene7_programs),
        },
        "direct_boot_negative_path": {
            "file": son_kouh.name,
            "disk": "Kouhen",
            "side": "A",
            "load_address": f"0x{son_kouh.load_address:04X}",
            "size": son_kouh.size,
        },
    }


def main() -> int:
    """Run the Part 2 startup audit."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit(args.zenpen, args.kouhen)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Part 2 startup handoff audit: PASS "
            f"({report['part2_target']['disk']} "
            f"Side {report['part2_target']['side']}, "
            f"scene {report['part2_target']['scene']})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
