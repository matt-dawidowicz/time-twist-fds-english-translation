#!/usr/bin/env python3
"""Inspect fixed-menu/runtime compatibility inside a Mesen .mss snapshot."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from time_twist import ui
from time_twist.english import render_english
from time_twist.entropy_codec import split_entropy_stream
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from time_twist.entropy_runtime import (
    BASE_RUNTIME_PATCHES,
    DYNAMIC_MENU_LAYOUT_PATCHES,
    ENTROPY_PREREQUISITE_PATCHES,
    ENTROPY_RUNTIME_PATCHES,
    LEADING_CONTROL_RESUME_PATCHES,
    PARENT_BACK_GUARD_PATCHES,
)
from time_twist.fds import FdsImage
from time_twist.mesen_state import MesenState, MesenStateError, read_mesen_state
from time_twist.scenario import DICTIONARY_POINTER_OFFSET
from time_twist.textcodec import SymbolKind

BANK_LOAD = 0xA200
NOV3_BOUNDARY = 0xD7B5
RECORDS_PER_PAGE = 32
STALE_TT3B_RECORD_ZERO = 0xB14B


def _resident_overlay(state: MesenState) -> bytes:
    """Return the resident A200-D7B4 scenario/NOV3-safe RAM window."""
    work_ram = state.values.get("mapper.workRam")
    if work_ram is None:
        raise MesenStateError("save state has no mapper.workRam value")
    start = BANK_LOAD - 0x6000
    end = NOV3_BOUNDARY - 0x6000
    if len(work_ram) < end:
        raise MesenStateError(
            f"mapper.workRam has {len(work_ram)} bytes; expected at least {end}"
        )
    return work_ram[start:end]


def _menu_banks() -> dict[str, tuple[int, tuple[str, ...]]]:
    """Return large fixed-menu bank names keyed to canonical record-zero bases."""
    banks: dict[str, tuple[int, tuple[str, ...]]] = {}
    suffix = "_FIXED_TEXT_START_OFFSET"
    for name in dir(ui):
        if not name.endswith(suffix):
            continue
        bank = name[: -len(suffix)]
        records_name = f"{bank}_FIXED_TEXT_RECORDS"
        if not hasattr(ui, records_name):
            continue
        start_offset = int(getattr(ui, name))
        labels = tuple(getattr(ui, records_name))
        banks[bank] = (BANK_LOAD + start_offset, labels)
    return banks


def _identify_bank(state: MesenState) -> tuple[str | None, tuple[str, ...]]:
    """Identify the resident fixed-menu bank from header $A214."""
    record_zero = state.cpu_word(0xA214)
    for bank, (expected, labels) in _menu_banks().items():
        if record_zero == expected:
            return bank, labels
    if record_zero == STALE_TT3B_RECORD_ZERO:
        return "TT3B(stale-pointer)", tuple(ui.TT3B_FIXED_TEXT_RECORDS)
    return None, ()


def _resident_menu_records(
    state: MesenState,
    *,
    record_count: int,
) -> tuple[tuple[object, ...], ...]:
    """Decode all resident menu records using $A214/$A21A page addressing."""
    data = _resident_overlay(state)
    record_zero = state.cpu_word(0xA214)
    page_table = state.cpu_word(0xA21A)
    page_count = math.ceil(record_count / RECORDS_PER_PAGE)

    starts = [record_zero]
    for page in range(1, page_count):
        starts.append(state.cpu_word(page_table + (page - 1) * 2))

    decoded: list[tuple[object, ...]] = []
    for page, start in enumerate(starts):
        count = min(
            RECORDS_PER_PAGE,
            record_count - page * RECORDS_PER_PAGE,
        )
        offset = start - BANK_LOAD
        if count <= 0 or not 0 <= offset < len(data):
            raise MesenStateError(
                f"menu page {page} start ${start:04X} is outside the overlay"
            )
        records, _, _ = split_entropy_stream(
            data[offset:],
            offset=0,
            limit=count,
        )
        decoded.extend(tuple(record) for record in records)

    if len(decoded) != record_count:
        raise MesenStateError(
            f"decoded {len(decoded)} menu records; expected {record_count}"
        )
    return tuple(decoded)


def _decode_resident_menu(
    state: MesenState,
    labels: tuple[str, ...],
) -> list[str]:
    """Expand and render the resident fixed-menu records."""
    data = _resident_overlay(state)
    records = _resident_menu_records(state, record_count=len(labels))
    required_dictionary_entries = max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )

    expansions = []
    if required_dictionary_entries:
        dictionary_address = int.from_bytes(
            data[
                DICTIONARY_POINTER_OFFSET : DICTIONARY_POINTER_OFFSET + 2
            ],
            "little",
        )
        dictionary_offset = dictionary_address - BANK_LOAD
        if not 0 <= dictionary_offset < len(data):
            raise MesenStateError(
                "resident entropy dictionary pointer is outside the overlay"
            )
        dictionary, _, _ = split_entropy_stream(
            data[dictionary_offset:],
            offset=0,
            limit=required_dictionary_entries,
        )
        expansions = expand_entropy_dictionary(dictionary)

    return [
        render_english(expand_entropy_record(record, expansions)).rstrip()
        for record in records
    ]


def _resident_nov2_patch_mismatches(
    state: MesenState,
) -> list[tuple[int, str]]:
    """Return canonical runtime patch sites that differ in resident NOV2."""
    work_ram = state.values.get("mapper.workRam")
    if work_ram is None:
        raise MesenStateError("save state has no mapper.workRam value")

    patches = (
        *LEADING_CONTROL_RESUME_PATCHES,
        *BASE_RUNTIME_PATCHES,
        *DYNAMIC_MENU_LAYOUT_PATCHES,
        *ENTROPY_PREREQUISITE_PATCHES,
        *ENTROPY_RUNTIME_PATCHES,
        *PARENT_BACK_GUARD_PATCHES,
    )
    mismatches: list[tuple[int, str]] = []
    for patch in patches:
        start = patch.file_offset
        end = start + len(patch.replacement)
        if end > len(work_ram) or work_ram[start:end] != patch.replacement:
            mismatches.append((patch.cpu_address, patch.label))
    return mismatches


def _find_bank(path: Path, bank: str) -> bytes:
    """Return one named FDS file payload from a candidate image."""
    image = FdsImage.read(path)
    matches = [
        entry.data
        for side in image.sides
        for entry in side.files
        if entry.name == bank
    ]
    if len(matches) != 1:
        raise MesenStateError(
            f"candidate contains {len(matches)} {bank} files; expected exactly one"
        )
    return matches[0]


def _candidate_record_zero(path: Path, bank: str) -> int:
    data = _find_bank(path, bank)
    return int.from_bytes(
        data[
            ui.FIXED_RECORD_TABLE_POINTER_OFFSET
            : ui.FIXED_RECORD_TABLE_POINTER_OFFSET + 2
        ],
        "little",
    )


def _word_or_none(state: MesenState, address: int) -> str:
    try:
        return f"${state.cpu_word(address):04X}"
    except MesenStateError:
        return "<unavailable>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", type=Path, help="Mesen .mss snapshot")
    parser.add_argument(
        "--fds",
        type=Path,
        help="optional exact candidate FDS used with the snapshot",
    )
    args = parser.parse_args()

    try:
        state = read_mesen_state(args.state)
        bank, labels = _identify_bank(state)

        print(f"ROM name: {state.rom_name}")
        print(
            "Mesen versions: "
            f"emulator=0x{state.emulator_version:08X}, "
            f"state-format={state.format_version}"
        )
        try:
            pc = state.scalar("cpu.pc")
            print(f"CPU PC: ${pc:04X}")
        except MesenStateError:
            print("CPU PC: <unavailable>")

        print("Resident scenario header:")
        for address, label in (
            (0xA210, "secondary table 1"),
            (0xA212, "secondary table 2"),
            (0xA214, "menu record zero"),
            (0xA216, "dictionary"),
            (0xA21A, "menu page table"),
            (0xA226, "scenario group zero"),
        ):
            print(f"  ${address:04X} {label}: {_word_or_none(state, address)}")

        print(f"Detected menu bank: {bank or '<unknown>'}")
        stream_pointer = state.cpu_word(0x006A)
        bit_mask = state.cpu_byte(0x006C)
        print(
            "Entropy runtime: "
            f"stream=${stream_pointer:04X}, bit-mask=${bit_mask:02X}"
        )

        runtime_mismatches = _resident_nov2_patch_mismatches(state)
        if runtime_mismatches:
            print(
                "Resident NOV2 runtime: "
                f"{len(runtime_mismatches)} canonical patch sites mismatch"
            )
            for address, label in runtime_mismatches:
                print(f"  ${address:04X}: {label}")
        else:
            print("Resident NOV2 runtime: all canonical patch sites match")

        decoded: list[str] = []
        if labels:
            decoded = _decode_resident_menu(state, labels)
            mismatches = [
                (index, actual, expected)
                for index, (actual, expected) in enumerate(
                    zip(decoded, labels, strict=True)
                )
                if actual != expected
            ]
            print(
                "Resident menu decode: "
                f"{len(labels) - len(mismatches)}/{len(labels)} labels match"
            )
            for index, actual, expected in mismatches[:12]:
                print(
                    f"  {index:03d}: {actual!r} != {expected!r}"
                )

        disk_pointer = None
        if args.fds is not None and bank and "(" not in bank:
            disk_pointer = _candidate_record_zero(args.fds, bank)
            expected_pointer = _menu_banks()[bank][0]
            status = "OK" if disk_pointer == expected_pointer else "WRONG"
            print(
                f"Candidate {bank} record-zero pointer: "
                f"${disk_pointer:04X} [{status}]"
            )

        print("Triage:")
        if bank is None:
            print(
                "  UNKNOWN BANK: resident $A214 does not match a canonical "
                "fixed-menu base. Inspect the overlay load boundary."
            )
        elif runtime_mismatches:
            print(
                "  STALE RUNTIME: the snapshot predates the current NOV2 "
                "renderer/entropy ABI. Do not use it as a compatibility test "
                "for a newer candidate after an overlay transition."
            )
            if decoded and decoded == list(labels):
                print(
                    "  The resident menu data itself is intact; corruption "
                    "after continuing is therefore a mixed-version runtime/"
                    "overlay problem, not damaged fixed-menu text."
                )
        elif decoded and decoded != list(labels):
            print(
                "  DATA FAILURE: the resident menu stream/dictionary does not "
                "decode to canonical labels."
            )
        elif decoded:
            print(
                "  DATA/RUNTIME OK: this snapshot is compatible at the checked "
                "surfaces; trace transient menu state and $9402 initialization."
            )
        else:
            print("  INCOMPLETE: no decodable fixed-menu bank was identified.")

        if disk_pointer is not None:
            expected_pointer = _menu_banks()[bank][0]
            if disk_pointer != expected_pointer:
                print(
                    "  CANDIDATE FAILURE: the supplied FDS has a noncanonical "
                    "record-zero pointer for the detected bank."
                )
    except (OSError, MesenStateError, ValueError) as error:
        parser.error(str(error))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
