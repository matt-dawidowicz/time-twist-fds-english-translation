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
from time_twist.retail_vm import RETAIL_VM_OPCODE_VALUES, RETAIL_VM_OPCODES

NOV2_LOAD = 0x6000
OVERLAY_LOAD = 0xA200
NOV3_LOAD = 0xD7B5
SCENE_TABLE = 0x7BA5
SCENE_COUNT = 15
SCENE_WIDTH = 4
EXPECTED_GAMEPLAY_SCENES = (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14)
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
    0x7363: bytes.fromhex("A9 FF 85 4A A9 1B A2 07 4C 19 61"),
    0x78BA: bytes.fromhex(
        "A9 C1 A0 78 4C 2A 61 CB 78 6A 79 6D 79 72 79 98 79"
    ),
    0x7972: bytes.fromhex(
        "AD 8C 07 F0 1E A0 00 B1 C5 8D 89 07 C8 B1 C5 8D 8A 07 "
        "C8 B1 C5 8D 8B 07"
    ),
    0x79A7: bytes.fromhex("A9 AE A0 79 4C 2A 61 BA 79 C0 79 5E 7B"),
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


def _scene_ids(nov2: bytes, index: int) -> tuple[int, ...]:
    """Read one four-file NOV2 gameplay scene load-list entry."""
    start = SCENE_TABLE - NOV2_LOAD + index * SCENE_WIDTH
    return tuple(nov2[start : start + SCENE_WIDTH])


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
    scene_rows: list[dict[str, object]] = []
    gameplay_indexes: list[int] = []
    for index in range(SCENE_COUNT):
        ids = _scene_ids(nov2, index)
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
        scene_rows.append(
            {
                "scene_index": index,
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
        "reachability_baseline": {
            "route_seeded_commands": 7283,
            "covered_script_bytes": 23902,
            "total_script_bytes": 24229,
            "coverage_percent": 98.6504,
            "non_reached_source_bytes": 327,
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
