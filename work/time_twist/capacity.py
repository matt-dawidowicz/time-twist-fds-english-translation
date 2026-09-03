"""Public capacity facts for rebuilt English scenario banks.

The scenario-capacity table records the native reservation from scenario group
zero through the last source dictionary entry required by each bank. Canonical
full-word menu releases reclaim a second, disjoint region: from the original
fixed-table base through the first following pointer-addressed structure.
``release.fixed_record_table_combined_capacity`` verifies those same boundaries
directly against locked source bytes during a private ROM-backed build.

These values are not extra/free disk space. They are recovered RAM bytes inside
each source overlay that the relocation code already moves and repoints safely.
Keeping the source-derived capacities here lets ROM-free CI, compression audits,
and workbook generation evaluate the same fixed-footprint constraints without
requiring proprietary baseline ROMs.
"""

from __future__ import annotations

from types import MappingProxyType

SCENARIO_CAPACITY_BYTES = MappingProxyType(
    {
        "TT1A": 1669,
        "TT1B": 4026,
        "TT2": 3847,
        "T22": 1812,
        "TT3A": 3741,
        "TT3B": 1840,
        "TT4": 4741,
        "TT5": 3702,
        "T25": 2374,
        "TT6A": 2833,
        "TT6B": 2336,
        "TT6C": 3536,
        "TT6D": 332,
    }
)

RELOCATED_FIXED_TABLE_PREFIX_BYTES = MappingProxyType(
    {
        "TT1B": 208,
        "TT2": 294,
        "T22": 127,
        "TT3A": 428,
        "TT3B": 87,
        "TT4": 446,
        "TT5": 499,
        "T25": 187,
        "TT6A": 167,
        "TT6B": 265,
        "TT6C": 411,
    }
)


def playable_capacity(bank_name: str, scenario_capacity: int | None = None) -> int:
    """Return canonical English text/menu capacity for one scenario bank.

    Args:
        bank_name: Canonical scenario-bank identifier.
        scenario_capacity: Optional explicit native scenario reservation. When
            omitted, use :data:`SCENARIO_CAPACITY_BYTES`. Supplying an explicit
            value preserves callers that are validating an independently
            recovered source fact.

    Returns:
        Native scenario capacity plus any source-verified movable fixed-table
        prefix used by the canonical full-word-menu release architecture.

    Raises:
        ValueError: If no known capacity exists or an explicit value is negative.
    """
    if scenario_capacity is None:
        try:
            scenario_capacity = SCENARIO_CAPACITY_BYTES[bank_name]
        except KeyError as error:
            raise ValueError(f"unknown scenario bank {bank_name}") from error
    if scenario_capacity < 0:
        raise ValueError("scenario capacity must be nonnegative")
    return scenario_capacity + RELOCATED_FIXED_TABLE_PREFIX_BYTES.get(
        bank_name, 0
    )
