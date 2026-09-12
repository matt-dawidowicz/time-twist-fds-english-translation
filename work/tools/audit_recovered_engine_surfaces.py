"""Audit recovered Time Twist graphics-load and control-dispatch contracts.

The tool consumes the original Zenpen and Kouhen FDS images supplied by the
maintainer. It does not modify them. Its purpose is to turn two formerly vague
reverse-engineering areas into repeatable evidence:

* ``OB*``/``OBJ*``/``BG*`` files are direct CHR-RAM payloads selected by
  NOV2's scene file-ID table; and
* native control value 7 reaches the same row-advance fallthrough as control 0,
  while the recovered scenario/menu corpus contains no control-7 tokens.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from time_twist.fds import FdsFile, FdsImage
from time_twist.project import KNOWN_SCENARIO_BANKS, source_dictionary_reference_floor
from time_twist.release_metadata import SCENARIO_LOCATIONS
from time_twist.scenario import parse_scenario_bank
from time_twist.textcodec import SymbolKind, split_records
from time_twist.ui import FIXED_RECORD_TABLE_SPECS

NOV2_LOAD_ADDRESS = 0x6000
PPUCTRL_GAMEPLAY_INIT_CPU = 0x619C
PPUCTRL_GAMEPLAY_INIT_BYTES = bytes.fromhex("A9 10 8D 00 20 85 FF")
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


class EngineSurfaceAuditError(ValueError):
    """Report source drift or a recovered-engine contract violation."""


@dataclass(frozen=True)
class GraphicsComponent:
    """Describe one recovered FDS object/background CHR component."""

    image: str
    side: int
    name: str
    file_id: int
    file_number: int
    kind: int
    role: str
    load_address: int
    end_address: int
    size: int
    tile_count: int
    first_tile: int
    end_tile_exclusive: int


@dataclass(frozen=True)
class SceneLoadSet:
    """Describe one four-byte NOV2 FDS file-ID list entry."""

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


def _graphics_role(name: str) -> str | None:
    """Return the recovered broad role encoded by one graphics filename."""
    if name.startswith("BG"):
        return "background"
    if name.startswith("OBJ") or name.startswith("OB"):
        return "object"
    return None


def _graphics_component(image: str, side: int, file: FdsFile) -> GraphicsComponent:
    """Validate and describe one FDS graphics payload as raw 2bpp CHR tiles."""
    role = _graphics_role(file.name)
    if role is None:
        raise EngineSurfaceAuditError(f"{file.name}: not a graphics-family file")
    if file.kind != 1:
        raise EngineSurfaceAuditError(
            f"{file.name}: expected FDS character-data kind 1, got {file.kind}"
        )
    if file.size % 16:
        raise EngineSurfaceAuditError(
            f"{file.name}: CHR payload size {file.size} is not a multiple of 16"
        )
    if file.load_address % 16:
        raise EngineSurfaceAuditError(
            f"{file.name}: PPU load ${file.load_address:04X} is not tile-aligned"
        )
    end = file.load_address + file.size
    if role == "object":
        low, high = 0x0000, 0x1000
    else:
        low, high = 0x1000, 0x2000
    if not low <= file.load_address < end <= high:
        raise EngineSurfaceAuditError(
            f"{file.name}: {role} CHR range ${file.load_address:04X}-${end - 1:04X} "
            f"escapes ${low:04X}-${high - 1:04X}"
        )
    return GraphicsComponent(
        image=image,
        side=side,
        name=file.name,
        file_id=file.file_id,
        file_number=file.number,
        kind=file.kind,
        role=role,
        load_address=file.load_address,
        end_address=end,
        size=file.size,
        tile_count=file.size // 16,
        first_tile=(file.load_address & 0x0FFF) // 16,
        end_tile_exclusive=(end & 0x0FFF) // 16 if end & 0x0FFF else 0x100,
    )


def _inventory_graphics(
    images: dict[str, FdsImage],
) -> tuple[GraphicsComponent, ...]:
    """Return all validated OB/OBJ/BG components from both source images."""
    components: list[GraphicsComponent] = []
    for image_name, image in images.items():
        for side in image.sides:
            for file in side.files:
                if _graphics_role(file.name) is not None:
                    components.append(
                        _graphics_component(image_name, side.index, file)
                    )
    if not components:
        raise EngineSurfaceAuditError("no OB/OBJ/BG graphics components found")
    return tuple(components)


def _id_map(images: dict[str, FdsImage]) -> dict[int, tuple[str, ...]]:
    """Map each FDS file ID to all filenames carrying that ID."""
    values: defaultdict[int, list[str]] = defaultdict(list)
    for image in images.values():
        for side in image.sides:
            for file in side.files:
                values[file.file_id].append(file.name)
    return {file_id: tuple(names) for file_id, names in values.items()}


def _validate_graphics_pairs(components: tuple[GraphicsComponent, ...]) -> None:
    """Require every graphics file ID to pair one object and one background file."""
    by_id: defaultdict[int, list[GraphicsComponent]] = defaultdict(list)
    for component in components:
        by_id[component.file_id].append(component)
    for file_id, group in sorted(by_id.items()):
        roles = sorted(component.role for component in group)
        if roles != ["background", "object"]:
            names = ", ".join(component.name for component in group)
            raise EngineSurfaceAuditError(
                f"graphics ID ${file_id:02X} is not one object/background pair: {names}"
            )


def _nov2(images: dict[str, FdsImage]) -> bytes:
    """Return the original Zenpen-side-0 NOV2 payload."""
    try:
        return images["zenpen"].sides[0].find_file("NOV2").data
    except (KeyError, IndexError) as error:
        raise EngineSurfaceAuditError("cannot locate Zenpen side-0 NOV2") from error


def _validate_gameplay_pattern_tables(nov2: bytes) -> None:
    """Verify gameplay PPUCTRL selects sprites at $0000 and backgrounds at $1000."""
    start = _offset(PPUCTRL_GAMEPLAY_INIT_CPU)
    end = start + len(PPUCTRL_GAMEPLAY_INIT_BYTES)
    if nov2[start:end] != PPUCTRL_GAMEPLAY_INIT_BYTES:
        raise EngineSurfaceAuditError(
            f"NOV2 gameplay PPUCTRL initialization changed at "
            f"${PPUCTRL_GAMEPLAY_INIT_CPU:04X}"
        )


def _scene_load_sets(
    nov2: bytes, id_map: dict[int, tuple[str, ...]]
) -> tuple[SceneLoadSet, ...]:
    """Decode NOV2's 15-entry, four-file scene load table."""
    start = _offset(SCENE_LOAD_TABLE_CPU)
    total = SCENE_LOAD_TABLE_RECORDS * SCENE_LOAD_TABLE_WIDTH
    raw = nov2[start : start + total]
    if len(raw) != total:
        raise EngineSurfaceAuditError("NOV2 ends inside the scene load table")
    result: list[SceneLoadSet] = []
    for index in range(SCENE_LOAD_TABLE_RECORDS):
        chunk = tuple(
            raw[
                index * SCENE_LOAD_TABLE_WIDTH : (index + 1)
                * SCENE_LOAD_TABLE_WIDTH
            ]
        )
        files = tuple(
            () if value in (0x00, 0xFF) else id_map.get(value, ())
            for value in chunk
        )
        result.append(SceneLoadSet(index=index, ids=chunk, files=files))
    return tuple(result)


def _validate_scene_table_consumers(nov2: bytes) -> None:
    """Verify the source copy loop feeding the BIOS file-list buffer."""
    expected = bytes.fromhex(
        "BD A5 7B 8D DF 60 "
        "BD A6 7B 8D E0 60 "
        "BD A7 7B 8D E1 60 "
        "BD A8 7B 8D E2 60"
    )
    start = _offset(SCENE_LOAD_TABLE_COPY_CPU)
    if nov2[start : start + len(expected)] != expected:
        raise EngineSurfaceAuditError(
            f"NOV2 scene-load table copy changed at ${SCENE_LOAD_TABLE_COPY_CPU:04X}"
        )


def _control_dispatch_contract(nov2: bytes) -> dict[str, object]:
    """Verify that controls 0 and 7 share NOV2's row-advance fallthrough."""
    start = _offset(CONTROL_HANDLER_CPU)
    end = start + len(CONTROL_HANDLER_PREFIX)
    if nov2[start:end] != CONTROL_HANDLER_PREFIX:
        raise EngineSurfaceAuditError(
            f"NOV2 control dispatcher changed at ${CONTROL_HANDLER_CPU:04X}"
        )
    compared = (1, 2, 4, 3, 5, 6)
    return {
        "handler_cpu": f"0x{CONTROL_HANDLER_CPU:04X}",
        "fallthrough_cpu": f"0x{CONTROL_FALLTHROUGH_CPU:04X}",
        "explicit_values": list(compared),
        "fallthrough_values": [0, 7],
        "verified_effect": "shared row-advance branch",
    }


def _source_control_counts(
    images: dict[str, FdsImage],
) -> tuple[dict[int, int], dict[str, int]]:
    """Count native controls in scenario groups/dictionaries and menu tables."""
    counts: Counter[int] = Counter()
    surfaces: Counter[str] = Counter()
    with tempfile.TemporaryDirectory(
        prefix="time_twist_control_audit_"
    ) as directory:
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
            records, end = split_records(
                data, offset=spec.start, limit=len(spec.records)
            )
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
    """Return a JSON-serializable report of the recovered engine surfaces."""
    images = {
        "zenpen": FdsImage.from_bytes(zenpen.read_bytes()),
        "kouhen": FdsImage.from_bytes(kouhen.read_bytes()),
    }
    components = _inventory_graphics(images)
    _validate_graphics_pairs(components)
    nov2 = _nov2(images)
    _validate_gameplay_pattern_tables(nov2)
    _validate_scene_table_consumers(nov2)
    id_map = _id_map(images)
    load_sets = _scene_load_sets(nov2, id_map)
    control_dispatch = _control_dispatch_contract(nov2)
    control_counts, control_surfaces = _source_control_counts(images)
    if control_counts[7] != 0:
        raise EngineSurfaceAuditError(
            f"recovered source corpus unexpectedly contains {control_counts[7]} "
            "CTRL:7 tokens"
        )

    return {
        "graphics": {
            "format": "raw NES 2bpp CHR in FDS kind-1 character files",
            "gameplay_ppuctrl": "0x10",
            "object_pattern_table": "0x0000-0x0FFF",
            "background_pattern_table": "0x1000-0x1FFF",
            "components": [asdict(component) for component in components],
            "scene_load_table_cpu": f"0x{SCENE_LOAD_TABLE_CPU:04X}",
            "scene_load_list_cpu": f"0x{SCENE_LOAD_LIST_CPU:04X}",
            "scene_load_sets": [asdict(load_set) for load_set in load_sets],
        },
        "control_7": {
            **control_dispatch,
            "source_counts": control_counts,
            "counted_surfaces": control_surfaces,
            "source_ctrl7_occurrences": 0,
            "production_policy": (
                "runtime alias of CTRL:0 is verified; production should still not "
                "invent CTRL:7 because the recovered scenario/menu corpus never "
                "uses it"
            ),
        },
    }


def _print_human(report: dict[str, object]) -> None:
    """Print a compact maintainer-readable summary of one audit report."""
    graphics = report["graphics"]
    assert isinstance(graphics, dict)
    components = graphics["components"]
    assert isinstance(components, list)
    print("Graphics components")
    print("-------------------")
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
    scene_load_sets = graphics["scene_load_sets"]
    assert isinstance(scene_load_sets, list)
    for item in scene_load_sets:
        assert isinstance(item, dict)
        labels: list[str] = []
        for value, names in zip(item["ids"], item["files"], strict=True):
            if value == 0x00:
                labels.append("00")
            elif value == 0xFF:
                labels.append("FF")
            else:
                labels.append(f"{value:02X}=" + "/".join(names))
        print(f"{item['index']:2d}: " + " | ".join(labels))
    control = report["control_7"]
    assert isinstance(control, dict)
    print()
    print("CTRL:7")
    print("------")
    print(
        f"dispatcher {control['handler_cpu']} -> "
        f"fallthrough {control['fallthrough_cpu']}; "
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
