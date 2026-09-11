"""Static FDS load-path analysis for Time Twist runtime profiling.

Time Twist funnels runtime disk reads through the FDS BIOS ``LoadFiles``
routine at ``$E1F8``. This module finds literal call sites and decodes the
source-verified NOV2 table that supplies dynamic scenario/graphics file IDs.
It never modifies an image.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .fds import FdsFile, FdsImage, FdsSide

LOAD_FILES_ADDRESS = 0xE1F8
LOAD_FILES_OPCODE = bytes(
    (0x20, LOAD_FILES_ADDRESS & 0xFF, LOAD_FILES_ADDRESS >> 8)
)
MAX_LOAD_FILE_IDS = 20
NOV2_LOAD_ADDRESS = 0x6000
PRIMARY_LOAD_CALL = 0x6008
SECONDARY_LOAD_CALL = 0x606D
DYNAMIC_LOAD_TABLE = 0x7BA5
DYNAMIC_LOAD_TABLE_ENTRIES = 15
DYNAMIC_LOAD_TABLE_ENTRY_SIZE = 4

_PRIMARY_CALL_SIGNATURE = bytes.fromhex("20 F8 E1 CB 60 DF 60")
_SECONDARY_CALL_SIGNATURE = bytes.fromhex("20 F8 E1 CB 60 E4 60")
_DYNAMIC_COPY_ADDRESS = 0x7A3D
_DYNAMIC_COPY_SIGNATURE = bytes.fromhex(
    "BD A5 7B 8D DF 60 BD A6 7B 8D E0 60 "
    "BD A7 7B 8D E1 60 BD A8 7B 8D E2 60"
)


class LoadProfileError(ValueError):
    """Report a source revision that does not match the profiled layout."""


@dataclass(frozen=True)
class LoadFilesCall:
    """One literal ``JSR $E1F8`` call and its inline pointer arguments."""

    side: int
    file_name: str
    file_offset: int
    cpu_address: int
    disk_id_pointer: int
    file_list_pointer: int
    static_file_ids: tuple[int, ...] | None


@dataclass(frozen=True)
class LoadTarget:
    """One disk side that can satisfy a dynamic file-list entry."""

    game_code: str
    side: int
    files: tuple[str, ...]
    last_file_number: int
    prefix_bytes: int
    full_used_bytes: int

    @property
    def avoidable_archival_bytes(self) -> int:
        """Return declared bytes after the last required physical file."""
        return self.full_used_bytes - self.prefix_bytes


@dataclass(frozen=True)
class DynamicLoadEntry:
    """One four-byte row copied into NOV2's dynamic file-list buffer."""

    index: int
    raw_ids: tuple[int, int, int, int]
    boot_semantics: bool
    targets: tuple[LoadTarget, ...]


def _read_loaded(entry: FdsFile, address: int, size: int) -> bytes | None:
    offset = address - entry.load_address
    if offset < 0 or offset + size > len(entry.data):
        return None
    return entry.data[offset : offset + size]


def _file_ids(entry: FdsFile, address: int) -> tuple[int, ...] | None:
    offset = address - entry.load_address
    if offset < 0 or offset >= len(entry.data):
        return None
    result: list[int] = []
    for value in entry.data[offset : offset + MAX_LOAD_FILE_IDS + 1]:
        if value == 0xFF:
            return tuple(result)
        result.append(value)
        if len(result) == MAX_LOAD_FILE_IDS:
            return tuple(result)
    return None


def scan_load_files_calls(image: FdsImage) -> tuple[LoadFilesCall, ...]:
    """Find literal BIOS ``LoadFiles`` calls in every program file."""
    calls: list[LoadFilesCall] = []
    for side in image.sides:
        for entry in side.files:
            if entry.kind != 0:
                continue
            start = 0
            while True:
                offset = entry.data.find(LOAD_FILES_OPCODE, start)
                if offset < 0:
                    break
                args = entry.data[offset + 3 : offset + 7]
                if len(args) == 4:
                    disk_pointer = int.from_bytes(args[:2], "little")
                    list_pointer = int.from_bytes(args[2:], "little")
                    calls.append(
                        LoadFilesCall(
                            side=side.index,
                            file_name=entry.name,
                            file_offset=offset,
                            cpu_address=entry.load_address + offset,
                            disk_id_pointer=disk_pointer,
                            file_list_pointer=list_pointer,
                            static_file_ids=_file_ids(entry, list_pointer),
                        )
                    )
                start = offset + 1
    return tuple(calls)


def _source_nov2(zenpen: FdsImage) -> FdsFile:
    try:
        entry = zenpen.sides[0].find_file("NOV2")
    except (IndexError, KeyError) as error:
        raise LoadProfileError("Zenpen side A has no unique NOV2") from error
    if entry.load_address != NOV2_LOAD_ADDRESS:
        raise LoadProfileError("NOV2 load address changed")
    checks = (
        (PRIMARY_LOAD_CALL, _PRIMARY_CALL_SIGNATURE),
        (SECONDARY_LOAD_CALL, _SECONDARY_CALL_SIGNATURE),
        (_DYNAMIC_COPY_ADDRESS, _DYNAMIC_COPY_SIGNATURE),
    )
    for address, expected in checks:
        if _read_loaded(entry, address, len(expected)) != expected:
            raise LoadProfileError(
                f"NOV2 load-profile signature changed at ${address:04X}"
            )
    return entry


def _effective_ids(raw_ids: tuple[int, int, int, int]) -> tuple[int, ...]:
    result: list[int] = []
    for value in raw_ids:
        if value == 0xFF:
            break
        result.append(value)
    return tuple(result)


def _target(side: FdsSide, ids: tuple[int, ...]) -> LoadTarget | None:
    if not ids:
        return None
    requested = set(ids)
    if not requested <= {entry.file_id for entry in side.files}:
        return None
    matched = [entry for entry in side.files if entry.file_id in requested]
    last = max(matched, key=lambda entry: entry.index)
    return LoadTarget(
        game_code=side.game_code,
        side=side.index,
        files=tuple(entry.name for entry in matched),
        last_file_number=last.number,
        prefix_bytes=last.data_offset + len(last.data),
        full_used_bytes=side.parsed_length,
    )


def dynamic_load_entries(
    zenpen: FdsImage, kouhen: FdsImage
) -> tuple[DynamicLoadEntry, ...]:
    """Decode the source-verified 15-entry NOV2 dynamic load table."""
    nov2 = _source_nov2(zenpen)
    table_size = DYNAMIC_LOAD_TABLE_ENTRIES * DYNAMIC_LOAD_TABLE_ENTRY_SIZE
    table = _read_loaded(nov2, DYNAMIC_LOAD_TABLE, table_size)
    if table is None:
        raise LoadProfileError("NOV2 dynamic load table is truncated")

    sides = (*zenpen.sides, *kouhen.sides)
    result: list[DynamicLoadEntry] = []
    for index in range(DYNAMIC_LOAD_TABLE_ENTRIES):
        start = index * DYNAMIC_LOAD_TABLE_ENTRY_SIZE
        raw = table[start : start + DYNAMIC_LOAD_TABLE_ENTRY_SIZE]
        raw_ids = (raw[0], raw[1], raw[2], raw[3])
        ids = _effective_ids(raw_ids)
        result.append(
            DynamicLoadEntry(
                index=index,
                raw_ids=raw_ids,
                boot_semantics=raw_ids[0] == 0xFF,
                targets=tuple(
                    target
                    for side in sides
                    if (target := _target(side, ids)) is not None
                ),
            )
        )
    return tuple(result)


def format_load_profile(zenpen_path: Path, kouhen_path: Path) -> str:
    """Render direct calls and dynamic load-table targets as text."""
    zenpen = FdsImage.read(zenpen_path)
    kouhen = FdsImage.read(kouhen_path)
    lines = ["Direct BIOS LoadFiles call sites:"]
    for label, image in (("zenpen", zenpen), ("kouhen", kouhen)):
        for call in scan_load_files_calls(image):
            ids = call.static_file_ids
            ids_text = (
                "unresolved"
                if ids is None
                else " ".join(f"{value:02X}" for value in ids)
            )
            lines.append(
                f"  {label} side {call.side} {call.file_name} "
                f"CPU=${call.cpu_address:04X} "
                f"disk_ptr=${call.disk_id_pointer:04X} "
                f"list_ptr=${call.file_list_pointer:04X} ids=[{ids_text}]"
            )

    lines.append(f"Dynamic NOV2 list table @${DYNAMIC_LOAD_TABLE:04X}:")
    for item in dynamic_load_entries(zenpen, kouhen):
        raw_text = " ".join(f"{value:02X}" for value in item.raw_ids)
        suffix = " boot-semantics" if item.boot_semantics else ""
        lines.append(f"  {item.index:02d}: [{raw_text}]{suffix}")
        lines.extend(
            f"      {target.game_code} side {target.side}: "
            f"{', '.join(target.files)}; "
            f"last_file={target.last_file_number}; "
            f"prefix={target.prefix_bytes}; "
            f"used={target.full_used_bytes}; "
            f"after_last={target.avoidable_archival_bytes}"
            for target in item.targets
        )
    return "\n".join(lines)
