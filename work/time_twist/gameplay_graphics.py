"""Parse recovered gameplay graphics and scene-data structures.

Time Twist loads a scenario/program overlay at CPU ``$A200`` and stores several
scene tables behind absolute pointers in that overlay's header. This module
models the structures whose binary formats have been recovered well enough to
round-trip or validate independently of a specific Japanese source image.

It deliberately does not assign narrative meaning to unresolved state/script
fields. Pure format recovery belongs here; source-revision guards and complete
FDS scene composition remain maintainer-audit responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass

OVERLAY_LOAD_ADDRESS = 0xA200


class GameplayGraphicsError(ValueError):
    """Report malformed recovered gameplay graphics or scene data."""


@dataclass(frozen=True)
class MetaspriteCell:
    """One row-major cell in a packed metasprite definition."""

    tile: int | None
    attributes: int | None


@dataclass(frozen=True)
class MetaspriteDefinition:
    """One length-prefixed rectangular metasprite definition."""

    address: int
    byte_length: int
    width: int
    height: int
    cells: tuple[MetaspriteCell, ...]


@dataclass(frozen=True)
class StaticPlacement:
    """One static metasprite reference positioned in eight-pixel cells."""

    metasprite_index: int
    x_cell: int
    y_cell: int


@dataclass(frozen=True)
class StaticPlacementRecord:
    """One count-prefixed static metasprite placement record."""

    placements: tuple[StaticPlacement, ...]


@dataclass(frozen=True)
class ActorSpawn:
    """One four-byte actor spawn descriptor."""

    actor_type: int
    x_low: int
    x_high: int
    y: int

    @property
    def x_raw(self) -> int:
        """Return the source little-endian horizontal coordinate word."""
        return self.x_low | (self.x_high << 8)


@dataclass(frozen=True)
class ActorSpawnRecord:
    """One count-prefixed actor spawn/layout record."""

    actors: tuple[ActorSpawn, ...]


@dataclass(frozen=True)
class HotspotRectangle:
    """One four-byte gameplay hotspot rectangle or special terminal entry."""

    left_and_flags: int
    top: int
    right: int
    bottom_or_special: int

    @property
    def left(self) -> int:
        """Return the seven-bit left bound used by the native lookup."""
        return self.left_and_flags & 0x7F

    @property
    def context_flag(self) -> bool:
        """Return whether the native high-bit context flag is set."""
        return bool(self.left_and_flags & 0x80)


@dataclass(frozen=True)
class HotspotRecord:
    """One count-prefixed group of gameplay hotspot rectangles."""

    rectangles: tuple[HotspotRectangle, ...]


@dataclass(frozen=True)
class BackgroundMapStream:
    """One decoded rectangular nametable tile-patch stream."""

    address: int
    left: int
    right: int
    start_row: int
    tiles: tuple[int, ...]
    encoded_end_address: int

    @property
    def width(self) -> int:
        """Return the decoded rectangle width in nametable cells."""
        return self.right - self.left + 1

    @property
    def height(self) -> int:
        """Return the decoded rectangle height in nametable rows."""
        return len(self.tiles) // self.width


@dataclass(frozen=True)
class BackgroundMapRecord:
    """One length-prefixed descriptor containing one or more map variants."""

    address: int
    byte_length: int
    streams: tuple[BackgroundMapStream, ...]



def _offset(address: int, *, load_address: int, size: int) -> int:
    """Convert one absolute overlay address to a validated file/RAM offset."""
    offset = address - load_address
    if offset < 0 or offset > size:
        raise GameplayGraphicsError(
            f"address ${address:04X} is outside loaded range "
            f"${load_address:04X}-${load_address + size:04X}"
        )
    return offset


def _validate_range(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int,
) -> tuple[int, int]:
    """Return validated offsets for one half-open absolute-address range."""
    start = _offset(start_address, load_address=load_address, size=len(data))
    end = _offset(end_address, load_address=load_address, size=len(data))
    if start > end:
        raise GameplayGraphicsError(
            f"range ${start_address:04X}-${end_address:04X} is reversed"
        )
    return start, end


def parse_metasprite_definitions(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[MetaspriteDefinition, ...]:
    """Parse the length-prefixed metasprite table selected through ``$A204``."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    definitions: list[MetaspriteDefinition] = []
    while cursor < limit:
        record_start = cursor
        byte_length = data[cursor]
        if byte_length < 3 or record_start + byte_length > limit:
            raise GameplayGraphicsError(
                f"invalid metasprite length {byte_length} at "
                f"${load_address + record_start:04X}"
            )
        dimensions = data[cursor + 1]
        width = dimensions >> 4
        height = dimensions & 0x0F
        if width == 0 or height == 0:
            raise GameplayGraphicsError(
                f"zero-sized metasprite at ${load_address + record_start:04X}"
            )
        cursor += 2
        cells: list[MetaspriteCell] = []
        for _ in range(width * height):
            if cursor >= record_start + byte_length:
                raise GameplayGraphicsError(
                    f"metasprite cell overruns record at "
                    f"${load_address + record_start:04X}"
                )
            tile = data[cursor]
            cursor += 1
            if tile == 0xFF:
                cells.append(MetaspriteCell(None, None))
                continue
            if cursor >= record_start + byte_length:
                raise GameplayGraphicsError(
                    f"metasprite attribute is truncated at "
                    f"${load_address + record_start:04X}"
                )
            cells.append(MetaspriteCell(tile, data[cursor]))
            cursor += 1
        if cursor != record_start + byte_length:
            raise GameplayGraphicsError(
                f"metasprite payload disagrees with record length at "
                f"${load_address + record_start:04X}"
            )
        definitions.append(
            MetaspriteDefinition(
                address=load_address + record_start,
                byte_length=byte_length,
                width=width,
                height=height,
                cells=tuple(cells),
            )
        )
    if cursor != limit:
        raise GameplayGraphicsError("metasprite table did not end exactly")
    return tuple(definitions)


def parse_static_placement_records(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[StaticPlacementRecord, ...]:
    """Parse count-prefixed ``(metasprite, x-cell, y-cell)`` placement records."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    records: list[StaticPlacementRecord] = []
    while cursor < limit:
        count = data[cursor]
        cursor += 1
        payload_end = cursor + count * 3
        if payload_end > limit:
            raise GameplayGraphicsError("static placement record crosses table end")
        placements = tuple(
            StaticPlacement(*data[offset : offset + 3])
            for offset in range(cursor, payload_end, 3)
        )
        records.append(StaticPlacementRecord(placements))
        cursor = payload_end
    return tuple(records)


def parse_actor_spawn_records(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[ActorSpawnRecord, ...]:
    """Parse count-prefixed four-byte actor spawn/layout records."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    records: list[ActorSpawnRecord] = []
    while cursor < limit:
        count = data[cursor]
        cursor += 1
        payload_end = cursor + count * 4
        if payload_end > limit:
            raise GameplayGraphicsError("actor spawn record crosses table end")
        actors = tuple(
            ActorSpawn(*data[offset : offset + 4])
            for offset in range(cursor, payload_end, 4)
        )
        records.append(ActorSpawnRecord(actors))
        cursor = payload_end
    return tuple(records)


def parse_hotspot_records(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[HotspotRecord, ...]:
    """Parse count-prefixed four-byte hotspot rectangle records."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    records: list[HotspotRecord] = []
    while cursor < limit:
        count = data[cursor]
        cursor += 1
        payload_end = cursor + count * 4
        if payload_end > limit:
            raise GameplayGraphicsError("hotspot record crosses table end")
        rectangles = tuple(
            HotspotRectangle(*data[offset : offset + 4])
            for offset in range(cursor, payload_end, 4)
        )
        records.append(HotspotRecord(rectangles))
        cursor = payload_end
    return tuple(records)


def decode_background_map_stream(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> BackgroundMapStream:
    """Decode one clipped gameplay nametable-patch stream through source ``$FF``."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    if cursor + 3 > limit:
        raise GameplayGraphicsError("background map stream header is truncated")
    left = data[cursor]
    right = data[cursor + 1]
    start_row = data[cursor + 2]
    if left > right or right >= 32:
        raise GameplayGraphicsError(
            f"invalid background map columns {left}-{right} at ${start_address:04X}"
        )
    cursor += 3
    tiles: list[int] = []
    while cursor < limit:
        value = data[cursor]
        cursor += 1
        if value == 0xFF:
            width = right - left + 1
            if len(tiles) % width:
                raise GameplayGraphicsError(
                    f"decoded map length {len(tiles)} is not divisible by width {width}"
                )
            if not tiles and (left, right, start_row) != (0, 0, 0):
                raise GameplayGraphicsError("noncanonical empty background map stream")
            return BackgroundMapStream(
                address=start_address,
                left=left,
                right=right,
                start_row=start_row,
                tiles=tuple(tiles),
                encoded_end_address=load_address + cursor,
            )
        if value < 0xC0:
            tiles.append(value)
            continue
        count = value & 0x3F
        if count == 0 or cursor >= limit:
            raise GameplayGraphicsError(
                f"invalid background RLE run at ${load_address + cursor - 1:04X}"
            )
        tile = data[cursor]
        cursor += 1
        tiles.extend((tile,) * count)
    raise GameplayGraphicsError("background map stream lacks an $FF terminator")


def parse_background_map_records(
    data: bytes,
    start_address: int,
    end_address: int,
    *,
    load_address: int = OVERLAY_LOAD_ADDRESS,
) -> tuple[BackgroundMapRecord, ...]:
    """Parse the `$A21E` length/type descriptors and every map variant."""
    cursor, limit = _validate_range(
        data, start_address, end_address, load_address=load_address
    )
    records: list[BackgroundMapRecord] = []
    while cursor < limit:
        record_start = cursor
        if cursor + 2 > limit:
            raise GameplayGraphicsError("background descriptor header is truncated")
        byte_length = data[cursor] + ((data[cursor + 1] & 0x3F) << 8)
        variant_count = data[cursor + 1] >> 6
        if byte_length < 2 or variant_count not in (1, 2, 3):
            raise GameplayGraphicsError(
                f"invalid background descriptor at ${load_address + cursor:04X}"
            )
        record_end = record_start + byte_length
        prefix_end = record_start + variant_count * 2
        if record_end > limit or prefix_end > record_end:
            raise GameplayGraphicsError("background descriptor crosses table end")

        stream_addresses = [load_address + prefix_end]
        stream_addresses.extend(
            int.from_bytes(
                data[
                    record_start + variant * 2 : record_start + variant * 2 + 2
                ],
                "little",
            )
            for variant in range(1, variant_count)
        )
        streams: list[BackgroundMapStream] = []
        for stream_address in stream_addresses:
            if not load_address + record_start <= stream_address < load_address + record_end:
                raise GameplayGraphicsError(
                    "background map pointer escapes its descriptor record"
                )
            streams.append(
                decode_background_map_stream(
                    data,
                    stream_address,
                    load_address + record_end,
                    load_address=load_address,
                )
            )
        records.append(
            BackgroundMapRecord(
                address=load_address + record_start,
                byte_length=byte_length,
                streams=tuple(streams),
            )
        )
        cursor = record_end
    if cursor != limit:
        raise GameplayGraphicsError("background map table did not end exactly")
    return tuple(records)
