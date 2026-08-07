"""Reproducible end-to-end release builder for the English translation.

Release commands operate on a project checkout rather than package data. This
keeps the installable Python wheel free of ROMs and large project artifacts while
still allowing ``time-twist`` to drive a checkout from any working directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .compression import compress_english_groups, packed_size
from .english import EnglishTextError, control_values, encode_english, validate_display_width
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .project import (
    KNOWN_SCENARIO_BANKS,
    PERSONALITY_QUESTION_IDS,
    required_dictionary_entries,
)
from .scenario import ScenarioBank, parse_scenario_bank, rebuild_scenario_bank, render_symbols
from .title import DEFAULT_SUBTITLE, patched_nov4_title
from .ui import (
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_t22_ui,
    patched_t25_ui,
    patched_tt1a_ui,
    patched_tt1b_ui,
    patched_tt2_ui,
    patched_tt3a_ui,
    patched_tt3b_ui,
    patched_tt4_ui,
    patched_tt5_ui,
    patched_tt6a_ui,
    patched_tt6b_ui,
    patched_tt6c_ui,
)


SOURCE_CHECKOUT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT_ROOT = (
    SOURCE_CHECKOUT_ROOT
    if (SOURCE_CHECKOUT_ROOT / "work" / "translations").is_dir()
    else None
)
DEFAULT_SOURCE_LOCK = (
    DEFAULT_PROJECT_ROOT / "work" / "release_sources.json"
    if DEFAULT_PROJECT_ROOT is not None
    else Path("work/release_sources.json")
)
DEFAULT_RELEASE_TARGET = (
    DEFAULT_PROJECT_ROOT / "work" / "release_target.json"
    if DEFAULT_PROJECT_ROOT is not None
    else Path("work/release_target.json")
)
DEFAULT_TITLE_ASSET = (
    DEFAULT_PROJECT_ROOT / "work" / "title_assets" / "Time Twist approved native title.png"
    if DEFAULT_PROJECT_ROOT is not None
    else Path("work/title_assets/Time Twist approved native title.png")
)
DEFAULT_ZENPEN_BASELINE = (
    DEFAULT_PROJECT_ROOT / "work" / "baseline" / "time_twist_zenpen_japan.fds"
    if DEFAULT_PROJECT_ROOT is not None
    else Path("work/baseline/time_twist_zenpen_japan.fds")
)
DEFAULT_KOUHEN_BASELINE = (
    DEFAULT_PROJECT_ROOT / "work" / "baseline" / "time_twist_kouhen_japan.fds"
    if DEFAULT_PROJECT_ROOT is not None
    else Path("work/baseline/time_twist_kouhen_japan.fds")
)

RELEASE_OUTPUT_KEYS = ("zenpen", "kouhen", "four_side")
RELEASE_FILENAMES = {
    "zenpen": "Time Twist Zenpen - reproducible English playtest.fds",
    "kouhen": "Time Twist Kouhen - reproducible English playtest.fds",
    "four_side": "Time Twist - reproducible English four-side playtest.fds",
}

SCENARIO_LOCATIONS: dict[str, tuple[str, int]] = {
    "TT3A": ("zenpen", 0),
    "TT3B": ("zenpen", 0),
    "TT1B": ("zenpen", 1),
    "TT1A": ("zenpen", 1),
    "TT2": ("zenpen", 1),
    "T22": ("zenpen", 1),
    "TT6C": ("kouhen", 0),
    "TT6B": ("kouhen", 0),
    "TT6A": ("kouhen", 0),
    "TT6D": ("kouhen", 0),
    "TT4": ("kouhen", 1),
    "TT5": ("kouhen", 1),
    "T25": ("kouhen", 1),
}

SCENARIO_UI_PATCHERS: dict[str, Callable[[bytes], bytes]] = {
    "TT1A": patched_tt1a_ui,
    "TT1B": patched_tt1b_ui,
    "TT2": patched_tt2_ui,
    "T22": patched_t22_ui,
    "TT3A": patched_tt3a_ui,
    "TT3B": patched_tt3b_ui,
    "TT4": patched_tt4_ui,
    "TT5": patched_tt5_ui,
    "T25": patched_t25_ui,
    "TT6A": patched_tt6a_ui,
    "TT6B": patched_tt6b_ui,
    "TT6C": patched_tt6c_ui,
}


class ReleaseBuildError(ValueError):
    """Report an unapproved input, invalid translation, or release mismatch."""


@dataclass(frozen=True)
class ReleasePaths:
    """Resolved project files used by release and promotion commands."""

    project_root: Path
    work_root: Path
    source_lock: Path
    release_target: Path
    title_asset: Path
    zenpen_baseline: Path
    kouhen_baseline: Path
    translations: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "ReleasePaths":
        """Create canonical paths beneath a validated project checkout."""

        root = project_root.resolve()
        work = root / "work"
        return cls(
            project_root=root,
            work_root=work,
            source_lock=work / "release_sources.json",
            release_target=work / "release_target.json",
            title_asset=work / "title_assets" / "Time Twist approved native title.png",
            zenpen_baseline=work / "baseline" / "time_twist_zenpen_japan.fds",
            kouhen_baseline=work / "baseline" / "time_twist_kouhen_japan.fds",
            translations=work / "translations",
        )


@dataclass(frozen=True)
class ScenarioBuildResult:
    """One rebuilt scenario bank and its compression statistics."""

    data: bytes
    records: int
    dictionary_entries: int
    packed_bytes: int
    capacity_bytes: int


def sha256_bytes(data: bytes) -> str:
    """Return an uppercase SHA-256 digest."""

    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    """Return an uppercase SHA-256 digest for a file."""

    return sha256_bytes(path.read_bytes())


def _is_project_root(path: Path) -> bool:
    """Return whether ``path`` has the source checkout's stable public markers."""

    return (
        (path / "pyproject.toml").is_file()
        and (path / "work" / "translations").is_dir()
        and (path / "work" / "title_assets").is_dir()
    )


def discover_project_root(
    explicit: Path | None = None,
    *,
    start: Path | None = None,
) -> Path:
    """Resolve the checkout that owns release data.

    An explicit path is authoritative. Otherwise the current directory, its
    parents, and the module source location are searched. Installed wheels can
    therefore operate on any checkout through ``--project-root`` without
    packaging translations, art, or ROM data inside the wheel.
    """

    if explicit is not None:
        candidate = explicit.expanduser().resolve()
        if not _is_project_root(candidate):
            raise ReleaseBuildError(
                f"not a Time Twist project checkout: {candidate}; expected "
                "pyproject.toml, work/translations, and work/title_assets"
            )
        return candidate

    seeds = [start or Path.cwd(), Path(__file__).resolve()]
    visited: set[Path] = set()
    for seed in seeds:
        current = seed.resolve()
        if current.is_file():
            current = current.parent
        for candidate in (current, *current.parents):
            if candidate in visited:
                continue
            visited.add(candidate)
            if _is_project_root(candidate):
                return candidate
    raise ReleaseBuildError(
        "could not locate the Time Twist project checkout; pass --project-root PATH"
    )


def _project_relative(path: Path, project_root: Path) -> str:
    """Return a stable relative path and reject release inputs outside the project."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError as error:
        raise ReleaseBuildError(
            f"release input is outside the project checkout: {resolved}"
        ) from error


def display_path(path: Path, project_root: Path) -> str:
    """Return a readable manifest path without assuming it is inside the checkout."""

    resolved = path.expanduser().resolve()
    try:
        return resolved.relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def authoritative_source_paths(paths: ReleasePaths) -> tuple[Path, ...]:
    """Return all non-code files that intentionally define a release build."""

    translations = tuple(
        paths.translations / f"{bank}.json"
        for bank in KNOWN_SCENARIO_BANKS
    )
    return (
        paths.zenpen_baseline,
        paths.kouhen_baseline,
        paths.title_asset,
        *translations,
    )


def build_source_lock_payload(project_root: Path | None = None) -> dict[str, object]:
    """Create the deterministic approved-input lock payload."""

    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    files: dict[str, dict[str, object]] = {}
    for path in authoritative_source_paths(paths):
        if not path.is_file():
            raise ReleaseBuildError(f"required release source is missing: {path}")
        files[_project_relative(path, root)] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    return {
        "schema": "Time Twist release source lock v1",
        "authority": (
            "The locked scenario maps, fixed UI/font/title code in this revision, "
            "and the locked title asset are the playable release authority. "
            "Workbook patch-safe fields mirror this authority; editorial alternatives "
            "remain in the natural-translation fields."
        ),
        "subtitle": DEFAULT_SUBTITLE,
        "files": files,
    }


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    """Atomically replace one JSON file after its complete contents are prepared."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    try:
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_source_lock(
    path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, object]:
    """Write the approved release-source hashes."""

    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    destination = (path or paths.source_lock).expanduser().resolve()
    payload = build_source_lock_payload(root)
    _atomic_write_json(destination, payload)
    return payload


def validate_source_lock(
    path: Path | None = None,
    *,
    project_root: Path | None = None,
) -> dict[str, object]:
    """Fail unless every approved release input matches its locked digest."""

    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    lock_path = (path or paths.source_lock).expanduser().resolve()
    if not lock_path.is_file():
        raise ReleaseBuildError(
            f"release source lock is missing: {lock_path}; run release-lock --update"
        )
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "Time Twist release source lock v1":
        raise ReleaseBuildError("unsupported release source lock schema")
    expected_files = payload.get("files")
    if not isinstance(expected_files, dict):
        raise ReleaseBuildError("release source lock has no file mapping")

    actual_paths = {
        _project_relative(source_path, root): source_path
        for source_path in authoritative_source_paths(paths)
    }
    if set(expected_files) != set(actual_paths):
        missing = sorted(set(actual_paths) - set(expected_files))
        stale = sorted(set(expected_files) - set(actual_paths))
        raise ReleaseBuildError(
            f"release source lock path mismatch; missing={missing}, stale={stale}"
        )
    for relative, source_path in actual_paths.items():
        if not source_path.is_file():
            raise ReleaseBuildError(f"required release source is missing: {source_path}")
        record = expected_files[relative]
        if not isinstance(record, dict):
            raise ReleaseBuildError(f"invalid lock record for {relative}")
        actual_hash = sha256_file(source_path)
        if record.get("sha256") != actual_hash:
            raise ReleaseBuildError(
                f"unapproved release input changed: {relative}; "
                f"expected {record.get('sha256')}, got {actual_hash}"
            )
        if record.get("bytes") != source_path.stat().st_size:
            raise ReleaseBuildError(f"locked size mismatch for {relative}")
    if payload.get("subtitle") != DEFAULT_SUBTITLE:
        raise ReleaseBuildError("locked subtitle differs from the code default")
    return payload


def _validated_output_records(payload: object, *, label: str) -> dict[str, dict[str, object]]:
    """Validate release output records shared by target and build manifests."""

    if not isinstance(payload, dict) or set(payload) != set(RELEASE_OUTPUT_KEYS):
        raise ReleaseBuildError(
            f"{label} outputs must contain exactly {list(RELEASE_OUTPUT_KEYS)}"
        )
    output: dict[str, dict[str, object]] = {}
    for name in RELEASE_OUTPUT_KEYS:
        record = payload[name]
        if not isinstance(record, dict):
            raise ReleaseBuildError(f"{label} output {name} is not an object")
        digest = record.get("sha256")
        size = record.get("bytes")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789ABCDEF" for character in digest)
        ):
            raise ReleaseBuildError(f"{label} output {name} has an invalid SHA-256")
        if not isinstance(size, int) or size <= 0:
            raise ReleaseBuildError(f"{label} output {name} has an invalid byte size")
        output[name] = dict(record)
    return output


def validate_release_target(
    path: Path,
    *,
    source_lock_sha256: str,
) -> dict[str, object]:
    """Validate a promoted output target against the active source lock."""

    target_path = path.expanduser().resolve()
    if not target_path.is_file():
        raise ReleaseBuildError(
            f"release target is missing: {target_path}; build a candidate and run "
            "release-promote"
        )
    payload = json.loads(target_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "Time Twist release target v1":
        raise ReleaseBuildError("unsupported release target schema")
    if payload.get("source_lock_sha256") != source_lock_sha256:
        raise ReleaseBuildError(
            "release target belongs to a different source lock; build a candidate "
            "and promote it after review"
        )
    _validated_output_records(payload.get("outputs"), label="release target")
    return payload


def _load_translation_map(bank_name: str, translations_directory: Path) -> dict[str, str]:
    path = translations_directory / f"{bank_name}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReleaseBuildError(f"{path} must contain a JSON object")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in payload.items()):
        raise ReleaseBuildError(f"{path} must map string IDs to string text")
    return payload


def _encoded_groups(
    bank: ScenarioBank,
    bank_name: str,
    translations: dict[str, str],
) -> tuple[tuple[tuple[object, ...], ...], ...]:
    records_by_id = {
        f"{bank_name}/g{record.group_index}/r{record.record_index}": record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    missing = sorted(set(records_by_id) - set(translations))
    if unknown or missing:
        raise ReleaseBuildError(
            f"{bank_name} translation IDs differ from the source; "
            f"unknown={unknown[:1]}, missing={missing[:1]}"
        )

    encoded: dict[str, tuple[object, ...]] = {}
    for record_id, record in records_by_id.items():
        english = translations[record_id]
        if not english:
            raise ReleaseBuildError(f"empty English translation: {record_id}")
        japanese = render_symbols(record.symbols, bank.dictionary)
        if control_values(english) != control_values(japanese):
            raise ReleaseBuildError(f"control tags changed in {record_id}")
        try:
            validate_display_width(
                english,
                allow_wrap=record_id in PERSONALITY_QUESTION_IDS,
            )
            encoded[record_id] = encode_english(english)
        except EnglishTextError as error:
            raise ReleaseBuildError(f"invalid English in {record_id}: {error}") from error

    return tuple(
        tuple(
            encoded[f"{bank_name}/g{group_index}/r{record.record_index}"]
            for record in bank.records
            if record.group_index == group_index
        )
        for group_index in range(len(bank.group_addresses))
    )


def build_scenario_bank(
    source: bytes,
    bank_name: str,
    *,
    temporary_directory: Path,
    translations_directory: Path,
) -> ScenarioBuildResult:
    """Build and fixed-UI-patch one scenario component from approved text."""

    source_path = temporary_directory / f"{bank_name}_source.bin"
    source_path.write_bytes(source)
    bank = parse_scenario_bank(source_path)
    groups = _encoded_groups(
        bank,
        bank_name,
        _load_translation_map(bank_name, translations_directory),
    )
    compressed, dictionary = compress_english_groups(
        groups,
        required_entries=required_dictionary_entries(bank_name),
    )
    if bank_name in SCENARIO_UI_PATCHERS and len(dictionary) != 31:
        raise ReleaseBuildError(
            f"{bank_name} fixed UI requires exactly 31 dictionary entries; "
            f"compressor produced {len(dictionary)}"
        )
    rebuilt = rebuild_scenario_bank(
        bank,
        compressed,
        dictionary=dictionary,
        preserve_memory_footprint=True,
    )
    patcher = SCENARIO_UI_PATCHERS.get(bank_name)
    if patcher is not None:
        rebuilt = patcher(rebuilt)

    text_start = bank.group_addresses[0] - bank.load_address
    capacity = bank.dictionary_end_offset - text_start
    used = packed_size(compressed, dictionary) + 2 * (len(groups) - 1)
    return ScenarioBuildResult(
        data=rebuilt,
        records=len(bank.records),
        dictionary_entries=len(dictionary),
        packed_bytes=used,
        capacity_bytes=capacity,
    )


def _replace(image: FdsImage, side: int, name: str, data: bytes) -> None:
    image.sides[side].find_file(name).data = data


def _output_records(output_bytes: Mapping[str, bytes]) -> dict[str, dict[str, object]]:
    return {
        name: {
            "path": RELEASE_FILENAMES[name],
            "bytes": len(output_bytes[name]),
            "sha256": sha256_bytes(output_bytes[name]),
        }
        for name in RELEASE_OUTPUT_KEYS
    }


def _target_mismatches(
    target: Mapping[str, object],
    outputs: Mapping[str, Mapping[str, object]],
) -> dict[str, dict[str, object]]:
    expected = _validated_output_records(target.get("outputs"), label="release target")
    mismatches: dict[str, dict[str, object]] = {}
    for name in RELEASE_OUTPUT_KEYS:
        expected_record = expected[name]
        actual_record = outputs[name]
        differences = {
            field: {"expected": expected_record[field], "actual": actual_record[field]}
            for field in ("bytes", "sha256")
            if expected_record[field] != actual_record[field]
        }
        if differences:
            mismatches[name] = differences
    return mismatches


def _atomic_publish_file(source: Path, destination: Path) -> None:
    """Atomically publish a staged file with destination-directory access.

    The temporary file is created directly inside the destination directory.
    This matters on Windows: moving a file out of ``TemporaryDirectory`` keeps
    that private directory's ACL and can make the published ROM inaccessible
    to the interactive emulator account. A destination-local temporary file
    inherits the intended directory ACL before the final atomic replacement.
    """

    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        with source.open("rb") as staged:
            shutil.copyfileobj(staged, handle)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.chmod(source.stat().st_mode)
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _publish_staged_release(staging: Path, output_directory: Path) -> None:
    """Publish verified staged files, writing the manifest last."""

    output_directory.mkdir(parents=True, exist_ok=True)
    for name in RELEASE_OUTPUT_KEYS:
        filename = RELEASE_FILENAMES[name]
        _atomic_publish_file(staging / filename, output_directory / filename)
    _atomic_publish_file(
        staging / "release_manifest.json",
        output_directory / "release_manifest.json",
    )


def build_release(
    output_directory: Path,
    *,
    project_root: Path | None = None,
    source_lock: Path | None = None,
    release_target: Path | None = None,
    verify_target: bool = True,
    subtitle: str = DEFAULT_SUBTITLE,
) -> dict[str, object]:
    """Build all images transactionally from a locked project checkout.

    Candidate mode (``verify_target=False``) publishes a complete build without
    approving its hashes. Verified mode requires a promoted ``release_target``
    tied to the active source lock. No new output is published before all build,
    hash, and target checks succeed.
    """

    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    lock_path = (source_lock or paths.source_lock).expanduser().resolve()
    target_path = (release_target or paths.release_target).expanduser().resolve()
    lock = validate_source_lock(lock_path, project_root=root)
    lock_sha256 = sha256_file(lock_path)
    if subtitle != lock.get("subtitle"):
        raise ReleaseBuildError("release subtitle differs from the approved lock")

    zenpen = FdsImage.read(paths.zenpen_baseline)
    kouhen = FdsImage.read(paths.kouhen_baseline)
    images = {"zenpen": zenpen, "kouhen": kouhen}
    scenario_report: dict[str, dict[str, object]] = {}

    with tempfile.TemporaryDirectory(prefix="time_twist_components_") as directory:
        temporary_directory = Path(directory)
        for bank_name, (image_name, side) in SCENARIO_LOCATIONS.items():
            entry = images[image_name].sides[side].find_file(bank_name)
            result = build_scenario_bank(
                entry.data,
                bank_name,
                temporary_directory=temporary_directory,
                translations_directory=paths.translations,
            )
            entry.data = result.data
            scenario_report[bank_name] = {
                "records": result.records,
                "dictionary_entries": result.dictionary_entries,
                "packed_bytes": result.packed_bytes,
                "capacity_bytes": result.capacity_bytes,
                "remaining_bytes": result.capacity_bytes - result.packed_bytes,
                "sha256": sha256_bytes(result.data),
            }

    nov2_source = zenpen.sides[0].find_file("NOV2").data
    _replace(zenpen, 0, "NOV2", patched_nov2_ui(nov2_source))

    nov4_source = zenpen.sides[0].find_file("NOV4").data
    nov4 = patched_nov4_ui(nov4_source)
    nov4 = patched_nov4_font(nov4)
    nov4 = patched_nov4_title(nov4, paths.title_asset, subtitle=subtitle)
    _replace(zenpen, 0, "NOV4", nov4)

    son_kouh_source = kouhen.sides[0].find_file("SON-KOUH").data
    _replace(kouhen, 0, "SON-KOUH", patched_kouhen_boot_guard(son_kouh_source))

    output_bytes = {
        "zenpen": zenpen.to_bytes(),
        "kouhen": kouhen.to_bytes(),
        "four_side": combine_images([zenpen, kouhen]).to_bytes(),
    }
    outputs = _output_records(output_bytes)

    target_payload: dict[str, object] | None = None
    if verify_target:
        target_payload = validate_release_target(
            target_path,
            source_lock_sha256=lock_sha256,
        )
        mismatches = _target_mismatches(target_payload, outputs)
        if mismatches:
            raise ReleaseBuildError(
                f"release output differs from the promoted target: {mismatches}; "
                "use --candidate, review the build, then release-promote"
            )

    manifest: dict[str, object] = {
        "schema": "Time Twist reproducible release manifest v2",
        "mode": "verified" if verify_target else "candidate",
        "project_source_lock": display_path(lock_path, root),
        "source_lock_sha256": lock_sha256,
        "release_target": display_path(target_path, root) if verify_target else None,
        "release_target_sha256": sha256_file(target_path) if verify_target else None,
        "release_id": target_payload.get("release_id") if target_payload else None,
        "subtitle": subtitle,
        "scenario_banks": scenario_report,
        "component_sha256": {
            "NOV2": sha256_bytes(zenpen.sides[0].find_file("NOV2").data),
            "NOV4": sha256_bytes(zenpen.sides[0].find_file("NOV4").data),
            "SON-KOUH": sha256_bytes(kouhen.sides[0].find_file("SON-KOUH").data),
        },
        "outputs": outputs,
    }

    destination = output_directory.expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".time_twist_release_",
        dir=destination.parent,
    ) as stage_directory:
        staging = Path(stage_directory)
        for name in RELEASE_OUTPUT_KEYS:
            (staging / RELEASE_FILENAMES[name]).write_bytes(output_bytes[name])
        (staging / "release_manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        _publish_staged_release(staging, destination)
    return manifest


def promote_release_target(
    candidate_manifest: Path,
    *,
    target_path: Path | None = None,
    project_root: Path | None = None,
    release_id: str | None = None,
) -> dict[str, object]:
    """Promote a reviewed candidate manifest into the strict output target."""

    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    manifest_path = candidate_manifest.expanduser().resolve()
    if not manifest_path.is_file():
        raise ReleaseBuildError(f"candidate manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "Time Twist reproducible release manifest v2":
        raise ReleaseBuildError("unsupported candidate manifest schema")
    if manifest.get("mode") != "candidate":
        raise ReleaseBuildError("release-promote requires a candidate-mode manifest")

    lock_path_value = manifest.get("project_source_lock")
    if not isinstance(lock_path_value, str):
        raise ReleaseBuildError("candidate manifest has no source-lock path")
    lock_path = Path(lock_path_value)
    if not lock_path.is_absolute():
        lock_path = root / lock_path
    validate_source_lock(lock_path, project_root=root)
    lock_sha256 = sha256_file(lock_path)
    if manifest.get("source_lock_sha256") != lock_sha256:
        raise ReleaseBuildError("candidate manifest does not match the current source lock")

    output_records = _validated_output_records(
        manifest.get("outputs"),
        label="candidate manifest",
    )
    for name, record in output_records.items():
        relative = record.get("path")
        if not isinstance(relative, str) or Path(relative).name != relative:
            raise ReleaseBuildError(f"candidate output {name} has an unsafe path")
        output_path = manifest_path.parent / relative
        if not output_path.is_file():
            raise ReleaseBuildError(f"candidate output is missing: {output_path}")
        if output_path.stat().st_size != record["bytes"]:
            raise ReleaseBuildError(f"candidate output size changed: {output_path}")
        if sha256_file(output_path) != record["sha256"]:
            raise ReleaseBuildError(f"candidate output hash changed: {output_path}")

    target = {
        "schema": "Time Twist release target v1",
        "release_id": release_id or "english-playtest",
        "source_lock_sha256": lock_sha256,
        "promoted_from_manifest_sha256": sha256_file(manifest_path),
        "outputs": {
            name: {
                "bytes": output_records[name]["bytes"],
                "sha256": output_records[name]["sha256"],
            }
            for name in RELEASE_OUTPUT_KEYS
        },
    }
    destination = (target_path or paths.release_target).expanduser().resolve()
    _atomic_write_json(destination, target)
    return target
