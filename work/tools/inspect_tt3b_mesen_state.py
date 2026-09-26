#!/usr/bin/env python3
"""Inspect the exact TT3B menu runtime state inside a Mesen .mss snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from time_twist import ui
from time_twist.english import render_english
from time_twist.entropy_codec import (
    split_entropy_stream,
    unpack_entropy_stream,
)
from time_twist.entropy_compression import (
    expand_entropy_dictionary,
    expand_entropy_record,
)
from time_twist.fds import FdsImage
from time_twist.mesen_state import MesenState, MesenStateError, read_mesen_state
from time_twist.scenario import DICTIONARY_POINTER_OFFSET
from time_twist.textcodec import SymbolKind

BANK_LOAD = 0xA200
NOV3_BOUNDARY = 0xD7B5
TT3B_RECORD_ZERO = 0xA620
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


def _decode_resident_tt3b_menu(state: MesenState) -> list[str]:
    """Decode the 21 TT3B labels from the resident runtime pointers."""
    data = _resident_overlay(state)
    record_zero = state.cpu_word(0xA214)
    start = record_zero - BANK_LOAD
    if not 0 <= start < len(data):
        raise MesenStateError(
            f"resident menu pointer ${record_zero:04X} is outside the overlay"
        )

    records = unpack_entropy_stream(
        data[start:],
        record_count=len(ui.TT3B_FIXED_TEXT_RECORDS),
    )
    required_dictionary_entries = max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )
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
    else:
        expansions = []

    return [
        render_english(expand_entropy_record(record, expansions)).rstrip()
        for record in records
    ]


def _find_tt3b_pointer(path: Path) -> int:
    """Read TT3B's on-disk record-zero pointer from a candidate FDS."""
    image = FdsImage.read(path)
    matches = [
        side.find_file("TT3B")
        for side in image.sides
        if any(entry.name == "TT3B" for entry in side.files)
    ]
    if len(matches) != 1:
        raise MesenStateError(
            f"candidate contains {len(matches)} TT3B files; expected exactly one"
        )
    data = matches[0].data
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
    parser = argparse.ArgumentParser(
        description=(
            "Cross-check TT3B's on-disk menu pointer, the resident Mesen "
            "Work RAM header, and entropy decoder state."
        )
    )
    parser.add_argument("state", type=Path, help="Mesen .mss snapshot")
    parser.add_argument(
        "--fds",
        type=Path,
        help="optional candidate FDS used with the snapshot",
    )
    args = parser.parse_args()

    try:
        state = read_mesen_state(args.state)
        print(f"ROM name: {state.rom_name}")
        print(
            "Mesen versions: "
            f"emulator=0x{state.emulator_version:08X}, "
            f"state-format={state.format_version}"
        )
        try:
            pc = state.scalar("cpu.state.pc")
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

        stream_pointer = state.cpu_word(0x006A)
        bit_mask = state.cpu_byte(0x006C)
        print(
            "Entropy runtime: "
            f"stream=${stream_pointer:04X}, bit-mask=${bit_mask:02X}"
        )

        if args.fds is not None:
            disk_pointer = _find_tt3b_pointer(args.fds)
            disk_status = (
                "OK"
                if disk_pointer == TT3B_RECORD_ZERO
                else "STALE/WRONG"
            )
            print(
                "Candidate TT3B disk pointer: "
                f"${disk_pointer:04X} [{disk_status}]"
            )

        resident_pointer = state.cpu_word(0xA214)
        print(
            "Resident TT3B pointer status: "
            + (
                "OK"
                if resident_pointer == TT3B_RECORD_ZERO
                else "STALE v28 pointer"
                if resident_pointer == STALE_TT3B_RECORD_ZERO
                else f"unexpected ${resident_pointer:04X}"
            )
        )

        try:
            labels = _decode_resident_tt3b_menu(state)
        except Exception as error:
            print(f"Resident TT3B menu decode: FAILED: {error}")
            labels = []

        if labels:
            expected = list(ui.TT3B_FIXED_TEXT_RECORDS)
            print("Resident TT3B menu labels:")
            for index, (actual, target) in enumerate(zip(labels, expected)):
                marker = "OK" if actual == target else "MISMATCH"
                print(f"  {index:02d}: {actual!r} [{marker}]")
            mismatch_count = sum(
                actual != target for actual, target in zip(labels, expected)
            )
            print(f"Menu decode mismatches: {mismatch_count}/{len(expected)}")

        print("Triage:")
        if args.fds is not None and _find_tt3b_pointer(args.fds) != TT3B_RECORD_ZERO:
            print(
                "  FAIL: the candidate itself lacks the v29 TT3B pointer repair."
            )
        elif resident_pointer == STALE_TT3B_RECORD_ZERO:
            print(
                "  FAIL: disk/source may be fixed, but this snapshot still has "
                "the stale TT3B overlay resident in Work RAM. Cold-boot the "
                "candidate and create a new native Mesen checkpoint."
            )
        elif labels and labels != list(ui.TT3B_FIXED_TEXT_RECORDS):
            print(
                "  FAIL: the resident header points to the repaired base, but "
                "the resident menu stream/dictionary does not decode to the "
                "canonical TT3B labels. Inspect FDS IPS persistence and the "
                "overlay load path."
            )
        elif labels:
            print(
                "  DATA OK: the TT3B menu bytes decode correctly in resident "
                "RAM. A visible corruption from this exact state is downstream "
                "of bank placement; trace menu selection/page setup at $9402 "
                "and entropy state $6A-$6C."
            )
        else:
            print(
                "  INCOMPLETE: capture the failing state and rerun this tool "
                "with the exact candidate FDS."
            )
    except (OSError, MesenStateError) as error:
        parser.error(str(error))
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
