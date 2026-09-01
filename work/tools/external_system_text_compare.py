"""Logical layouts for repacked external NOV2/NOV4 system text.

The third-party comparison patch does not preserve the Japanese fixed-address
layout for these components.  Keep the recovered physical offsets here, away
from production parsers, so audits can decode corresponding records by stable
logical IDs without pretending source offsets survived the repack.

Only structural metadata is stored.  Third-party prose remains an ephemeral
diagnostic input and is never checked into the repository.
"""

from __future__ import annotations

from collections.abc import Iterable

from tools.external_translation_compare import Symbol, decode_fixed_records

# Logical source/runtime IDs mapped to physical record starts in the external
# patch.  NOV2 packs most of these into a shorter contiguous block.  NOV4
# appends a new packed table after the original 9,077-byte file and redirects
# the title/menu code to it.
EXTERNAL_SYSTEM_RECORD_OFFSETS: dict[str, tuple[tuple[str, int], ...]] = {
    "NOV2": (
        ("NOV2/wait", 0x25D9),
        ("NOV2/system/save_destination", 0x25E5),
        ("NOV2/system/saving_status", 0x25F6),
        ("NOV2/disk/r0", 0x25FC),
        ("NOV2/disk/r1", 0x2604),
        ("NOV2/disk/r2", 0x260C),
        ("NOV2/disk/r3", 0x2615),
        ("NOV2/disk/r4", 0x261E),
        ("NOV2/system/chapter_start", 0x262D),
        ("NOV2/system/disk_trouble", 0x2636),
        ("NOV2/system/ram_store", 0x263F),
        ("NOV2/save", 0x2645),
        ("NOV2/system/ram_fetch", 0x2649),
        ("NOV2/start", 0x264F),
        ("NOV2/load", 0x2654),
    ),
    "NOV4": (
        ("NOV4/start", 0x2384),
        ("NOV4/load", 0x2389),
    ),
}

# These two Japanese NOV2 records remain byte-identical at their original
# locations in both supplied external-patch inputs.  They therefore have no
# independent external English wording to compare.  Keeping that distinction
# explicit prevents an unchanged Japanese slot from being misreported as an
# aligned English translation.
EXTERNAL_SYSTEM_UNALIGNED_SOURCE_IDS: dict[str, tuple[str, ...]] = {
    "NOV2": ("NOV2/disk/r5", "NOV2/disk/r6"),
    "NOV4": (),
}

# The relocated NOV4 block is larger than the two gameplay-equivalent labels
# above.  This span describes the complete 26-record appended table so audits
# can prove its boundaries without assigning speculative source identities to
# diagnostic/menu entries that have no one-to-one canonical row.
EXTERNAL_NOV4_APPENDED_TABLE = (0x2375, 26)


def decode_external_named_records(
    data: bytes, layout: Iterable[tuple[str, int]]
) -> dict[str, list[Symbol]]:
    """Decode one record per declared logical ID at recovered external offsets."""
    decoded: dict[str, list[Symbol]] = {}
    seen_offsets: set[int] = set()
    for record_id, offset in layout:
        if not record_id:
            raise ValueError("external system record ID must not be empty")
        if record_id in decoded:
            raise ValueError(
                f"duplicate external system record ID: {record_id}"
            )
        if offset in seen_offsets:
            raise ValueError(
                f"duplicate external system record offset: {offset}"
            )
        records, _ = decode_fixed_records(data, offset, 1)
        decoded[record_id] = records[0]
        seen_offsets.add(offset)
    if not decoded:
        raise ValueError("at least one external system record is required")
    return decoded
