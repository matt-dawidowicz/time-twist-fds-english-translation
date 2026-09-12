"""Audit recovered Time Twist gameplay graphics and control contracts.

The tool consumes maintainer-supplied original Zenpen and Kouhen FDS images and
never modifies them. It composes NOV2's real scene file-ID lists before parsing
same-address `$A200` overlays, so inherited high tables are audited exactly as
the game sees them at runtime.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from time_twist.fds import FdsFile, FdsImage
from time_twist.gameplay_graphics import (
    OVERLAY_LOAD_ADDRESS,
    parse_actor_spawn_records,
    parse_background_map_records,
    parse_hotspot_records,
    parse_metasprite_definitions,
    parse_static_placement_records,
)
from time_twist.project import KNOWN_SCENARIO_BANKS, source_dictionary_reference_floor
from time_twist.release_metadata import SCENARIO_LOCATIONS
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import SymbolKind, split_records
from time_twist.ui import FIXED_RECORD_TABLE_SPECS

NOV2_LOAD_ADDRESS = 0x6000
NOV3_LOAD_ADDRESS = 0xD7B5

PPUCTRL_GAMEPLAY_INIT_CPU = 0x619C
PPUCTRL_GAMEPLAY_INIT_BYTES = bytes.fromhex("A9 10 8D 00 20 85 FF")
OAM_DMA_CPU = 0x6154
OAM_DMA_BYTES = bytes.fromhex("A9 00 8D 03 20 A9 02 8D 14 40 60")
OAM_APPEND_CPU = 0x6851
OAM_APPEND_BYTES = bytes.fromhex(
    "A5 10 C9 40 90 01 60 84 3B 0A 0A A8 "
    "A5 11 99 00 02 A5 12 99 01 02 A5 13 99 02 02 "
    "A5 14 99 03 02 A4 3B E6 10 60"
)
PALETTE_SELECT_CPU = 0x89EB
PALETTE_SELECT_PREFIX = bytes.fromhex(
    "A5 86 D0 05 A5 87 D0 01 60 AD 08 A2 85 3C AD 09 A2 85 3D"
)
STATIC_PLACEMENT_CPU = 0x8AFC
STATIC_PLACEMENT_PREFIX = bytes.fromhex(
    "AD 00 A2 85 3E AD 01 A2 85 3F A5 85 D0 09 A9 00 "
    "8D 88 05 8D 89 05 60 C9 FF F0 FB 85 35 C6 35 F0 1A"
)
ACTOR_SPAWN_CPU = 0x8C88
ACTOR_SPAWN_PREFIX = bytes.fromhex(
    "A9 A0 85 3C A9 04 85 3D AD 02 A2 85 3E AD 03 A2 "
    "85 3F A6 88 D0 04 20 E0 6F 60 E0 FF F0 FB CA F0 0F"
)
METASPRITE_RENDER_CPU = 0x901D
METASPRITE_RENDER_PREFIX = bytes.fromhex(
    "AD 04 A2 85 3E AD 05 A2 85 3F A0 00 A5 31 D0 03 4C AD 90 "
    "C6 31 F0 11 B1 3E 18 65 3E 85 3E A9 00 65 3F 85 3F "
    "C6 31 D0 EF C8 B1 3E 29 0F 85 38 B1 3E 4A 4A 4A 4A 85 37"
)
HOTSPOT_LOOKUP_CPU = 0x768F
HOTSPOT_LOOKUP_PREFIX = bytes.fromhex(
    "A9 00 85 34 85 A4 A5 1F 29 88 F0 02 C6 34 A0 02 "
    "B1 3C 85 32 C8 B1 3C 4A 66 32 4A 66 32 4A 66 32"
)
BACKGROUND_MAP_SELECT_CPU = 0x9E29
BACKGROUND_MAP_SELECT_PREFIX = bytes.fromhex(
    "AD 1E A2 85 3C AD 1F A2 85 3D CE 95 07 F0 1D A0 00 "
    "B1 3C 85 3E C8 B1 3C 29 3F 85 3F A5 3C 18 65 3E"
)
BACKGROUND_MAP_DECODE_CPU = 0x9F84
BACKGROUND_MAP_DECODE_PREFIX = bytes.fromhex(
    "AD A2 07 D0 01 60 8D 93 A0 A2 00 AD A0 07 8D 91 A0 "
    "AD 9F 07 8D 92 A0 AD 9D 07 85 3C AD 9E 07 85 3D"
)
BACKGROUND_MAP_UPLOAD_CPU = 0xA049
BACKGROUND_MAP_UPLOAD_PREFIX = bytes.fromhex(
    "AD 91 A0 D0 01 60 8D 06 20 AD 92 A0 8D 06 20 AE 93 A0 "
    "CA A0 00 B9 94 A0 C9 FF D0 11 AD 18 9F F0 06 B9 94 A0"
)

SCENE_LOAD_TABLE_CPU = 0x7BA5
SCENE_LOAD_TABLE_RECORDS = 15
SCENE_LOAD_TABLE_WIDTH = 4
SCENE_LOAD_TABLE_COPY_CPU = 0x7A3D
SCENE_LOAD_LIST_CPU = 0x60DF

CONTROL_HANDLER_CPU = 0x8242
CONTROL_FALLTHROUGH_CPU = 0x826E
CONTROL_HANDLER_PREFIX = bytes.fromhex(
    "A5 3A "
    "C9 01 D0 03 4C EB 82 "
    "C9 02 D0 03 4C F0 82 "
    "C9 04 D0 03 4C F5 82 "
    "C9 03 D0 03 4C FA 82 "
    "C9 05 D0 03 4C 04 83 "
    "C9 06 D0 03 4C FF 82"
)

PLACEMENT_START_OFFSET = 0x00
ACTOR_START_OFFSET = 0x02
METASPRITE_START_OFFSET = 0x04
PALETTE_START_OFFSET = 0x08
HOTSPOT_START_OFFSET = 0x0C
HOTSPOT_END_OFFSET = 0x14
BACKGROUND_MAP_START_OFFSET = 0x1E
ACTOR_END_OFFSET = 0x2C


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


def _offset(cpu_address: int) -> int:
    """Convert one NOV2 CPU address to a file-relative offset."""
    offset = cpu_address - NOV2_LOAD_ADDRESS
    if offset < 0:
        raise EngineSurfaceAuditError(
            f"CPU ${cpu_address:04X} precedes NOV2 load ${NOV2_LOAD_ADDRESS:04X}"
        )
    return offset


def _read_word(data: bytes, offset: int) -> int:
    """Read one bounded little-endian word."""
    if offset < 0 or offset + 2 > len(data):
        raise EngineSurfaceAuditError(f"word offset 0x{offset:04X} is outside data")
    return int.from_bytes(data[offset : offset + 2], "little")


def _validate_nov2_bytes(
    nov2: bytes, cpu_address: int, expected: bytes, label: str
) -> None:
    """Verify one exact recovered NOV2 instruction sequence."""
    start = _offset(cpu_address)
    end = start + len(expected)
    if nov2[start:end] != expected:
        raise EngineSurfaceAuditError(
            f"NOV2 {label} changed at CPU ${cpu_address:04X}"
        )


def _graphics_role(name: str) -> str | None:
    """Return the broad role encoded by one graphics filename."""
    if name.startswith("BG"):
        return "background"
    if name.startswith("OBJ") or name.startswith("OB"):
        return "object"
    return None


def _inventory_graphics(images: dict[str, FdsImage]) -> tuple[GraphicsComponent, ...]:
    """Validate and return every OB/OBJ/BG raw CHR component."""
    components: list[GraphicsComponent] = []
    for image_name, image in images.items():
        for side in image.sides:
            for file in side.files:
                role = _graphics_role(file.name)
                if role is None:
                    continue
                if file.kind != 1 or file.size % 16 or file.load_address % 16:
                    raise EngineSurfaceAuditError(
                        f"{file.name}: graphics file is not aligned FDS kind-1 CHR"
                    )
                end = file.load_address + file.size
                low, high = (0x0000, 0x1000) if role == "object" else (0x1000, 0x2000)
                if not low <= file.load_address < end <= high:
                    raise EngineSurfaceAuditError(
                        f"{file.name}: {role} CHR escapes its pattern table"
                    )
                components.append(
                    GraphicsComponent(
                        image=image_name,
                        side=side.index,
                        name=file.name,
                        file_id=file.file_id,
                        role=role,
                        load_address=file.load_address,
                        end_address=end,
                        size=file.size,
                        tile_count=file.size // 16,
                    )
                )
    if not components:
        raise EngineSurfaceAuditError("no OB/OBJ/BG graphics components found")
    by_id: defaultdict[int, list[GraphicsComponent]] = defaultdict(list)
    for component in components:
        by_id[component.file_id].append(component)
    for file_id, group in by_id.items():
        if sorted(component.role for component in group) != ["background", "object"]:
            raise EngineSurfaceAuditError(
                f"graphics ID ${file_id:02X} is not one object/background pair"
            )
    return tuple(components)


def _files_by_id(images: dict[str, FdsImage]) -> dict[int, tuple[FdsFile, ...]]:
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


def _validate_runtime_contracts(nov2: bytes) -> None:
    """Guard the recovered PPU, OAM, scene-table, and map consumers."""
    guards = (
        (PPUCTRL_GAMEPLAY_INIT_CPU, PPUCTRL_GAMEPLAY_INIT_BYTES, "PPUCTRL init"),
        (OAM_DMA_CPU, OAM_DMA_BYTES, "OAM DMA"),
        (OAM_APPEND_CPU, OAM_APPEND_BYTES, "OAM append"),
        (PALETTE_SELECT_CPU, PALETTE_SELECT_PREFIX, "palette selector"),
        (STATIC_PLACEMENT_CPU, STATIC_PLACEMENT_PREFIX, "static placement"),
        (ACTOR_SPAWN_CPU, ACTOR_SPAWN_PREFIX, "actor spawn"),
        (METASPRITE_RENDER_CPU, METASPRITE_RENDER_PREFIX, "metasprite renderer"),
        (HOTSPOT_LOOKUP_CPU, HOTSPOT_LOOKUP_PREFIX, "hotspot lookup"),
        (BACKGROUND_MAP_SELECT_CPU, BACKGROUND_MAP_SELECT_PREFIX, "map selector"),
        (BACKGROUND_MAP_DECODE_CPU, BACKGROUND_MAP_DECODE_PREFIX, "map decoder"),
        (BACKGROUND_MAP_UPLOAD_CPU, BACKGROUND_MAP_UPLOAD_PREFIX, "map uploader"),
    )
    for address, expected, label in guards:
        _validate_nov2_bytes(nov2, address, expected, label)
    _validate_nov2_bytes(
        nov2,
        SCENE_LOAD_TABLE_COPY_CPU,
        bytes.fromhex(
            "BD A5 7B 8D DF 60 BD A6 7B 8D E0 60 "
            "BD A7 7B 8D E1 60 BD A8 7B 8D E2 60"
        ),
        "scene file-ID copy",
    )


def _scene_load_sets(
    nov2: bytes, files_by_id: dict[int, tuple[FdsFile, ...]]
) -> tuple[SceneLoadSet, ...]:
    """Decode NOV2's 15-entry four-file scene load table."""
    start = _offset(SCENE_LOAD_TABLE_CPU)
    total = SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH
    raw = nov2[start : start + total]
    if len(raw) != total:
        raise EngineSurfaceAuditError("NOV2 ends inside the scene load table")
    result: list[SceneLoadSet] = []
    for index in range(SCENE_LOAD_TABLE_RECORDS):
        begin = index * SCENE_LOAD_TABLE_WIDTH
        ids = tuple(raw[begin : begin + SCENE_LOAD_TABLE_WIDTH])
        files = tuple(
            tuple(file.name for file in files_by_id.get(file_id, ()))
            if file_id not in (0x00, 0xFF)
            else ()
            for file_id in ids
        )
        result.append(SceneLoadSet(index=index, ids=ids, files=files))
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
        if file_id in (0x00, 0xFF):
            continue
        for file in files_by_id.get(file_id, ()):
            if file.kind != 0 or file.load_address != OVERLAY_LOAD_ADDRESS:
                continue
            if file.size > size:
                raise EngineSurfaceAuditError(
                    f"{file.name}: program overlay crosses NOV3"
                )
            programs.append(file.name)
            memory[: file.size] = file.data
            owners[: file.size] = [file.name] * file.size
    if not programs:
        return None
    return bytes(memory), tuple(owners), tuple(programs)


def _range_owner(
    owners: tuple[str, ...],
    programs: tuple[str, ...],
    start_address: int,
    end_address: int,
    *,
    scene_index: int,
    label: str,
) -> tuple[str, bool]:
    """Return the sole source program owning one nonempty composed range."""
    if start_address == end_address:
        return "", False
    start = start_address - OVERLAY_LOAD_ADDRESS
    end = end_address - OVERLAY_LOAD_ADDRESS
    table_owners = set(owners[start:end]) - {""}
    if len(table_owners) != 1:
        raise EngineSurfaceAuditError(
            f"scene {scene_index}: {label} has owners {sorted(table_owners)}"
        )
    owner = next(iter(table_owners))
    return owner, owner != programs[-1]


def _scene_structure_report(
    scene: SceneLoadSet,
    composed: tuple[bytes, tuple[str, ...], tuple[str, ...]],
) -> dict[str, object]:
    """Parse every currently recovered non-text table in one composed scene."""
    data, owners, programs = composed
    placement_start = _read_word(data, PLACEMENT_START_OFFSET)
    actor_start = _read_word(data, ACTOR_START_OFFSET)
    metasprite_start = _read_word(data, METASPRITE_START_OFFSET)
    palette_start = _read_word(data, PALETTE_START_OFFSET)
    hotspot_start = _read_word(data, HOTSPOT_START_OFFSET)
    hotspot_end = _read_word(data, HOTSPOT_END_OFFSET)
    map_start = _read_word(data, BACKGROUND_MAP_START_OFFSET)
    actor_end = _read_word(data, ACTOR_END_OFFSET)

    metasprites = parse_metasprite_definitions(
        data, metasprite_start, placement_start
    )
    placements = parse_static_placement_records(data, placement_start, actor_start)
    actors = parse_actor_spawn_records(data, actor_start, actor_end)
    hotspots = parse_hotspot_records(data, hotspot_start, hotspot_end)
    maps = parse_background_map_records(data, map_start, metasprite_start)

    map_streams = tuple(stream for record in maps for stream in record.streams)
    visible_cells = tuple(
        cell
        for definition in metasprites
        for cell in definition.cells
        if cell.tile is not None
    )
    rectangles = tuple(
        rectangle for record in hotspots for rectangle in record.rectangles
    )
    actor_entries = tuple(actor for record in actors for actor in record.actors)
    placement_entries = tuple(
        placement for record in placements for placement in record.placements
    )

    def owner(start: int, end: int, label: str) -> tuple[str, bool]:
        return _range_owner(
            owners,
            programs,
            start,
            end,
            scene_index=scene.index,
            label=label,
        )

    metasprite_owner, metasprite_inherited = owner(
        metasprite_start, placement_start, "metasprites"
    )
    placement_owner, placement_inherited = owner(
        placement_start, actor_start, "static placements"
    )
    actor_owner, actor_inherited = owner(actor_start, actor_end, "actor spawns")
    hotspot_owner, hotspot_inherited = owner(
        hotspot_start, hotspot_end, "hotspots"
    )
    map_owner, map_inherited = owner(map_start, metasprite_start, "background maps")

    shapes = sorted({f"{stream.width}x{stream.height}" for stream in map_streams})
    maximum_tile = max(
        (tile for stream in map_streams for tile in stream.tiles),
        default=0,
    )
    duplicate_streams = sum(
        len(record.streams) - len({stream.address for stream in record.streams})
        for record in maps
    )
    return {
        "scene_index": scene.index,
        "program_chain": list(programs),
        "active_program": programs[-1],
        "metasprites": {
            "start": metasprite_start,
            "end": placement_start,
            "definitions": len(metasprites),
            "visible_cells": len(visible_cells),
            "transparent_cells": sum(
                cell.tile is None
                for definition in metasprites
                for cell in definition.cells
            ),
            "attributes": sorted(
                {
                    cell.attributes
                    for cell in visible_cells
                    if cell.attributes is not None
                }
            ),
            "owner": metasprite_owner,
            "inherited": metasprite_inherited,
        },
        "static_placements": {
            "start": placement_start,
            "end": actor_start,
            "records": len(placements),
            "placements": len(placement_entries),
            "maximum_metasprite_index": max(
                (placement.metasprite_index for placement in placement_entries),
                default=0,
            ),
            "owner": placement_owner,
            "inherited": placement_inherited,
        },
        "actor_spawns": {
            "start": actor_start,
            "end": actor_end,
            "records": len(actors),
            "actors": len(actor_entries),
            "actor_types": len({actor.actor_type for actor in actor_entries}),
            "sentinel_coordinates": sum(
                actor.x_high == 0xFF or actor.y == 0xFF for actor in actor_entries
            ),
            "owner": actor_owner,
            "inherited": actor_inherited,
        },
        "hotspots": {
            "start": hotspot_start,
            "end": hotspot_end,
            "records": len(hotspots),
            "rectangles": len(rectangles),
            "fd_markers": sum(
                rectangle.bottom_or_special == 0xFD for rectangle in rectangles
            ),
            "fe_markers": sum(
                rectangle.bottom_or_special == 0xFE for rectangle in rectangles
            ),
            "owner": hotspot_owner,
            "inherited": hotspot_inherited,
        },
        "background_maps": {
            "start": map_start,
            "end": metasprite_start,
            "records": len(maps),
            "streams": len(map_streams),
            "duplicate_streams": duplicate_streams,
            "empty_streams": sum(not stream.tiles for stream in map_streams),
            "full_32x16_streams": sum(
                stream.width == 32 and stream.height == 16 for stream in map_streams
            ),
            "maximum_tile": maximum_tile,
            "shapes": shapes,
            "owner": map_owner,
            "inherited": map_inherited,
        },
        "palette_pointer": palette_start,
    }


def _control_dispatch_contract(nov2: bytes) -> dict[str, object]:
    """Verify that control values 0 and 7 share the row-advance fallthrough."""
    _validate_nov2_bytes(
        nov2,
        CONTROL_HANDLER_CPU,
        CONTROL_HANDLER_PREFIX,
        "control dispatcher",
    )
    return {
        "handler_cpu": f"0x{CONTROL_HANDLER_CPU:04X}",
        "fallthrough_cpu": f"0x{CONTROL_FALLTHROUGH_CPU:04X}",
        "explicit_values": [1, 2, 4, 3, 5, 6],
        "fallthrough_values": [0, 7],
    }


def _source_control_counts(
    images: dict[str, FdsImage],
) -> tuple[dict[int, int], dict[str, int]]:
    """Count native controls in scenario groups, dictionaries, and menu tables."""
    counts: Counter[int] = Counter()
    surfaces: Counter[str] = Counter()
    with tempfile.TemporaryDirectory(prefix="time_twist_control_audit_") as directory:
        root = Path(directory)
        for bank_name in KNOWN_SCENARIO_BANKS:
            image_name, side_index = SCENARIO_LOCATIONS[bank_name]
            data = images[image_name].sides[side_index].find_file(bank_name).data
            path = root / f"{bank_name}.bin"
            path.write_bytes(data)
            bank = parse_scenario_bank(
                path,
                minimum_dictionary_entries=source_dictionary_reference_floor(
                    bank_name, data
                ),
            )
            for record in bank.records:
                for symbol in record.symbols:
                    if symbol.kind is SymbolKind.CONTROL:
                        counts[symbol.value] += 1
                        surfaces["scenario"] += 1
            for entry in bank.dictionary:
                for symbol in entry:
                    if symbol.kind is SymbolKind.CONTROL:
                        counts[symbol.value] += 1
                        surfaces["dictionary"] += 1

            spec = FIXED_RECORD_TABLE_SPECS.get(bank_name)
            if spec is None:
                continue
            records, end = split_records(data, offset=spec.start, limit=len(spec.records))
            if end != spec.end:
                raise EngineSurfaceAuditError(
                    f"{bank_name} fixed menu ended at 0x{end:04X}, "
                    f"expected 0x{spec.end:04X}"
                )
            for record in records:
                for symbol in record:
                    if symbol.kind is SymbolKind.CONTROL:
                        counts[symbol.value] += 1
                        surfaces["fixed_menu"] += 1
    return ({value: counts[value] for value in range(8)}, dict(surfaces))


def audit_engine_surfaces(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Return a JSON-serializable audit of the recovered engine surfaces."""
    images = {
        "zenpen": FdsImage.from_bytes(zenpen.read_bytes()),
        "kouhen": FdsImage.from_bytes(kouhen.read_bytes()),
    }
    graphics = _inventory_graphics(images)
    files_by_id = _files_by_id(images)
    nov2 = _nov2(images)
    _validate_runtime_contracts(nov2)
    scenes = _scene_load_sets(nov2, files_by_id)
    scene_reports = []
    for scene in scenes:
        composed = _compose_program_overlay(scene, files_by_id)
        if composed is not None:
            scene_reports.append(_scene_structure_report(scene, composed))

    control = _control_dispatch_contract(nov2)
    control_counts, control_surfaces = _source_control_counts(images)
    if control_counts[7] != 0:
        raise EngineSurfaceAuditError(
            f"source corpus unexpectedly contains {control_counts[7]} CTRL:7 tokens"
        )
    return {
        "graphics": {
            "format": "raw NES 2bpp CHR in FDS kind-1 character files",
            "gameplay_ppuctrl": "0x10",
            "object_pattern_table": "0x0000-0x0FFF",
            "background_pattern_table": "0x1000-0x1FFF",
            "components": [asdict(component) for component in graphics],
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
            "background_map_selector_cpu": f"0x{BACKGROUND_MAP_SELECT_CPU:04X}",
            "background_map_decoder_cpu": f"0x{BACKGROUND_MAP_DECODE_CPU:04X}",
            "background_map_uploader_cpu": f"0x{BACKGROUND_MAP_UPLOAD_CPU:04X}",
            "palette_pointer_header": "0xA208",
            "palette_staging_ram": "0x0300-0x031F",
            "palette_update_flag": "0x30",
        },
        "control_7": {
            **control,
            "source_counts": control_counts,
            "counted_surfaces": control_surfaces,
            "source_ctrl7_occurrences": 0,
        },
    }


def _format_range(item: dict[str, object]) -> str:
    """Return one report table's half-open addresses as an inclusive string."""
    start = int(item["start"])
    end = int(item["end"])
    return "empty" if start == end else f"${start:04X}-${end - 1:04X}"


def _print_human(report: dict[str, object]) -> None:
    """Print a compact maintainer-readable summary of one audit report."""
    graphics = report["graphics"]
    assert isinstance(graphics, dict)
    print("Graphics components")
    print("-------------------")
    components = graphics["components"]
    assert isinstance(components, list)
    for item in components:
        assert isinstance(item, dict)
        print(
            f"{item['name']:6s} id=${item['file_id']:02X} {item['role']:10s} "
            f"PPU ${item['load_address']:04X}-${item['end_address'] - 1:04X} "
            f"tiles={item['tile_count']}"
        )

    print()
    print("Scene file-ID table")
    print("-------------------")
    load_sets = graphics["scene_load_sets"]
    assert isinstance(load_sets, list)
    for item in load_sets:
        assert isinstance(item, dict)
        labels = []
        for file_id, names in zip(item["ids"], item["files"], strict=True):
            if file_id == 0x00:
                labels.append("00")
            elif file_id == 0xFF:
                labels.append("FF")
            else:
                labels.append(f"{file_id:02X}=" + "/".join(names))
        print(f"{item['index']:2d}: " + " | ".join(labels))

    scenes = report["scene_structures"]
    assert isinstance(scenes, list)
    print()
    print("Recovered `$A200` scene structures")
    print("---------------------------------")
    for scene in scenes:
        assert isinstance(scene, dict)
        meta = scene["metasprites"]
        placements = scene["static_placements"]
        actors = scene["actor_spawns"]
        maps = scene["background_maps"]
        hotspots = scene["hotspots"]
        assert isinstance(meta, dict)
        assert isinstance(placements, dict)
        assert isinstance(actors, dict)
        assert isinstance(maps, dict)
        assert isinstance(hotspots, dict)
        inherited = " inherited" if meta["inherited"] else ""
        print(
            f"scene {scene['scene_index']:2d} {scene['active_program']:4s}: "
            f"meta={meta['definitions']:2d}({meta['owner']}{inherited}) "
            f"place={placements['placements']:3d} actors={actors['actors']:3d} "
            f"maps={maps['records']:2d}/{maps['streams']:2d} "
            f"mapmax=${maps['maximum_tile']:02X} hotspots={hotspots['rectangles']:2d}"
        )

    control = report["control_7"]
    assert isinstance(control, dict)
    print()
    print("CTRL:7")
    print("------")
    print(
        f"dispatcher {control['handler_cpu']} -> {control['fallthrough_cpu']}; "
        f"fallthrough values {control['fallthrough_values']}"
    )
    print(f"source control counts: {control['source_counts']}")


def main() -> None:
    """Audit two original Time Twist FDS images and emit human or JSON output."""
    parser = argparse.ArgumentParser()
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    report = audit_engine_surfaces(args.zenpen, args.kouhen)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
