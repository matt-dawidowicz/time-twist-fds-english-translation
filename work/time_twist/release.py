"""Release construction and candidate promotion public API.

Source locks, provenance, and manifest validation live in
:mod:`time_twist.release_metadata`; this module owns image construction
and promotion while preserving the established public exports.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: F401 - retained as a public test/embedding patch seam
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .compression import compress_english_groups, packed_size
from .english import EnglishTextError
from .fds import FdsImage, combine_images
from .font import patched_nov4_font
from .project import (
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
from .release_metadata import (
    BUILD_ENVIRONMENT_SCHEMA,
    CODE_LOGICAL_ROOT,
    CODE_PROVENANCE_SCHEMA,
    CODE_TREE_HASH_ALGORITHM,
    DEFAULT_KOUHEN_BASELINE,
    DEFAULT_PROJECT_ROOT,
    DEFAULT_RELEASE_TARGET,
    DEFAULT_SOURCE_LOCK,
    DEFAULT_TITLE_ASSET,
    DEFAULT_ZENPEN_BASELINE,
    EXECUTING_PACKAGE_ROOT,
    RELEASE_FILENAMES,
    RELEASE_MANIFEST_SCHEMA,
    RELEASE_OUTPUT_KEYS,
    RELEASE_TARGET_SCHEMA,
    SCENARIO_LOCATIONS,
    SCENARIO_UI_PATCHERS,
    SOURCE_CHECKOUT_ROOT,
    SOURCE_LOCK_SCHEMA,
    SOURCE_NORMALIZATION_LF,
    SOURCE_NORMALIZATION_RAW,
    ReleaseBuildError,
    ReleasePaths,
    ScenarioBuildResult,
    _atomic_write_json,
    _protected_release_paths,
    _read_json_object,
    _validate_destination_collision,
    _validated_code_provenance,
    _validated_output_records,
    authoritative_source_paths,
    build_environment_provenance,
    build_source_lock_payload,
    discover_project_root,
    display_path,
    executing_release_code_tree_sha256,
    release_code_paths,
    release_code_tree_sha256,
    sha256_bytes,
    sha256_file,
    source_lock_sha256,
    validate_release_manifest_metadata,
    validate_release_target,
    validate_source_lock,
    validate_source_lock_metadata,
    write_source_lock,
)
from .release_metadata import (
    build_code_provenance as _build_code_provenance,
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
)


def build_code_provenance(
    project_root: Path,
    *,
    executing_code_root: Path | None = None,
) -> dict[str, object]:
    """Build provenance while retaining the release-module patch seam.

    Tests and embedders have historically patched
    ``time_twist.release.EXECUTING_PACKAGE_ROOT``. Keep that public seam at
    the facade even though the implementation now lives in
    :mod:`time_twist.release_metadata`.
    """
    return _build_code_provenance(
        project_root,
        executing_code_root=(
            executing_code_root
            if executing_code_root is not None
            else EXECUTING_PACKAGE_ROOT
        ),
    )


def validate_code_provenance(
    payload: object,
    *,
    project_root: Path,
    label: str,
) -> dict[str, object]:
    """Validate provenance through the facade's executable-code boundary."""
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
    """Reject a code-tree change using the facade's execution boundary."""
    current = build_code_provenance(project_root)
    for field in ("tree_sha256", "file_count"):
        if current[field] != initial[field]:
            raise ReleaseBuildError(
                "release-critical code changed while the release operation "
                "was running; discard the result and retry from a stable tree"
            )


def _load_translation_map(
    bank_name: str, translations_directory: Path
) -> dict[str, str]:
    """Load one bank's stable-ID English map for a release rebuild.

    Release construction never invents or infers translations from packed ROM
    bytes.  This boundary accepts only the reviewed ``ID -> English`` mapping
    from the private source overlay; later validation proves that its IDs match
    the recovered scenario records exactly.
    """
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
    """Replace one named overlay without changing its FDS side or identity.

    The side index and file name are recovered game layout, not build-time
    choices.  Keeping this write in one small helper makes each release-layer
    replacement auditable against the four-side source image.
    """
    image.sides[side].find_file(name).data = data


def _output_records(
    output_bytes: Mapping[str, bytes],
) -> dict[str, dict[str, object]]:
    """Describe each candidate image with its canonical name and exact hash.

    These records become the public-facing identity of a playtest candidate.
    The hash lets a tester, maintainer, and later promotion step prove they are
    discussing the same Zenpen, Kouhen, or combined four-side image.
    """
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
    """Return only byte-size or hash differences from a promoted target.

    Strict release mode compares the newly built candidate with the reviewed
    target instead of trusting filenames or a prior manifest.  The structured
    result gives a maintainer a precise explanation while keeping publication
    blocked whenever any image differs.
    """
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


__all__ = (
    "BUILD_ENVIRONMENT_SCHEMA",
    "CODE_LOGICAL_ROOT",
    "CODE_PROVENANCE_SCHEMA",
    "CODE_TREE_HASH_ALGORITHM",
    "DEFAULT_KOUHEN_BASELINE",
    "DEFAULT_PROJECT_ROOT",
    "DEFAULT_RELEASE_TARGET",
    "DEFAULT_SOURCE_LOCK",
    "DEFAULT_TITLE_ASSET",
    "DEFAULT_ZENPEN_BASELINE",
    "EXECUTING_PACKAGE_ROOT",
    "RELEASE_FILENAMES",
    "RELEASE_MANIFEST_SCHEMA",
    "RELEASE_OUTPUT_KEYS",
    "RELEASE_TARGET_SCHEMA",
    "SCENARIO_LOCATIONS",
    "SCENARIO_UI_PATCHERS",
    "SOURCE_CHECKOUT_ROOT",
    "SOURCE_LOCK_SCHEMA",
    "SOURCE_NORMALIZATION_LF",
    "SOURCE_NORMALIZATION_RAW",
    "ReleaseBuildError",
    "ReleasePaths",
    "ScenarioBuildResult",
    "authoritative_source_paths",
    "build_code_provenance",
    "build_environment_provenance",
    "build_release",
    "build_scenario_bank",
    "build_source_lock_payload",
    "discover_project_root",
    "display_path",
    "executing_release_code_tree_sha256",
    "promote_release_target",
    "release_code_paths",
    "release_code_tree_sha256",
    "sha256_bytes",
    "sha256_file",
    "source_lock_sha256",
    "validate_code_provenance",
    "validate_release_manifest_metadata",
    "validate_release_target",
    "validate_source_lock",
    "validate_source_lock_metadata",
    "write_source_lock",
)
