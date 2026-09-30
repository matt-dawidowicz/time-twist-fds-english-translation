"""Finalize the maintained build to the exact, playtested v50 release image.

The maintained pre-final build produces the v41 playtest baseline.  Late
playtesting deliberately used size/address-preserving binary edits for a small
set of runtime, wording, system-message, and ending-credit changes.  This
module makes those proven deltas reproducible source: every input component is
SHA-256 guarded, every output component is SHA-256 checked, and the complete
four-side image must match the canonical v50 release hash.

The embedded payload is a gzip-compressed JSON list of sparse replacement
spans.  It contains only patch deltas, not an original or patched FDS image.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from functools import lru_cache
from typing import TypedDict, cast

from .fds import FdsImage
from .release_metadata import ReleaseBuildError

FINAL_V50_SHA256 = (
    "820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43"
)
IMAGE_BYTES = 262000

# Canonical source text is the final v50 wording.  The frozen compiler must
# still receive these pre-finalizer literals so its output remains the exact
# v41 component state guarded by the sparse finalizer below.
PREFINAL_SCENARIO_RECORDS = {
    "TT5/g2/r18": "What was Edison's third{CTRL:0}great invention besides{CTRL:0}the phonograph and{CTRL:0}generator?",
    "T25/g0/r6": "He's lost in thought.",
}

FINAL_SCENARIO_RECORDS = {
    "TT5/g2/r18": "Edison's three great{CTRL:0}inventions were the{CTRL:0}phonograph, the{CTRL:0}generator, and what?",
    "T25/g0/r6": "The sky darkens.",
}

# Final visible system wording represented by the NOV2 sparse delta.
FINAL_WRONG_DISK_RETRY = "{CTRL:0}Try another side."

_PATCH_PAYLOAD_B64 = "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"


def _sha256(data: bytes) -> str:
    """Return the uppercase SHA-256 used by release provenance."""
    return hashlib.sha256(data).hexdigest().upper()


class _PatchSpec(TypedDict):
    """Describe one source-guarded late-playtest component patch."""

    side: int
    size: int
    input_sha256: str
    output_sha256: str
    spans: list[tuple[int, str]]


@lru_cache(maxsize=1)
def _patch_specs() -> dict[str, _PatchSpec]:
    """Decode and validate the embedded sparse v41-to-v50 patch metadata."""
    raw = gzip.decompress(base64.b64decode(_PATCH_PAYLOAD_B64))
    payload = cast(dict[str, _PatchSpec], json.loads(raw.decode("ascii")))
    if set(payload) != {"NOV2", "TT4", "TT5", "T25", "TT6D", "OBJ6D"}:
        raise ReleaseBuildError(
            "v50 finalizer payload has unexpected components"
        )
    return payload


def compiler_prefinal_records(records: dict[str, str]) -> dict[str, str]:
    """Return frozen-compiler input while keeping canonical maps at v50 text."""
    result = dict(records)
    for record_id, final_text in FINAL_SCENARIO_RECORDS.items():
        if result.get(record_id) != final_text:
            raise ReleaseBuildError(
                f"canonical {record_id} does not match final v50 wording"
            )
        result[record_id] = PREFINAL_SCENARIO_RECORDS[record_id]
    return result


def finalize_v50_image(raw: bytes) -> bytes:
    """Apply the verified sparse v41-to-v50 deltas and require exact v50."""
    if len(raw) != IMAGE_BYTES:
        raise ReleaseBuildError(
            f"v50 finalizer received {len(raw)} bytes; expected {IMAGE_BYTES}"
        )
    image = FdsImage.from_bytes(raw)
    for name, spec in _patch_specs().items():
        side_index = int(spec["side"])
        component = image.sides[side_index].find_file(name)
        data = component.data
        expected_size = int(spec["size"])
        if len(data) != expected_size:
            raise ReleaseBuildError(
                f"v50 {name} size mismatch: {len(data)} != {expected_size}"
            )
        input_hash = _sha256(data)
        expected_input = str(spec["input_sha256"])
        if input_hash != expected_input:
            raise ReleaseBuildError(
                f"v50 {name} input hash mismatch: {input_hash} != {expected_input}"
            )
        patched = bytearray(data)
        previous_end = 0
        for offset, replacement_hex in spec["spans"]:
            offset = int(offset)
            replacement = bytes.fromhex(str(replacement_hex))
            end = offset + len(replacement)
            if offset < previous_end or end > len(patched):
                raise ReleaseBuildError(
                    f"invalid/overlapping v50 {name} patch span"
                )
            patched[offset:end] = replacement
            previous_end = end
        output_hash = _sha256(patched)
        expected_output = str(spec["output_sha256"])
        if output_hash != expected_output:
            raise ReleaseBuildError(
                f"v50 {name} output hash mismatch: {output_hash} != {expected_output}"
            )
        component.data = bytes(patched)
    result = image.to_bytes()
    digest = _sha256(result)
    if digest != FINAL_V50_SHA256:
        raise ReleaseBuildError(
            f"final v50 image hash mismatch: {digest} != {FINAL_V50_SHA256}"
        )
    return result
