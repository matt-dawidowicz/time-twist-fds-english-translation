"""Build the full production translation with the frozen entropy codec.

This path is intentionally separate from the certified release builder and
from the discarded Adaptive255 spill candidate. It materializes the complete
production English script, builds a deterministic nested dictionary optimized
for the frozen entropy cost model, chooses the best NOV3-safe layout, converts
every decoder-visible fixed stream to the same entropy grammar, and then
installs the matching NOV2 entropy runtime directly.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

from .english import encode_english
from .entropy_codec import pack_entropy_pages, unpack_entropy_stream
from .entropy_compression import (
    EntropyCompressionResult,
    expand_entropy_dictionary,
    expand_entropy_record,
    optimize_entropy_dictionary,
    usage_pruned_entropy_variants,
)
from .entropy_fixed_ui import (
    entropy_fixed_text_coverage,
    patched_nov4_entropy_text,
    patched_tt1a_entropy_ui,
    tt1a_renderer_entropy_payload,
)
from .entropy_runtime import NOV3_LOAD_ADDRESS, patch_entropy_nov2
from .entropy_scenario import (
    EntropyScenarioError,
    EntropyScenarioLayout,
    build_entropy_scenario_bank,
    relocate_entropy_fixed_record_table,
    validate_entropy_scenario_bank,
)
from .entropy_title import patched_nov4_entropy_title
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .production_release import (
    ProductionBuildError,
    _encoded_groups,
    _load_translation_map,
    _semantic_record,
    _sha256,
)
from .project import source_dictionary_reference_floor
from .release_metadata import SCENARIO_LOCATIONS
from .scenario import parse_scenario_bank
from .textcodec import PackedSymbol
from .title import DEFAULT_SUBTITLE
from .ui import (
    FIXED_RECORD_PAGE_POINTER_OFFSET,
    FIXED_RECORD_TABLE_SPECS,
    FIXED_RECORDS_PER_PAGE,
    UiPatchError,
    fixed_record_table_page_pointer_bytes,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
)

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]


@dataclass(frozen=True)
class EntropyProductionBankResult:
    """One entropy-coded scenario bank plus exact capacity statistics."""

    data: bytes
    records: int
    dictionary_entries: int
    scenario_bytes: int
    menu_bytes: int
    dictionary_bytes: int
    optimizer_bytes: int
    source_bytes: int
    resident_groups: tuple[int, ...]
    spilled_groups: tuple[int, ...]
    spill_bytes: int
    loaded_end: int

    @property
    def headroom(self) -> int:
        """Return bytes remaining before the exact NOV3 load address."""
        return NOV3_LOAD_ADDRESS - self.loaded_end


def _dictionary_key(dictionary: ScenarioDictionary) -> tuple[object, ...]:
    """Support the dictionary key operation for this module."""
    return tuple(
        tuple((symbol.kind.value, symbol.value) for symbol in record)
        for record in dictionary
    )


def _menu_bytes(records: tuple[tuple[PackedSymbol, ...], ...]) -> int:
    """Support the menu bytes operation for this module."""
    if not records:
        return 0
    packed, _ = pack_entropy_pages(
        records,
        records_per_page=FIXED_RECORDS_PER_PAGE,
    )
    return len(packed)


def _build_variant_layout(
    source: bytes,
    bank,
    bank_name: str,
    variant: EntropyCompressionResult,
    *,
    prg_ram_end: int = NOV3_LOAD_ADDRESS,
) -> tuple[EntropyScenarioLayout, int]:
    """Build variant layout."""
    text_start = bank.group_addresses[0] - bank.load_address
    if bank_name in FIXED_RECORD_TABLE_SPECS:
        base_data, region_start = relocate_entropy_fixed_record_table(
            source,
            bank_name=bank_name,
            load_address=bank.load_address,
            group_zero_offset=text_start,
            records=variant.menu,
        )
        menu_bytes = _menu_bytes(variant.menu)
    else:
        base_data = source
        region_start = text_start
        menu_bytes = 0
    layout = build_entropy_scenario_bank(
        bank,
        variant.groups,
        variant.dictionary,
        base_data=base_data,
        old_region_start=region_start,
        prg_ram_end=prg_ram_end,
    )
    return layout, menu_bytes


ENTROPY_DICTIONARY_ENTRY_CAPS: dict[str, int] = {
    # TT2 reaches the same NOV3-safe boundary with 96 entries. Extending its
    # grammar search to 128 adds substantial optimizer time without improving
    # the selected loaded end.
    "TT2": 96,
}


def _select_safe_variant(
    source: bytes,
    bank,
    bank_name: str,
    literal_groups: ScenarioGroups,
    literal_menu: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[EntropyCompressionResult, EntropyScenarioLayout, int]:
    """Select safe variant."""
    base = optimize_entropy_dictionary(
        literal_groups,
        literal_menu,
        maximum_entries=ENTROPY_DICTIONARY_ENTRY_CAPS.get(bank_name, 128),
        maximum_grammar_tokens=12,
        maximum_nesting_depth=4,
        trial_candidates=8,
    )
    variants = usage_pruned_entropy_variants(
        base,
        literal_groups,
        literal_menu,
        search_depth=16,
    )

    safe: list[
        tuple[
            tuple[object, ...],
            EntropyCompressionResult,
            EntropyScenarioLayout,
            int,
        ]
    ] = []
    for variant in variants:
        try:
            layout, menu_bytes = _build_variant_layout(
                source,
                bank,
                bank_name,
                variant,
            )
        except (EntropyScenarioError, UiPatchError):
            continue
        total_bytes = (
            sum(layout.group_bytes) + layout.dictionary_bytes + menu_bytes
        )
        key: tuple[object, ...] = (
            layout.loaded_end,
            layout.spill_bytes,
            total_bytes,
            len(variant.dictionary),
            _dictionary_key(variant.dictionary),
        )
        safe.append((key, variant, layout, menu_bytes))

    if safe:
        _, variant, layout, menu_bytes = min(safe, key=lambda item: item[0])
        return variant, layout, menu_bytes

    closest: tuple[int, int] | None = None
    for variant in variants:
        try:
            layout, _ = _build_variant_layout(
                source,
                bank,
                bank_name,
                variant,
                prg_ram_end=0xFFFF,
            )
        except (EntropyScenarioError, UiPatchError):
            continue
        candidate = (layout.loaded_end, len(variant.dictionary))
        if closest is None or candidate < closest:
            closest = candidate
    detail = (
        "no structurally valid entropy layout"
        if closest is None
        else (
            f"closest layout ends at ${closest[0]:04X} with "
            f"{closest[1]} dictionary entries"
        )
    )
    raise ProductionBuildError(
        f"{bank_name} cannot fit below NOV3 at ${NOV3_LOAD_ADDRESS:04X}; "
        f"{detail}"
    )


def _audit_menu(
    data: bytes,
    bank_name: str,
    dictionary: ScenarioDictionary,
    literal_menu: tuple[tuple[PackedSymbol, ...], ...],
) -> None:
    """Decode every byte-addressed menu page and prove semantic equality."""
    if not literal_menu:
        return
    spec = FIXED_RECORD_TABLE_SPECS[bank_name]
    page_index_address = int.from_bytes(
        data[
            FIXED_RECORD_PAGE_POINTER_OFFSET : FIXED_RECORD_PAGE_POINTER_OFFSET
            + 2
        ],
        "little",
    )
    page_index_offset = page_index_address - 0xA200
    pointer_bytes = fixed_record_table_page_pointer_bytes(bank_name)
    page_starts = [spec.start]
    page_starts.extend(
        int.from_bytes(data[offset : offset + 2], "little") - 0xA200
        for offset in range(
            page_index_offset,
            page_index_offset + pointer_bytes,
            2,
        )
    )
    page_ends = (*page_starts[1:], page_index_offset)
    decoded: list[tuple[PackedSymbol, ...]] = []
    for page_index, (start, end) in enumerate(
        zip(page_starts, page_ends, strict=True)
    ):
        remaining = len(literal_menu) - page_index * FIXED_RECORDS_PER_PAGE
        count = min(FIXED_RECORDS_PER_PAGE, remaining)
        decoded.extend(
            unpack_entropy_stream(
                data[start:end],
                record_count=count,
            )
        )
    if len(decoded) != len(literal_menu):
        raise ProductionBuildError(
            f"{bank_name} entropy menu decoded {len(decoded)} records, "
            f"expected {len(literal_menu)}"
        )
    expansions = expand_entropy_dictionary(dictionary)
    for index, (packed, expected) in enumerate(
        zip(decoded, literal_menu, strict=True)
    ):
        expanded = expand_entropy_record(packed, expansions)
        if _semantic_record(expanded) != _semantic_record(expected):
            raise ProductionBuildError(
                f"{bank_name} menu record {index} failed entropy round-trip"
            )


def build_entropy_scenario_candidate(
    source: bytes,
    bank_name: str,
    *,
    translations_directory: Path,
) -> EntropyProductionBankResult:
    """Rebuild one Japanese scenario overlay into the NOV3-safe entropy layout."""
    with tempfile.TemporaryDirectory(
        prefix=f"time_twist_entropy_{bank_name}_"
    ) as directory:
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
    literal_menu: tuple[tuple[PackedSymbol, ...], ...]
    if bank_name in FIXED_RECORD_TABLE_SPECS:
        literal_menu = tuple(
            encode_english(text)
            for text in FIXED_RECORD_TABLE_SPECS[bank_name].records
        )
    else:
        literal_menu = ()

    variant, layout, menu_bytes = _select_safe_variant(
        source,
        bank,
        bank_name,
        literal_groups,
        literal_menu,
    )

    # TT1A is the one scenario bank whose selector table has two native access
    # contracts. Direct entry points retain address-stable one-record entropy
    # mirrors, while the generic NOV2 renderer scans a separate contiguous copy
    # through $A214. The renderer copy is appended after the scenario layout.
    if bank_name == "TT1A":
        patched = patched_tt1a_entropy_ui(layout.data)
        layout = replace(layout, data=patched)
        menu_bytes = len(tt1a_renderer_entropy_payload())
        validate_entropy_scenario_bank(
            bank,
            literal_groups,
            variant.dictionary,
            layout,
        )

    if literal_menu:
        _audit_menu(
            layout.data,
            bank_name,
            variant.dictionary,
            literal_menu,
        )

    if layout.loaded_end > NOV3_LOAD_ADDRESS:
        raise ProductionBuildError(
            f"{bank_name} entropy layout crosses NOV3: "
            f"${layout.loaded_end:04X} > ${NOV3_LOAD_ADDRESS:04X}"
        )
    return EntropyProductionBankResult(
        data=layout.data,
        records=len(bank.records),
        dictionary_entries=len(variant.dictionary),
        scenario_bytes=sum(layout.group_bytes),
        menu_bytes=menu_bytes,
        dictionary_bytes=layout.dictionary_bytes,
        optimizer_bytes=variant.optimizer_bytes,
        source_bytes=len(source),
        resident_groups=layout.resident_groups,
        spilled_groups=layout.spilled_groups,
        spill_bytes=layout.spill_bytes,
        loaded_end=layout.loaded_end,
    )


def build_entropy_images(
    zenpen_raw: bytes,
    kouhen_raw: bytes,
    *,
    translations_directory: Path,
    title_asset: Path,
    slide_title_asset: Path,
    subtitle: str = DEFAULT_SUBTITLE,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Build Zenpen, Kouhen, and four-side frozen-entropy playtest images."""
    zenpen = FdsImage.from_bytes(zenpen_raw)
    kouhen = FdsImage.from_bytes(kouhen_raw)
    images = {"zenpen": zenpen, "kouhen": kouhen}
    bank_report: dict[str, dict[str, object]] = {}

    for bank_name, (image_name, side) in SCENARIO_LOCATIONS.items():
        entry = images[image_name].sides[side].find_file(bank_name)
        result = build_entropy_scenario_candidate(
            entry.data,
            bank_name,
            translations_directory=translations_directory,
        )
        entry.data = result.data
        bank_report[bank_name] = {
            "records": result.records,
            "dictionary_entries": result.dictionary_entries,
            "scenario_bytes": result.scenario_bytes,
            "menu_bytes": result.menu_bytes,
            "dictionary_bytes": result.dictionary_bytes,
            "optimizer_bytes": result.optimizer_bytes,
            "source_bytes": result.source_bytes,
            "grown_bytes": len(result.data) - result.source_bytes,
            "resident_groups": list(result.resident_groups),
            "spilled_groups": list(result.spilled_groups),
            "spill_bytes": result.spill_bytes,
            "loaded_end": f"0x{result.loaded_end:04X}",
            "nov3_headroom": result.headroom,
            "sha256": _sha256(result.data),
        }

    nov2 = patched_nov2_ui(zenpen.sides[0].find_file("NOV2").data)
    nov2 = patch_entropy_nov2(nov2)
    zenpen.sides[0].find_file("NOV2").data = nov2

    # The font patch retains a strict whole-bank source whitelist, so keep it
    # first.  Entropy conversion follows and owns every NOV4 packed-text stream
    # consumed by NOV2.  Title expansion is last and validates only the title
    # regions it owns.  The native patched_nov4_ui path is intentionally absent:
    # inserting byte-aligned native records here caused the R5 blank START menu.
    nov4 = zenpen.sides[0].find_file("NOV4").data
    nov4 = patched_nov4_font(nov4)
    nov4 = patched_nov4_entropy_text(nov4)
    nov4 = patched_nov4_entropy_title(
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
        "schema": "Time Twist frozen entropy production candidate v2",
        "codec": "frozen-entropy-v1",
        "decoder_format": "entropy-only",
        "record_framing": (
            "bit-contiguous within every independently addressed stream; "
            "menu pages begin on byte boundaries"
        ),
        "fixed_decoder_surfaces": entropy_fixed_text_coverage(),
        "nov3_exclusive_boundary": f"0x{NOV3_LOAD_ADDRESS:04X}",
        "subtitle": subtitle,
        "scenario_records": sum(
            cast(int, record["records"]) for record in bank_report.values()
        ),
        "scenario_banks": bank_report,
        "components": {
            "NOV2": _sha256(nov2),
            "NOV4": _sha256(nov4),
            "SON-KOUH": _sha256(kouhen.sides[0].find_file("SON-KOUH").data),
        },
        "outputs": {
            name: {"bytes": len(data), "sha256": _sha256(data)}
            for name, data in output.items()
        },
    }
    return output, manifest
