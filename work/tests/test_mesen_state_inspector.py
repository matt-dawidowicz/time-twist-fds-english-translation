from __future__ import annotations

import struct
import zlib

import pytest

from time_twist.mesen_state import MesenStateError, parse_mesen_state


def _serializer(entries: dict[str, bytes], *, compressed: bool) -> bytes:
    payload = bytearray()
    for key, value in entries.items():
        payload.extend(key.encode("ascii"))
        payload.append(0)
        payload.extend(struct.pack("<I", len(value)))
        payload.extend(value)

    if not compressed:
        return b"\x00" + bytes(payload)
    packed = zlib.compress(bytes(payload))
    return (
        b"\x01"
        + struct.pack("<II", len(payload), len(packed))
        + packed
    )


def _state(entries: dict[str, bytes], *, compressed: bool = True) -> bytes:
    video = zlib.compress(b"\x00\x00")
    rom_name = b"Time-Twist-test.fds"
    header = bytearray(b"MSS")
    header.extend(struct.pack("<II", 0x02020100, 4))
    header.extend(struct.pack("<I", 1))
    header.extend(struct.pack("<IIIII", 2, 1, 1, 100, len(video)))
    header.extend(video)
    header.extend(struct.pack("<I", len(rom_name)))
    header.extend(rom_name)
    header.extend(_serializer(entries, compressed=compressed))
    return bytes(header)


@pytest.mark.parametrize("compressed", [False, True])
def test_parse_mesen_state_and_ram_mapping(compressed: bool) -> None:
    internal_ram = bytearray(0x800)
    internal_ram[0x6A] = 0x20
    internal_ram[0x6B] = 0xA6
    internal_ram[0x6C] = 0x80

    work_ram = bytearray(0x8000)
    work_ram[0xA214 - 0x6000 : 0xA216 - 0x6000] = b"\x20\xA6"

    parsed = parse_mesen_state(
        _state(
            {
                "cpu.state.pc": b"\x02\x94",
                "memoryManager.internalRam": bytes(internal_ram),
                "mapper.workRam": bytes(work_ram),
            },
            compressed=compressed,
        )
    )

    assert parsed.format_version == 4
    assert parsed.rom_name == "Time-Twist-test.fds"
    assert parsed.scalar("cpu.state.pc") == 0x9402
    assert parsed.cpu_word(0x006A) == 0xA620
    assert parsed.cpu_byte(0x006C) == 0x80
    assert parsed.cpu_word(0xA214) == 0xA620


def test_rejects_bad_signature() -> None:
    with pytest.raises(MesenStateError, match="MSS signature"):
        parse_mesen_state(b"NOT A STATE")


def test_rejects_truncated_serializer() -> None:
    blob = _state({"cpu.state.pc": b"\x02\x94"})
    with pytest.raises(MesenStateError):
        parse_mesen_state(blob[:-3])
