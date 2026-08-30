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
    """Report an invalid archival FDS block, boundary, count, or capacity.

    Parsing and replacement routines raise this exception when bytes violate the
    block layout documented in ``docs/FORMATS.md`` or when a replacement would
    overrun a fixed payload.  Callers may treat it as a safe rejection: no image
    is serialized until the relevant structural check succeeds.
    """


@dataclass
class FdsFile:
    """One block-3 header and block-4 payload pair from an FDS side.

    Attributes:
        index: Zero-based order within the parsed side.
        header: Mutable 16-byte block-3 header, including its marker.
        data: Current immutable block-4 payload.
        header_offset: Original side offset of the block-3 marker.
        data_offset: Original side offset of the first payload byte.

    The offsets are diagnostic. Serialization rebuilds a side in file order,
    refreshes payload sizes, and does not attempt to preserve gaps between
    parsed file blocks because archival images omit physical FDS gaps.
    """

    index: int
    header: bytearray
    data: bytes
    header_offset: int
    data_offset: int

    @property
    def number(self) -> int:
        """Return the filesystem sequence number from the preserved header."""
        return self.header[1]

    @property
    def file_id(self) -> int:
        """Return the game-assigned identifier from the preserved header."""
        return self.header[2]

    @property
    def raw_name(self) -> bytes:
        """Return the exact eight-byte filename field, including padding."""
        return bytes(self.header[3:11])

    @property
    def name(self) -> str:
        """Decode the printable ASCII filename and remove trailing padding.

        Invalid ASCII bytes are replaced rather than raising an exception so a
        manifest can still identify a malformed or unusual file header. Use
        :attr:`raw_name` when exact filename bytes matter.
        """
        return self.raw_name.decode("ascii", "replace").rstrip("\0 ")

    @property
    def load_address(self) -> int:
        """Return the 16-bit little-endian CPU/PPU destination address."""
        return int.from_bytes(self.header[11:13], "little")

    @property
    def size(self) -> int:
        """Return the current payload size, not the stale header declaration."""
        return len(self.data)

    @property
    def kind(self) -> int:
        """Return the raw FDS file-kind byte.

        Conventionally 0 means program data, 1 means character data, and 2
        means nametable data. The parser preserves other values for diagnosis.
        """
        return self.header[15]

    def serialized_header(self) -> bytes:
        """Serialize the header with the current payload size.

        Returns:
            A new 16-byte header. The mutable :attr:`header` is not changed.

        Raises:
            OverflowError: If the payload is larger than the 16-bit FDS size
                field.
        """
        header = bytearray(self.header)
        header[13:15] = len(self.data).to_bytes(2, "little")
        return bytes(header)

    def manifest(self) -> dict[str, Any]:
        """Return exact and human-readable file metadata for audits.

        Returns:
            A JSON-serializable dictionary containing IDs, decoded and raw
            names, load address, current size, kind, and original offsets.
        """
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

    Attributes:
        index: Zero-based side position in the archival image.
        disk_info: Preserved 56-byte block-1 disk information.
        file_count_block: Mutable two-byte block-2 count record.
        files: Parsed block-3/block-4 pairs in source order.
        padding: Bytes after the last declared file.
        parsed_length: Original offset immediately after the last payload.

    ``padding`` retains every byte after the last parsed file. Rebuilding
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
    def parse(cls, raw: bytes, index: int) -> FdsSide:
        """Parse one fixed-size archival side.

        Args:
            raw: Exactly 65,500 side bytes without a 16-byte image header.
            index: Zero-based side number used in diagnostics.

        Returns:
            A side that preserves all block headers, payloads, and trailing
            padding.

        Raises:
            FdsFormatError: If the side size, block markers, declared payload
                boundary, or file count is inconsistent.
        """
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
        """Return the printable four-character game code."""
        return self.disk_info[16:20].decode("ascii", "replace").rstrip(" ")

    @property
    def version(self) -> int:
        """Return the unmodified disk version byte."""
        return self.disk_info[20]

    @property
    def side_number(self) -> int:
        """Return the game's own side number, which may differ from ``index``."""
        return self.disk_info[21]

    @property
    def disk_number(self) -> int:
        """Return the game-assigned disk number from block 1."""
        return self.disk_info[22]

    def find_file(self, name: str) -> FdsFile:
        """Find exactly one file by its decoded, unpadded name.

        Args:
            name: Case-sensitive filename such as ``"TT1B"`` or ``"NOV4"``.

        Returns:
            The mutable :class:`FdsFile` object owned by this side.

        Raises:
            KeyError: If no file or more than one file has the requested name.
        """
        matches = [entry for entry in self.files if entry.name == name]
        if len(matches) != 1:
            raise KeyError(
                f"side {self.index}: expected one file named {name!r}, "
                f"found {len(matches)}"
            )
        return matches[0]

    def to_bytes(self) -> bytes:
        """Rebuild this side at exactly :data:`SIDE_SIZE` bytes.

        Returns:
            Exactly :data:`SIDE_SIZE` rebuilt bytes.

        Raises:
            FdsFormatError: If current files no longer fit on the side or the
                file count does not fit its one-byte field.
            OverflowError: If a payload size does not fit its two-byte field.

        File count and payload-size fields are refreshed. All other disk-info
        and file-header bytes are preserved. Growth beyond the archival side
        capacity is rejected before a result is returned.

        The method has no side effects on the parsed object. It retains as much
        original padding as fits and appends deterministic zero padding only
        when necessary.
        """
        if len(self.files) > 0xFF:
            raise FdsFormatError(
                f"side {self.index}: file count {len(self.files)} exceeds "
                "the one-byte FDS limit"
            )
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
        """Return a JSON-serializable side layout and capacity report.

        ``used_bytes`` reflects current payloads and rebuilt headers;
        ``padding_bytes`` is the capacity still available to grow files.

        Returns:
            A dictionary containing side identity, layout offsets, capacity
            totals, and nested file manifests.
        """
        rebuilt_used = (
            DISK_INFO_SIZE
            + 2
            + sum(FILE_HEADER_SIZE + 1 + entry.size for entry in self.files)
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
    """Represent a complete raw or 16-byte-headered archival FDS image.

    Attributes:
        header: Empty bytes for a raw image or the preserved 16-byte header.
        sides: Parsed sides in image order.
        source_path: Optional path retained for manifests and diagnostics.
    """

    header: bytes
    sides: list[FdsSide]
    source_path: Path | None = None

    @classmethod
    def from_bytes(
        cls, raw: bytes, source_path: Path | None = None
    ) -> FdsImage:
        """Parse a complete archival image.

        Args:
            raw: Headered or raw image bytes.
            source_path: Optional provenance path; it is not opened.

        Returns:
            A parsed image with every side and file represented.

        Raises:
            FdsFormatError: If the image declares or contains zero sides, a
                header is truncated, its side count disagrees with the image
                size, a raw image is not side-aligned, or any side is malformed.
        """
        if raw[:4] == b"FDS\x1a":
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

        if side_count == 0:
            raise FdsFormatError("FDS image contains no sides")
        sides = [
            FdsSide.parse(
                side_data[index * SIDE_SIZE : (index + 1) * SIDE_SIZE], index
            )
            for index in range(side_count)
        ]
        return cls(header=header, sides=sides, source_path=source_path)

    @classmethod
    def read(cls, path: str | Path) -> FdsImage:
        """Read and parse an image while retaining its source path.

        Args:
            path: Headered or raw archival FDS file.

        Returns:
            The parsed image.

        Raises:
            OSError: If the path cannot be read.
            FdsFormatError: If the file is not a valid archival image.
        """
        source = Path(path)
        return cls.from_bytes(source.read_bytes(), source)

    def to_bytes(self) -> bytes:
        """Serialize all sides and refresh the optional header's side count.

        Returns:
            Complete image bytes using the original header convention.

        Raises:
            FdsFormatError: If any rebuilt side exceeds its capacity or the
                number of sides does not fit a header's one-byte count.

        The method does not modify :attr:`header` or any parsed side.
        """
        header = self.header
        if header:
            if len(self.sides) > 0xFF:
                raise FdsFormatError(
                    f"headered image side count {len(self.sides)} exceeds "
                    "the one-byte FDS limit"
                )
            mutable_header = bytearray(header)
            mutable_header[4] = len(self.sides)
            header = bytes(mutable_header)
        return header + b"".join(side.to_bytes() for side in self.sides)

    def write(self, path: str | Path) -> None:
        """Serialize the complete image to a filesystem path.

        Args:
            path: Destination file. Existing contents are replaced.

        Raises:
            OSError: If the destination cannot be written.
            FdsFormatError: If a side cannot be rebuilt safely.

        Side Effects:
            Creates or overwrites ``path``.
        """
        Path(path).write_bytes(self.to_bytes())

    def manifest(self) -> dict[str, Any]:
        """Return a JSON-serializable image, side, and file inventory.

        Returns:
            A dictionary containing source provenance, header status, side count,
            and nested side manifests.
        """
        return {
            "source": str(self.source_path) if self.source_path else None,
            "headered": bool(self.header),
            "side_count": len(self.sides),
            "sides": [side.manifest() for side in self.sides],
        }


def combine_images(images: list[FdsImage]) -> FdsImage:
    """Combine complete FDS images while preserving every side byte.

    Args:
        images: Complete images in the desired output order.

    Returns:
        A new image containing deep copies of every side. Mutating the result
        does not change an input image.

    Raises:
        ValueError: If ``images`` is empty.

    The result uses the first image's header convention. Side disk-info
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
