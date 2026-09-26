"""Read Mesen 2.x .mss save states for deterministic runtime diagnostics.

Mesen save states contain a small outer header followed by a Serializer binary
map.  The Serializer payload may itself be zlib-compressed.  This module keeps
parsing deliberately generic so diagnostic tools can inspect emulator state
without depending on Mesen internals at runtime.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


class MesenStateError(ValueError):
    """Report a malformed or unsupported Mesen save state."""


@dataclass(frozen=True)
class MesenState:
    """Parsed Mesen save-state header and Serializer values."""

    emulator_version: int
    format_version: int
    console_type: int
    rom_name: str
    values: Mapping[str, bytes]

    def cpu_byte(self, address: int) -> int:
        """Read an NES CPU byte from serialized RAM for FDS diagnostics."""
        if not 0 <= address <= 0xFFFF:
            raise MesenStateError(f"CPU address is out of range: {address:#x}")

        if address < 0x2000:
            ram = self.values.get("memoryManager.internalRam")
            if ram is None or not ram:
                raise MesenStateError(
                    "save state has no memoryManager.internalRam value"
                )
            return ram[address % len(ram)]

        if 0x6000 <= address <= 0xDFFF:
            ram = self.values.get("mapper.workRam")
            if ram is None:
                raise MesenStateError("save state has no mapper.workRam value")
            offset = address - 0x6000
            if offset >= len(ram):
                raise MesenStateError(
                    f"mapper.workRam is too short for CPU ${address:04X}"
                )
            return ram[offset]

        raise MesenStateError(
            f"CPU ${address:04X} is not backed by serialized RAM this helper maps"
        )

    def cpu_word(self, address: int) -> int:
        """Read one little-endian NES CPU word from serialized RAM."""
        return self.cpu_byte(address) | (self.cpu_byte(address + 1) << 8)

    def scalar(self, key: str) -> int:
        """Decode one little-endian integer Serializer value."""
        raw = self.values.get(key)
        if raw is None:
            raise MesenStateError(f"save state has no {key!r} value")
        if not 1 <= len(raw) <= 8:
            raise MesenStateError(
                f"{key!r} has unsupported scalar size {len(raw)}"
            )
        return int.from_bytes(raw, "little")


def _u32(data: bytes, offset: int, label: str) -> tuple[int, int]:
    """Read one little-endian uint32 and return value plus next offset."""
    end = offset + 4
    if end > len(data):
        raise MesenStateError(f"save state is truncated while reading {label}")
    return struct.unpack_from("<I", data, offset)[0], end


def _serializer_payload(data: bytes) -> bytes:
    """Decode Mesen Serializer's compression envelope."""
    if not data:
        raise MesenStateError("save state has no Serializer payload")

    compressed = data[0]
    if compressed == 0:
        return data[1:]
    if compressed != 1:
        raise MesenStateError(
            f"unknown Serializer compression marker: {compressed}"
        )

    if len(data) < 9:
        raise MesenStateError("compressed Serializer header is truncated")
    expected_size, compressed_size = struct.unpack_from("<II", data, 1)
    end = 9 + compressed_size
    if end > len(data):
        raise MesenStateError("compressed Serializer payload is truncated")

    try:
        payload = zlib.decompress(data[9:end])
    except zlib.error as error:
        raise MesenStateError(
            f"Serializer zlib decompression failed: {error}"
        ) from error
    if len(payload) != expected_size:
        raise MesenStateError(
            "Serializer decompressed-size mismatch: "
            f"expected {expected_size}, got {len(payload)}"
        )
    return payload


def _parse_serializer(data: bytes) -> Mapping[str, bytes]:
    """Parse Mesen's NUL-key, uint32-size, raw-value Serializer map."""
    payload = _serializer_payload(data)
    values: dict[str, bytes] = {}
    offset = 0

    while offset < len(payload):
        terminator = payload.find(b"\x00", offset)
        if terminator < 0:
            raise MesenStateError("Serializer key is not NUL-terminated")
        key_bytes = payload[offset:terminator]
        if not key_bytes:
            raise MesenStateError("Serializer contains an empty key")
        try:
            key = key_bytes.decode("ascii")
        except UnicodeDecodeError as error:
            raise MesenStateError("Serializer key is not ASCII") from error

        offset = terminator + 1
        size, offset = _u32(payload, offset, f"size of {key}")
        end = offset + size
        if end > len(payload):
            raise MesenStateError(f"Serializer value {key!r} is truncated")
        if key in values:
            raise MesenStateError(f"Serializer contains duplicate key {key!r}")
        values[key] = payload[offset:end]
        offset = end

    return MappingProxyType(values)


def parse_mesen_state(data: bytes) -> MesenState:
    """Parse one Mesen 2.x binary save state."""
    if data[:3] != b"MSS":
        raise MesenStateError("file does not begin with the MSS signature")

    offset = 3
    emulator_version, offset = _u32(data, offset, "emulator version")
    format_version, offset = _u32(data, offset, "save-state format version")
    if format_version < 3:
        raise MesenStateError(
            f"unsupported Mesen save-state format {format_version}"
        )
    if format_version <= 3:
        end = offset + 40
        if end > len(data):
            raise MesenStateError("legacy ROM hash field is truncated")
        offset = end

    console_type, offset = _u32(data, offset, "console type")
    _, offset = _u32(data, offset, "frame-buffer size")
    _, offset = _u32(data, offset, "frame width")
    _, offset = _u32(data, offset, "frame height")
    _, offset = _u32(data, offset, "frame scale")
    video_size, offset = _u32(data, offset, "compressed frame size")
    video_end = offset + video_size
    if video_end > len(data):
        raise MesenStateError("compressed frame data is truncated")
    offset = video_end

    name_size, offset = _u32(data, offset, "ROM name length")
    name_end = offset + name_size
    if name_end > len(data):
        raise MesenStateError("ROM name is truncated")
    rom_name = data[offset:name_end].decode("utf-8", errors="replace")
    offset = name_end

    values = _parse_serializer(data[offset:])
    return MesenState(
        emulator_version=emulator_version,
        format_version=format_version,
        console_type=console_type,
        rom_name=rom_name,
        values=values,
    )


def read_mesen_state(path: Path) -> MesenState:
    """Read and parse one Mesen save-state file."""
    return parse_mesen_state(path.read_bytes())
