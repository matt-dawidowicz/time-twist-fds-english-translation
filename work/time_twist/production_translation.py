"""Materialize the production-localization layer over reviewed base maps.

The maintained ``work/translations`` files remain the last certified playable
baseline while the production retranslation is in progress.  Small, reviewable
JSON override files under ``work/production_overrides`` replace individual
stable record IDs.  This keeps each editorial change auditable against the
Japanese-source workbook without copying thirteen complete maps on every pass.
"""

from __future__ import annotations

import json
from pathlib import Path


class ProductionTranslationError(ValueError):
    """Report a malformed override or an ID that is not in the base map."""


def _load_string_map(path: Path, *, label: str) -> dict[str, str]:
    """Load a JSON object whose keys and values are all strings."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProductionTranslationError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise ProductionTranslationError(f"{label} must be a JSON object: {path}")
    result: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value:
            raise ProductionTranslationError(
                f"{label} must map nonempty string IDs to nonempty strings: {path}"
            )
        result[key] = value
    return result


def merged_translation_map(
    bank_name: str,
    *,
    base_directory: Path,
    override_directory: Path,
) -> dict[str, str]:
    """Return one complete production map with source-safe stable IDs.

    An absent override file is equivalent to an empty override.  Unknown IDs
    fail closed so a typo cannot silently create dead localization data.
    """
    base = _load_string_map(
        base_directory / f"{bank_name}.json",
        label=f"{bank_name} base translation",
    )
    override_path = override_directory / f"{bank_name}.json"
    if not override_path.exists():
        return base
    overrides = _load_string_map(
        override_path,
        label=f"{bank_name} production override",
    )
    unknown = sorted(set(overrides) - set(base))
    if unknown:
        raise ProductionTranslationError(
            f"{bank_name} production overrides contain unknown IDs: {unknown[:3]}"
        )
    merged = dict(base)
    merged.update(overrides)
    return merged


def materialize_production_maps(
    bank_names: tuple[str, ...],
    *,
    base_directory: Path,
    override_directory: Path,
    output_directory: Path,
) -> dict[str, int]:
    """Write deterministic complete translation maps for a production build."""
    output_directory.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for bank_name in bank_names:
        merged = merged_translation_map(
            bank_name,
            base_directory=base_directory,
            override_directory=override_directory,
        )
        path = output_directory / f"{bank_name}.json"
        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        counts[bank_name] = len(merged)
    return counts
