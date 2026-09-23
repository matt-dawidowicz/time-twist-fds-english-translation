#!/usr/bin/env python3
"""Audit the source-backed retail gameplay VM semantic contract.

The tool consumes maintainer-supplied original Zenpen and Kouhen FDS images.
It never modifies or redistributes them. It source-guards the recovered NOV2
interpreter handlers and verifies that the 13 real composed gameplay scenes
retain the header invariants used by the retail-opcode specification.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from time_twist.fds import FdsFile, FdsImage
from time_twist.part_handoff import (
    KOUHEN_FIRST_SCENE_TARGET,
    SAVE_DISK_WRITE_MARKER,
    title_gate_from_save,
)
from time_twist.retail_vm import RETAIL_VM_OPCODE_VALUES, RETAIL_VM_OPCODES
from time_twist.scene_transitions import decode_fds_scene_transition_operand

NOV2_LOAD = 0x6000
OVERLAY_LOAD = 0xA200
NOV3_LOAD = 0xD7B5
SCENE_TABLE = 0x7BA5
SCENE_COUNT = 15
SCENE_WIDTH = 4
EXPECTED_GAMEPLAY_SCENES = (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14)
EXPECTED_SCENE_ROWS = (
    (0x00, 0x00, 0x00, 0x00),
    (0x41, 0x42, 0x51, 0x52),
    (0x41, 0x51, 0xFF, 0xFF),
    (0x43, 0x53, 0xFF, 0xFF),
    (0x43, 0x44, 0x53, 0xFF),
    (0x45, 0x55, 0xFF, 0xFF),
    (0x45, 0x46, 0x55, 0xFF),
    (0x47, 0x57, 0xFF, 0xFF),
    (0xFF, 0xFF, 0xFF, 0xFF),
    (0x49, 0x59, 0xFF, 0xFF),
    (0x49, 0x4A, 0x59, 0x5A),
    (0x4C, 0x4B, 0x5D, 0x5B),
    (0x4C, 0x5D, 0x5C, 0xFF),
    (0x4D, 0x5D, 0xFF, 0xFF),
    (0x4E, 0x5E, 0xFF, 0xFF),
)
EXPECTED_SCENE_TRANSITIONS = (
    (1, "TT1A", 0xA44F, 0x42),
    (2, "TT1B", 0xAB79, 0x43),
    (3, "TT2", 0xAD03, 0x44),
    (4, "T22", 0xA6BD, 0x05),
    (5, "TT3A", 0xA96F, 0x06),
    (7, "TT4", 0xADAA, 0xC9),
    (9, "TT5", 0xA759, 0xCA),
    (10, "T25", 0xA347, 0x8B),
    (11, "TT6A", 0xA737, 0x8C),
    (12, "TT6B", 0xA5A5, 0x8D),
    (13, "TT6C", 0xAAA6, 0x8E),
)
EXPECTED_SOURCE_REACHABLE = (
    0x00,
    0x01,
    0x02,
    0x04,
    0x06,
    0x09,
    0x0E,
    0x0F,
    0x10,
    0x11,
    0x18,
    0x19,
    0x20,
    0x21,
    0x28,
    0x29,
    0x30,
    0x31,
    0x40,
    0x41,
    0x44,
    0x45,
    0x49,
    0x4D,
    0x50,
    0x51,
    0x52,
    0x53,
    0x54,
    0x58,
    0x60,
    0x61,
    0x62,
    0x63,
    0x64,
    0x65,
    0x66,
    0x67,
    0x68,
    0x69,
    0x6C,
    0x6D,
    0x70,
    0x83,
    0x90,
    0x91,
    0x92,
    0x93,
    0xA1,
    0xB0,
    0xB2,
    0xB3,
    0xB5,
    0xB6,
    0xB7,
    0xB9,
    0xBA,
    0xBB,
    0xBC,
    0xD2,
    0xE0,
)

NOV2_GUARDS = {
    0x6990: bytes.fromhex(
        "A9 01 8D C4 69 20 76 9D 90 0D A9 E3 85 8D 20 CE 9B "
        "A9 00 AA 4C AD 69 AD DD 03 AE DE 03 85 D2 86 D3"
    ),
    0x69E5: bytes.fromhex(
        "A0 00 B1 C5 4A 4A 4A 4A 18 69 10 C9 10 D0 02 A9 20"
    ),
    0x6BFD: bytes.fromhex(
        "A0 00 B1 C5 29 01 F0 28 A5 A4 C9 FF F0 4B A4 A7 C8"
    ),
    0x6C5E: bytes.fromhex(
        "A0 00 B1 C5 29 03 AA F0 09 CA F0 16 CA F0 36 4C C8 6C"
    ),
    0x6DA9: bytes.fromhex(
        "A0 00 B1 C5 29 0F 85 31 29 08 F0 22 C8 B1 C5 85 3C"
    ),
    0x6F2C: bytes.fromhex("A0 00 B1 C5 29 0F F0 03 4C 40 6F 20 16 9C"),
    0x6F49: bytes.fromhex("A9 50 A0 6F 4C 2A 61 5E 6F 07 70 2E 70"),
    0x71A4: bytes.fromhex(
        "8A F0 03 4C DA 71 A0 00 B1 C5 29 0F F0 0C C8 B1 C5 85 B5"
    ),
    0x7226: bytes.fromhex(
        "C6 72 AF 72 78 72 49 72 F6 72 1A 73 63 73 6E 73 "
        "46 72 9F 72 86 73 DD 73 C6 72 46 72 46 72 46 72"
    ),
    0x729F: bytes.fromhex(
        "A5 C5 85 9B A5 C6 85 9C A5 9D 85 9F A5 9E 85 A0 " "A0 01 B1 C5 85 BA"
    ),
    0x7363: bytes.fromhex("A9 FF 85 4A A9 1B A2 07 4C 19 61"),
    0x76CF: bytes.fromhex(
        "AD 0C A2 85 3E AD 0D A2 85 3F A0 00 A6 BA CA F0 15 "
        "B1 3E 0A 0A 18 69 01 18 65 3E 85 3E A5 3F 69 00 "
        "85 3F 4C DA 76"
    ),
    0x76F4: bytes.fromhex("A0 00 B1 3E 85 91 AA A9 00 85 A7 C8 B1 3E"),
    0x78BA: bytes.fromhex(
        "A9 C1 A0 78 4C 2A 61 CB 78 6A 79 6D 79 72 79 98 79"
    ),
    0x7972: bytes.fromhex(
        "AD 8C 07 F0 1E A0 00 B1 C5 8D 89 07 C8 B1 C5 8D 8A 07 "
        "C8 B1 C5 8D 8B 07"
    ),
    0x79A7: bytes.fromhex("A9 AE A0 79 4C 2A 61 BA 79 C0 79 5E 7B"),
    0x79E5: bytes.fromhex(
        "A0 00 B1 C5 8D E3 79 C8 B1 C5 8D E4 79 A9 E3 85 C5 "
        "A9 79 85 C6 A0 01 B1 C5 29 40 D0 09 A9 CB A2 60 A0 "
        "06 4C 11 7A A9 D5 A2 60 A0 07 8D 0B 60 8E 0C 60 8C "
        "B9 7A A0 01 B1 C5 30 07 A0 04 A9 31 4C 2B 7A A0 05 "
        "A9 32 8C B7 7A 8D CE 60 8D D8 60 A0 01 B1 C5 29 3F "
        "0A 0A AA BD A5 7B 8D DF 60 BD A6 7B 8D E0 60 BD A7 "
        "7B 8D E1 60 BD A8 7B 8D E2 60"
    ),
    0x977D: bytes.fromhex(
        "A0 00 B1 94 29 0F C9 0F D0 0E C8 B1 94 85 31 A6 31 "
        "E8 E8 E8 E8 4C 99 97 85 31 A6 31 E8 E8 8A 4A 85 31"
    ),
    0x7B25: bytes.fromhex(
        "20 76 9D 90 03 20 5E 9D A5 CE C9 0B D0 05 A9 AA 8D "
        "DE 03 A9 55 8D DD 03 20 6A 9D 20 76 9D 4C 00 7B"
    ),
    0x7C0E: bytes.fromhex(
        "8A F0 03 4C C0 7D A9 FA 85 8D 20 E0 9B A9 FB 85 8D"
    ),
}


class RetailVmAuditError(ValueError):
    """Report drift in the recovered retail gameplay VM contract."""


def _word(data: bytes, offset: int) -> int:
    """Read one little-endian word from a composed overlay image."""
    return int.from_bytes(data[offset : offset + 2], "little")


def _files_by_id(
    images: tuple[FdsImage, ...],
) -> dict[int, tuple[FdsFile, ...]]:
    """Index every FDS file from both original images by game file ID."""
    result: defaultdict[int, list[FdsFile]] = defaultdict(list)
    for image in images:
        for side in image.sides:
            for file in side.files:
                result[file.file_id].append(file)
    return {file_id: tuple(files) for file_id, files in result.items()}


def _guard_nov2(nov2: bytes) -> None:
    """Verify native interpreter sequences underlying the semantic registry."""
    for address, expected in NOV2_GUARDS.items():
        offset = address - NOV2_LOAD
        if nov2[offset : offset + len(expected)] != expected:
            raise RetailVmAuditError(
                f"NOV2 semantic guard changed at CPU ${address:04X}"
            )


def _guard_part_handoff(
    images: tuple[FdsImage, ...],
    files_by_id: dict[int, tuple[FdsFile, ...]],
) -> dict[str, object]:
    """Verify the non-E0 Zenpen-to-Kouhen continuation path."""
    nov4 = images[0].sides[0].find_file("NOV4")
    route_address = 0xBFEB
    route_expected = bytes.fromhex(
        "0C D2 00 00 07 61 E4 61 EA 29 03 01 "
        "30 FE BF 51 C0 59 C0"
    )
    route_offset = route_address - nov4.load_address
    if nov4.data[route_offset : route_offset + len(route_expected)] != route_expected:
        raise RetailVmAuditError(
            "NOV4 Part 2 title-gate route changed at CPU $BFEB"
        )

    target_address = 0xC059
    target_expected = bytes((0xE0, KOUHEN_FIRST_SCENE_TARGET))
    target_offset = target_address - nov4.load_address
    if nov4.data[target_offset : target_offset + 2] != target_expected:
        raise RetailVmAuditError(
            "NOV4 Part 2 target changed at CPU $C059"
        )

    composed = _compose_scene(EXPECTED_SCENE_ROWS[6], files_by_id)
    if composed is None:
        raise RetailVmAuditError("Zenpen final scene has no composed program")
    ending, programs = composed
    if programs[-1] != "TT3B":
        raise RetailVmAuditError(
            f"Zenpen final scene owner changed to {programs[-1]}"
        )
    ending_address = 0xA60C
    ending_expected = bytes.fromhex(
        "B2 10 39 A1 78 10 3A 0F 05"
    )
    ending_offset = ending_address - OVERLAY_LOAD
    if ending[ending_offset : ending_offset + len(ending_expected)] != ending_expected:
        raise RetailVmAuditError(
            "TT3B ending system-sequence tail changed at CPU $A60C"
        )

    invalid = title_gate_from_save(
        save_valid=False,
        disk_write_marker=SAVE_DISK_WRITE_MARKER,
    )
    unmarked = title_gate_from_save(
        save_valid=True,
        disk_write_marker=0,
    )
    marked = title_gate_from_save(
        save_valid=True,
        disk_write_marker=SAVE_DISK_WRITE_MARKER,
    )
    if (
        invalid.load_visible
        or invalid.part2_visible
        or not unmarked.load_visible
        or unmarked.part2_visible
        or not marked.part2_visible
    ):
        raise RetailVmAuditError("Part 2 title-gate model drifted")

    return {
        "zenpen_ending_system_sequence": {
            "scene_index": 6,
            "active_program": "TT3B",
            "cpu_address": "0xA60C",
            "tail": "B2 10 39 A1 78 10 3A 0F 05",
        },
        "save_restore": {
            "checksum_valid_flag": "not E3",
            "disk_write_marker_address": "0x03DD",
            "disk_write_marker_value": f"0x{SAVE_DISK_WRITE_MARKER:02X}",
            "title_marker_zp": "0xD2",
        },
        "title_gate": {
            "route_cpu": "0xBFEB",
            "e4_rule": "D2 != 0",
            "load_rule": "!E3",
            "part2_rule": "!E3 && E4",
        },
        "part2_target": {
            "cpu_address": "0xC059",
            "operand": f"0x{KOUHEN_FIRST_SCENE_TARGET:02X}",
            "disk": "Kouhen",
            "side": "B",
            "scene_index": 7,
        },
    }


def _scene_ids(nov2: bytes, index: int) -> tuple[int, ...]:
    """Read one four-file NOV2 gameplay scene load-list entry."""
    start = SCENE_TABLE - NOV2_LOAD + index * SCENE_WIDTH
    return tuple(nov2[start : start + SCENE_WIDTH])


def _file_id_locations(
    images: tuple[FdsImage, ...], file_id: int
) -> set[tuple[int, int]]:
    """Return every disk/side pair carrying one FDS file ID."""
    result: set[tuple[int, int]] = set()
    for disk_index, image in enumerate(images):
        for side in image.sides:
            if any(file.file_id == file_id for file in side.files):
                result.add((disk_index, side.index))
    return result


def _file_id_names(
    files_by_id: dict[int, tuple[FdsFile, ...]], file_id: int
) -> tuple[str, ...]:
    """Return sorted unique names carried by one FDS file ID."""
    return tuple(sorted({file.name for file in files_by_id.get(file_id, ())}))


def _compose_scene(
    ids: tuple[int, ...], files_by_id: dict[int, tuple[FdsFile, ...]]
) -> tuple[bytes, tuple[str, ...]] | None:
    """Compose the `$A200` program overlay for one NOV2 scene entry."""
    memory = bytearray(NOV3_LOAD - OVERLAY_LOAD)
    programs: list[str] = []
    for file_id in ids:
        if file_id in (0x00, 0xFF):
            continue
        for file in files_by_id.get(file_id, ()):
            if file.kind != 0 or file.load_address != OVERLAY_LOAD:
                continue
            if file.size > len(memory):
                raise RetailVmAuditError(f"{file.name}: program crosses NOV3")
            programs.append(file.name)
            memory[: file.size] = file.data
    if not programs:
        return None
    return bytes(memory), tuple(programs)


def audit(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Audit originals and return a JSON-serializable semantic summary."""
    images = (FdsImage.read(zenpen), FdsImage.read(kouhen))
    nov2 = images[0].sides[0].find_file("NOV2").data
    _guard_nov2(nov2)

    if RETAIL_VM_OPCODE_VALUES != EXPECTED_SOURCE_REACHABLE:
        raise RetailVmAuditError(
            "retail opcode registry no longer matches baseline"
        )
    if len(RETAIL_VM_OPCODES) != len(set(RETAIL_VM_OPCODE_VALUES)):
        raise RetailVmAuditError("retail opcode registry contains duplicates")

    files_by_id = _files_by_id(images)
    part_handoff = _guard_part_handoff(images, files_by_id)
    scene_rows: list[dict[str, object]] = []
    gameplay_indexes: list[int] = []
    for index in range(SCENE_COUNT):
        ids = _scene_ids(nov2, index)
        if ids != EXPECTED_SCENE_ROWS[index]:
            raise RetailVmAuditError(
                f"scene {index}: load row drifted: {ids!r}"
            )
        composed = _compose_scene(ids, files_by_id)
        if composed is None:
            continue
        data, programs = composed
        gameplay_indexes.append(index)
        predicate_base = _word(data, 0x0E)
        label_table = _word(data, 0x20)
        entry = _word(data, 0x22)
        hotspot_table = _word(data, 0x0C)
        if predicate_base != 0:
            raise RetailVmAuditError(
                f"scene {index}: $A20E predicate base became "
                f"${predicate_base:04X}"
            )
        if not (
            OVERLAY_LOAD <= entry < label_table <= hotspot_table < NOV3_LOAD
        ):
            raise RetailVmAuditError(
                f"scene {index}: script/label/hotspot ordering changed"
            )
        if entry != 0xA232:
            raise RetailVmAuditError(
                f"scene {index}: initial script entry changed to ${entry:04X}"
            )
        locations = {
            location
            for file_id in ids
            if file_id not in (0x00, 0xFF)
            for location in _file_id_locations(images, file_id)
        }
        scene_rows.append(
            {
                "scene_index": index,
                "file_ids": [f"{file_id:02X}" for file_id in ids],
                "file_names": [
                    (
                        list(_file_id_names(files_by_id, file_id))
                        if file_id not in (0x00, 0xFF)
                        else []
                    )
                    for file_id in ids
                ],
                "disk_side_locations": [
                    {"disk_index": disk, "side_index": side}
                    for disk, side in sorted(locations)
                ],
                "program_chain": list(programs),
                "script_entry": entry,
                "label_table": label_table,
                "predicate_base": predicate_base,
            }
        )

    if tuple(gameplay_indexes) != EXPECTED_GAMEPLAY_SCENES:
        raise RetailVmAuditError(
            f"gameplay scene set changed: {tuple(gameplay_indexes)!r}"
        )

    transition_calls: list[dict[str, object]] = []
    for (
        source_scene,
        source_program,
        address,
        operand,
    ) in EXPECTED_SCENE_TRANSITIONS:
        source_ids = _scene_ids(nov2, source_scene)
        composed = _compose_scene(source_ids, files_by_id)
        if composed is None:
            raise RetailVmAuditError(
                f"scene {source_scene}: transition source has no program"
            )
        data, programs = composed
        if programs[-1] != source_program:
            raise RetailVmAuditError(
                f"scene {source_scene}: expected active transition owner "
                f"{source_program}, got {programs[-1]}"
            )
        offset = address - OVERLAY_LOAD
        actual = data[offset - 1 : offset + 2]
        expected = bytes((0xB2, 0xE0, operand))
        if actual != expected:
            raise RetailVmAuditError(
                f"scene {source_scene}: transition call drifted at "
                f"${address:04X}: {actual.hex().upper()} != "
                f"{expected.hex().upper()}"
            )

        target = decode_fds_scene_transition_operand(operand)
        if target.scene_index >= SCENE_COUNT:
            raise RetailVmAuditError(
                f"scene {source_scene}: transition targets invalid row "
                f"{target.scene_index}"
            )
        target_ids = _scene_ids(nov2, target.scene_index)
        target_location = (target.disk_index, target.side_index)
        for file_id in target_ids:
            if file_id in (0x00, 0xFF):
                continue
            locations = _file_id_locations(images, file_id)
            if locations != {target_location}:
                raise RetailVmAuditError(
                    f"transition ${operand:02X}: file ID ${file_id:02X} "
                    f"locations {sorted(locations)!r} do not match "
                    f"{target_location!r}"
                )

        transition_calls.append(
            {
                "source_scene": source_scene,
                "source_program": source_program,
                "call_address": f"0x{address:04X}",
                "operand": f"0x{operand:02X}",
                "target_disk": target.disk_name,
                "target_side": target.side_name,
                "target_scene": target.scene_index,
                "target_file_ids": [
                    f"{file_id:02X}" for file_id in target_ids
                ],
                "target_file_names": [
                    (
                        list(_file_id_names(files_by_id, file_id))
                        if file_id not in (0x00, 0xFF)
                        else []
                    )
                    for file_id in target_ids
                ],
            }
        )

    evidence_counts: defaultdict[str, int] = defaultdict(int)
    for entry in RETAIL_VM_OPCODES:
        evidence_counts[entry.evidence] += 1
    return {
        "opcode_count": len(RETAIL_VM_OPCODES),
        "opcodes": [f"{value:02X}" for value in RETAIL_VM_OPCODE_VALUES],
        "evidence_counts": dict(sorted(evidence_counts.items())),
        "native_guard_count": len(NOV2_GUARDS),
        "gameplay_scene_count": len(scene_rows),
        "scenes": scene_rows,
        "scene_transition_operand": {
            "disk_bit": "0x80",
            "disk_zero": "Zenpen",
            "disk_one": "Kouhen",
            "side_bit": "0x40",
            "side_zero": "A",
            "side_one": "B",
            "scene_mask": "0x3F",
        },
        "scene_transition_calls": transition_calls,
        "scene_transition_call_count": len(transition_calls),
        "part_handoff": part_handoff,
        "part_boundary": {
            "zenpen_final_gameplay_scene": 6,
            "kouhen_initial_gameplay_scene": 7,
            "direct_e0_edge": False,
        },
        "reachability_baseline": {
            "route_seeded_commands": 7283,
            "covered_script_bytes": 23902,
            "total_script_bytes": 24229,
            "coverage_percent": 98.6504,
            "non_reached_source_bytes": 327,
            "status": "historical conservative baseline",
        },
        "reachability_refinement": {
            "structural_may_reach_bytes": 24199,
            "total_script_bytes": 24229,
            "structural_may_reach_percent": 99.8762,
            "classified_non_live_bytes": 30,
            "unused_audio_helper_bytes": 20,
            "unreferenced_bytecode_bytes": 2,
            "skipped_or_padding_bytes": 8,
            "runtime_certified": False,
            "reference": "docs/GAMEPLAY_VM_REACHABILITY_AUDIT.md",
        },
    }


def main() -> int:
    """Run the command-line retail VM semantics audit."""
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
            "retail VM semantic audit: PASS "
            f"({report['opcode_count']} opcodes, "
            f"{report['gameplay_scene_count']} scenes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
