"""Build an unrestricted production-localization candidate from Japanese FDS.

This path is deliberately separate from the certified release builder. It uses
materialized production maps, the adaptive 255-entry codec, and group-level
high-RAM spill placement while retaining all source guards for menus, fonts,
title assets, and disk boot behavior.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from .compression import compress_english_groups, expand_dictionary_symbols
from .english import encode_english
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .production_codec import (
    PRODUCTION_DICTIONARY_ENTRY_COUNT,
    ScenarioDictionary,
    ScenarioGroups,
    compress_production_groups,
    production_packed_size,
    split_production_records,
)
from .production_runtime import patch_nov2
from .production_scenario import (
    ProductionScenarioLayout,
    build_spill_scenario_bank,
    relocate_production_fixed_record_table,
    validate_spill_scenario_bank,
)
from .production_validation import encode_production_english
from .project import source_dictionary_reference_floor
from .release_metadata import SCENARIO_LOCATIONS, SCENARIO_UI_PATCHERS
from .scenario import ScenarioBank, parse_scenario_bank, render_symbols
from .scenario_validation import scenario_record_id
from .textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT, PackedSymbol
from .title import DEFAULT_SUBTITLE, patched_nov4_title
from .ui import (
    FIXED_RECORD_TABLE_SPECS,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
)


class ProductionBuildError(ValueError):
    """Report a failed production source guard, translation, or round-trip."""


@dataclass(frozen=True)
class ProductionBankResult:
    """One rebuilt scenario overlay plus compression/spill statistics."""

    data: bytes
    records: int
    dictionary_entries: int
    packed_bytes: int
    source_bytes: int
    resident_groups: tuple[int, ...]
    spilled_groups: tuple[int, ...]
    spill_bytes: int
    dictionary_bytes: int
    loaded_end: int


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _load_translation_map(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductionBuildError(f"cannot load production map: {path}") from error
    if not isinstance(payload, dict):
        raise ProductionBuildError(f"production map is not an object: {path}")
    result: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value:
            raise ProductionBuildError(
                f"production map must contain nonempty string pairs: {path}"
            )
        result[key] = value
    return result


def _encoded_groups(
    bank: ScenarioBank,
    bank_name: str,
    translations: dict[str, str],
) -> ScenarioGroups:
    records_by_id = {
        scenario_record_id(bank_name, record.group_index, record.record_index): record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    missing = sorted(set(records_by_id) - set(translations))
    if unknown or missing:
        raise ProductionBuildError(
            f"{bank_name} production IDs differ from source; "
            f"unknown={unknown[:1]}, missing={missing[:1]}"
        )

    encoded: dict[str, tuple[PackedSymbol, ...]] = {}
    for record_id, record in records_by_id.items():
        japanese = render_symbols(record.symbols, bank.dictionary)
        encoded[record_id] = encode_production_english(
            record_id,
            translations[record_id],
            japanese,
        )

    return tuple(
        tuple(
            encoded[
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


def _compress(
    groups: ScenarioGroups,
    *,
    adaptive_dictionary: bool,
) -> tuple[ScenarioGroups, ScenarioDictionary]:
    if adaptive_dictionary:
        return compress_production_groups(
            groups,
            maximum_entries=PRODUCTION_DICTIONARY_ENTRY_COUNT,
        )
    compressed, dictionary = compress_english_groups(
        groups,
        maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
        optimize=False,
    )
    return compressed, dictionary


def _audit_menu(
    data: bytes,
    bank_name: str,
    dictionary: ScenarioDictionary,
) -> None:
    """Decode every relocated menu label and compare it with canonical text."""
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    records, _ = split_production_records(
        data,
        offset=spec.start,
        limit=len(spec.records),
    )
    for index, (record, expected_text) in enumerate(
        zip(records, spec.records, strict=True)
    ):
        expanded = expand_dictionary_symbols(record, dictionary)
        expected = encode_english(expected_text)
        if expanded != expected:
            raise ProductionBuildError(
                f"{bank_name} menu record {index} failed production round-trip"
            )


def build_production_scenario_bank(
    source: bytes,
    bank_name: str,
    *,
    translations_directory: Path,
    adaptive_dictionary: bool = True,
) -> ProductionBankResult:
    """Rebuild one Japanese scenario overlay into the production spill layout."""
    with tempfile.TemporaryDirectory(prefix=f"time_twist_{bank_name}_") as directory:
        source_path = Path(directory) / f"{bank_name}.bin"
        source_path.write_bytes(source)
        bank = parse_scenario_bank(
            source_path,
            minimum_dictionary_entries=source_dictionary_reference_floor(
                bank_name,
                source,
            ),
        )

    translations = _load_translation_map(
        translations_directory / f"{bank_name}.json"
    )
    literal_groups = _encoded_groups(bank, bank_name, translations)
    text_start = bank.group_addresses[0] - bank.load_address

    if bank_name in FIXED_RECORD_TABLE_SPECS:
        menu_literals = tuple(
            encode_english(text) for text in FIXED_RECORD_TABLE_SPECS[bank_name].records
        )
        compressed_all, dictionary = _compress(
            (*literal_groups, menu_literals),
            adaptive_dictionary=adaptive_dictionary,
        )
        compressed_groups = compressed_all[:-1]
        compressed_menu = compressed_all[-1]
        base_data, region_start = relocate_production_fixed_record_table(
            source,
            bank_name=bank_name,
            load_address=bank.load_address,
            group_zero_offset=text_start,
            records=compressed_menu,
        )
    else:
        compressed_groups, dictionary = _compress(
            literal_groups,
            adaptive_dictionary=adaptive_dictionary,
        )
        base_data = source
        region_start = text_start

    layout = build_spill_scenario_bank(
        bank,
        compressed_groups,
        dictionary,
        base_data=base_data,
        old_region_start=region_start,
    )

    patcher = SCENARIO_UI_PATCHERS.get(bank_name)
    if patcher is not None:
        patched = patcher(layout.data)
        if len(patched) != len(layout.data):
            raise ProductionBuildError(f"{bank_name} fixed UI patch changed file size")
        layout = replace(layout, data=patched)
        # TT1A's fixed selectors precede group zero. Scenario streams and the
        # dictionary must still decode identically after that direct-address patch.
        validate_spill_scenario_bank(bank, literal_groups, dictionary, layout)

    if bank_name in FIXED_RECORD_TABLE_SPECS:
        _audit_menu(layout.data, bank_name, dictionary)

    return ProductionBankResult(
        data=layout.data,
        records=len(bank.records),
        dictionary_entries=len(dictionary),
        packed_bytes=production_packed_size(compressed_groups, dictionary),
        source_bytes=len(source),
        resident_groups=layout.resident_groups,
        spilled_groups=layout.spilled_groups,
        spill_bytes=layout.spill_bytes,
        dictionary_bytes=layout.dictionary_bytes,
        loaded_end=layout.loaded_end,
    )


def build_production_images(
    zenpen_raw: bytes,
    kouhen_raw: bytes,
    *,
    translations_directory: Path,
    title_asset: Path,
    slide_title_asset: Path,
    subtitle: str = DEFAULT_SUBTITLE,
    adaptive_dictionary: bool = True,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Build Zenpen, Kouhen, and combined four-side production candidates."""
    zenpen = FdsImage.from_bytes(zenpen_raw)
    kouhen = FdsImage.from_bytes(kouhen_raw)
    images = {"zenpen": zenpen, "kouhen": kouhen}
    bank_report: dict[str, dict[str, object]] = {}

    for bank_name, (image_name, side) in SCENARIO_LOCATIONS.items():
        entry = images[image_name].sides[side].find_file(bank_name)
        result = build_production_scenario_bank(
            entry.data,
            bank_name,
            translations_directory=translations_directory,
            adaptive_dictionary=adaptive_dictionary,
        )
        entry.data = result.data
        bank_report[bank_name] = {
            "records": result.records,
            "dictionary_entries": result.dictionary_entries,
            "packed_bytes": result.packed_bytes,
            "source_bytes": result.source_bytes,
            "grown_bytes": len(result.data) - result.source_bytes,
            "resident_groups": list(result.resident_groups),
            "spilled_groups": list(result.spilled_groups),
            "spill_bytes": result.spill_bytes,
            "dictionary_bytes": result.dictionary_bytes,
            "loaded_end": f"0x{result.loaded_end:04X}",
            "sha256": _sha256(result.data),
        }

    nov2 = patched_nov2_ui(zenpen.sides[0].find_file("NOV2").data)
    nov2 = patch_nov2(nov2, adaptive_dictionary=adaptive_dictionary)
    zenpen.sides[0].find_file("NOV2").data = nov2

    nov4 = patched_nov4_ui(zenpen.sides[0].find_file("NOV4").data)
    nov4 = patched_nov4_font(nov4)
    nov4 = patched_nov4_title(
        nov4,
        title_asset,
        slide_target=slide_title_asset,
        subtitle=subtitle,
    )
    zenpen.sides[0].find_file("NOV4").data = nov4

    son_kouh = kouhen.sides[0].find_file("SON-KOUH").data
    kouhen.sides[0].find_file("SON-KOUH").data = patched_kouhen_boot_guard(
        son_kouh
    )

    output = {
        "zenpen": zenpen.to_bytes(),
        "kouhen": kouhen.to_bytes(),
    }
    output["four_side"] = combine_images([zenpen, kouhen]).to_bytes()
    manifest: dict[str, object] = {
        "schema": "Time Twist production localization candidate v1",
        "adaptive_dictionary": adaptive_dictionary,
        "subtitle": subtitle,
        "scenario_records": sum(
            int(record["records"]) for record in bank_report.values()
        ),
        "scenario_banks": bank_report,
        "components": {
            "NOV2": _sha256(nov2),
            "NOV4": _sha256(nov4),
            "SON-KOUH": _sha256(
                kouhen.sides[0].find_file("SON-KOUH").data
            ),
        },
        "outputs": {
            name: {"bytes": len(data), "sha256": _sha256(data)}
            for name, data in output.items()
        },
    }
    return output, manifest
