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
        raise EngineSurfaceAuditError(f"word offset 0x{offset:04X} is outside data")
    return int.from_bytes(data[offset : offset + 2], "little")


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


def _scene_load_sets(
    nov2: bytes, files_by_id: dict[int, tuple[FdsFile, ...]]
) -> tuple[SceneLoadSet, ...]:
    """Decode NOV2's 15-entry four-file scene load table."""
    start = SCENE_LOAD_TABLE_CPU - NOV2_LOAD_ADDRESS
    raw = nov2[start : start + SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH]
    if len(raw) != SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH:
        raise EngineSurfaceAuditError("NOV2 ends inside the scene load table")
    result = []
    for index in range(SCENE_LOAD_TABLE_RECORDS):
        begin = index * SCENE_LOAD_TABLE_WIDTH
        ids = tuple(raw[begin : begin + SCENE_LOAD_TABLE_WIDTH])
        names = tuple(
            tuple(file.name for file in files_by_id.get(file_id, ()))
            if file_id not in (0, 0xFF)
            else ()
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
                raise EngineSurfaceAuditError(f"{file.name}: overlay crosses NOV3")
            programs.append(file.name)
            memory[: file.size] = file.data
            owners[: file.size] = [file.name] * file.size
    if not programs:
        return None
    return bytes(memory), tuple(owners), tuple(programs)


def _graphics_inventory(images: dict[str, FdsImage]) -> tuple[GraphicsComponent, ...]:
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
                    raise EngineSurfaceAuditError(f"{file.name}: invalid {role} CHR")
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


def _range_owner(owners: tuple[str, ...], start: int, end: int) -> tuple[str, bool]:
    """Resolve ownership of one composed table range."""
    if start == end:
        return "", False
    names = (
        set(owners[start - OVERLAY_LOAD_ADDRESS : end - OVERLAY_LOAD_ADDRESS]) - {""}
    )
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
    rectangles = [rectangle for record in hotspots for rectangle in record.rectangles]
    streams = [stream for record in map_records for stream in record.streams]

    def owned(start: int, end: int) -> dict[str, object]:
        """Return source ownership metadata for one table."""
        owner, nonempty = _range_owner(owners, start, end)
        return {"owner": owner, "inherited": bool(nonempty and owner != programs[-1])}

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
            "fd_markers": sum(item.bottom_or_special == 0xFD for item in rectangles),
            "fe_markers": sum(item.bottom_or_special == 0xFE for item in rectangles),
            **owned(hotspot, hotspot_end),
        },
        "background_maps": {
            "start": maps,
            "end": metasprite,
            "records": len(map_records),
            "streams": len(streams),
            "maximum_tile": max(
                (tile for stream in streams for tile in stream.tiles), default=0
            ),
            "shapes": sorted({f"{stream.width}x{stream.height}" for stream in streams}),
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
                raise EngineSurfaceAuditError(f"{bank_name}: fixed-menu extent drift")
            for record in records:
                for symbol in record:
                    if symbol.kind is SymbolKind.CONTROL:
                        counts[symbol.value] += 1
                        surfaces["fixed_menu"] += 1
    return {value: counts[value] for value in range(8)}, dict(surfaces)


def audit_engine_surfaces(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Return a source-backed audit of the recovered gameplay-engine surfaces."""
    images = {
        "zenpen": FdsImage.from_bytes(zenpen.read_bytes()),
        "kouhen": FdsImage.from_bytes(kouhen.read_bytes()),
    }
    files_by_id = _files_by_id(images)
    nov2 = _nov2(images)
    scenes = _scene_load_sets(nov2, files_by_id)
    scene_reports = []
    for scene in scenes:
        composed = _compose_program_overlay(scene, files_by_id)
        if composed is not None:
            scene_reports.append(_scene_report(scene, composed))
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
            "components": [asdict(item) for item in _graphics_inventory(images)],
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
        },
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


if __name__ == "__main__":
    main()
