"""Audit recovered Time Twist gameplay graphics and control contracts."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from time_twist.fds import FdsFile, FdsImage
from time_twist.gameplay_graphics import (
    HOTSPOT_LEFT_BOUNDARY,
    HOTSPOT_RIGHT_BOUNDARY,
    OVERLAY_LOAD_ADDRESS,
    parse_actor_spawn_records,
    parse_background_map_records,
    parse_hotspot_records,
    parse_metasprite_definitions,
    parse_static_placement_records,
)
from time_twist.project import (
    KNOWN_SCENARIO_BANKS,
    source_dictionary_reference_floor,
)
from time_twist.release_metadata import SCENARIO_LOCATIONS
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import SymbolKind, split_records
from time_twist.ui import FIXED_RECORD_TABLE_SPECS

NOV2_LOAD_ADDRESS = 0x6000
NOV3_LOAD_ADDRESS = 0xD7B5
SCENE_LOAD_TABLE_CPU = 0x7BA5
SCENE_LOAD_TABLE_RECORDS = 15
SCENE_LOAD_TABLE_WIDTH = 4
SCENE_LOAD_LIST_CPU = 0x60DF

TEXT_CONTROL_HANDLER_CPU = 0x8242
TEXT_STATE_TABLE_CPU = 0x7F42
TEXT_DIRTY_ROW_SELECTOR_CPU = 0x837E
TEXT_CELL_UPLOAD_CPU = 0x83D9
TEXT_SOFTWARE_SCROLL_CPU = 0x844F
TEXT_SCROLL_NMI_CPU = 0x84AE
CONTROLLER_POLL_CPU = 0x67F2
NEW_PRESS_MASK_ADDRESS = 0x001F
A_BUTTON_NEW_PRESS_MASK = 0x80

TEXT_CONTROL_INITIAL_STATES = {
    1: 0x13,
    2: 0x0F,
    3: 0x06,
    4: 0x09,
    6: 0x17,
}
TEXT_CONTROL_WAIT_STATES = {
    1: 0x15,
    2: 0x11,
    3: 0x08,
    6: 0x19,
}
TEXT_CONTROL_RESUME_STATES = {
    1: 0x16,
    2: 0x12,
    3: 0x0C,
    6: 0x1A,
}
TEXT_CONTROL_RESUME_X = {
    1: 0x30,
    2: 0x60,
    3: 0x90,
    6: 0x90,
}


class EngineSurfaceAuditError(ValueError):
    """Report source drift or a recovered-engine contract violation."""


@dataclass(frozen=True)
class GraphicsComponent:
    """Describe one recovered object/background CHR component."""

    image: str
    side: int
    name: str
    file_id: int
    role: str
    load_address: int
    end_address: int
    size: int
    tile_count: int


@dataclass(frozen=True)
class SceneLoadSet:
    """Describe one four-byte NOV2 FDS scene file-ID list entry."""

    index: int
    ids: tuple[int, ...]
    files: tuple[tuple[str, ...], ...]


def _read_word(data: bytes, offset: int) -> int:
    """Read one bounded little-endian word."""
    if offset < 0 or offset + 2 > len(data):
        raise EngineSurfaceAuditError(
            f"word offset 0x{offset:04X} is outside data"
        )
    return int.from_bytes(data[offset : offset + 2], "little")


def _files_by_id(
    images: dict[str, FdsImage],
) -> dict[int, tuple[FdsFile, ...]]:
    """Map each game FDS file ID to every file carrying that ID."""
    values: defaultdict[int, list[FdsFile]] = defaultdict(list)
    for image in images.values():
        for side in image.sides:
            for file in side.files:
                values[file.file_id].append(file)
    return {file_id: tuple(files) for file_id, files in values.items()}


def _nov2(images: dict[str, FdsImage]) -> bytes:
    """Return the original Zenpen side-0 NOV2 payload."""
    return images["zenpen"].sides[0].find_file("NOV2").data


def _nov2_slice(nov2: bytes, cpu_address: int, size: int) -> bytes:
    """Return one bounded NOV2 CPU-addressed byte range."""
    offset = cpu_address - NOV2_LOAD_ADDRESS
    if offset < 0 or offset + size > len(nov2):
        raise EngineSurfaceAuditError(
            f"NOV2 range 0x{cpu_address:04X}+{size} is outside the payload"
        )
    return nov2[offset : offset + size]


def _expect_nov2_bytes(
    nov2: bytes, cpu_address: int, expected: bytes, label: str
) -> None:
    """Fail closed when one recovered native NOV2 sequence drifts."""
    actual = _nov2_slice(nov2, cpu_address, len(expected))
    if actual != expected:
        raise EngineSurfaceAuditError(
            f"{label} drifted at 0x{cpu_address:04X}: "
            f"{actual.hex().upper()} != {expected.hex().upper()}"
        )


def _text_state_handler(nov2: bytes, state: int) -> int:
    """Return the native handler pointer for one renderer state."""
    if not 0 <= state <= 0x1A:
        raise EngineSurfaceAuditError(f"invalid text state 0x{state:02X}")
    raw = _nov2_slice(nov2, TEXT_STATE_TABLE_CPU + state * 2, 2)
    return int.from_bytes(raw, "little")


def _text_control_report(nov2: bytes) -> dict[str, object]:
    """Validate and summarize the recovered NOV2 text-control state machine."""
    _expect_nov2_bytes(
        nov2,
        TEXT_CONTROL_HANDLER_CPU,
        bytes.fromhex(
            "A5 3A C9 01 D0 03 4C EB 82 "
            "C9 02 D0 03 4C F0 82 "
            "C9 04 D0 03 4C F5 82 "
            "C9 03 D0 03 4C FA 82 "
            "C9 05 D0 03 4C 04 83 "
            "C9 06 D0 03 4C FF 82"
        ),
        "text control dispatcher",
    )
    _expect_nov2_bytes(
        nov2,
        0x82EB,
        bytes.fromhex(
            "A9 13 4C 1D 83 "
            "A9 0F 4C 1D 83 "
            "A9 09 4C 1D 83 "
            "A9 06 4C 1D 83 "
            "A9 17 4C 1D 83"
        ),
        "text control state stubs",
    )
    _expect_nov2_bytes(
        nov2,
        0x831D,
        bytes.fromhex("85 69 E0 00 D0 04 A9 03 85 73 60"),
        "text semantic-state setter",
    )
    _expect_nov2_bytes(
        nov2,
        0x6831,
        bytes.fromhex("55 22 35 1D 95 1F"),
        "controller new-press edge derivation",
    )
    for cpu_address, next_state in (
        (0x7FC8, 0x0C),
        (0x8001, 0x12),
        (0x801A, 0x16),
        (0x8033, 0x1A),
    ):
        _expect_nov2_bytes(
            nov2,
            cpu_address,
            bytes(
                (
                    0xA5,
                    0x1F,
                    0x29,
                    0x80,
                    0xF0,
                    0x04,
                    0xA9,
                    next_state,
                    0x85,
                    0x69,
                )
            ),
            f"text A-wait state at 0x{cpu_address:04X}",
        )
    _expect_nov2_bytes(
        nov2,
        0x800E,
        bytes.fromhex("A9 FF 85 6E A0 00 A2 60 20 5E 81 60"),
        "CTRL:2 row-three continuation",
    )
    _expect_nov2_bytes(
        nov2,
        0x8027,
        bytes.fromhex("A9 80 85 6E A0 00 A2 30 20 5E 81 60"),
        "CTRL:1 row-two continuation",
    )
    _expect_nov2_bytes(
        nov2,
        0x8040,
        bytes.fromhex("A9 40 85 6E A0 00 A2 90 20 5E 81 60"),
        "CTRL:6 row-four continuation",
    )
    _expect_nov2_bytes(
        nov2,
        0x7FEB,
        bytes.fromhex("A9 0F 85 6D E6 69 60"),
        "CTRL:3/4 scroll countdown entry",
    )
    _expect_nov2_bytes(
        nov2,
        0x7FF2,
        bytes.fromhex("A9 40 85 6E 20 4F 84 A0 00 A2 90 20 5E 81 60"),
        "post-scroll row-four continuation",
    )
    _expect_nov2_bytes(
        nov2,
        TEXT_SOFTWARE_SCROLL_CPU,
        bytes.fromhex(
            "A2 00 BD 77 87 9D 47 87 E8 E0 90 D0 F5 "
            "A2 00 A9 AC 9D D7 87 E8 E0 30 D0 F8 60"
        ),
        "dialogue software row shift",
    )
    _expect_nov2_bytes(
        nov2,
        0x85B7,
        bytes.fromhex("C6 6D D0 04 A9 0E 85 69 60"),
        "dialogue scroll NMI countdown exit",
    )

    expected_handlers = {
        0x06: 0x7FC0,
        0x07: 0x7FC4,
        0x08: 0x7FC8,
        0x09: 0x7FC0,
        0x0A: 0x7FC4,
        0x0B: 0x7FE6,
        0x0C: 0x7FEB,
        0x0D: 0x7FF1,
        0x0E: 0x7FF2,
        0x0F: 0x7FC0,
        0x10: 0x7FC4,
        0x11: 0x8001,
        0x12: 0x800E,
        0x13: 0x7FC0,
        0x14: 0x7FC4,
        0x15: 0x801A,
        0x16: 0x8027,
        0x17: 0x7FC0,
        0x18: 0x7FC4,
        0x19: 0x8033,
        0x1A: 0x8040,
    }
    actual_handlers = {
        state: _text_state_handler(nov2, state) for state in expected_handlers
    }
    if actual_handlers != expected_handlers:
        raise EngineSurfaceAuditError(
            "text semantic-control state table drifted: "
            f"{actual_handlers!r} != {expected_handlers!r}"
        )

    return {
        "handler_cpu": f"0x{TEXT_CONTROL_HANDLER_CPU:04X}",
        "state_table_cpu": f"0x{TEXT_STATE_TABLE_CPU:04X}",
        "controller_poll_cpu": f"0x{CONTROLLER_POLL_CPU:04X}",
        "new_press_mask_address": f"0x{NEW_PRESS_MASK_ADDRESS:04X}",
        "a_button_new_press_mask": f"0x{A_BUTTON_NEW_PRESS_MASK:02X}",
        "dirty_row_selector_cpu": f"0x{TEXT_DIRTY_ROW_SELECTOR_CPU:04X}",
        "cell_upload_cpu": f"0x{TEXT_CELL_UPLOAD_CPU:04X}",
        "software_scroll_cpu": f"0x{TEXT_SOFTWARE_SCROLL_CPU:04X}",
        "scroll_nmi_cpu": f"0x{TEXT_SCROLL_NMI_CPU:04X}",
        "controls": {
            "0": {
                "name": "ROW_NEXT",
                "wait_for_a": False,
                "resume_x": "next row",
            },
            "1": {
                "name": "WAIT_ROW2",
                "initial_state": "0x13",
                "wait_state": "0x15",
                "resume_state": "0x16",
                "wait_for_a": True,
                "scroll": False,
                "resume_x": "0x30",
            },
            "2": {
                "name": "WAIT_ROW3",
                "initial_state": "0x0F",
                "wait_state": "0x11",
                "resume_state": "0x12",
                "wait_for_a": True,
                "scroll": False,
                "resume_x": "0x60",
            },
            "3": {
                "name": "WAIT_SCROLL_ROW4",
                "initial_state": "0x06",
                "wait_state": "0x08",
                "resume_state": "0x0C",
                "wait_for_a": True,
                "scroll": True,
                "resume_x": "0x90",
            },
            "4": {
                "name": "SCROLL_ROW4",
                "initial_state": "0x09",
                "wait_for_a": False,
                "scroll": True,
                "resume_x": "0x90",
            },
            "5": {
                "name": "END_RECORD_OR_DICTIONARY",
                "wait_for_a": False,
            },
            "6": {
                "name": "WAIT_ROW4",
                "initial_state": "0x17",
                "wait_state": "0x19",
                "resume_state": "0x1A",
                "wait_for_a": True,
                "scroll": False,
                "resume_x": "0x90",
            },
            "7": {
                "name": "ROW_NEXT_UNUSED_ALIAS",
                "wait_for_a": False,
                "resume_x": "same fallthrough as control 0",
            },
        },
    }


def _scene_load_sets(
    nov2: bytes, files_by_id: dict[int, tuple[FdsFile, ...]]
) -> tuple[SceneLoadSet, ...]:
    """Decode NOV2's 15-entry four-file scene load table."""
    start = SCENE_LOAD_TABLE_CPU - NOV2_LOAD_ADDRESS
    raw = nov2[
        start : start + SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH
    ]
    if len(raw) != SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH:
        raise EngineSurfaceAuditError("NOV2 ends inside the scene load table")
    result = []
    for index in range(SCENE_LOAD_TABLE_RECORDS):
        begin = index * SCENE_LOAD_TABLE_WIDTH
        ids = tuple(raw[begin : begin + SCENE_LOAD_TABLE_WIDTH])
        names = tuple(
            (
                tuple(file.name for file in files_by_id.get(file_id, ()))
                if file_id not in (0, 0xFF)
                else ()
            )
            for file_id in ids
        )
        result.append(SceneLoadSet(index, ids, names))
    return tuple(result)


def _compose_program_overlay(
    scene: SceneLoadSet,
    files_by_id: dict[int, tuple[FdsFile, ...]],
) -> tuple[bytes, tuple[str, ...], tuple[str, ...]] | None:
    """Compose the `$A200` program RAM produced by one scene load list."""
    size = NOV3_LOAD_ADDRESS - OVERLAY_LOAD_ADDRESS
    memory = bytearray(size)
    owners = [""] * size
    programs: list[str] = []
    for file_id in scene.ids:
        if file_id in (0, 0xFF):
            continue
        for file in files_by_id.get(file_id, ()):
            if file.kind != 0 or file.load_address != OVERLAY_LOAD_ADDRESS:
                continue
            if file.size > size:
                raise EngineSurfaceAuditError(
                    f"{file.name}: overlay crosses NOV3"
                )
            programs.append(file.name)
            memory[: file.size] = file.data
            owners[: file.size] = [file.name] * file.size
    if not programs:
        return None
    return bytes(memory), tuple(owners), tuple(programs)


def _graphics_inventory(
    images: dict[str, FdsImage],
) -> tuple[GraphicsComponent, ...]:
    """Return and validate every recovered gameplay CHR component."""
    result = []
    for image_name, image in images.items():
        for side in image.sides:
            for file in side.files:
                if file.name.startswith("BG"):
                    role, low, high = "background", 0x1000, 0x2000
                elif file.name.startswith(("OB", "OBJ")):
                    role, low, high = "object", 0x0000, 0x1000
                else:
                    continue
                end = file.load_address + file.size
                if (
                    file.kind != 1
                    or file.size % 16
                    or not low <= file.load_address < end <= high
                ):
                    raise EngineSurfaceAuditError(
                        f"{file.name}: invalid {role} CHR"
                    )
                result.append(
                    GraphicsComponent(
                        image_name,
                        side.index,
                        file.name,
                        file.file_id,
                        role,
                        file.load_address,
                        end,
                        file.size,
                        file.size // 16,
                    )
                )
    by_id: defaultdict[int, list[str]] = defaultdict(list)
    for component in result:
        by_id[component.file_id].append(component.role)
    invalid_pair = any(
        sorted(roles) != ["background", "object"] for roles in by_id.values()
    )
    if not result or invalid_pair:
        raise EngineSurfaceAuditError(
            "graphics file IDs are not object/background pairs"
        )
    return tuple(result)


def _range_owner(
    owners: tuple[str, ...], start: int, end: int
) -> tuple[str, bool]:
    """Resolve ownership of one composed table range."""
    if start == end:
        return "", False
    names = set(
        owners[start - OVERLAY_LOAD_ADDRESS : end - OVERLAY_LOAD_ADDRESS]
    ) - {""}
    if len(names) != 1:
        raise EngineSurfaceAuditError(
            f"table range ${start:04X}-${end:04X} has owners {sorted(names)}"
        )
    return next(iter(names)), True


def _scene_report(
    scene: SceneLoadSet,
    composed: tuple[bytes, tuple[str, ...], tuple[str, ...]],
) -> dict[str, object]:
    """Parse the recovered gameplay structures in one composed scene."""
    data, owners, programs = composed
    placement = _read_word(data, 0x00)
    actor = _read_word(data, 0x02)
    metasprite = _read_word(data, 0x04)
    palette = _read_word(data, 0x08)
    hotspot = _read_word(data, 0x0C)
    hotspot_end = _read_word(data, 0x14)
    maps = _read_word(data, 0x1E)
    actor_end = _read_word(data, 0x2C)
    metasprites = parse_metasprite_definitions(data, metasprite, placement)
    placements = parse_static_placement_records(data, placement, actor)
    actors = parse_actor_spawn_records(data, actor, actor_end)
    hotspots = parse_hotspot_records(data, hotspot, hotspot_end)
    map_records = parse_background_map_records(data, maps, metasprite)
    rectangles = [
        rectangle for record in hotspots for rectangle in record.rectangles
    ]
    for record in hotspots:
        left_edges = [
            item for item in record.rectangles if item.boundary_side == "left"
        ]
        right_edges = [
            item for item in record.rectangles if item.boundary_side == "right"
        ]
        if (
            left_edges
            and right_edges
            and max(item.right for item in left_edges)
            >= min(item.left for item in right_edges)
        ):
            raise EngineSurfaceAuditError(
                f"{programs[-1]}: directional hotspot geometry inverted"
            )
    streams = [stream for record in map_records for stream in record.streams]

    def owned(start: int, end: int) -> dict[str, object]:
        """Return source ownership metadata for one table."""
        owner, nonempty = _range_owner(owners, start, end)
        return {
            "owner": owner,
            "inherited": bool(nonempty and owner != programs[-1]),
        }

    return {
        "scene_index": scene.index,
        "program_chain": list(programs),
        "active_program": programs[-1],
        "metasprites": {
            "start": metasprite,
            "end": placement,
            "definitions": len(metasprites),
            **owned(metasprite, placement),
        },
        "static_placements": {
            "start": placement,
            "end": actor,
            "records": len(placements),
            "placements": sum(len(record.placements) for record in placements),
            **owned(placement, actor),
        },
        "actor_spawns": {
            "start": actor,
            "end": actor_end,
            "records": len(actors),
            "actors": sum(len(record.actors) for record in actors),
            **owned(actor, actor_end),
        },
        "hotspots": {
            "start": hotspot,
            "end": hotspot_end,
            "records": len(hotspots),
            "rectangles": len(rectangles),
            "left_boundary_markers": sum(
                item.bottom_or_special == HOTSPOT_LEFT_BOUNDARY
                for item in rectangles
            ),
            "right_boundary_markers": sum(
                item.bottom_or_special == HOTSPOT_RIGHT_BOUNDARY
                for item in rectangles
            ),
            **owned(hotspot, hotspot_end),
        },
        "background_maps": {
            "start": maps,
            "end": metasprite,
            "records": len(map_records),
            "streams": len(streams),
            "maximum_tile": max(
                (tile for stream in streams for tile in stream.tiles),
                default=0,
            ),
            "shapes": sorted(
                {f"{stream.width}x{stream.height}" for stream in streams}
            ),
            **owned(maps, metasprite),
        },
        "palette_pointer": palette,
    }


def _source_control_counts(
    images: dict[str, FdsImage],
) -> tuple[dict[int, int], dict[str, int]]:
    """Count controls in scenario groups, dictionaries, and fixed-menu tables."""
    counts: Counter[int] = Counter()
    surfaces: Counter[str] = Counter()
    with tempfile.TemporaryDirectory(
        prefix="time_twist_control_audit_"
    ) as directory:
        root = Path(directory)
        for bank_name in KNOWN_SCENARIO_BANKS:
            image_name, side_index = SCENARIO_LOCATIONS[bank_name]
            data = (
                images[image_name].sides[side_index].find_file(bank_name).data
            )
            path = root / f"{bank_name}.bin"
            path.write_bytes(data)
            bank = parse_scenario_bank(
                path,
                minimum_dictionary_entries=source_dictionary_reference_floor(
                    bank_name, data
                ),
            )
            sources = (
                ("scenario", (record.symbols for record in bank.records)),
                ("dictionary", bank.dictionary),
            )
            for surface, records in sources:
                for record in records:
                    for symbol in record:
                        if symbol.kind is SymbolKind.CONTROL:
                            counts[symbol.value] += 1
                            surfaces[surface] += 1
            spec = FIXED_RECORD_TABLE_SPECS.get(bank_name)
            if spec is None:
                continue
            records, end = split_records(
                data, offset=spec.start, limit=len(spec.records)
            )
            if end != spec.end:
                raise EngineSurfaceAuditError(
                    f"{bank_name}: fixed-menu extent drift"
                )
            for record in records:
                for symbol in record:
                    if symbol.kind is SymbolKind.CONTROL:
                        counts[symbol.value] += 1
                        surfaces["fixed_menu"] += 1
    return {value: counts[value] for value in range(8)}, dict(surfaces)


def _reported_hotspot_marker_count(report: dict[str, object], key: str) -> int:
    """Return one validated hotspot-marker count from a scene report."""
    hotspots = report.get("hotspots")
    if not isinstance(hotspots, dict):
        raise EngineSurfaceAuditError("scene report lacks hotspot metadata")
    value = hotspots.get(key)
    if not isinstance(value, int):
        raise EngineSurfaceAuditError(
            f"scene hotspot count {key!r} is invalid"
        )
    return value


def audit_engine_surfaces(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Return a source-backed audit of the recovered gameplay-engine surfaces."""
    images = {
        "zenpen": FdsImage.from_bytes(zenpen.read_bytes()),
        "kouhen": FdsImage.from_bytes(kouhen.read_bytes()),
    }
    files_by_id = _files_by_id(images)
    nov2 = _nov2(images)
    scenes = _scene_load_sets(nov2, files_by_id)
    _expect_nov2_bytes(
        nov2,
        0x67F2,
        bytes.fromhex(
            "A9 08 85 31 B9 16 40 85 21 4A 05 21 4A 36 1D " "C6 31 D0 F1"
        ),
        "controller serial-bit decode",
    )
    _expect_nov2_bytes(
        nov2,
        0x7556,
        bytes.fromhex(
            "A5 1D C9 01 F0 0C C9 02 F0 1A A9 00 8D A4 07 4C 45 76 "
            "A5 34 C9 FE F0 F2 AD AA 07 20 48 77 20 8E 76 4C 8C 75 "
            "A5 34 C9 FD F0 E0 AD AB 07 20 48 77 20 8E 76 4C C2 75"
        ),
        "left/right hotspot boundary gate",
    )
    scene_reports = []
    for scene in scenes:
        composed = _compose_program_overlay(scene, files_by_id)
        if composed is not None:
            scene_reports.append(_scene_report(scene, composed))
    left_boundary_markers = sum(
        _reported_hotspot_marker_count(report, "left_boundary_markers")
        for report in scene_reports
    )
    right_boundary_markers = sum(
        _reported_hotspot_marker_count(report, "right_boundary_markers")
        for report in scene_reports
    )
    if (left_boundary_markers, right_boundary_markers) != (9, 8):
        raise EngineSurfaceAuditError(
            "retail hotspot boundary-marker inventory drifted: "
            f"{left_boundary_markers} left, {right_boundary_markers} right"
        )
    counts, surfaces = _source_control_counts(images)
    if counts[7]:
        raise EngineSurfaceAuditError(
            f"source unexpectedly contains {counts[7]} CTRL:7 tokens"
        )
    return {
        "graphics": {
            "format": "raw NES 2bpp CHR in FDS kind-1 character files",
            "gameplay_ppuctrl": "0x10",
            "object_pattern_table": "0x0000-0x0FFF",
            "background_pattern_table": "0x1000-0x1FFF",
            "components": [
                asdict(item) for item in _graphics_inventory(images)
            ],
            "scene_load_table_cpu": f"0x{SCENE_LOAD_TABLE_CPU:04X}",
            "scene_load_list_cpu": f"0x{SCENE_LOAD_LIST_CPU:04X}",
            "scene_load_sets": [asdict(scene) for scene in scenes],
        },
        "scene_structures": scene_reports,
        "runtime": {
            "oam_page": "0x0200",
            "oam_dma_page": 2,
            "actor_base": "0x04A0",
            "actor_stride": 16,
            "actor_metasprite_index_offset": 8,
            "palette_pointer_header": "0xA208",
            "palette_staging_ram": "0x0300-0x031F",
            "palette_update_flag": "0x30",
            "controller_direction_bits": {
                "right": "0x01",
                "left": "0x02",
                "down": "0x04",
                "up": "0x08",
            },
            "hotspot_boundaries": {
                "left": "0xFD",
                "right": "0xFE",
                "left_marker_count": left_boundary_markers,
                "right_marker_count": right_boundary_markers,
            },
        },
        "text_controls": _text_control_report(nov2),
        "control_7": {
            "handler_cpu": "0x8242",
            "fallthrough_cpu": "0x826E",
            "explicit_values": [1, 2, 4, 3, 5, 6],
            "fallthrough_values": [0, 7],
            "source_counts": counts,
            "counted_surfaces": surfaces,
            "source_ctrl7_occurrences": 0,
        },
    }


def main() -> None:
    """Audit two original Time Twist FDS images and print JSON or a compact summary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit_engine_surfaces(args.zenpen, args.kouhen)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(f"graphics components: {len(report['graphics']['components'])}")
    print(f"composed gameplay scenes: {len(report['scene_structures'])}")
    occurrences = report["control_7"]["source_ctrl7_occurrences"]
    print(f"CTRL:7 source occurrences: {occurrences}")
    controls = report["text_controls"]["controls"]
    semantic = ", ".join(
        f"CTRL:{value}={controls[str(value)]['name']}"
        for value in (1, 2, 3, 6)
    )
    print(f"semantic text controls: {semantic}")


if __name__ == "__main__":
    main()
