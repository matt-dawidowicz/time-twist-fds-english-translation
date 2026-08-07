"""Compose the lossless parsers and guarded patch layers as ``time-twist``.

Individual patch commands remain small and explicit. Release commands discover
a project checkout from the current directory or accept ``--project-root``, so
the installed console command does not depend on package-bundled project data.
"""

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
from .project import (
    PERSONALITY_QUESTION_IDS,
    infer_bank_name,
    required_dictionary_entries,
)
from .release import (
    build_release,
    discover_project_root,
    promote_release_target,
    validate_source_lock,
    write_source_lock,
)
from .ui import (
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


def safe_filename(name: str) -> str:
    """Convert an FDS filename into a conservative local filename component.

    Args:
        name: Decoded FDS filename.

    Returns:
        ``name`` with every character except alphanumerics, hyphen, and
        underscore replaced by an underscore.

    This is a portability transformation, not a reversible encoding. Extracted
    filenames also include side/index metadata to retain identity.
    """

    return "".join(char if char.isalnum() or char in "-_" else "_" for char in name)


def command_manifest(args: argparse.Namespace) -> None:
    """Run the ``manifest`` command.

    Args:
        args: Namespace with ``image`` and optional ``output`` paths.

    Raises:
        OSError: If input cannot be read or output cannot be written.
        FdsFormatError: If the image is malformed.

    Side Effects:
        Writes UTF-8 JSON to ``args.output`` or prints it to standard output.
    """

    image = FdsImage.read(args.image)
    output = json.dumps(image.manifest(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


def command_extract(args: argparse.Namespace) -> None:
    """Run the ``extract`` command.

    Args:
        args: Namespace with source ``image`` and destination ``output_dir``.

    Raises:
        OSError: If files or directories cannot be read or written.
        FdsFormatError: If the image is malformed.

    Side Effects:
        Creates the output directory, writes one payload per FDS file, and
        prints each created path. The source image is never changed.
    """

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
    """Run the lossless FDS round-trip proof.

    Args:
        args: Namespace with source ``image`` and rebuilt ``output`` paths.

    Raises:
        OSError: If either path cannot be read or written.
        FdsFormatError: If parsing/rebuilding fails.
        SystemExit: If rebuilt bytes differ from the source.

    Side Effects:
        Writes the rebuilt image and prints both SHA-256 hashes plus status.
    """

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
    """Run the multi-image side-combination command.

    Args:
        args: Namespace containing ordered ``images`` and an ``output`` path.

    Raises:
        OSError: If an image cannot be read or output cannot be written.
        FdsFormatError: If parsing or rebuilding a side fails.
        ValueError: If no source images are supplied programmatically.

    Side Effects:
        Creates the output directory, writes the combined image, and prints
        its path and side count.
    """

    image = combine_images([FdsImage.read(path) for path in args.images])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.write(args.output)
    print(f"{args.output} ({len(image.sides)} sides)")


def command_scenario_extract(args: argparse.Namespace) -> None:
    """Run scenario extraction while retaining compatible English edits.

    Args:
        args: Namespace with extracted ``bank`` and destination ``output``.

    Raises:
        OSError: If either file cannot be read or written.
        JSONDecodeError: If an existing output file is not valid JSON.
        ScenarioError: If bank pointers or packed records are invalid.

    Side Effects:
        Creates parent directories and replaces ``output`` with formatted
        UTF-8 JSON. Existing English is retained only when group and record
        coordinates still match; Japanese and raw symbols are always refreshed.
    """

    bank = parse_scenario_bank(args.bank)
    bank_name = infer_bank_name(args.bank, getattr(args, "bank_name", None))
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
    """Run scenario insertion with control and RAM-footprint validation.

    Args:
        args: Namespace with source ``bank``, merged ``translation`` JSON,
            destination ``output``, and ``no_compress`` flag.

    Raises:
        OSError: If files cannot be read or written.
        JSONDecodeError: If translation JSON is malformed.
        SystemExit: If group/record counts, field types, or control sequences
            differ from the source.
        EnglishTextError: If translated text cannot be encoded.
        ScenarioError: If packed data cannot fit the preserved bank footprint.

    Side Effects:
        Creates the output directory, writes the rebuilt bank, and prints
        translation/compression statistics.

    A partial translation retains the Japanese dictionary because untranslated
    source records may still reference it. A complete translation normally
    builds a deterministic English dictionary.
    """

    bank = parse_scenario_bank(args.bank)
    bank_name = infer_bank_name(args.bank, getattr(args, "bank_name", None))
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
            required_entries=required_dictionary_entries(bank_name),
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
    """Validate and merge English text by stable record ID.

    Args:
        document: Scenario-extract JSON object.
        translations: Mapping from stable IDs to nonempty English strings.
        require_complete: Require every scenario ID to be present.

    Returns:
        A deep copy of ``document`` with validated ``english`` fields replaced.
        Neither input mapping is modified.

    Raises:
        SystemExit: If document IDs are missing/duplicated, translation IDs are
            unknown/incomplete, values are invalid, controls differ, a segment
            is display-unsafe, or a character cannot be encoded.

    Personality-test records are the only records allowed to use validated
    automatic wrapping; all other control-delimited segments must fit one row.
    """

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
    """Run the translation-map merge command.

    Args:
        args: Namespace with ``scenario``, ``translations``, optional
            ``output``, and ``allow_partial``.

    Raises:
        OSError: If input/output files cannot be accessed.
        JSONDecodeError: If either input is malformed.
        SystemExit: If either root is not an object or merge validation fails.

    Side Effects:
        Writes formatted UTF-8 JSON to ``output`` or updates ``scenario`` in
        place, then prints the destination.
    """

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
    """Report native scenario capacity and optionally simulate compression.

    Args:
        args: Namespace with source ``bank`` and optional ID-keyed
            ``translations`` JSON.

    Raises:
        OSError: If input files cannot be read.
        ScenarioError: If the bank layout is invalid.
        SystemExit: If translation IDs/text/controls are invalid or the
            complete compressed result exceeds the fixed reservation.

    Side Effects:
        Prints bank layout, translation progress, and final footprint. No files
        are modified.

    Pointer-table bytes are included in final usage because each group after
    group zero adds one two-byte loaded address.
    """

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
    bank_name = infer_bank_name(args.bank, getattr(args, "bank_name", None))
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
        required_entries=required_dictionary_entries(bank_name),
    )
    used = packed_size(compressed_groups, dictionary) + 2 * (len(groups) - 1)
    print(
        f"final compressed footprint: {used}/{capacity} bytes; "
        f"remaining: {capacity - used} bytes"
    )
    if used > capacity:
        raise SystemExit(f"translation exceeds fixed RAM reservation by {used - capacity} bytes")


def command_font_patch(args: argparse.Namespace) -> None:
    """Run the deterministic NOV4 dialogue-font patch.

    Args:
        args: Namespace with source ``nov4`` and destination ``output`` paths.

    Raises:
        OSError: If files cannot be read or written.
        FontPatchError: If NOV4 is incompatible or a glyph is unavailable.

    Side Effects:
        Creates the destination directory, writes patched NOV4, and prints its
        path.
    """

    patched = patched_nov4_font(args.nov4.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(args.output)


def command_title_patch(args: argparse.Namespace) -> None:
    """Run the English title-asset conversion and NOV4 relocation.

    Args:
        args: Namespace with source ``nov4``, reference ``target``, destination
            ``output``, and subtitle string.

    Raises:
        OSError: If source/reference/output files cannot be accessed.
        TitlePatchError: If revision, artwork, capacity, or verification checks
            fail.

    Side Effects:
        Creates the destination directory, writes expanded NOV4, and prints its
        path.
    """

    patched = patched_nov4_title(
        args.nov4.read_bytes(),
        args.target,
        subtitle=args.subtitle,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(args.output)


def command_ui_patch(args: argparse.Namespace) -> None:
    """Run the selected fixed-UI/program patch.

    Args:
        args: Namespace with ``component``, source ``source``, and destination
            ``output``.

    Raises:
        OSError: If source/output files cannot be accessed.
        KeyError: If called programmatically with an unsupported component.
        UiPatchError: If the component or fixed slots do not match the guarded
            source.

    Side Effects:
        Creates the destination directory, writes the patched component, and
        prints its path.
    """

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
    """Run guarded replacement of one named FDS payload.

    Args:
        args: Namespace with source ``image``, zero-based ``side``, exact
            ``name``, replacement ``data``, and output image path.

    Raises:
        OSError: If inputs/output cannot be accessed.
        SystemExit: If the side index is outside the image.
        KeyError: If the filename is missing or nonunique on the side.
        FdsFormatError: If the rebuilt payloads exceed side capacity.

    Side Effects:
        Mutates the parsed in-memory file entry, writes a new image, and prints
        its destination. The source image on disk is never overwritten unless
        the caller explicitly chooses the same output path.
    """

    image = FdsImage.read(args.image)
    if args.side < 0 or args.side >= len(image.sides):
        raise SystemExit(f"side {args.side} is outside this image")
    entry = image.sides[args.side].find_file(args.name)
    entry.data = args.data.read_bytes()
    image.write(args.output)
    print(args.output)



def command_release_lock(args: argparse.Namespace) -> None:
    """Validate or intentionally refresh the approved release-source lock."""

    project_root = discover_project_root(args.project_root)
    lock_path = args.lock or project_root / "work" / "release_sources.json"
    if args.update:
        payload = write_source_lock(lock_path, project_root=project_root)
        print(f"updated {lock_path} ({len(payload['files'])} approved files)")
    else:
        payload = validate_source_lock(lock_path, project_root=project_root)
        print(f"release source lock: PASS ({len(payload['files'])} files)")


def command_release_build(args: argparse.Namespace) -> None:
    """Build all release images and write a hash manifest."""

    project_root = discover_project_root(args.project_root)
    output_directory = args.output_dir or project_root / "build" / "release"
    manifest = build_release(
        output_directory,
        project_root=project_root,
        source_lock=args.lock,
        release_target=args.target,
        verify_target=not args.candidate,
    )
    print(f"mode: {manifest['mode']}")
    for name, record in manifest["outputs"].items():
        print(f"{name}: {record['path']} SHA-256 {record['sha256']}")
    print(output_directory.resolve() / "release_manifest.json")


def command_release_promote(args: argparse.Namespace) -> None:
    """Promote a reviewed candidate manifest into the strict release target."""

    project_root = discover_project_root(args.project_root)
    target = promote_release_target(
        args.candidate_manifest,
        target_path=args.target,
        project_root=project_root,
        release_id=args.release_id,
    )
    target_path = args.target or project_root / "work" / "release_target.json"
    print(f"promoted {target_path} ({target['release_id']})")

def build_parser() -> argparse.ArgumentParser:
    """Construct the complete command-line parser.

    Returns:
        Configured parser whose successful subcommand namespaces include a
        ``function`` callback.

    The function is side-effect free: it does not inspect the filesystem,
    import user configuration, or parse process arguments.
    """

    parser = argparse.ArgumentParser(
        prog="time-twist",
        description=(
            "Inspect, extract, translate, rebuild, and verify Time Twist "
            "Famicom Disk System images."
        ),
        epilog=(
            "All patch commands validate the recovered source layout. "
            "Original and patched ROM images are intentionally not stored "
            "in the repository."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    manifest = subparsers.add_parser(
        "manifest",
        help="describe every side and named FDS file as JSON",
        description=(
            "Parse an archival FDS image and report its header convention, "
            "disk metadata, side capacity, and named file layout."
        ),
    )
    manifest.add_argument("image", type=Path, help="source .fds image")
    manifest.add_argument(
        "--output",
        type=Path,
        help="write JSON to this file instead of standard output",
    )
    manifest.set_defaults(function=command_manifest)

    extract = subparsers.add_parser(
        "extract",
        help="extract every named FDS file payload",
        description=(
            "Write one .bin file per FDS file. Output names include side, "
            "file index, FDS name, and load address."
        ),
    )
    extract.add_argument("image", type=Path, help="source .fds image")
    extract.add_argument("output_dir", type=Path, help="destination directory")
    extract.set_defaults(function=command_extract)

    roundtrip = subparsers.add_parser(
        "roundtrip",
        help="prove lossless FDS parse/serialization",
        description=(
            "Parse and serialize an image, print both SHA-256 values, and "
            "fail unless the complete output is byte-identical."
        ),
    )
    roundtrip.add_argument("image", type=Path, help="source .fds image")
    roundtrip.add_argument("output", type=Path, help="rebuilt verification image")
    roundtrip.set_defaults(function=command_roundtrip)

    combine = subparsers.add_parser(
        "combine",
        help="combine sides from multiple FDS images",
        description=(
            "Append every side from each image in argument order. The first "
            "image determines whether the result has a 16-byte FDS header."
        ),
    )
    combine.add_argument(
        "images",
        nargs="+",
        type=Path,
        help="two or more source images in desired side order",
    )
    combine.add_argument(
        "--output",
        required=True,
        type=Path,
        help="combined output .fds path",
    )
    combine.set_defaults(function=command_combine)

    scenario_extract = subparsers.add_parser(
        "scenario-extract",
        help="decode a packed scenario bank to editable JSON",
        description=(
            "Decode group pointers, packed records, dictionary references, "
            "Japanese text, and raw symbols. Existing English in the output "
            "is retained at matching group/record coordinates."
        ),
    )
    scenario_extract.add_argument("bank", type=Path, help="extracted scenario .bin")
    scenario_extract.add_argument(
        "--bank-name",
        choices=(
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
            "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_extract.add_argument("output", type=Path, help="scenario JSON path")
    scenario_extract.set_defaults(function=command_scenario_extract)

    scenario_insert = subparsers.add_parser(
        "scenario-insert",
        help="encode translated JSON into a scenario bank",
        description=(
            "Rebuild scenario groups and pointers while retaining code/data "
            "outside the original text reservation. Fully translated banks "
            "receive a compact English dictionary."
        ),
    )
    scenario_insert.add_argument("bank", type=Path, help="clean extracted bank")
    scenario_insert.add_argument(
        "--bank-name",
        choices=(
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
            "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_insert.add_argument(
        "translation",
        type=Path,
        help="merged scenario JSON containing English fields",
    )
    scenario_insert.add_argument("output", type=Path, help="rebuilt bank .bin")
    scenario_insert.add_argument(
        "--no-compress",
        action="store_true",
        help="diagnostic: preserve the original dictionary on a complete bank",
    )
    scenario_insert.set_defaults(function=command_scenario_insert)

    scenario_merge = subparsers.add_parser(
        "scenario-merge",
        help="validate and merge an ID-keyed English map",
        description=(
            "Merge translations into extracted scenario JSON while checking "
            "IDs, control order, display width, and font encodability."
        ),
    )
    scenario_merge.add_argument(
        "scenario",
        type=Path,
        help="scenario-extract JSON document",
    )
    scenario_merge.add_argument(
        "translations",
        type=Path,
        help="JSON object mapping record IDs to English",
    )
    scenario_merge.add_argument(
        "--output",
        type=Path,
        help="destination scenario JSON (default: update SCENARIO)",
    )
    scenario_merge.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow translation IDs to cover only part of the bank",
    )
    scenario_merge.set_defaults(function=command_scenario_merge)

    scenario_footprint = subparsers.add_parser(
        "scenario-footprint",
        help="report fixed text capacity and compressed usage",
        description=(
            "Show the scenario reservation and fixed tail. With a complete "
            "translation map, build the English dictionary and report "
            "remaining bytes or a hard overrun."
        ),
    )
    scenario_footprint.add_argument("bank", type=Path, help="clean extracted bank")
    scenario_footprint.add_argument(
        "--bank-name",
        choices=(
            "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B",
            "TT4", "TT5", "T25", "TT6A", "TT6B", "TT6C", "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_footprint.add_argument(
        "--translations",
        type=Path,
        help="optional ID-keyed English JSON map",
    )
    scenario_footprint.set_defaults(function=command_scenario_footprint)

    font_patch = subparsers.add_parser(
        "font-patch",
        help="install the translated 8x8 dialogue font",
        description=(
            "Replace recovered NOV4 font-table glyph rows without changing "
            "the component's size."
        ),
    )
    font_patch.add_argument("nov4", type=Path, help="source NOV4 .bin")
    font_patch.add_argument("output", type=Path, help="patched NOV4 .bin")
    font_patch.set_defaults(function=command_font_patch)

    title_patch = subparsers.add_parser(
        "title-patch",
        help="build and install the English title assets",
        description=(
            "Install a reviewed native 256x240 indexed NES title asset, retain "
            "the animated clock sprites, and append relocated NOV4 helpers "
            "and nametables below resident NOV3."
        ),
    )
    title_patch.add_argument("nov4", type=Path, help="source/patched-size NOV4 .bin")
    title_patch.add_argument(
        "target",
        type=Path,
        help="approved 256x240 indexed title image",
    )
    title_patch.add_argument("output", type=Path, help="expanded NOV4 .bin")
    title_patch.add_argument(
        "--subtitle",
        default=DEFAULT_SUBTITLE,
        help=f"title subtitle (default: {DEFAULT_SUBTITLE!r})",
    )
    title_patch.set_defaults(function=command_title_patch)

    ui_patch = subparsers.add_parser(
        "ui-patch",
        help="apply a verified fixed UI/text-table patch",
        description=(
            "Patch one extracted component's fixed prompts, menu labels, "
            "commands, objects, quiz answers, or small input/program behavior."
        ),
    )
    ui_patch.add_argument("source", type=Path, help="source component .bin")
    ui_patch.add_argument("output", type=Path, help="patched component .bin")
    ui_patch.add_argument(
        "--component",
        choices=(
            "SON-KOUH", "NOV2", "NOV4", "TT1A", "TT1B", "TT2", "T22", "TT3A", "TT3B", "TT4",
            "TT5", "T25", "TT6A", "TT6B", "TT6C",
        ),
        default="NOV2",
        help="owning FDS component (default: NOV2)",
    )
    ui_patch.set_defaults(function=command_ui_patch)

    replace_file = subparsers.add_parser(
        "replace-file",
        help="replace one named file and rebuild its FDS image",
        description=(
            "Replace the unique FDS file NAME on zero-based SIDE, refresh its "
            "size field, and fail if the rebuilt side exceeds 65,500 bytes."
        ),
    )
    replace_file.add_argument("image", type=Path, help="input .fds image")
    replace_file.add_argument("side", type=int, help="zero-based side index")
    replace_file.add_argument("name", help="exact printable FDS filename")
    replace_file.add_argument("data", type=Path, help="replacement payload .bin")
    replace_file.add_argument("output", type=Path, help="rebuilt output .fds")
    replace_file.set_defaults(function=command_replace_file)

    release_lock = subparsers.add_parser(
        "release-lock",
        help="validate or update the approved release-input lock",
        description=(
            "Check all baseline, translation-map, and title-asset hashes. "
            "Use --update only when intentionally promoting edited sources."
        ),
    )
    release_lock.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_lock.add_argument(
        "--lock",
        type=Path,
        help="source-lock JSON path (default: PROJECT/work/release_sources.json)",
    )
    release_lock.add_argument(
        "--update",
        action="store_true",
        help="rewrite the lock from the current approved source files",
    )
    release_lock.set_defaults(function=command_release_lock)

    release_build = subparsers.add_parser(
        "release-build",
        help="build Zenpen, Kouhen, and a combined four-side image",
        description=(
            "Validate the approved source lock, rebuild every scenario bank, "
            "apply fixed UI/font/title patches, and emit output hashes."
        ),
    )
    release_build.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_build.add_argument(
        "--output-dir",
        type=Path,
        help="output directory (default: PROJECT/build/release)",
    )
    release_build.add_argument(
        "--lock",
        type=Path,
        help="approved source-lock JSON path (default: PROJECT/work/release_sources.json)",
    )
    release_build.add_argument(
        "--target",
        type=Path,
        help="promoted output target (default: PROJECT/work/release_target.json)",
    )
    release_build.add_argument(
        "--candidate",
        action="store_true",
        help="publish an unpromoted candidate instead of verifying the release target",
    )
    release_build.set_defaults(function=command_release_build)

    release_promote = subparsers.add_parser(
        "release-promote",
        help="promote a reviewed candidate manifest into the release target",
        description=(
            "Verify every candidate output and its active source lock, then write "
            "the versioned target used by strict release builds."
        ),
    )
    release_promote.add_argument(
        "candidate_manifest",
        type=Path,
        help="candidate release_manifest.json produced by release-build --candidate",
    )
    release_promote.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_promote.add_argument(
        "--target",
        type=Path,
        help="target JSON path (default: PROJECT/work/release_target.json)",
    )
    release_promote.add_argument(
        "--release-id",
        help="human-readable target identifier (default: english-playtest)",
    )
    release_promote.set_defaults(function=command_release_promote)
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, run one command, and present expected failures cleanly."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.function(args)
    except (OSError, ValueError, KeyError, OverflowError, json.JSONDecodeError) as error:
        message = str(error)
        if isinstance(error, KeyError) and len(message) >= 2:
            message = message.strip("'\"")
        parser.exit(2, f"{parser.prog}: error: {message}\n")


if __name__ == "__main__":
    main()
