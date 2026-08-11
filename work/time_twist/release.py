"""Reproducible end-to-end release builder for the English translation.

Release commands operate on a project checkout rather than package data. This
keeps the installable Python wheel free of ROMs and large project artifacts while
still allowing ``time-twist`` to drive a checkout from any working directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import version as package_version
from pathlib import Path, PurePosixPath

from .compression import compress_english_groups, packed_size
from .english import EnglishTextError
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .project import (
    KNOWN_SCENARIO_BANKS,
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
from .scenario import (
    ScenarioBank,
    parse_scenario_bank,
    rebuild_scenario_bank,
    render_symbols,
)
from .scenario_validation import (
    encode_validated_english,
    scenario_record_id,
)
from .textcodec import PackedSymbol
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
EXECUTING_PACKAGE_ROOT = Path(__file__).resolve().parent
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
    DEFAULT_PROJECT_ROOT
    / "work"
    / "title_assets"
    / "Time Twist approved native title.png"
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
SOURCE_LOCK_SCHEMA = "Time Twist release source lock v2"
SOURCE_NORMALIZATION_RAW = "raw"
SOURCE_NORMALIZATION_LF = "lf"
CODE_PROVENANCE_SCHEMA = "Time Twist release code provenance v1"
CODE_TREE_HASH_ALGORITHM = (
    "sha256-length-prefixed-posix-path-and-lf-normalized-content-v1"
)
CODE_LOGICAL_ROOT = "work/time_twist"
BUILD_ENVIRONMENT_SCHEMA = "Time Twist build environment v1"
RELEASE_MANIFEST_SCHEMA = "Time Twist reproducible release manifest v4"
LEGACY_RELEASE_MANIFEST_SCHEMA = "Time Twist reproducible release manifest v3"
RELEASE_TARGET_SCHEMA = "Time Twist release target v2"
LEGACY_RELEASE_TARGET_SCHEMA = "Time Twist release target v1"
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
    def from_project_root(cls, project_root: Path) -> ReleasePaths:
        """Create canonical paths beneath a validated project checkout."""
        root = project_root.resolve()
        work = root / "work"
        return cls(
            project_root=root,
            work_root=work,
            source_lock=work / "release_sources.json",
            release_target=work / "release_target.json",
            title_asset=work
            / "title_assets"
            / "Time Twist approved native title.png",
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


def _lf_normalized_bytes(data: bytes) -> bytes:
    """Return bytes with CRLF and bare CR line endings normalized to LF."""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def source_lock_sha256(path: Path) -> str:
    """Hash a source-lock document independently of host line endings."""
    return sha256_bytes(_lf_normalized_bytes(path.read_bytes()))


def _read_json_object(path: Path, *, label: str) -> dict[str, object]:
    """Read a UTF-8 JSON object with a path-specific release error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ReleaseBuildError(
            f"{label} is malformed JSON: {path} "
            f"(line {error.lineno}, column {error.colno})"
        ) from error
    except UnicodeError as error:
        raise ReleaseBuildError(
            f"{label} is not valid UTF-8 JSON: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise ReleaseBuildError(f"{label} must contain a JSON object: {path}")
    return payload


def _is_sha256(value: object) -> bool:
    """Return whether ``value`` is one uppercase hexadecimal SHA-256."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789ABCDEF" for character in value)
    )


def build_environment_provenance() -> dict[str, str]:
    """Return informational versions that can explain reproduction differences."""
    return {
        "schema": BUILD_ENVIRONMENT_SCHEMA,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "pillow_version": package_version("Pillow"),
    }


def release_code_paths(project_root: Path) -> tuple[Path, ...]:
    """Return release-critical Python sources in deterministic path order."""
    root = project_root.resolve()
    code_root = root / "work" / "time_twist"
    return tuple(path for _, path in _release_code_entries(code_root))


def _release_code_entries(code_root: Path) -> tuple[tuple[str, Path], ...]:
    """Return logical release paths paired with their physical source files."""
    root = code_root.expanduser().resolve()
    if not root.is_dir():
        raise ReleaseBuildError(
            f"release-critical code directory is missing: {root}"
        )
    entries = tuple(
        sorted(
            (
                (
                    f"{CODE_LOGICAL_ROOT}/{path.relative_to(root).as_posix()}",
                    path,
                )
                for path in root.rglob("*.py")
                if path.is_file()
            ),
            key=lambda entry: entry[0],
        )
    )
    if not entries:
        raise ReleaseBuildError(
            f"release-critical code directory contains no Python files: {root}"
        )
    for _, path in entries:
        if path.is_symlink():
            raise ReleaseBuildError(
                f"release-critical source must not be a symlink: {path}"
            )
    return entries


def _release_code_tree_sha256(entries: tuple[tuple[str, Path], ...]) -> str:
    """Hash a stable release-code path set and its normalized contents."""
    digest = hashlib.sha256()
    digest.update(b"Time Twist release code tree v1\0")
    digest.update(len(entries).to_bytes(8, "big"))
    for logical_path, physical_path in entries:
        relative = logical_path.encode("utf-8")
        contents = (
            physical_path.read_bytes()
            .replace(b"\r\n", b"\n")
            .replace(b"\r", b"\n")
        )
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(contents).to_bytes(8, "big"))
        digest.update(contents)
    return digest.hexdigest().upper()


def release_code_tree_sha256(project_root: Path) -> str:
    """Hash release code by normalized path and platform-neutral contents.

    Each record contains an eight-byte big-endian path length, its UTF-8
    POSIX-relative path, an eight-byte content length, and source bytes with
    all line endings normalized to LF. Length prefixes make path/content
    boundaries unambiguous, while normalization makes equivalent Git
    checkouts hash identically on Windows and Unix.
    """
    root = project_root.resolve()
    return _release_code_tree_sha256(
        _release_code_entries(root / "work" / "time_twist")
    )


def executing_release_code_tree_sha256(
    code_root: Path | None = None,
) -> str:
    """Hash the imported package using checkout-equivalent logical paths."""
    return _release_code_tree_sha256(
        _release_code_entries(code_root or EXECUTING_PACKAGE_ROOT)
    )


def _git_provenance(project_root: Path) -> tuple[str | None, bool | None]:
    """Return optional Git commit and dirty state without requiring Git."""
    command = ["git", "-C", str(project_root.resolve())]
    try:
        commit_result = subprocess.run(
            [*command, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        status_result = subprocess.run(
            [*command, "status", "--porcelain", "--untracked-files=normal"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None, None
    commit = commit_result.stdout.strip().lower()
    if len(commit) not in (40, 64) or any(
        character not in "0123456789abcdef" for character in commit
    ):
        return None, None
    return commit, bool(status_result.stdout)


def build_code_provenance(
    project_root: Path,
    *,
    executing_code_root: Path | None = None,
) -> dict[str, object]:
    """Describe code proven identical in the executor and project checkout."""
    root = project_root.resolve()
    project_entries = _release_code_entries(root / "work" / "time_twist")
    executing_entries = _release_code_entries(
        executing_code_root or EXECUTING_PACKAGE_ROOT
    )
    project_digest = _release_code_tree_sha256(project_entries)
    executing_digest = _release_code_tree_sha256(executing_entries)
    if executing_digest != project_digest:
        raise ReleaseBuildError(
            "installed/executing time_twist package differs from the supplied "
            "project checkout release code; "
            f"executing={executing_digest}, project={project_digest}. "
            "Reinstall or update the package, or execute the matching checkout."
        )
    commit, dirty = _git_provenance(root)
    return {
        "schema": CODE_PROVENANCE_SCHEMA,
        "code_root": CODE_LOGICAL_ROOT,
        "hash_algorithm": CODE_TREE_HASH_ALGORITHM,
        "tree_sha256": project_digest,
        "file_count": len(project_entries),
        "git_commit": commit,
        "git_dirty": dirty,
    }


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
        paths.translations / f"{bank}.json" for bank in KNOWN_SCENARIO_BANKS
    )
    return (
        paths.zenpen_baseline,
        paths.kouhen_baseline,
        paths.title_asset,
        *translations,
    )


def _protected_release_paths(paths: ReleasePaths) -> dict[Path, str]:
    """Return project files that release metadata must never overwrite."""
    protected: dict[Path, str] = {
        (paths.project_root / "pyproject.toml").resolve(): "project metadata",
        paths.source_lock.resolve(): "release source lock",
        paths.release_target.resolve(): "release target",
    }
    for path in authoritative_source_paths(paths):
        protected[path.resolve()] = "approved release source"
    for path in release_code_paths(paths.project_root):
        protected[path.resolve()] = "release-critical code"
    return protected


def _validate_destination_collision(
    destination: Path,
    protected: Mapping[Path, str],
    *,
    label: str,
) -> None:
    """Reject metadata output that aliases a protected release file."""
    resolved = destination.expanduser().resolve()
    protected_label = protected.get(resolved)
    if protected_label is not None:
        raise ReleaseBuildError(
            f"{label} collides with protected {protected_label}: {resolved}"
        )


def _source_normalization(relative: str) -> str:
    """Return the established content policy for one locked source path."""
    logical_path = PurePosixPath(relative)
    if (
        len(logical_path.parts) == 3
        and logical_path.parts[:2] == ("work", "translations")
        and logical_path.suffix == ".json"
    ):
        return SOURCE_NORMALIZATION_LF
    return SOURCE_NORMALIZATION_RAW


def _source_bytes(path: Path, normalization: object) -> bytes:
    """Read bytes according to an explicitly validated lock policy."""
    data = path.read_bytes()
    if normalization == SOURCE_NORMALIZATION_RAW:
        return data
    if normalization == SOURCE_NORMALIZATION_LF:
        return _lf_normalized_bytes(data)
    raise ReleaseBuildError(
        f"unsupported source normalization {normalization!r}: {path}"
    )


def build_source_lock_payload(
    project_root: Path | None = None,
) -> dict[str, object]:
    """Create the deterministic approved-input lock payload."""
    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    files: dict[str, dict[str, object]] = {}
    for path in authoritative_source_paths(paths):
        if not path.is_file():
            raise ReleaseBuildError(
                f"required release source is missing: {path}"
            )
        relative = _project_relative(path, root)
        normalization = _source_normalization(relative)
        contents = _source_bytes(path, normalization)
        files[relative] = {
            "normalization": normalization,
            "sha256": sha256_bytes(contents),
            "bytes": len(contents),
        }
    return {
        "schema": SOURCE_LOCK_SCHEMA,
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
        newline="\n",
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
    protected = _protected_release_paths(paths)
    protected.pop(paths.source_lock.resolve(), None)
    _validate_destination_collision(
        destination,
        protected,
        label="source-lock destination",
    )
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
    payload = validate_source_lock_metadata(
        _read_json_object(lock_path, label="release source lock")
    )

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
            raise ReleaseBuildError(
                f"required release source is missing: {source_path}"
            )
        record = expected_files[relative]
        if not isinstance(record, dict):
            raise ReleaseBuildError(f"invalid lock record for {relative}")
        normalization = record.get("normalization")
        contents = _source_bytes(source_path, normalization)
        actual_hash = sha256_bytes(contents)
        if record.get("sha256") != actual_hash:
            raise ReleaseBuildError(
                f"unapproved release input changed: {relative}; "
                f"expected {record.get('sha256')}, got {actual_hash}"
            )
        if record.get("bytes") != len(contents):
            raise ReleaseBuildError(f"locked size mismatch for {relative}")
    if payload.get("subtitle") != DEFAULT_SUBTITLE:
        raise ReleaseBuildError(
            "locked subtitle differs from the code default"
        )
    return payload


def validate_source_lock_metadata(payload: object) -> dict[str, object]:
    """Validate source-lock JSON structure without requiring private files."""
    if not isinstance(payload, dict):
        raise ReleaseBuildError("release source lock must be a JSON object")
    required_fields = {"schema", "authority", "subtitle", "files"}
    if set(payload) != required_fields:
        raise ReleaseBuildError(
            "release source lock fields must be exactly "
            f"{sorted(required_fields)}"
        )
    if payload.get("schema") != SOURCE_LOCK_SCHEMA:
        raise ReleaseBuildError("unsupported release source lock schema")
    authority = payload.get("authority")
    if not isinstance(authority, str) or not authority.strip():
        raise ReleaseBuildError(
            "release source lock has invalid authority text"
        )
    subtitle = payload.get("subtitle")
    if not isinstance(subtitle, str) or not subtitle:
        raise ReleaseBuildError("release source lock has an invalid subtitle")
    expected_files = payload.get("files")
    if not isinstance(expected_files, dict):
        raise ReleaseBuildError("release source lock has no file mapping")
    if not expected_files:
        raise ReleaseBuildError("release source lock file mapping is empty")
    for relative, record in expected_files.items():
        if not isinstance(relative, str):
            raise ReleaseBuildError("release source lock path is not a string")
        logical_path = PurePosixPath(relative)
        if (
            "\\" in relative
            or logical_path.is_absolute()
            or logical_path.as_posix() != relative
            or not logical_path.parts
            or logical_path.parts[0] != "work"
            or ".." in logical_path.parts
        ):
            raise ReleaseBuildError(
                f"release source lock has unsafe path: {relative!r}"
            )
        if not isinstance(record, dict) or set(record) != {
            "normalization",
            "sha256",
            "bytes",
        }:
            raise ReleaseBuildError(f"invalid lock record for {relative}")
        normalization = record.get("normalization")
        expected_normalization = _source_normalization(relative)
        if normalization != expected_normalization:
            raise ReleaseBuildError(
                f"invalid source normalization for {relative}; expected "
                f"{expected_normalization!r}, got {normalization!r}"
            )
        if not _is_sha256(record.get("sha256")):
            raise ReleaseBuildError(f"invalid locked SHA-256 for {relative}")
        locked_size = record.get("bytes")
        if type(locked_size) is not int or locked_size < 0:
            raise ReleaseBuildError(f"invalid locked size for {relative}")
    return dict(payload)


def _validated_output_records(
    payload: object, *, label: str, include_path: bool = False
) -> dict[str, dict[str, object]]:
    """Validate release output records shared by target and build manifests."""
    if not isinstance(payload, dict) or set(payload) != set(
        RELEASE_OUTPUT_KEYS
    ):
        raise ReleaseBuildError(
            f"{label} outputs must contain exactly {list(RELEASE_OUTPUT_KEYS)}"
        )
    output: dict[str, dict[str, object]] = {}
    for name in RELEASE_OUTPUT_KEYS:
        record = payload[name]
        if not isinstance(record, dict):
            raise ReleaseBuildError(f"{label} output {name} is not an object")
        required_fields = {"bytes", "sha256"}
        if include_path:
            required_fields.add("path")
        if set(record) != required_fields:
            raise ReleaseBuildError(
                f"{label} output {name} fields must be exactly "
                f"{sorted(required_fields)}"
            )
        digest = record.get("sha256")
        size = record.get("bytes")
        if not _is_sha256(digest):
            raise ReleaseBuildError(
                f"{label} output {name} has an invalid SHA-256"
            )
        if type(size) is not int or size <= 0:
            raise ReleaseBuildError(
                f"{label} output {name} has an invalid byte size"
            )
        if include_path and record.get("path") != RELEASE_FILENAMES[name]:
            raise ReleaseBuildError(
                f"{label} output {name} must use canonical path "
                f"{RELEASE_FILENAMES[name]!r}"
            )
        output[name] = dict(record)
    return output


def _validated_code_provenance(
    payload: object,
    *,
    label: str,
) -> dict[str, object]:
    """Validate the shape of a manifest or target provenance record."""
    if not isinstance(payload, dict):
        raise ReleaseBuildError(f"{label} has no code provenance")
    required_fields = {
        "schema",
        "code_root",
        "hash_algorithm",
        "tree_sha256",
        "file_count",
        "git_commit",
        "git_dirty",
    }
    if set(payload) != required_fields:
        raise ReleaseBuildError(
            f"{label} code provenance fields must be exactly "
            f"{sorted(required_fields)}"
        )
    if payload.get("schema") != CODE_PROVENANCE_SCHEMA:
        raise ReleaseBuildError(f"{label} has unsupported code provenance")
    if payload.get("code_root") != CODE_LOGICAL_ROOT:
        raise ReleaseBuildError(f"{label} has an unexpected code root")
    if payload.get("hash_algorithm") != CODE_TREE_HASH_ALGORITHM:
        raise ReleaseBuildError(f"{label} has an unsupported code-tree hash")
    digest = payload.get("tree_sha256")
    if not _is_sha256(digest):
        raise ReleaseBuildError(f"{label} has an invalid code-tree SHA-256")
    file_count = payload.get("file_count")
    if type(file_count) is not int or file_count <= 0:
        raise ReleaseBuildError(f"{label} has an invalid code file count")
    commit = payload.get("git_commit")
    if commit is not None and (
        not isinstance(commit, str)
        or len(commit) not in (40, 64)
        or any(character not in "0123456789abcdef" for character in commit)
    ):
        raise ReleaseBuildError(f"{label} has an invalid Git commit")
    dirty = payload.get("git_dirty")
    if dirty is not None and type(dirty) is not bool:
        raise ReleaseBuildError(f"{label} has an invalid Git dirty state")
    return dict(payload)


def _validated_build_environment(
    payload: object,
    *,
    label: str,
) -> dict[str, str]:
    """Validate informational Python and Pillow build-environment metadata."""
    if not isinstance(payload, dict):
        raise ReleaseBuildError(f"{label} has no build environment")
    required_fields = {
        "schema",
        "python_implementation",
        "python_version",
        "pillow_version",
    }
    if set(payload) != required_fields:
        raise ReleaseBuildError(
            f"{label} build environment fields must be exactly "
            f"{sorted(required_fields)}"
        )
    if payload.get("schema") != BUILD_ENVIRONMENT_SCHEMA:
        raise ReleaseBuildError(f"{label} has unsupported build environment")
    result: dict[str, str] = {}
    for field in required_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ReleaseBuildError(
                f"{label} build environment has invalid {field}"
            )
        result[field] = value
    return result


def _validated_scenario_report(
    payload: object,
    *,
    label: str,
) -> dict[str, dict[str, object]]:
    """Validate the complete per-bank audit summary in a release manifest."""
    if not isinstance(payload, dict) or set(payload) != set(
        SCENARIO_LOCATIONS
    ):
        raise ReleaseBuildError(
            f"{label} scenario banks must contain exactly "
            f"{sorted(SCENARIO_LOCATIONS)}"
        )
    output: dict[str, dict[str, object]] = {}
    required_fields = {
        "records",
        "dictionary_entries",
        "packed_bytes",
        "capacity_bytes",
        "remaining_bytes",
        "sha256",
    }
    for bank_name in SCENARIO_LOCATIONS:
        record = payload[bank_name]
        if not isinstance(record, dict) or set(record) != required_fields:
            raise ReleaseBuildError(
                f"{label} scenario bank {bank_name} fields must be exactly "
                f"{sorted(required_fields)}"
            )
        records = record.get("records")
        dictionary_entries = record.get("dictionary_entries")
        packed_bytes = record.get("packed_bytes")
        capacity_bytes = record.get("capacity_bytes")
        remaining_bytes = record.get("remaining_bytes")
        if type(records) is not int or records <= 0:
            raise ReleaseBuildError(
                f"{label} scenario bank {bank_name} has invalid record count"
            )
        if (
            type(dictionary_entries) is not int
            or dictionary_entries < 0
            or dictionary_entries > 31
        ):
            raise ReleaseBuildError(
                f"{label} scenario bank {bank_name} has invalid dictionary count"
            )
        for field, value in (
            ("packed_bytes", packed_bytes),
            ("capacity_bytes", capacity_bytes),
            ("remaining_bytes", remaining_bytes),
        ):
            if type(value) is not int or value < 0:
                raise ReleaseBuildError(
                    f"{label} scenario bank {bank_name} has invalid {field}"
                )
        assert isinstance(packed_bytes, int)
        assert isinstance(capacity_bytes, int)
        assert isinstance(remaining_bytes, int)
        if remaining_bytes != capacity_bytes - packed_bytes:
            raise ReleaseBuildError(
                f"{label} scenario bank {bank_name} has inconsistent capacity"
            )
        if not _is_sha256(record.get("sha256")):
            raise ReleaseBuildError(
                f"{label} scenario bank {bank_name} has invalid SHA-256"
            )
        output[bank_name] = dict(record)
    return output


def _validated_component_hashes(
    payload: object,
    *,
    label: str,
) -> dict[str, str]:
    """Validate the fixed release-component hashes in a manifest."""
    expected = {"NOV2", "NOV4", "SON-KOUH"}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ReleaseBuildError(
            f"{label} component hashes must contain exactly {sorted(expected)}"
        )
    output: dict[str, str] = {}
    for component in sorted(expected):
        digest = payload.get(component)
        if not _is_sha256(digest):
            raise ReleaseBuildError(
                f"{label} component {component} has invalid SHA-256"
            )
        assert isinstance(digest, str)
        output[component] = digest
    return output


def validate_release_manifest_metadata(
    payload: object,
    *,
    label: str = "release manifest",
) -> dict[str, object]:
    """Validate a complete candidate or verified release audit manifest."""
    if not isinstance(payload, dict):
        raise ReleaseBuildError(f"{label} must be a JSON object")
    schema = payload.get("schema")
    if schema == LEGACY_RELEASE_MANIFEST_SCHEMA:
        raise ReleaseBuildError(
            "legacy release manifest v3 lacks the complete audit metadata "
            "required by the v4 release pipeline; rebuild the candidate"
        )
    if schema != RELEASE_MANIFEST_SCHEMA:
        raise ReleaseBuildError(
            f"unsupported release manifest schema: {schema!r}"
        )
    required_fields = {
        "schema",
        "mode",
        "project_source_lock",
        "source_lock_sha256",
        "code_provenance",
        "build_environment",
        "release_target",
        "release_target_sha256",
        "release_id",
        "subtitle",
        "scenario_banks",
        "component_sha256",
        "outputs",
    }
    if set(payload) != required_fields:
        raise ReleaseBuildError(
            f"{label} fields must be exactly {sorted(required_fields)}"
        )
    mode = payload.get("mode")
    if mode not in ("candidate", "verified"):
        raise ReleaseBuildError(f"{label} has invalid mode: {mode!r}")
    lock_path = payload.get("project_source_lock")
    if not isinstance(lock_path, str) or not lock_path.strip():
        raise ReleaseBuildError(f"{label} has invalid source-lock path")
    if not _is_sha256(payload.get("source_lock_sha256")):
        raise ReleaseBuildError(f"{label} has invalid source-lock SHA-256")
    _validated_code_provenance(payload.get("code_provenance"), label=label)
    _validated_build_environment(payload.get("build_environment"), label=label)
    subtitle = payload.get("subtitle")
    if not isinstance(subtitle, str) or not subtitle:
        raise ReleaseBuildError(f"{label} has invalid subtitle")
    _validated_scenario_report(payload.get("scenario_banks"), label=label)
    _validated_component_hashes(payload.get("component_sha256"), label=label)
    _validated_output_records(
        payload.get("outputs"), label=label, include_path=True
    )
    release_target = payload.get("release_target")
    release_target_sha256 = payload.get("release_target_sha256")
    release_id = payload.get("release_id")
    if mode == "candidate":
        if any(
            value is not None
            for value in (release_target, release_target_sha256, release_id)
        ):
            raise ReleaseBuildError(
                f"{label} candidate target fields must all be null"
            )
    else:
        if not isinstance(release_target, str) or not release_target.strip():
            raise ReleaseBuildError(
                f"{label} verified build has invalid target path"
            )
        if not _is_sha256(release_target_sha256):
            raise ReleaseBuildError(
                f"{label} verified build has invalid target SHA-256"
            )
        if not isinstance(release_id, str) or not release_id.strip():
            raise ReleaseBuildError(
                f"{label} verified build has invalid release ID"
            )
    return dict(payload)


def validate_code_provenance(
    payload: object,
    *,
    project_root: Path,
    label: str,
) -> dict[str, object]:
    """Reject provenance that does not match active release-critical code."""
    expected = _validated_code_provenance(payload, label=label)
    actual = build_code_provenance(project_root)
    for field in ("tree_sha256", "file_count"):
        if expected[field] != actual[field]:
            raise ReleaseBuildError(
                f"{label} belongs to different release-critical code; "
                "build and review a new candidate"
            )
    return expected


def _validate_release_code_stable(
    initial: Mapping[str, object], project_root: Path
) -> None:
    """Fail if release-critical source changed during one operation."""
    current = build_code_provenance(project_root)
    for field in ("tree_sha256", "file_count"):
        if current[field] != initial[field]:
            raise ReleaseBuildError(
                "release-critical code changed while the release operation "
                "was running; discard the result and retry from a stable tree"
            )


def validate_release_target(
    path: Path,
    *,
    source_lock_sha256: str,
    project_root: Path,
) -> dict[str, object]:
    """Validate a promoted target against active inputs and implementation."""
    target_path = path.expanduser().resolve()
    if not target_path.is_file():
        raise ReleaseBuildError(
            f"release target is missing: {target_path}; build a candidate and run "
            "release-promote"
        )
    payload = _read_json_object(target_path, label="release target")
    schema = payload.get("schema")
    if schema == LEGACY_RELEASE_TARGET_SCHEMA:
        raise ReleaseBuildError(
            "legacy release target v1 is intentionally untrusted by the v2 "
            "release pipeline; rebuild a candidate with the current code, "
            "review and playtest it, then run release-promote"
        )
    if schema != RELEASE_TARGET_SCHEMA:
        raise ReleaseBuildError(
            f"unsupported release target schema: {schema!r}"
        )
    required_fields = {
        "schema",
        "release_id",
        "source_lock_sha256",
        "code_provenance",
        "promoted_from_manifest_sha256",
        "outputs",
    }
    if set(payload) != required_fields:
        raise ReleaseBuildError(
            "release target fields must be exactly "
            f"{sorted(required_fields)}"
        )
    release_id = payload.get("release_id")
    if not isinstance(release_id, str) or not release_id.strip():
        raise ReleaseBuildError("release target has an invalid release ID")
    promoted_digest = payload.get("promoted_from_manifest_sha256")
    if not _is_sha256(promoted_digest):
        raise ReleaseBuildError(
            "release target has an invalid promoted-manifest SHA-256"
        )
    target_lock_digest = payload.get("source_lock_sha256")
    if not _is_sha256(target_lock_digest):
        raise ReleaseBuildError(
            "release target has an invalid source-lock SHA-256"
        )
    if target_lock_digest != source_lock_sha256:
        raise ReleaseBuildError(
            "release target belongs to a different source lock; build a candidate "
            "and promote it after review"
        )
    validate_code_provenance(
        payload.get("code_provenance"),
        project_root=project_root,
        label="release target",
    )
    _validated_output_records(payload.get("outputs"), label="release target")
    return payload


def _load_translation_map(
    bank_name: str, translations_directory: Path
) -> dict[str, str]:
    path = translations_directory / f"{bank_name}.json"
    payload = _read_json_object(path, label=f"{bank_name} translation map")
    translations: dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ReleaseBuildError(
                f"{path} must map string IDs to string text"
            )
        translations[key] = value
    return translations


def _encoded_groups(
    bank: ScenarioBank,
    bank_name: str,
    translations: dict[str, str],
) -> tuple[tuple[tuple[PackedSymbol, ...], ...], ...]:
    """Validate release translations through the shared scenario policy."""
    records_by_id = {
        scenario_record_id(
            bank_name,
            record.group_index,
            record.record_index,
        ): record
        for record in bank.records
    }
    unknown = sorted(set(translations) - set(records_by_id))
    missing = sorted(set(records_by_id) - set(translations))
    if unknown or missing:
        raise ReleaseBuildError(
            f"{bank_name} translation IDs differ from the source; "
            f"unknown={unknown[:1]}, missing={missing[:1]}"
        )

    encoded: dict[str, tuple[PackedSymbol, ...]] = {}
    for record_id, record in records_by_id.items():
        japanese = render_symbols(record.symbols, bank.dictionary)
        try:
            encoded[record_id] = encode_validated_english(
                record_id,
                translations[record_id],
                japanese,
            )
        except EnglishTextError as error:
            raise ReleaseBuildError(
                f"invalid English in {record_id}: {error}"
            ) from error

    return tuple(
        tuple(
            encoded[
                scenario_record_id(
                    bank_name,
                    group_index,
                    record.record_index,
                )
            ]
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
    """Build one scenario bank with fixed-UI boundary and capacity guards."""
    source_path = temporary_directory / f"{bank_name}_source.bin"
    source_path.write_bytes(source)
    bank = parse_scenario_bank(
        source_path,
        minimum_dictionary_entries=source_dictionary_reference_floor(
            bank_name,
            source,
        ),
    )
    groups = _encoded_groups(
        bank,
        bank_name,
        _load_translation_map(bank_name, translations_directory),
    )
    text_start = bank.group_addresses[0] - bank.load_address
    capacity = bank.dictionary_end_offset - text_start
    pointer_bytes = 2 * (len(groups) - 1)
    compressed, dictionary = compress_english_groups(
        groups,
        required_entries=required_dictionary_entries(bank_name),
        max_bytes=capacity - pointer_bytes,
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

    used = packed_size(compressed, dictionary) + pointer_bytes
    return ScenarioBuildResult(
        data=rebuilt,
        records=len(bank.records),
        dictionary_entries=len(dictionary),
        packed_bytes=used,
        capacity_bytes=capacity,
    )


def _replace(image: FdsImage, side: int, name: str, data: bytes) -> None:
    image.sides[side].find_file(name).data = data


def _output_records(
    output_bytes: Mapping[str, bytes],
) -> dict[str, dict[str, object]]:
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
) -> dict[str, dict[str, dict[str, object]]]:
    expected = _validated_output_records(
        target.get("outputs"), label="release target"
    )
    mismatches: dict[str, dict[str, dict[str, object]]] = {}
    for name in RELEASE_OUTPUT_KEYS:
        expected_record = expected[name]
        actual_record = outputs[name]
        differences = {
            field: {
                "expected": expected_record[field],
                "actual": actual_record[field],
            }
            for field in ("bytes", "sha256")
            if expected_record[field] != actual_record[field]
        }
        if differences:
            mismatches[name] = differences
    return mismatches


def _validate_candidate_outputs(
    manifest_path: Path,
    output_records: Mapping[str, Mapping[str, object]],
) -> None:
    """Fail unless candidate files still match their validated manifest records."""
    for name in RELEASE_OUTPUT_KEYS:
        record = output_records[name]
        output_path = manifest_path.parent / RELEASE_FILENAMES[name]
        if output_path.is_symlink():
            raise ReleaseBuildError(
                f"candidate output must not be a symlink: {output_path}"
            )
        if not output_path.is_file():
            raise ReleaseBuildError(
                f"candidate output is missing: {output_path}"
            )
        if output_path.stat().st_size != record["bytes"]:
            raise ReleaseBuildError(
                f"candidate output size changed: {output_path}"
            )
        if sha256_file(output_path) != record["sha256"]:
            raise ReleaseBuildError(
                f"candidate output hash changed: {output_path}"
            )


def _validate_candidate_against_rebuild(
    manifest: Mapping[str, object],
    rebuilt: Mapping[str, object],
) -> None:
    """Bind candidate audit claims to a fresh deterministic rebuild."""
    for field in ("scenario_banks", "component_sha256", "outputs"):
        if manifest.get(field) != rebuilt.get(field):
            raise ReleaseBuildError(
                f"candidate manifest {field} does not match a fresh canonical "
                "rebuild from the active source lock and release code"
            )


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
    # A previous manifest must never attest a partially updated output set if
    # publication fails between individual atomic file replacements.
    (output_directory / "release_manifest.json").unlink(missing_ok=True)
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
    code_provenance = build_code_provenance(root)
    lock_path = (source_lock or paths.source_lock).expanduser().resolve()
    target_path = (
        (release_target or paths.release_target).expanduser().resolve()
    )
    if not lock_path.is_file():
        validate_source_lock(lock_path, project_root=root)
    lock_sha256_before = source_lock_sha256(lock_path)
    lock = validate_source_lock(lock_path, project_root=root)
    lock_sha256 = source_lock_sha256(lock_path)
    if lock_sha256 != lock_sha256_before:
        raise ReleaseBuildError(
            "release source lock changed while it was being validated"
        )
    if subtitle != lock.get("subtitle"):
        raise ReleaseBuildError(
            "release subtitle differs from the approved lock"
        )

    target_payload: dict[str, object] | None = None
    target_sha256: str | None = None
    if verify_target:
        if not target_path.is_file():
            validate_release_target(
                target_path,
                source_lock_sha256=lock_sha256,
                project_root=root,
            )
        target_sha256_before = sha256_file(target_path)
        target_payload = validate_release_target(
            target_path,
            source_lock_sha256=lock_sha256,
            project_root=root,
        )
        target_sha256 = sha256_file(target_path)
        if target_sha256 != target_sha256_before:
            raise ReleaseBuildError(
                "release target changed while it was being validated"
            )

    zenpen = FdsImage.read(paths.zenpen_baseline)
    kouhen = FdsImage.read(paths.kouhen_baseline)
    images = {"zenpen": zenpen, "kouhen": kouhen}
    scenario_report: dict[str, dict[str, object]] = {}

    with tempfile.TemporaryDirectory(
        prefix="time_twist_components_"
    ) as directory:
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

    if target_payload is not None:
        mismatches = _target_mismatches(target_payload, outputs)
        if mismatches:
            raise ReleaseBuildError(
                f"release output differs from the promoted target: {mismatches}; "
                "use --candidate, review the build, then release-promote"
            )

    manifest: dict[str, object] = {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "mode": "verified" if verify_target else "candidate",
        "project_source_lock": display_path(lock_path, root),
        "source_lock_sha256": lock_sha256,
        "code_provenance": code_provenance,
        "build_environment": build_environment_provenance(),
        "release_target": (
            display_path(target_path, root) if verify_target else None
        ),
        "release_target_sha256": (target_sha256 if verify_target else None),
        "release_id": (
            target_payload.get("release_id") if target_payload else None
        ),
        "subtitle": subtitle,
        "scenario_banks": scenario_report,
        "component_sha256": {
            "NOV2": sha256_bytes(zenpen.sides[0].find_file("NOV2").data),
            "NOV4": sha256_bytes(zenpen.sides[0].find_file("NOV4").data),
            "SON-KOUH": sha256_bytes(
                kouhen.sides[0].find_file("SON-KOUH").data
            ),
        },
        "outputs": outputs,
    }
    validate_release_manifest_metadata(
        manifest, label="generated release manifest"
    )

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
        _validate_release_code_stable(code_provenance, root)
        validate_source_lock(lock_path, project_root=root)
        if source_lock_sha256(lock_path) != lock_sha256:
            raise ReleaseBuildError(
                "release source lock changed while the release was built"
            )
        if verify_target and (
            not target_path.is_file()
            or sha256_file(target_path) != target_sha256
        ):
            raise ReleaseBuildError(
                "release target changed while the release was built"
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
    """Promote only a candidate reproduced from active inputs and code."""
    root = discover_project_root(project_root)
    paths = ReleasePaths.from_project_root(root)
    active_code_provenance = build_code_provenance(root)
    manifest_path = candidate_manifest.expanduser().resolve()
    if not manifest_path.is_file():
        raise ReleaseBuildError(
            f"candidate manifest is missing: {manifest_path}"
        )
    manifest_sha256 = sha256_file(manifest_path)
    manifest = validate_release_manifest_metadata(
        _read_json_object(manifest_path, label="candidate release manifest"),
        label="candidate release manifest",
    )
    if manifest.get("mode") != "candidate":
        raise ReleaseBuildError(
            "release-promote requires a candidate-mode manifest"
        )

    lock_path_value = manifest.get("project_source_lock")
    if not isinstance(lock_path_value, str):
        raise ReleaseBuildError("candidate manifest has no source-lock path")
    lock_path = Path(lock_path_value)
    if not lock_path.is_absolute():
        lock_path = (root / lock_path).resolve()
        try:
            lock_path.relative_to(root)
        except ValueError as error:
            raise ReleaseBuildError(
                "candidate manifest source-lock path escapes the project; "
                "external source locks must use an absolute path"
            ) from error
    if not lock_path.is_file():
        validate_source_lock(lock_path, project_root=root)
    lock_sha256_before = source_lock_sha256(lock_path)
    lock = validate_source_lock(lock_path, project_root=root)
    lock_sha256 = source_lock_sha256(lock_path)
    if lock_sha256 != lock_sha256_before:
        raise ReleaseBuildError(
            "release source lock changed while it was being validated"
        )
    if manifest.get("source_lock_sha256") != lock_sha256:
        raise ReleaseBuildError(
            "candidate manifest does not match the current source lock"
        )
    locked_subtitle = lock.get("subtitle")
    if not isinstance(locked_subtitle, str):
        raise ReleaseBuildError("active source lock has no valid subtitle")
    if manifest.get("subtitle") != locked_subtitle:
        raise ReleaseBuildError(
            "candidate manifest subtitle does not match the active source lock"
        )
    code_provenance = validate_code_provenance(
        manifest.get("code_provenance"),
        project_root=root,
        label="candidate manifest",
    )

    output_records = _validated_output_records(
        manifest.get("outputs"),
        label="candidate manifest",
        include_path=True,
    )
    _validate_candidate_outputs(manifest_path, output_records)

    selected_release_id = (
        release_id if release_id is not None else "english-playtest"
    )
    if not selected_release_id.strip():
        raise ReleaseBuildError("release ID must not be empty")

    destination = (target_path or paths.release_target).expanduser().resolve()
    protected = _protected_release_paths(paths)
    protected.pop(paths.release_target.resolve(), None)
    protected[lock_path.resolve()] = "active source lock"
    protected[manifest_path] = "candidate manifest"
    for filename in RELEASE_FILENAMES.values():
        protected[(manifest_path.parent / filename).resolve()] = (
            "candidate output"
        )
    _validate_destination_collision(
        destination,
        protected,
        label="release-target destination",
    )

    with tempfile.TemporaryDirectory(
        prefix="time_twist_promotion_rebuild_"
    ) as directory:
        rebuilt = build_release(
            Path(directory) / "candidate",
            project_root=root,
            source_lock=lock_path,
            verify_target=False,
            subtitle=locked_subtitle,
        )
    _validate_candidate_against_rebuild(manifest, rebuilt)

    _validate_release_code_stable(active_code_provenance, root)
    validate_source_lock(lock_path, project_root=root)
    if source_lock_sha256(lock_path) != lock_sha256:
        raise ReleaseBuildError(
            "release source lock changed while the candidate was validated"
        )

    target: dict[str, object] = {
        "schema": RELEASE_TARGET_SCHEMA,
        "release_id": selected_release_id,
        "source_lock_sha256": lock_sha256,
        "code_provenance": code_provenance,
        "promoted_from_manifest_sha256": manifest_sha256,
        "outputs": {
            name: {
                "bytes": output_records[name]["bytes"],
                "sha256": output_records[name]["sha256"],
            }
            for name in RELEASE_OUTPUT_KEYS
        },
    }
    _validate_candidate_outputs(manifest_path, output_records)
    if sha256_file(manifest_path) != manifest_sha256:
        raise ReleaseBuildError(
            "candidate manifest changed while it was being validated"
        )
    _atomic_write_json(destination, target)
    return target
