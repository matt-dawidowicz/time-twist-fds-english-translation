"""Audit the recovered Time Twist VM-to-audio command latch contract."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from time_twist.fds import FdsImage

NOV2_LOAD = 0x6000
NOV3_LOAD = 0xD7B5
AUDIO_LATCHES = tuple(range(0x07E0, 0x07E4))

NOV2_GUARDS = {
    0x717E: bytes.fromhex(
        "A0 00 B1 C5 29 0F AA C8 B1 C5 9D E0 07 85 D1 A9 02 4C"
    ),
    0x7192: bytes.fromhex("A0 00 B1 C5 29 0F AA C8 B1 C5 9D E0 07 A9 02 4C"),
}
NOV3_GUARDS = {
    0xD7B5: bytes.fromhex(
        "A9 FF 8D 17 40 A9 0F 8D 15 40 A5 DD F0 03 6C DC 00 "
        "20 04 D8 20 7E D8 20 3C DA A9 00 8D E3 07"
    ),
    0xD804: bytes.fromhex("AD E5 07 AC E0 07 30 60 4A B0 51 4E E0 07"),
    0xD87E: bytes.fromhex(
        "AD E7 07 29 70 D0 4B AD E2 07 D0 06 AD E8 07 D0 25 60"
    ),
    0xDA3C: bytes.fromhex("AD E3 07 30 F8 D0 06 AD E7 07 D0 EE 60 20 3E DB"),
}

# NMOS 6502 absolute-address opcodes relevant for a conservative static reference count.
ABSOLUTE_OPCODES = frozenset(
    bytes.fromhex(
        "0D 0E 19 1D 1E 20 2C 2D 2E 39 3D 3E 4C 4D 4E 59 5D 5E "
        "6D 6E 79 7D 7E 8C 8D 8E 99 9D AC AD AE B9 BC BD BE CC "
        "CD CE D9 DD DE EC ED EE F9 FD FE"
    )
)


class AudioLatchAuditError(ValueError):
    """Report drift in the recovered VM-to-audio contract."""


def _guard(
    data: bytes, load: int, address: int, expected: bytes, label: str
) -> None:
    """Verify one exact instruction prefix at an absolute CPU address."""
    offset = address - load
    if offset < 0 or data[offset : offset + len(expected)] != expected:
        raise AudioLatchAuditError(f"{label} changed at CPU ${address:04X}")


def _absolute_references(
    data: bytes, load: int, target: int
) -> tuple[int, ...]:
    """Return static absolute-address instruction references to one target."""
    low = target & 0xFF
    high = target >> 8
    return tuple(
        load + offset
        for offset in range(len(data) - 2)
        if data[offset] in ABSOLUTE_OPCODES
        and data[offset + 1] == low
        and data[offset + 2] == high
    )


def audit_audio_latches(zenpen: Path, kouhen: Path) -> dict[str, object]:
    """Audit NOV2 writers, NOV3 consumers, and overlay consumers of audio latches."""
    images = {
        "zenpen": FdsImage.from_bytes(zenpen.read_bytes()),
        "kouhen": FdsImage.from_bytes(kouhen.read_bytes()),
    }
    nov2 = images["zenpen"].sides[0].find_file("NOV2").data
    nov3 = images["zenpen"].sides[0].find_file("NOV3").data
    for address, expected in NOV2_GUARDS.items():
        _guard(nov2, NOV2_LOAD, address, expected, "NOV2 audio VM writer")
    for address, expected in NOV3_GUARDS.items():
        _guard(nov3, NOV3_LOAD, address, expected, "NOV3 audio consumer")

    resident_refs = {
        f"0x{target:04X}": [
            f"0x{address:04X}"
            for address in _absolute_references(nov3, NOV3_LOAD, target)
        ]
        for target in AUDIO_LATCHES
    }
    if (
        not resident_refs["0x07E0"]
        or not resident_refs["0x07E2"]
        or not resident_refs["0x07E3"]
    ):
        raise AudioLatchAuditError(
            "NOV3 lost a recovered audio-latch consumer"
        )

    overlay_refs: Counter[int] = Counter()
    overlay_files: dict[str, list[str]] = {
        f"0x{target:04X}": [] for target in AUDIO_LATCHES
    }
    for image_name, image in images.items():
        for side in image.sides:
            for file in side.files:
                if file.kind != 0 or file.load_address != 0xA200:
                    continue
                for target in AUDIO_LATCHES:
                    refs = _absolute_references(
                        file.data, file.load_address, target
                    )
                    if refs:
                        overlay_refs[target] += len(refs)
                        overlay_files[f"0x{target:04X}"].append(
                            f"{image_name}:side{side.index}:{file.name}"
                        )
    if not overlay_refs[0x07E1]:
        raise AudioLatchAuditError(
            "no overlay-local $07E1 audio consumers found"
        )

    return {
        "vm_writers": {
            "0x717E": "8x: write $07E0+low_nibble and mirror value to $D1",
            "0x7192": "9x: write $07E0+low_nibble",
        },
        "resident_audio_tick": "0xD7B5",
        "resident_consumers": resident_refs,
        "overlay_reference_counts": {
            f"0x{target:04X}": overlay_refs[target] for target in AUDIO_LATCHES
        },
        "overlay_consumer_files": overlay_files,
        "latch_roles": {
            "0x07E0": "resident APU/noise-SFX command latch",
            "0x07E1": "scene-overlay audio/SFX command latch",
            "0x07E2": "resident pulse-channel SFX command latch",
            "0x07E3": "resident music/FDS-audio command latch",
        },
    }


def main() -> None:
    """Audit two original Time Twist FDS images and print JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            audit_audio_latches(args.zenpen, args.kouhen),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
