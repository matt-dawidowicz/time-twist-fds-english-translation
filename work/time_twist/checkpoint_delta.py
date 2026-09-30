"""Apply compact source-copy deltas used by validated release checkpoints."""

from __future__ import annotations

import hashlib

from .release_metadata import ReleaseBuildError

MAGIC = b"TTD1"


def _read_varint(data: bytes, position: int) -> tuple[int, int]:
    """Decode one unsigned LEB128-style integer from checkpoint data."""
    value = 0
    shift = 0
    while True:
        if position >= len(data):
            raise ReleaseBuildError("truncated checkpoint delta integer")
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7
        if shift > 63:
            raise ReleaseBuildError("checkpoint delta integer is too large")


def apply_checkpoint_delta(source: bytes, patch: bytes) -> bytes:
    """Apply a TTD1 copy/literal delta and verify source and target SHA-256."""
    if len(patch) < 68 or patch[:4] != MAGIC:
        raise ReleaseBuildError("invalid checkpoint delta header")
    expected_source = patch[4:36]
    expected_target = patch[36:68]
    if hashlib.sha256(source).digest() != expected_source:
        raise ReleaseBuildError("checkpoint delta source SHA-256 mismatch")

    output = bytearray()
    position = 68
    while position < len(patch):
        opcode = patch[position]
        position += 1
        if opcode == 0:
            offset, position = _read_varint(patch, position)
            length, position = _read_varint(patch, position)
            end = offset + length
            if end > len(source):
                raise ReleaseBuildError("checkpoint delta copy is out of range")
            output.extend(source[offset:end])
        elif opcode == 1:
            length, position = _read_varint(patch, position)
            end = position + length
            if end > len(patch):
                raise ReleaseBuildError("checkpoint delta literal is truncated")
            output.extend(patch[position:end])
            position = end
        else:
            raise ReleaseBuildError(
                f"unsupported checkpoint delta opcode: {opcode}"
            )

    result = bytes(output)
    if hashlib.sha256(result).digest() != expected_target:
        raise ReleaseBuildError("checkpoint delta target SHA-256 mismatch")
    return result
