"""Command-line interface for the Time Twist FDS tools."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from .compression import compress_english_groups, packed_size
from .english import (
    EnglishTextError,
    control_values,
    encode_english,
    validate_display_width,
)
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .scenario import parse_scenario_bank, rebuild_scenario_bank, render_symbols
from .textcodec import pack_records
from .title import DEFAULT_SUBTITLE, patched_nov4_title
from .ui import (
    T22_REQUIRED_DICTIONARY_TEXT,
    TT1B_REQUIRED_DICTIONARY_TEXT,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_t22_ui,
    patched_tt1a_ui,
    patched_tt1b_ui,
    patched_tt2_ui,
    patched_tt3a_ui,
    patched_tt3b_ui,
    patched_tt4_ui,
    patched_tt5_ui,
    patched_t25_ui,
    patched_tt6a_ui,
    patched_tt6b_ui,
    patched_tt6c_ui,
)


BANK_REQUIRED_DICTIONARY_TEXT = {
    "TT1B": TT1B_REQUIRED_DICTIONARY_TEXT,
    "TT2": ("CROWD", "Bishop"),
    "T22": T22_REQUIRED_DICTIONARY_TEXT,
    "TT3B": ("Cougar",),
    # TT4 repeats these dialogue prefixes heavily. Reserving them produces a
    # substantially smaller flat dictionary than fragment-only greedy picks.
    "TT4": (
        "Cerberus: ",
        "Soldier: ",
        "Fisher: ",
        "Man: ",
        "Me: ",
        "Merchant: ",
        "Devil: ",
        "Dario: ",
        "Girl: ",
        "Youth: ",
        "Priest: ",
    ),
    # TT5 uses Tom's speaker prefix often enough that reserving it beats the
    # greedy fragment it replaces and keeps the rebuilt scenario in RAM.
    "TT5": ("Tom: ",),
}


PERSONALITY_QUESTION_IDS = frozenset(
    f"TT1A/g0/r{record}" for record in range(6, 21)
)


def _required_dictionary_entries(
    bank_name: str,
) -> tuple[tuple[object, ...], ...]:
    """Return bank-specific entries shared with fixed packed-text tables."""

    return tuple(
        encode_english(text)
        for text in BANK_REQUIRED_DICTIONARY_TEXT.get(bank_name, ())
    )


def safe_filename(name: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "_" for char in name)


def command_manifest(args: argparse.Namespace) -> None:
    image = FdsImage.read(args.image)
    output = json.dumps(image.manifest(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def command_extract(args: argparse.Namespace) -> None:
    image = FdsImage.read(args.image)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for side in image.sides:
        for entry in side.files:
            filename = (
                f"side{side.index}_{entry.index:02d}_{safe_filename(entry.name)}_"
                f"{entry.load_address:04X}.bin"
            )
            path = args.output_dir / filename
            path.write_bytes(entry.data)
            print(path)


def command_roundtrip(args: argparse.Namespace) -> None:
    source = args.image.read_bytes()
    image = FdsImage.from_bytes(source, args.image)
    rebuilt = image.to_bytes()
    args.output.write_bytes(rebuilt)
    source_hash = hashlib.sha256(source).hexdigest().upper()
    rebuilt_hash = hashlib.sha256(rebuilt).hexdigest().upper()
    print(f"source  SHA-256 {source_hash}")
    print(f"rebuilt SHA-256 {rebuilt_hash}")
    if source != rebuilt:
        raise SystemExit("round-trip mismatch")
    print("byte-identical round trip: PASS")


def command_combine(args: argparse.Namespace) -> None:
    image = combine_images([FdsImage.read(path) for path in args.images])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.write(args.output)
    print(f"{args.output} ({len(image.sides)} sides)")


def command_scenario_extract(args: argparse.Namespace) -> None:
    bank = parse_scenario_bank(args.bank)
    bank_name = args.bank.stem.split("_")[2] if "_" in args.bank.stem else args.bank.stem
    existing_english: dict[tuple[int, int], str] = {}
    if args.output.is_file():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        for previous_group in previous.get("groups", []):
            group_number = previous_group.get("group")
            if not isinstance(group_number, int):
                continue
            for previous_record in previous_group.get("records", []):
                record_number = previous_record.get("record")
                english = previous_record.get("english", "")
                if isinstance(record_number, int) and isinstance(english, str):
                    existing_english[(group_number, record_number)] = english
    groups: list[dict[str, object]] = []
    for group_index, group_address in enumerate(bank.group_addresses):
        records: list[dict[str, object]] = []
        for record in bank.records:
            if record.group_index != group_index:
                continue
            records.append(
                {
                    "id": f"{bank_name}/g{group_index}/r{record.record_index}",
                    "record": record.record_index,
                    "japanese": render_symbols(record.symbols, bank.dictionary),
                    "english": existing_english.get(
                        (group_index, record.record_index), ""
                    ),
                    "symbols": [
                        {"kind": symbol.kind.value, "value": symbol.value}
                        for symbol in record.symbols
                    ],
                }
            )
        groups.append(
            {
                "group": group_index,
                "address": f"0x{group_address:04X}",
                "records": records,
            }
        )

    document = {
        "source": str(args.bank),
        "load_address": f"0x{bank.load_address:04X}",
        "dictionary_address": f"0x{bank.dictionary_address:04X}",
        "group_table_address": f"0x{bank.group_table_address:04X}",
        "groups": groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


def command_scenario_insert(args: argparse.Namespace) -> None:
    bank = parse_scenario_bank(args.bank)
    bank_name = (
        args.bank.stem.split("_")[2]
        if "_" in args.bank.stem
        else args.bank.stem
    )
    document = json.loads(args.translation.read_text(encoding="utf-8"))
    json_groups = document.get("groups")
    if not isinstance(json_groups, list) or len(json_groups) != len(bank.group_addresses):
        raise SystemExit("translation group count does not match the scenario bank")

    rebuilt_groups: list[tuple[tuple[object, ...], ...]] = []
    translated_count = 0
    total_count = 0
    for group_index, json_group in enumerate(json_groups):
        original_records = tuple(
            record for record in bank.records if record.group_index == group_index
        )
        json_records = json_group.get("records")
        if not isinstance(json_records, list) or len(json_records) != len(original_records):
            raise SystemExit(f"translation record count mismatch in group {group_index}")
        rebuilt_records: list[tuple[object, ...]] = []
        for original, translated in zip(original_records, json_records):
            total_count += 1
            english = translated.get("english", "")
            if not isinstance(english, str):
                raise SystemExit(
                    f"English text must be a string in group {group_index}, "
                    f"record {original.record_index}"
                )
            if english:
                translated_count += 1
                japanese = render_symbols(original.symbols, bank.dictionary)
                if control_values(english) != control_values(japanese):
                    raise SystemExit(
                        f"control tags changed in group {group_index}, "
                        f"record {original.record_index}"
                    )
                rebuilt_records.append(encode_english(english))
            else:
                rebuilt_records.append(original.symbols)
        rebuilt_groups.append(tuple(rebuilt_records))

    packed_groups = tuple(rebuilt_groups)
    if translated_count == total_count and not args.no_compress:
        original_size = packed_size(packed_groups, ())
        packed_groups, dictionary = compress_english_groups(
            packed_groups,
            required_entries=_required_dictionary_entries(bank_name),
        )
        compressed_size = packed_size(packed_groups, dictionary)
        print(
            f"English dictionary: {len(dictionary)} entries, "
            f"{original_size} -> {compressed_size} packed bytes"
        )
    elif translated_count == total_count:
        dictionary = bank.dictionary
        print(
            f"uncompressed layout build: {translated_count}/{total_count} records; "
            "preserving the original dictionary region"
        )
    else:
        dictionary = bank.dictionary
        print(
            f"partial translation: {translated_count}/{total_count} records; "
            "preserving the Japanese dictionary"
        )

    rebuilt = rebuild_scenario_bank(
        bank,
        packed_groups,
        dictionary=dictionary,
        preserve_memory_footprint=True,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rebuilt)
    print(args.output)


def merge_translation_document(
    document: dict[str, object],
    translations: dict[str, object],
    *,
    require_complete: bool = True,
) -> dict[str, object]:
    """Merge an ID-keyed English map into an extracted scenario document."""

    result = copy.deepcopy(document)
    records_by_id: dict[str, dict[str, object]] = {}
    for group in result.get("groups", []):
        for record in group.get("records", []):
            record_id = record.get("id")
            if not isinstance(record_id, str):
                raise SystemExit("scenario document contains a record without an ID")
            if record_id in records_by_id:
                raise SystemExit(f"duplicate scenario record ID: {record_id}")
            records_by_id[record_id] = record

    unknown = sorted(set(translations) - set(records_by_id))
    if unknown:
        raise SystemExit(f"unknown translation IDs: {', '.join(unknown)}")
    if require_complete:
        missing = sorted(set(records_by_id) - set(translations))
        if missing:
            raise SystemExit(
                f"translation map is missing {len(missing)} IDs; first: {missing[0]}"
            )

    for record_id, english in translations.items():
        if not isinstance(english, str) or not english:
            raise SystemExit(f"English translation for {record_id} must be nonempty")
        record = records_by_id[record_id]
        japanese = record.get("japanese")
        if not isinstance(japanese, str):
            raise SystemExit(f"Japanese source for {record_id} is invalid")
        if control_values(english) != control_values(japanese):
            raise SystemExit(f"control tags changed in {record_id}")
        try:
            validate_display_width(
                english,
                allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
            )
            encode_english(english)
        except EnglishTextError as error:
            raise SystemExit(f"invalid English text in {record_id}: {error}") from error
        record["english"] = english
    return result


def command_scenario_merge(args: argparse.Namespace) -> None:
    document = json.loads(args.scenario.read_text(encoding="utf-8"))
    translations = json.loads(args.translations.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(translations, dict):
        raise SystemExit("scenario and translation files must contain JSON objects")
    merged = merge_translation_document(
        document,
        translations,
        require_complete=not args.allow_partial,
    )
    output = args.output or args.scenario
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)


def command_scenario_footprint(args: argparse.Namespace) -> None:
    """Report the fixed RAM reservation and optional translation progress."""

    bank = parse_scenario_bank(args.bank)
    text_start_offset = bank.group_addresses[0] - bank.load_address
    capacity = bank.dictionary_end_offset - text_start_offset
    print(f"bank bytes: {len(bank.data)}")
    print(
        f"loaded range: ${bank.load_address:04X}-"
        f"${bank.load_address + len(bank.data):04X}"
    )
    print(
        f"fixed text reservation: {capacity} bytes "
        f"(${bank.group_addresses[0]:04X}-"
        f"${bank.load_address + bank.dictionary_end_offset:04X})"
    )
    print(f"fixed tail: {len(bank.data) - bank.dictionary_end_offset} bytes")
    print(
        f"groups: {len(bank.group_addresses)}; records: {len(bank.records)}; "
        f"original dictionary entries: {len(bank.dictionary)}"
    )

    if args.translations is None:
        return
    translations = json.loads(args.translations.read_text(encoding="utf-8"))
    if not isinstance(translations, dict):
        raise SystemExit("translation file must contain an ID-keyed JSON object")
    bank_name = (
        args.bank.stem.split("_")[2]
        if "_" in args.bank.stem
        else args.bank.stem
    )
    records_by_id = {
        f"{bank_name}/g{record.group_index}/r{record.record_index}": record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    if unknown:
        raise SystemExit(f"unknown translation IDs: {', '.join(unknown)}")

    encoded_by_id: dict[str, tuple[object, ...]] = {}
    literal_bytes = 0
    for record_id, english in translations.items():
        if not isinstance(english, str) or not english:
            raise SystemExit(f"English translation for {record_id} must be nonempty")
        record = records_by_id[record_id]
        japanese = render_symbols(record.symbols, bank.dictionary)
        if control_values(english) != control_values(japanese):
            raise SystemExit(f"control tags changed in {record_id}")
        try:
            validate_display_width(
                english,
                allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
            )
        except EnglishTextError as error:
            raise SystemExit(f"invalid English text in {record_id}: {error}") from error
        encoded = encode_english(english)
        encoded_by_id[record_id] = encoded
        literal_bytes += len(pack_records((encoded,)))
    print(
        f"translated records: {len(translations)}/{len(bank.records)}; "
        f"translated literal bytes so far: {literal_bytes}"
    )

    if len(translations) != len(bank.records):
        print("final compressed footprint: pending complete translation")
        return

    groups = tuple(
        tuple(
            encoded_by_id[f"{bank_name}/g{group_index}/r{record.record_index}"]
            for record in bank.records
            if record.group_index == group_index
        )
        for group_index in range(len(bank.group_addresses))
    )
    compressed_groups, dictionary = compress_english_groups(
        groups,
        required_entries=_required_dictionary_entries(bank_name),
    )
    used = packed_size(compressed_groups, dictionary) + 2 * (len(groups) - 1)
    print(
        f"final compressed footprint: {used}/{capacity} bytes; "
        f"remaining: {capacity - used} bytes"
    )
    if used > capacity:
        raise SystemExit(f"translation exceeds fixed RAM reservation by {used - capacity} bytes")


def command_font_patch(args: argparse.Namespace) -> None:
    patched = patched_nov4_font(args.nov4.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(args.output)


def command_title_patch(args: argparse.Namespace) -> None:
    patched = patched_nov4_title(
        args.nov4.read_bytes(),
        args.target,
        subtitle=args.subtitle,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(args.output)


def command_ui_patch(args: argparse.Namespace) -> None:
    patcher = {
        "SON-KOUH": patched_kouhen_boot_guard,
        "NOV2": patched_nov2_ui,
        "NOV4": patched_nov4_ui,
        "TT1A": patched_tt1a_ui,
        "TT1B": patched_tt1b_ui,
        "TT2": patched_tt2_ui,
        "T22": patched_t22_ui,
        "TT3A": patched_tt3a_ui,
        "TT3B": patched_tt3b_ui,
        "TT4": patched_tt4_ui,
        "TT5": patched_tt5_ui,
        "T25": patched_t25_ui,
        "TT6A": patched_tt6a_ui,
        "TT6B": patched_tt6b_ui,
        "TT6C": patched_tt6c_ui,
    }[args.component]
    patched = patcher(args.source.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(args.output)


def command_replace_file(args: argparse.Namespace) -> None:
    image = FdsImage.read(args.image)
    if args.side < 0 or args.side >= len(image.sides):
        raise SystemExit(f"side {args.side} is outside this image")
    entry = image.sides[args.side].find_file(args.name)
    entry.data = args.data.read_bytes()
    image.write(args.output)
    print(args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("image", type=Path)
    manifest.add_argument("--output", type=Path)
    manifest.set_defaults(function=command_manifest)

    extract = subparsers.add_parser("extract")
    extract.add_argument("image", type=Path)
    extract.add_argument("output_dir", type=Path)
    extract.set_defaults(function=command_extract)

    roundtrip = subparsers.add_parser("roundtrip")
    roundtrip.add_argument("image", type=Path)
    roundtrip.add_argument("output", type=Path)
    roundtrip.set_defaults(function=command_roundtrip)

    combine = subparsers.add_parser("combine")
    combine.add_argument("images", nargs="+", type=Path)
    combine.add_argument("--output", required=True, type=Path)
    combine.set_defaults(function=command_combine)

    scenario_extract = subparsers.add_parser("scenario-extract")
    scenario_extract.add_argument("bank", type=Path)
    scenario_extract.add_argument("output", type=Path)
    scenario_extract.set_defaults(function=command_scenario_extract)

    scenario_insert = subparsers.add_parser("scenario-insert")
    scenario_insert.add_argument("bank", type=Path)
    scenario_insert.add_argument("translation", type=Path)
    scenario_insert.add_argument("output", type=Path)
    scenario_insert.add_argument("--no-compress", action="store_true")
    scenario_insert.set_defaults(function=command_scenario_insert)

    scenario_merge = subparsers.add_parser("scenario-merge")
    scenario_merge.add_argument("scenario", type=Path)
    scenario_merge.add_argument("translations", type=Path)
    scenario_merge.add_argument("--output", type=Path)
    scenario_merge.add_argument("--allow-partial", action="store_true")
    scenario_merge.set_defaults(function=command_scenario_merge)

    scenario_footprint = subparsers.add_parser("scenario-footprint")
    scenario_footprint.add_argument("bank", type=Path)
    scenario_footprint.add_argument("--translations", type=Path)
    scenario_footprint.set_defaults(function=command_scenario_footprint)

    font_patch = subparsers.add_parser("font-patch")
    font_patch.add_argument("nov4", type=Path)
    font_patch.add_argument("output", type=Path)
    font_patch.set_defaults(function=command_font_patch)

    title_patch = subparsers.add_parser("title-patch")
    title_patch.add_argument("nov4", type=Path)
    title_patch.add_argument("target", type=Path)
    title_patch.add_argument("output", type=Path)
    title_patch.add_argument("--subtitle", default=DEFAULT_SUBTITLE)
    title_patch.set_defaults(function=command_title_patch)

    ui_patch = subparsers.add_parser("ui-patch")
    ui_patch.add_argument("source", type=Path)
    ui_patch.add_argument("output", type=Path)
    ui_patch.add_argument(
        "--component",
        choices=(
            "SON-KOUH", "NOV2", "NOV4", "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B", "TT4",
            "TT5", "T25", "TT6A", "TT6B", "TT6C",
        ),
        default="NOV2",
    )
    ui_patch.set_defaults(function=command_ui_patch)

    replace_file = subparsers.add_parser("replace-file")
    replace_file.add_argument("image", type=Path)
    replace_file.add_argument("side", type=int)
    replace_file.add_argument("name")
    replace_file.add_argument("data", type=Path)
    replace_file.add_argument("output", type=Path)
    replace_file.set_defaults(function=command_replace_file)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
