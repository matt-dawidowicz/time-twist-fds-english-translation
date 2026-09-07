"""Public capacity facts for rebuilt English scenario banks.

NATIVE_SCENARIO_CAPACITY_BYTES records the native scenario reservation from
scenario group zero through the last source dictionary entry required by that
bank.  Canonical full-word menu releases reclaim a second, disjoint region:
from the original fixed-table base through the first following pointer-addressed
structure.  ``release.fixed_record_table_combined_capacity`` verifies the same
boundaries directly against the locked source bytes at build time.

These values are therefore not extra/free disk space.  They are recovered RAM
bytes inside each source overlay that the relocation code already moves and
repoints safely.  Keeping the source-derived deltas here lets ROM-free CI
recompute current translation footprints against the same combined capacity as
the canonical release builder.
"""

from __future__ import annotations

from types import MappingProxyType

NATIVE_SCENARIO_CAPACITY_BYTES = MappingProxyType(
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


def playable_capacity(bank_name: str, scenario_capacity: int) -> int:
    """Return the canonical English text/menu capacity for one scenario bank.

    Non-relocated banks retain exactly their native scenario reservation.
    Relocated full-word-menu banks also use the source-verified movable prefix
    described above.  Structural pointer bytes still count as used bytes; this
    helper changes only the available capacity, not the packed-size model.
    """
    if scenario_capacity < 0:
        raise ValueError("scenario capacity must be nonnegative")
    return scenario_capacity + RELOCATED_FIXED_TABLE_PREFIX_BYTES.get(
        bank_name, 0
    )
