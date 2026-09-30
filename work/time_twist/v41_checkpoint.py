"""Promote the exact frozen v38 checkpoint to the validated late-v41 image."""

from __future__ import annotations

import base64
import hashlib
import zlib
from pathlib import Path

from .checkpoint_delta import apply_checkpoint_delta
from .release_metadata import ReleaseBuildError

V38_SHA256 = "62C5DBC2DE33C484DE9F8C1318FC903642EB08E2B4D5FA8E28384DC699C4C400"
V41_SHA256 = "13D4E21D1D4393E5B24A1FAEEBE3FF99CE28E5887B2CC7B54BA1AD664EBC91D1"
V38_TO_V41_DELTA_SHA256 = (
    "05231C06BE2033E97A922E2D9265E5E8A501DEBB3AC4E79866D198B34F4900A0"
)
_PATCH_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "recovery" / "v41" / "patches"
)


def _sha256(data: bytes) -> str:
    """Return the uppercase SHA-256 used by checkpoint provenance."""
    return hashlib.sha256(data).hexdigest().upper()


def _load_delta(stem: str) -> bytes:
    """Decode one chunked, compressed checkpoint delta from the source tree."""
    parts = sorted(_PATCH_DIRECTORY.glob(f"{stem}.ttd.zlib.b64.part*"))
    if not parts:
        raise ReleaseBuildError(f"missing {stem} checkpoint delta parts")
    try:
        encoded = "".join(
            part.read_text(encoding="ascii").strip() for part in parts
        )
        return zlib.decompress(base64.b64decode(encoded, validate=True))
    except (OSError, ValueError, zlib.error) as exc:
        raise ReleaseBuildError(
            f"could not decode {stem} checkpoint delta"
        ) from exc


def promote_v38_to_v41(raw: bytes) -> bytes:
    """Apply the reviewed v38-to-v41 delta and require the exact late-v41 ROM."""
    source_hash = _sha256(raw)
    if source_hash != V38_SHA256:
        raise ReleaseBuildError(
            f"v41 checkpoint source mismatch: {source_hash} != {V38_SHA256}"
        )
    patch = _load_delta("v38-to-v41")
    patch_hash = _sha256(patch)
    if patch_hash != V38_TO_V41_DELTA_SHA256:
        raise ReleaseBuildError(
            "v38-to-v41 checkpoint delta SHA-256 mismatch: "
            f"{patch_hash} != {V38_TO_V41_DELTA_SHA256}"
        )
    output = apply_checkpoint_delta(raw, patch)
    output_hash = _sha256(output)
    if output_hash != V41_SHA256:
        raise ReleaseBuildError(
            f"v41 checkpoint output mismatch: {output_hash} != {V41_SHA256}"
        )
    return output
