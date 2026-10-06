"""Create deterministic BPS deltas from maintainer-supplied images."""

from __future__ import annotations

import binascii
from collections import defaultdict


def number(value: int) -> bytes:
    """Encode an unsigned integer with the BPS biased base-128 grammar."""
    result = bytearray()
    while True:
        byte = value & 127
        value >>= 7
        if not value:
            result.append(byte | 128)
            return bytes(result)
        result.append(byte)
        value -= 1


def create_bps(source: bytes, target: bytes, metadata: str = "") -> bytes:
    """Emit source-copy and changed-literal actions with all three BPS CRCs."""
    index: dict[bytes, list[int]] = defaultdict(list)
    for offset in range(len(source) - 7):
        index[source[offset : offset + 8]].append(offset)
    description = metadata.encode("utf-8")
    result = bytearray(b"BPS1")
    result += number(len(source)) + number(len(target))
    result += number(len(description)) + description
    pending = bytearray()
    position = source_relative = 0
    while position < len(target):
        candidates = index.get(target[position : position + 8], [])
        if len(candidates) > 128:
            candidates = (
                ([position] if position in candidates else [])
                + candidates[:64]
                + candidates[-64:]
            )
        best_length = best_offset = 0
        for offset in candidates:
            length = 8
            while (
                offset + length < len(source)
                and position + length < len(target)
                and source[offset + length] == target[position + length]
            ):
                length += 1
            if length > best_length:
                best_length, best_offset = length, offset
        if best_length < 8:
            pending.append(target[position])
            position += 1
            continue
        if pending:
            result += number(((len(pending) - 1) << 2) | 1) + pending
            pending.clear()
        if best_offset == position:
            result += number((best_length - 1) << 2)
        else:
            result += number(((best_length - 1) << 2) | 2)
            delta = best_offset - source_relative
            result += number((abs(delta) << 1) | (delta < 0))
            source_relative = best_offset + best_length
        position += best_length
    if pending:
        result += number(((len(pending) - 1) << 2) | 1) + pending
    result += binascii.crc32(source).to_bytes(4, "little")
    result += binascii.crc32(target).to_bytes(4, "little")
    result += binascii.crc32(result).to_bytes(4, "little")
    return bytes(result)
