"""Install the definitive IPS-derived title pixel authority."""

from __future__ import annotations

import base64
import hashlib
import json
import zlib
from pathlib import Path
from typing import Callable

from PIL import Image

from . import title_assets as _assets
from .title_layout import (
    DEFAULT_SLIDE_ASSET_NAME,
    TITLE_PALETTE,
    TitlePatchError,
)

DEFINITIVE_IPS_AUTHORITY_NAME = "definitive_ips_logo.json"
DEFINITIVE_FINAL_ASSET_NAME = "Time Twist approved native title.png"
DEFINITIVE_FINAL_PIXEL_SHA256 = (
    "EA50A1888635F7A8FE863C61EB6D728CE260D281FABF3259E2FED700BC75CBA8"
)
DEFINITIVE_SLIDE_PIXEL_SHA256 = (
    "7FA164F34514B568560F5FC4BE7186719A692EB1013E7B00A26DE9FAE61080AB"
)

_TargetLoader = Callable[..., Image.Image]
_ORIGINAL_TARGET_LOADER: _TargetLoader = _assets._target_to_indices


def _sha256(data: bytes) -> str:
    """Return an uppercase SHA-256 digest."""
    return hashlib.sha256(data).hexdigest().upper()


def _load_final_authority(path: Path) -> Image.Image:
    """Materialize and validate the exact final logo from the text authority."""
    authority_path = path.with_name(DEFINITIVE_IPS_AUTHORITY_NAME)
    try:
        payload = json.loads(authority_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TitlePatchError(
            f"cannot read definitive IPS title authority: {authority_path}"
        ) from exc
    if payload.get("schema") != "Time Twist definitive IPS logo v1":
        raise TitlePatchError(
            "unsupported definitive IPS title authority schema"
        )
    if (
        payload.get("width"),
        payload.get("height"),
        payload.get("owned_rows"),
    ) != (256, 240, 97):
        raise TitlePatchError(
            "definitive IPS title authority has invalid geometry"
        )
    if payload.get("palette") != [list(color) for color in TITLE_PALETTE]:
        raise TitlePatchError("definitive IPS title authority palette drifted")
    if payload.get("final_pixel_sha256") != DEFINITIVE_FINAL_PIXEL_SHA256:
        raise TitlePatchError(
            "definitive IPS title authority hash metadata drifted"
        )
    encoded = payload.get("owned_pixels_zlib_base64")
    if not isinstance(encoded, str):
        raise TitlePatchError(
            "definitive IPS title authority has no pixel payload"
        )
    try:
        owned = zlib.decompress(base64.b64decode(encoded, validate=True))
    except (ValueError, zlib.error) as exc:
        raise TitlePatchError(
            "definitive IPS title pixel payload is invalid"
        ) from exc
    if len(owned) != 256 * 97 or any(pixel > 3 for pixel in owned):
        raise TitlePatchError(
            "definitive IPS title pixel payload has invalid data"
        )
    full = owned + bytes(256 * (240 - 97))
    if _sha256(full) != DEFINITIVE_FINAL_PIXEL_SHA256:
        raise TitlePatchError("definitive IPS title pixels drifted")
    image = Image.new("L", (256, 240), 0)
    image.putdata(full)
    return image


def _load_slide_authority(path: Path) -> Image.Image:
    """Derive the exact monochrome swipe from the final logo silhouette."""
    final = _load_final_authority(path)
    final_pixels = bytes(final.get_flattened_data())
    slide_pixels = bytearray(256 * 240)
    for index, value in enumerate(final_pixels[: 256 * 96]):
        slide_pixels[index] = 1 if value else 0
    if _sha256(bytes(slide_pixels)) != DEFINITIVE_SLIDE_PIXEL_SHA256:
        raise TitlePatchError("definitive IPS slide pixels drifted")
    slide = Image.new("L", (256, 240), 0)
    slide.putdata(slide_pixels)
    return slide


def _target_to_indices(
    path: Path,
    *,
    last_owned_row: int = 96,
) -> Image.Image:
    """Use IPS pixels for production title paths and preserve custom assets."""
    authority_path = path.with_name(DEFINITIVE_IPS_AUTHORITY_NAME)
    if authority_path.is_file() and path.name == DEFINITIVE_FINAL_ASSET_NAME:
        result = _load_final_authority(path)
    elif authority_path.is_file() and path.name == DEFAULT_SLIDE_ASSET_NAME:
        result = _load_slide_authority(path)
    else:
        return _ORIGINAL_TARGET_LOADER(path, last_owned_row=last_owned_row)
    if not 0 <= last_owned_row < 240:
        raise TitlePatchError("native title authority row limit is invalid")
    if any(
        result.crop((0, last_owned_row + 1, 256, 240)).get_flattened_data()
    ):
        raise TitlePatchError(
            "native title authority owns pixels below its approved rows"
        )
    return result


def install_definitive_title_authority() -> None:
    """Route the existing title builder through the definitive IPS pixels."""
    _assets._target_to_indices = _target_to_indices
