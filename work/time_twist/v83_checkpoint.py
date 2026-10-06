"""Reproduce and audit the user-confirmed v83 translation checkpoint."""

from __future__ import annotations

import base64
import hashlib
import json
import zlib
from pathlib import Path

from .checkpoint_delta import apply_checkpoint_delta
from .english import render_english
from .entropy_compression import expand_entropy_record
from .fds import FdsImage
from .incremental_build import (
    _decode_verified_stream,
    _expand_dictionary,
    _group_addresses,
    _read_word,
    _split_group,
)
from .release_metadata import SCENARIO_LOCATIONS, ReleaseBuildError

V83_SHA256 = "4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A"
DELTA_SHA256 = (
    "833FABDD349A7064FE984A7C5F228DB719F41785A0CB75FAA3220EB75ECEDBFF"
)
ADDED_RECORD_IDS = frozenset(
    {
        "T22/g1/r26",
        "T25/g2/r12",
        "TT2/g5/r9",
        "TT4/g5/r23",
        "TT5/g3/r27",
        "TT5/g4/r0",
    }
)
RECOVERY_ROOT = Path(__file__).resolve().parents[2] / "recovery" / "v83"


def _recovery_root(recovery_root: Path | None) -> Path:
    """Resolve checkpoint artifacts from the selected project checkout."""
    return (recovery_root or RECOVERY_ROOT).expanduser().resolve()


def load_v83_delta(*, recovery_root: Path | None = None) -> bytes:
    """Load the reviewed copy/literal delta and enforce its independent hash."""
    root = _recovery_root(recovery_root)
    parts = sorted(
        (root / "patches").glob("release-to-v83.ttd.zlib.b64.part*")
    )
    try:
        encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
        patch = zlib.decompress(base64.b64decode(encoded, validate=True))
    except (OSError, ValueError, zlib.error) as error:
        raise ReleaseBuildError(
            "could not decode v83 checkpoint delta"
        ) from error
    if hashlib.sha256(patch).hexdigest().upper() != DELTA_SHA256:
        raise ReleaseBuildError("v83 checkpoint delta SHA-256 mismatch")
    return patch


def promote_release_to_v83(
    raw: bytes,
    *,
    recovery_root: Path | None = None,
) -> bytes:
    """Apply the hash-guarded public-release-to-v83 checkpoint delta."""
    result = apply_checkpoint_delta(
        raw,
        load_v83_delta(recovery_root=recovery_root),
    )
    if hashlib.sha256(result).hexdigest().upper() != V83_SHA256:
        raise ReleaseBuildError("v83 checkpoint output SHA-256 mismatch")
    return result


def validate_v83_sources(
    raw: bytes,
    translations_directory: Path,
    *,
    recovery_root: Path | None = None,
) -> dict:
    """Prove all current dialogue and menu source matches the actual ROM."""
    root = _recovery_root(recovery_root)
    manifest = json.loads(
        (root / "bank_manifest.json").read_text(encoding="utf-8")
    )
    menus = json.loads((root / "menus.json").read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest().upper() != V83_SHA256:
        raise ReleaseBuildError(
            "source audit requires the exact v83 checkpoint"
        )
    image = FdsImage.from_bytes(raw)
    for bank, (part, side) in SCENARIO_LOCATIONS.items():
        data = (
            image.sides[side + (2 if part == "kouhen" else 0)]
            .find_file(bank)
            .data
        )
        info = manifest[bank]
        count = info["dictionary_entries"]
        definitions = (
            _decode_verified_stream(
                data, address=_read_word(data, 22), record_count=count
            )
            if count
            else ()
        )
        expansions = _expand_dictionary(definitions)
        split = _split_group(data)
        actual = {}
        for group, (address, count) in enumerate(
            zip(
                _group_addresses(data, len(info["counts"])),
                info["counts"],
                strict=True,
            )
        ):
            streams = [(address, count)]
            if split is not None and split.group_index == group:
                streams = [
                    (address, split.first_record_count),
                    (split.suffix_address, count - split.first_record_count),
                ]
            records = [
                record
                for address, count in streams
                for record in _decode_verified_stream(
                    data, address=address, record_count=count
                )
            ]
            for index, record in enumerate(records):
                actual[f"{bank}/g{group}/r{index}"] = render_english(
                    expand_entropy_record(record, expansions)
                )
        expected = json.loads(
            (translations_directory / f"{bank}.json").read_text(
                encoding="utf-8"
            )
        )
        if actual != expected:
            raise ReleaseBuildError(
                f"{bank}: canonical text differs from v83 checkpoint"
            )
        labels: list[str] = []
        for first in range(0, len(menus[bank]), 32):
            address = (
                _read_word(data, 20)
                if first == 0
                else _read_word(
                    data, _read_word(data, 26) - 0xA200 + 2 * (first // 32 - 1)
                )
            )
            labels.extend(
                render_english(expand_entropy_record(record, expansions))
                for record in _decode_verified_stream(
                    data,
                    address=address,
                    record_count=min(32, len(menus[bank]) - first),
                )
            )
        if labels != menus[bank]:
            raise ReleaseBuildError(
                f"{bank}: menu source differs from v83 checkpoint"
            )
    return manifest
