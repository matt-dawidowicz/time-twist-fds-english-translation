"""Lossless parser and rebuilder for headered or raw FDS images.

The common archival FDS representation stores exactly 65,500 bytes per side
and omits physical gaps and CRCs.  This module preserves every parsed byte so
an unmodified image serializes byte-for-byte identically.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SIDE_SIZE = 65_500
FDS_HEADER_SIZE = 16
DISK_INFO_SIZE = 56
FILE_HEADER_SIZE = 16


class FdsFormatError(ValueError):
    """Raised when an image does not follow the archival FDS block layout."""


@dataclass
class FdsFile:
    """One block-3 header and block-4 payload pair from an FDS side.

    ``header_offset`` points to the block-3 marker in the original archival
    side. ``data_offset`` points to the first payload byte after block 4.
    These offsets are diagnostic; serialization rebuilds the side in file
    order and recalculates payload sizes.
    """

    index: int
    header: bytearray
    data: bytes
    header_offset: int
    data_offset: int

    @property
    def number(self) -> int:
        """File number used by the FDS filesystem."""

        return self.header[1]

    @property
    def file_id(self) -> int:
        """Game-assigned file identifier."""

        return self.header[2]

    @property
    def raw_name(self) -> bytes:
        """Return the exact eight-byte on-disk filename field."""

        return bytes(self.header[3:11])

    @property
    def name(self) -> str:
        """Return the printable FDS filename with trailing padding removed."""

        return self.raw_name.decode("ascii", "replace").rstrip("\0 ")

    @property
    def load_address(self) -> int:
        """Return the little-endian destination address from the header."""

        return int.from_bytes(self.header[11:13], "little")

    @property
    def size(self) -> int:
        """Current payload size, including any in-memory replacement."""

        return len(self.data)

    @property
    def kind(self) -> int:
        """FDS file kind byte (program, character, or nametable data)."""

        return self.header[15]

    def serialized_header(self) -> bytes:
        """Return the preserved header with its payload-size field refreshed."""

        header = bytearray(self.header)
        header[13:15] = len(self.data).to_bytes(2, "little")
        return bytes(header)

    def manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable description for audits and diffs."""

        return {
            "index": self.index,
            "number": self.number,
            "file_id": self.file_id,
            "name": self.name,
            "raw_name_hex": self.raw_name.hex().upper(),
            "load_address": self.load_address,
            "load_address_hex": f"0x{self.load_address:04X}",
            "size": self.size,
            "size_hex": f"0x{self.size:04X}",
            "kind": self.kind,
            "header_offset": self.header_offset,
            "data_offset": self.data_offset,
        }


@dataclass
class FdsSide:
    """One 65,500-byte archival FDS side.

    ``padding`` retains every byte after the last parsed file.  Rebuilding
    consumes that original padding first when a file grows and pads with zeroes
    only if the original padding is shorter than the remaining side capacity.
    """

    index: int
    disk_info: bytes
    file_count_block: bytearray
    files: list[FdsFile] = field(default_factory=list)
    padding: bytes = b""
    parsed_length: int = 0

    @classmethod
    def parse(cls, raw: bytes, index: int) -> "FdsSide":
        """Parse one side and validate every expected block marker/boundary."""

        if len(raw) != SIDE_SIZE:
            raise FdsFormatError(
                f"side {index}: expected {SIDE_SIZE} bytes, got {len(raw)}"
            )
        if raw[0] != 0x01:
            raise FdsFormatError(
                f"side {index}: expected block 1 at 0x0000, got 0x{raw[0]:02X}"
            )

        disk_info = raw[:DISK_INFO_SIZE]
        position = DISK_INFO_SIZE
        if raw[position] != 0x02:
            raise FdsFormatError(
                f"side {index}: expected block 2 at 0x{position:04X}, "
                f"got 0x{raw[position]:02X}"
            )
        file_count_block = bytearray(raw[position : position + 2])
        file_count = file_count_block[1]
        position += 2

        files: list[FdsFile] = []
        for file_index in range(file_count):
            if position + FILE_HEADER_SIZE > len(raw) or raw[position] != 0x03:
                actual = raw[position] if position < len(raw) else None
                shown = "EOF" if actual is None else f"0x{actual:02X}"
                raise FdsFormatError(
                    f"side {index} file {file_index}: expected block 3 at "
                    f"0x{position:04X}, got {shown}"
                )
            header_offset = position
            header = bytearray(raw[position : position + FILE_HEADER_SIZE])
            declared_size = int.from_bytes(header[13:15], "little")
            position += FILE_HEADER_SIZE

            if position >= len(raw) or raw[position] != 0x04:
                actual = raw[position] if position < len(raw) else None
                shown = "EOF" if actual is None else f"0x{actual:02X}"
                raise FdsFormatError(
                    f"side {index} file {file_index}: expected block 4 at "
                    f"0x{position:04X}, got {shown}"
                )
            data_offset = position + 1
            data_end = data_offset + declared_size
            if data_end > len(raw):
                raise FdsFormatError(
                    f"side {index} file {file_index}: data overruns side "
                    f"({data_end} > {len(raw)})"
                )
            files.append(
                FdsFile(
                    index=file_index,
                    header=header,
                    data=raw[data_offset:data_end],
                    header_offset=header_offset,
                    data_offset=data_offset,
                )
            )
            position = data_end

        return cls(
            index=index,
            disk_info=disk_info,
            file_count_block=file_count_block,
            files=files,
            padding=raw[position:],
            parsed_length=position,
        )

    @property
    def game_code(self) -> str:
        """Return the four-character game code from the disk-info block."""

        return self.disk_info[16:20].decode("ascii", "replace").rstrip(" ")

    @property
    def version(self) -> int:
        """Return the disk version byte."""

        return self.disk_info[20]

    @property
    def side_number(self) -> int:
        """Return the game's side number from disk metadata."""

        return self.disk_info[21]

    @property
    def disk_number(self) -> int:
        """Return the game's disk number from disk metadata."""

        return self.disk_info[22]

    def find_file(self, name: str) -> FdsFile:
        """Return the unique file named ``name`` or raise :class:`KeyError`."""

        matches = [entry for entry in self.files if entry.name == name]
        if len(matches) != 1:
            raise KeyError(
                f"side {self.index}: expected one file named {name!r}, "
                f"found {len(matches)}"
            )
        return matches[0]

    def to_bytes(self) -> bytes:
        """Rebuild this side at exactly :data:`SIDE_SIZE` bytes.

        File count and payload-size fields are refreshed.  All other disk-info
        and file-header bytes are preserved.  Growth beyond the archival side
        capacity is rejected before a result is returned.
        """

        count_block = bytearray(self.file_count_block)
        count_block[1] = len(self.files)
        output = bytearray(self.disk_info)
        output.extend(count_block)
        for entry in self.files:
            output.extend(entry.serialized_header())
            output.append(0x04)
            output.extend(entry.data)

        if len(output) > SIDE_SIZE:
            raise FdsFormatError(
                f"side {self.index}: rebuilt data is {len(output) - SIDE_SIZE} "
                "bytes larger than the archival side capacity"
            )

        required_padding = SIDE_SIZE - len(output)
        output.extend(self.padding[:required_padding])
        if len(output) < SIDE_SIZE:
            output.extend(b"\x00" * (SIDE_SIZE - len(output)))
        return bytes(output)

    def manifest(self) -> dict[str, Any]:
        """Return side layout, capacity, metadata, and per-file details."""

        rebuilt_used = DISK_INFO_SIZE + 2 + sum(
            FILE_HEADER_SIZE + 1 + entry.size for entry in self.files
        )
        return {
            "index": self.index,
            "game_code": self.game_code,
            "version": self.version,
            "side_number": self.side_number,
            "disk_number": self.disk_number,
            "file_count": len(self.files),
            "used_bytes": rebuilt_used,
            "padding_bytes": SIDE_SIZE - rebuilt_used,
            "files": [entry.manifest() for entry in self.files],
        }


@dataclass
class FdsImage:
    """A complete raw or 16-byte-headered archival FDS image."""

    header: bytes
    sides: list[FdsSide]
    source_path: Path | None = None

    @classmethod
    def from_bytes(cls, raw: bytes, source_path: Path | None = None) -> "FdsImage":
        """Parse all declared/raw sides and enforce exact image sizing."""

        if raw[:4] == b"FDS\x1A":
            if len(raw) < FDS_HEADER_SIZE:
                raise FdsFormatError("truncated 16-byte FDS header")
            header = raw[:FDS_HEADER_SIZE]
            side_count = header[4]
            side_data = raw[FDS_HEADER_SIZE:]
            expected = side_count * SIDE_SIZE
            if len(side_data) != expected:
                raise FdsFormatError(
                    f"header declares {side_count} sides ({expected} bytes), "
                    f"but image contains {len(side_data)} side bytes"
                )
        else:
            header = b""
            if len(raw) % SIDE_SIZE:
                raise FdsFormatError(
                    f"raw image size {len(raw)} is not a multiple of {SIDE_SIZE}"
                )
            side_count = len(raw) // SIDE_SIZE
            side_data = raw

        sides = [
            FdsSide.parse(
                side_data[index * SIDE_SIZE : (index + 1) * SIDE_SIZE], index
            )
            for index in range(side_count)
        ]
        return cls(header=header, sides=sides, source_path=source_path)

    @classmethod
    def read(cls, path: str | Path) -> "FdsImage":
        """Read and parse an image from ``path``."""

        source = Path(path)
        return cls.from_bytes(source.read_bytes(), source)

    def to_bytes(self) -> bytes:
        """Serialize all sides and refresh the optional header's side count."""

        header = self.header
        if header:
            mutable_header = bytearray(header)
            mutable_header[4] = len(self.sides)
            header = bytes(mutable_header)
        return header + b"".join(side.to_bytes() for side in self.sides)

    def write(self, path: str | Path) -> None:
        """Serialize the complete image to ``path``."""

        Path(path).write_bytes(self.to_bytes())

    def manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable image/side/file inventory."""

        return {
            "source": str(self.source_path) if self.source_path else None,
            "headered": bool(self.header),
            "side_count": len(self.sides),
            "sides": [side.manifest() for side in self.sides],
        }


def combine_images(images: list[FdsImage]) -> FdsImage:
    """Combine complete FDS images while preserving every side byte.

    The result uses the first image's header convention.  Side disk-info
    blocks are intentionally left untouched because multi-disk games use
    their own game and disk identifiers when validating an inserted side.
    """

    if not images:
        raise ValueError("at least one FDS image is required")

    sides: list[FdsSide] = []
    for image in images:
        for side in image.sides:
            cloned = copy.deepcopy(side)
            cloned.index = len(sides)
            sides.append(cloned)
    return FdsImage(header=images[0].header, sides=sides)
