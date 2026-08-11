"""Hardened public facade for reproducible Time Twist release builds."""

from __future__ import annotations

from pathlib import Path

from . import _release_core as _core
from .compression import compress_english_groups, packed_size
from .english import EnglishTextError
from .project import (
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
from .scenario import (
    ScenarioBank,
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from .scenario_validation import encode_validated_english, scenario_record_id
from .textcodec import PackedSymbol

for _name in dir(_core):
    if not _name.startswith("__") and _name not in globals():
        globals()[_name] = getattr(_core, _name)
del _name

ReleaseBuildError = _core.ReleaseBuildError
ScenarioBuildResult = _core.ScenarioBuildResult
SCENARIO_UI_PATCHERS = _core.SCENARIO_UI_PATCHERS


def _encoded_groups(
    bank: ScenarioBank,
    bank_name: str,
    translations: dict[str, str],
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    """Validate release translations through the shared scenario policy."""
    records_by_id = {
        scenario_record_id(
            bank_name,
            record.group_index,
            record.record_index,
        ): record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    missing = sorted(set(records_by_id) - set(translations))
    if unknown or missing:
        raise ReleaseBuildError(
            f"{bank_name} translation IDs differ from the source; "
            f"unknown={unknown[:1]}, missing={missing[:1]}"
        )

    encoded: dict[str, tuple[PackedSymbol, ...]] = {}
    for record_id, record in records_by_id.items():
        japanese = render_symbols(record.symbols, bank.dictionary)
        try:
            encoded[record_id] = encode_validated_english(
                record_id,
                translations[record_id],
                japanese,
            )
        except EnglishTextError as error:
            raise ReleaseBuildError(
                f"invalid English in {record_id}: {error}"
            ) from error

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


def build_scenario_bank(
    source: bytes,
    bank_name: str,
    *,
    temporary_directory: Path,
    translations_directory: Path,
) -> ScenarioBuildResult:
    """Build one scenario bank with fixed-UI boundary and capacity guards."""
    source_path = temporary_directory / f"{bank_name}_source.bin"
    source_path.write_bytes(source)
    bank = parse_scenario_bank(
        source_path,
        minimum_dictionary_entries=source_dictionary_reference_floor(
            bank_name,
            source,
        ),
    )
    groups = _encoded_groups(
        bank,
        bank_name,
        _core._load_translation_map(bank_name, translations_directory),
    )
    text_start = bank.group_addresses[0] - bank.load_address
    capacity = bank.dictionary_end_offset - text_start
    pointer_bytes = 2 * (len(groups) - 1)
    compressed, dictionary = compress_english_groups(
        groups,
        required_entries=required_dictionary_entries(bank_name),
        max_bytes=capacity - pointer_bytes,
    )
    if bank_name in SCENARIO_UI_PATCHERS and len(dictionary) != 31:
        raise ReleaseBuildError(
            f"{bank_name} fixed UI requires exactly 31 dictionary entries; "
            f"compressor produced {len(dictionary)}"
        )
    rebuilt = rebuild_scenario_bank(
        bank,
        compressed,
        dictionary=dictionary,
        preserve_memory_footprint=True,
    )
    patcher = SCENARIO_UI_PATCHERS.get(bank_name)
    if patcher is not None:
        rebuilt = patcher(rebuilt)

    used = packed_size(compressed, dictionary) + pointer_bytes
    return ScenarioBuildResult(
        data=rebuilt,
        records=len(bank.records),
        dictionary_entries=len(dictionary),
        packed_bytes=used,
        capacity_bytes=capacity,
    )


# The original release orchestrator resolves these names in its module globals.
_core._encoded_groups = _encoded_groups
_core.build_scenario_bank = build_scenario_bank
