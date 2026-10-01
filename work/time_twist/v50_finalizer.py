"""Finalize the validated late-v41 checkpoint to exact, playtested v50.

Canonical source text records the final wording. The executable release lineage
is reproduced with a compact source-copy delta whose source, delta and target
identities are SHA-256 guarded.
"""

from __future__ import annotations

import base64
import hashlib
import zlib
from pathlib import Path

from .checkpoint_delta import apply_checkpoint_delta
from .release_metadata import ReleaseBuildError

FINAL_V50_SHA256 = (
    "820B960AAC377C3EC3072DE67F12EE178F056DAE6147F9A699EDBBB302724E43"
)
PRE_SIMON_RELEASE_SHA256 = (
    "BB3D147FE2245987EFAE579A4130DD8B8599AD7049C264696EA4B52C8CED4D4B"
)
FINAL_RELEASE_SHA256 = (
    "39587318BC6CFD9BE3FE454372E7B483FA3DA81E884324C6D7BD84B8C435B9F5"
)
SIMON_FIX_DELTA_SHA256 = (
    "5D708BA25707C1DB096FDAA4980C88D406E45194E6B6E7A4F74A6D14C9329E9B"
)
FINAL_RELEASE_TT1A_CONTROL_OFFSET = 0x141CA
FINAL_RELEASE_TT1A_CONTROL_OLD = 0x80
FINAL_RELEASE_TT1A_CONTROL_NEW = 0x8C
IMAGE_BYTES = 262000

# Canonical source text is the final v50 wording. The historical late-v41
# checkpoint still contains these two pre-finalizer literals.
PREFINAL_SCENARIO_RECORDS = {
    "TT5/g2/r18": "What was Edison's third{CTRL:0}great invention besides{CTRL:0}the phonograph and{CTRL:0}generator?",
    "T25/g0/r6": "He's lost in thought.",
}

FINAL_SCENARIO_RECORDS = {
    "TT5/g2/r18": "Edison's three great{CTRL:0}inventions were the{CTRL:0}phonograph, the{CTRL:0}generator, and what?",
    "T25/g0/r6": "The sky darkens.",
}

# Final visible system wording represented by the late checkpoint delta.
FINAL_WRONG_DISK_RETRY = "{CTRL:0}Try another side."

V41_SHA256 = "13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1"
V41_TO_V50_DELTA_SHA256 = (
    "07F8ED88371DD5E2FC63427490A9BA73DBDC3FA1BFA4037B4D374626E5F689B9"
)
_PATCH_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "recovery" / "v41" / "patches"
)
_SIMON_PATCH_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "recovery" / "v50" / "patches"
)


def _sha256(data: bytes) -> str:
    """Return the uppercase SHA-256 used by release provenance."""
    return hashlib.sha256(data).hexdigest().upper()


def _load_delta() -> bytes:
    """Decode the chunked, compressed late-v41-to-v50 checkpoint delta."""
    parts = sorted(_PATCH_DIRECTORY.glob("v41-to-v50.ttd.zlib.b64.part*"))
    if not parts:
        raise ReleaseBuildError("missing v41-to-v50 checkpoint delta parts")
    try:
        encoded = "".join(
            part.read_text(encoding="ascii").strip() for part in parts
        )
        return zlib.decompress(base64.b64decode(encoded, validate=True))
    except (OSError, ValueError, zlib.error) as exc:
        raise ReleaseBuildError(
            "could not decode v41-to-v50 checkpoint delta"
        ) from exc



def _load_simon_fix_delta() -> bytes:
    """Decode the reviewed public-release-to-Simon-fix checkpoint delta."""
    parts = sorted(
        _SIMON_PATCH_DIRECTORY.glob("release-to-simon-fix.ttd.zlib.b64.part*")
    )
    if not parts:
        raise ReleaseBuildError("missing Simon dialogue-fix checkpoint delta")
    try:
        encoded = "".join(
            part.read_text(encoding="ascii").strip() for part in parts
        )
        return zlib.decompress(base64.b64decode(encoded, validate=True))
    except (OSError, ValueError, zlib.error) as exc:
        raise ReleaseBuildError(
            "could not decode Simon dialogue-fix checkpoint delta"
        ) from exc

def compiler_prefinal_records(records: dict[str, str]) -> dict[str, str]:
    """Return the two pre-v50 literals used by historical in-place edits."""
    result = dict(records)
    for record_id, final_text in FINAL_SCENARIO_RECORDS.items():
        if result.get(record_id) != final_text:
            raise ReleaseBuildError(
                f"canonical {record_id} does not match final v50 wording"
            )
        result[record_id] = PREFINAL_SCENARIO_RECORDS[record_id]
    return result


def finalize_v50_image(raw: bytes) -> bytes:
    """Apply the reviewed late-v41-to-v50 delta and require exact v50."""
    if len(raw) != IMAGE_BYTES:
        raise ReleaseBuildError(
            f"v50 finalizer received {len(raw)} bytes; expected {IMAGE_BYTES}"
        )
    source_hash = _sha256(raw)
    if source_hash != V41_SHA256:
        raise ReleaseBuildError(
            f"v50 finalizer source mismatch: {source_hash} != {V41_SHA256}"
        )
    patch = _load_delta()
    patch_hash = _sha256(patch)
    if patch_hash != V41_TO_V50_DELTA_SHA256:
        raise ReleaseBuildError(
            "v41-to-v50 checkpoint delta SHA-256 mismatch: "
            f"{patch_hash} != {V41_TO_V50_DELTA_SHA256}"
        )
    result = apply_checkpoint_delta(raw, patch)
    digest = _sha256(result)
    if digest != FINAL_V50_SHA256:
        raise ReleaseBuildError(
            f"final v50 image hash mismatch: {digest} != {FINAL_V50_SHA256}"
        )
    return result


def finalize_release_image(raw: bytes) -> bytes:
    """Promote through v50, TT1A correction, and the reviewed Simon fix."""
    v50 = finalize_v50_image(raw)
    result = bytearray(v50)
    offset = FINAL_RELEASE_TT1A_CONTROL_OFFSET
    if result[offset] != FINAL_RELEASE_TT1A_CONTROL_OLD:
        raise ReleaseBuildError(
            "final release TT1A control source byte mismatch: "
            f"{result[offset]:02X} != {FINAL_RELEASE_TT1A_CONTROL_OLD:02X}"
        )
    result[offset] = FINAL_RELEASE_TT1A_CONTROL_NEW
    corrected = bytes(result)
    digest = _sha256(corrected)
    if digest != PRE_SIMON_RELEASE_SHA256:
        raise ReleaseBuildError(
            "corrected pre-Simon release hash mismatch: "
            f"{digest} != {PRE_SIMON_RELEASE_SHA256}"
        )

    patch = _load_simon_fix_delta()
    patch_hash = _sha256(patch)
    if patch_hash != SIMON_FIX_DELTA_SHA256:
        raise ReleaseBuildError(
            "Simon dialogue-fix delta SHA-256 mismatch: "
            f"{patch_hash} != {SIMON_FIX_DELTA_SHA256}"
        )
    final = apply_checkpoint_delta(corrected, patch)
    digest = _sha256(final)
    if digest != FINAL_RELEASE_SHA256:
        raise ReleaseBuildError(
            "final release hash mismatch after Simon dialogue fix: "
            f"{digest} != {FINAL_RELEASE_SHA256}"
        )
    return final