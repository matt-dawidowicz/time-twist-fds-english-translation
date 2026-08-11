"""Hardened public CLI facade for Time Twist translation tooling."""

from __future__ import annotations

import argparse
import copy
import json
from typing import Any

from . import _cli_core as _core
from .compression import compress_english_groups, packed_size
from .english import EnglishTextError
from .project import (
    infer_bank_name,
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
from .scenario import (
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from .scenario_validation import encode_validated_english, scenario_record_id
from .textcodec import PackedSymbol, pack_records

for _name in dir(_core):
    if not _name.startswith("__") and _name not in globals():
        globals()[_name] = getattr(_core, _name)
del _name

safe_filename = _core.safe_filename
command_manifest = _core.command_manifest
command_extract = _core.command_extract
command_roundtrip = _core.command_roundtrip
command_combine = _core.command_combine
command_font_patch = _core.command_font_patch
command_title_patch = _core.command_title_patch
command_ui_patch = _core.command_ui_patch
command_replace_file = _core.command_replace_file
command_release_lock = _core.command_release_lock
command_release_build = _core.command_release_build
command_release_promote = _core.command_release_promote
build_parser = _core.build_parser
main = _core.main


def _parse_source_bank(args: argparse.Namespace):
    """Parse a named source bank including fixed-UI dictionary references."""
    bank_name = infer_bank_name(args.bank, getattr(args, "bank_name", None))
    source = args.bank.read_bytes()
    bank = parse_scenario_bank(
        args.bank,
        minimum_dictionary_entries=source_dictionary_reference_floor(
            bank_name,
            source,
        ),
    )
    return bank_name, bank


def command_scenario_extract(args: argparse.Namespace) -> None:
    """Decode a bank while retaining English only for matching stable IDs."""
    bank_name, bank = _parse_source_bank(args)
    existing_english: dict[str, str] = {}
    if args.output.is_file():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if isinstance(previous, dict):
            previous_groups = previous.get("groups", [])
            if isinstance(previous_groups, list):
                for previous_group in previous_groups:
                    if not isinstance(previous_group, dict):
                        continue
                    previous_records = previous_group.get("records", [])
                    if not isinstance(previous_records, list):
                        continue
                    for previous_record in previous_records:
                        if not isinstance(previous_record, dict):
                            continue
                        record_id = previous_record.get("id")
                        english = previous_record.get("english", "")
                        if isinstance(record_id, str) and isinstance(
                            english, str
                        ):
                            existing_english[record_id] = english

    groups: list[dict[str, object]] = []
    for group_index, group_address in enumerate(bank.group_addresses):
        records: list[dict[str, object]] = []
        for record in bank.records:
            if record.group_index != group_index:
                continue
            record_id = scenario_record_id(
                bank_name,
                group_index,
                record.record_index,
            )
            records.append(
                {
                    "id": record_id,
                    "record": record.record_index,
                    "japanese": render_symbols(
                        record.symbols,
                        bank.dictionary,
                    ),
                    "english": existing_english.get(record_id, ""),
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
    """Insert merged JSON only after structural and display validation."""
    bank_name, bank = _parse_source_bank(args)
    document = json.loads(args.translation.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise SystemExit("translation document must contain a JSON object")
    json_groups = document.get("groups")
    if not isinstance(json_groups, list) or len(json_groups) != len(
        bank.group_addresses
    ):
        raise SystemExit(
            "translation group count does not match the scenario bank"
        )

    rebuilt_groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    translated_count = 0
    total_count = 0
    for group_index, json_group in enumerate(json_groups):
        if not isinstance(json_group, dict):
            raise SystemExit(f"translation group {group_index} is invalid")
        if json_group.get("group") != group_index:
            raise SystemExit(
                f"translation group index mismatch at position {group_index}"
            )
        original_records = tuple(
            record
            for record in bank.records
            if record.group_index == group_index
        )
        json_records = json_group.get("records")
        if not isinstance(json_records, list) or len(json_records) != len(
            original_records
        ):
            raise SystemExit(
                f"translation record count mismatch in group {group_index}"
            )

        rebuilt_records: list[tuple[PackedSymbol, ...]] = []
        for original, translated in zip(
            original_records,
            json_records,
            strict=True,
        ):
            total_count += 1
            if not isinstance(translated, dict):
                raise SystemExit(
                    "translation record "
                    f"{group_index}/{original.record_index} is invalid"
                )
            record_id = scenario_record_id(
                bank_name,
                group_index,
                original.record_index,
            )
            if translated.get("id") != record_id:
                raise SystemExit(
                    f"record ID mismatch at group {group_index}, record "
                    f"{original.record_index}; expected {record_id}"
                )
            if translated.get("record") != original.record_index:
                raise SystemExit(f"record index mismatch in {record_id}")
            english = translated.get("english", "")
            if not isinstance(english, str):
                raise SystemExit(
                    f"English text must be a string in {record_id}"
                )
            if not english:
                rebuilt_records.append(original.symbols)
                continue

            translated_count += 1
            japanese = render_symbols(original.symbols, bank.dictionary)
            try:
                encoded = encode_validated_english(
                    record_id,
                    english,
                    japanese,
                )
            except EnglishTextError as error:
                raise SystemExit(
                    f"invalid English text in {record_id}: {error}"
                ) from error
            rebuilt_records.append(encoded)
        rebuilt_groups.append(tuple(rebuilt_records))

    packed_groups = tuple(rebuilt_groups)
    text_start = bank.group_addresses[0] - bank.load_address
    capacity = bank.dictionary_end_offset - text_start
    pointer_bytes = 2 * (len(packed_groups) - 1)
    if translated_count == total_count and not args.no_compress:
        original_size = packed_size(packed_groups, ())
        packed_groups, dictionary = compress_english_groups(
            packed_groups,
            required_entries=required_dictionary_entries(bank_name),
            max_bytes=capacity - pointer_bytes,
        )
        compressed_size = packed_size(packed_groups, dictionary)
        print(
            f"English dictionary: {len(dictionary)} entries, "
            f"{original_size} -> {compressed_size} packed bytes"
        )
    elif translated_count == total_count:
        dictionary = bank.dictionary
        print(
            "uncompressed layout build: "
            f"{translated_count}/{total_count} records; preserving the "
            "original dictionary region"
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
    document: dict[str, Any],
    translations: dict[str, Any],
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    """Validate and merge English by stable record ID through one policy."""
    result = copy.deepcopy(document)
    records_by_id: dict[str, dict[str, object]] = {}
    groups = result.get("groups", [])
    if not isinstance(groups, list):
        raise SystemExit("scenario document groups must be a list")
    for group in groups:
        if not isinstance(group, dict):
            raise SystemExit("scenario document contains an invalid group")
        records = group.get("records", [])
        if not isinstance(records, list):
            raise SystemExit(
                "scenario document contains an invalid record list"
            )
        for record in records:
            if not isinstance(record, dict):
                raise SystemExit(
                    "scenario document contains an invalid record"
                )
            record_id = record.get("id")
            if not isinstance(record_id, str):
                raise SystemExit(
                    "scenario document contains a record without an ID"
                )
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
                f"translation map is missing {len(missing)} IDs; "
                f"first: {missing[0]}"
            )

    for record_id, english in translations.items():
        record = records_by_id[record_id]
        japanese = record.get("japanese")
        if not isinstance(japanese, str):
            raise SystemExit(f"Japanese source for {record_id} is invalid")
        try:
            encode_validated_english(record_id, english, japanese)
        except EnglishTextError as error:
            raise SystemExit(
                f"invalid English text in {record_id}: {error}"
            ) from error
        record["english"] = english
    return result


def command_scenario_footprint(args: argparse.Namespace) -> None:
    """Report capacity using the same boundary and validation as insertion."""
    bank_name, bank = _parse_source_bank(args)
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
        raise SystemExit(
            "translation file must contain an ID-keyed JSON object"
        )
    records_by_id = {
        scenario_record_id(
            bank_name,
            record.group_index,
            record.record_index,
        ): record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    if unknown:
        raise SystemExit(f"unknown translation IDs: {', '.join(unknown)}")

    encoded_by_id: dict[str, tuple[PackedSymbol, ...]] = {}
    literal_bytes = 0
    for record_id, english in translations.items():
        record = records_by_id[record_id]
        japanese = render_symbols(record.symbols, bank.dictionary)
        try:
            encoded = encode_validated_english(
                record_id,
                english,
                japanese,
            )
        except EnglishTextError as error:
            raise SystemExit(
                f"invalid English text in {record_id}: {error}"
            ) from error
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
            encoded_by_id[
                scenario_record_id(
                    bank_name,
                    group_index,
                    record.record_index,
                )
            ]
            for record in bank.records
            if record.group_index == group_index
        )
        for group_index in range(len(bank.group_addresses))
    )
    pointer_bytes = 2 * (len(groups) - 1)
    compressed_groups, dictionary = compress_english_groups(
        groups,
        required_entries=required_dictionary_entries(bank_name),
        max_bytes=capacity - pointer_bytes,
    )
    used = packed_size(compressed_groups, dictionary) + pointer_bytes
    print(
        f"final compressed footprint: {used}/{capacity} bytes; "
        f"remaining: {capacity - used} bytes"
    )
    if used > capacity:
        raise SystemExit(
            "translation exceeds fixed RAM reservation by "
            f"{used - capacity} bytes"
        )


# build_parser() and main() live in the original implementation module and
# resolve command callbacks from its globals, so replace those globals here.
_core.command_scenario_extract = command_scenario_extract
_core.command_scenario_insert = command_scenario_insert
_core.merge_translation_document = merge_translation_document
_core.command_scenario_footprint = command_scenario_footprint

command_scenario_merge = _core.command_scenario_merge
