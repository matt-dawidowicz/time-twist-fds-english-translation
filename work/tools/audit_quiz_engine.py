"""Audit every scored Time Twist quiz against a compiled candidate.

This candidate-level maintainer check proves the quiz/menu invariants that can
be established statically. Clean emulator playtesting remains the runtime/PPU
certification layer.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from time_twist.english import encode_english
from time_twist.entropy_codec import split_entropy_stream
from time_twist.entropy_compression import expand_entropy_record
from time_twist.fds import FdsImage
from time_twist.incremental_build import _load_entropy_bank
from time_twist.menu_geometry import (
    menu_pair_geometry,
    primary_menu_descriptors,
    validate_menu_label,
)
from time_twist.production_translation import merged_translation_map
from time_twist.quiz_manifest import QUIZ_ANSWERS
from time_twist.textcodec import SymbolKind
from time_twist.ui_fixed_tables import (
    TT2_FIXED_TEXT_RECORDS,
    TT3A_FIXED_TEXT_RECORDS,
    TT4_FIXED_TEXT_RECORDS,
    TT5_FIXED_TEXT_RECORDS,
    TT6B_FIXED_TEXT_RECORDS,
    TT6C_FIXED_TEXT_RECORDS,
)

LOAD_ADDRESS = 0xA200
NOV2_LOAD_ADDRESS = 0x6000

FIXED_LABELS = {
    "TT2": TT2_FIXED_TEXT_RECORDS,
    "TT3A": TT3A_FIXED_TEXT_RECORDS,
    "TT4": TT4_FIXED_TEXT_RECORDS,
    "TT5": TT5_FIXED_TEXT_RECORDS,
    "TT6B": TT6B_FIXED_TEXT_RECORDS,
    "TT6C": TT6C_FIXED_TEXT_RECORDS,
}

QUIZ_PROMPTS = {
    "TT2": ((1, 12), (1, 15), (1, 16), (1, 17), (1, 18)),
    "TT3A": ((4, 2), (4, 4), (4, 5), (4, 6), (4, 7)),
    "TT4": ((5, 7), (5, 10), (5, 11), (5, 12), (5, 13)),
    "TT5": ((2, 12), (2, 15), (2, 16), (2, 17), (2, 18)),
    "TT6B": ((1, 30), (2, 0), (2, 1), (2, 2), (2, 3)),
    "TT6C": tuple((2, record) for record in range(16, 30)),
}

FINAL_COMPLETION = {
    "TT2": ("flag", 0x26),
    "TT3A": ("flag", 0x42),
    "TT4": ("flag", 0x4E),
    "TT5": ("flag", 0x25),
    "TT6B": ("flag", 0x1D),
    "TT6C": ("route", 0x06),
}

EXPECTED_WRONG = {
    "TT2": 0xA747,
    "TT3A": 0xAAEE,
    "TT4": 0xAE19,
    "TT5": 0xA77E,
    "TT6B": 0xA682,
    "TT6C": 0xA797,
}


def _word(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def _signed(value: int) -> int:
    return value - 0x100 if value & 0x80 else value


def _semantic(record):
    return tuple((symbol.kind, symbol.value) for symbol in record)


def _files(image: FdsImage) -> dict[str, tuple[int, bytes]]:
    found: dict[str, tuple[int, bytes]] = {}
    for side in image.sides:
        for file in side.files:
            if file.name not in found:
                found[file.name] = (file.load_address, file.data)
    return found


def _fixed_record(data: bytes, state, one_based: int):
    index = one_based - 1
    page, within = divmod(index, 32)
    if page == 0:
        address = _word(data, 0x14)
    else:
        page_table = _word(data, 0x1A) - LOAD_ADDRESS
        address = _word(data, page_table + 2 * (page - 1))
    records, _byte, _mask = split_entropy_stream(
        data,
        offset=address - LOAD_ADDRESS,
        limit=within + 1,
    )
    return expand_entropy_record(tuple(records[-1]), state.expansions)


def _find_call(data: bytes, selector: int, count: int, direct: bool):
    start = _word(data, 0x22) - LOAD_ADDRESS
    end = _word(data, 0x20) - LOAD_ADDRESS
    wanted = 0x20 if direct else 0x28
    hits = []
    for offset in range(start, end - 2):
        if data[offset] != wanted or data[offset + 1] != selector:
            continue
        result = offset + 2
        if data[result] != 0x31:
            continue
        raw = data[result + 1 : result + 1 + count]
        if len(raw) != count:
            continue
        targets = tuple(
            LOAD_ADDRESS + result + _signed(value) for value in raw
        )
        hits.append((offset, result, targets))
    if len(hits) != 1:
        raise AssertionError(
            f"selector ${selector:02X}: expected one scored call, got {hits}"
        )
    return hits[0]


def _navigation(count: int) -> None:
    for current in range(count):
        down = 0 if current + 1 == count else current + 1
        up = count - 1 if current == 0 else current - 1
        right = current + 4 if current + 4 < count else current
        left = current - 4 if current >= 4 else current
        assert all(
            0 <= value < count for value in (down, up, right, left)
        )


def _completion(data: bytes, address: int, kind: str, value: int):
    offset = address - LOAD_ADDRESS
    stop = min(len(data), offset + 48)
    while offset < stop:
        opcode = data[offset]
        if kind == "flag" and opcode == 0x61 and data[offset + 1] == value:
            return LOAD_ADDRESS + offset
        if kind == "route" and opcode == 0x51 and data[offset + 1] == value:
            return LOAD_ADDRESS + offset
        if opcode in (
            0x10, 0x11, 0x18, 0x19, 0x61, 0x64,
            0x90, 0x91, 0x92, 0x93, 0xA1,
        ):
            length = 2
        elif opcode in (0x52, 0x53):
            length = 1
        elif opcode in (0x50, 0x54):
            length = 3
        elif opcode == 0x70:
            length = 2 + data[offset + 1].bit_count()
        elif opcode in (0x20, 0x28):
            length = 2
        else:
            length = 1
        if opcode in (0x18, 0x19, 0x50, 0x51, 0x52, 0x53):
            break
        offset += length
    return None


def _engine_guards(nov2: bytes) -> None:
    def at(address: int, size: int) -> bytes:
        offset = address - NOV2_LOAD_ADDRESS
        return nov2[offset : offset + size]

    # 20/28 primary menus take the all-choice path, not predicate filtering.
    assert at(0x6AF6, 2) == bytes.fromhex("A9 02")
    # Bit 3 snapshots a parent; direct menus preserve an inherited parent.
    assert at(0x6BA3, 24) == bytes.fromhex(
        "A0 00 B1 C5 29 08 F0 10 A5 C5 85 9B A5 C6 85 9C "
        "A5 9D 85 9F A5 9E 85 A0"
    )
    # Missing/self parent rejects B and redraws instead of returning a result.
    assert at(0x99DC, 14) == bytes.fromhex(
        "A5 9C F0 AC 20 2E 6A F0 A7 A9 04 4C B6 7D"
    )
    # Relative result dispatcher checks A4 and indexes with logical slot A7.
    assert at(0x6BFD, 11) == bytes.fromhex(
        "A0 00 B1 C5 29 01 F0 28 A5 A4 C9"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()

    image = FdsImage.read(args.candidate)
    files = _files(image)
    _engine_guards(files["NOV2"][1])

    answers = {
        (entry.bank, entry.selector): entry.answer for entry in QUIZ_ANSWERS
    }
    total = 0

    for bank, prompts in QUIZ_PROMPTS.items():
        load, data = files[bank]
        assert load == LOAD_ADDRESS
        state = _load_entropy_bank(data, bank)
        assert not any(
            symbol.kind is SymbolKind.CONTROL
            for expansion in state.expansions
            for symbol in expansion
        ), f"{bank}: dictionary expansion contains presentation control"

        descriptors = primary_menu_descriptors(data)
        labels = FIXED_LABELS[bank]
        translations = merged_translation_map(bank)
        wrong_targets = []
        success_targets = []

        entries = sorted(
            (entry for entry in QUIZ_ANSWERS if entry.bank == bank),
            key=lambda entry: entry.selector,
        )
        assert len(entries) == len(prompts)

        for entry, (group, record) in zip(entries, prompts, strict=True):
            descriptor = descriptors[entry.selector - 1]
            visible_labels = []
            for fixed_index in descriptor:
                expected = labels[fixed_index - 1]
                decoded = _fixed_record(data, state, fixed_index)
                assert _semantic(decoded) == _semantic(encode_english(expected))
                visible_labels.append(expected)
                validate_menu_label(expected)

            for left, right in ((0, 4), (1, 5), (2, 6), (3, 7)):
                if right < len(visible_labels):
                    menu_pair_geometry(
                        visible_labels[left], visible_labels[right]
                    )
            _navigation(len(visible_labels))

            expected_answer = answers[(bank, entry.selector)]
            assert expected_answer in visible_labels
            correct = visible_labels.index(expected_answer)

            call, _result, targets = _find_call(
                data,
                entry.selector,
                len(visible_labels),
                bank == "TT3A",
            )
            wrong = {
                target
                for index, target in enumerate(targets)
                if index != correct
            }
            assert len(wrong) == 1
            wrong_target = next(iter(wrong))
            assert targets[correct] != wrong_target
            wrong_targets.append(wrong_target)
            success_targets.append(targets[correct])

            literal = state.literal_groups[group][record]
            record_id = f"{bank}/g{group}/r{record}"
            assert _semantic(literal) == _semantic(
                encode_english(translations[record_id])
            )
            visible_segments = []
            for piece in translations[record_id].split("{CTRL:"):
                visible_segments.append(
                    piece.split("}", 1)[-1] if "}" in piece else piece
                )
            assert max(map(len, visible_segments)) <= 24

            script_start = _word(data, 0x22)
            script_end = _word(data, 0x20)
            assert all(
                script_start <= target < script_end for target in targets
            )
            total += 1
            print(
                f"{bank} ${LOAD_ADDRESS + call:04X} "
                f"selector=${entry.selector:02X} answer={expected_answer!r} "
                f"success=${targets[correct]:04X} wrong=${wrong_target:04X}"
            )

        assert set(wrong_targets) == {EXPECTED_WRONG[bank]}
        kind, value = FINAL_COMPLETION[bank]
        assert _completion(
            data, success_targets[-1], kind, value
        ) is not None

        for index in range(len(success_targets) - 1):
            next_entry = entries[index + 1]
            next_call, _result, _targets = _find_call(
                data,
                next_entry.selector,
                len(descriptors[next_entry.selector - 1]),
                bank == "TT3A",
            )
            next_address = LOAD_ADDRESS + next_call
            assert 0 < next_address - success_targets[index] < 20

        if bank == "TT6C":
            offset = EXPECTED_WRONG[bank] - LOAD_ADDRESS
            assert data[offset : offset + 6] == bytes.fromhex(
                "10 4C 10 51 28 14"
            )

    assert total == 39
    print(
        "PASS: all 39 scored quiz paths satisfy the recovered "
        "quiz-engine invariants"
    )


if __name__ == "__main__":
    main()
