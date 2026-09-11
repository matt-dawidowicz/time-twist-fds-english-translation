"""Canonical release build, publication, and promotion API.

All playable image construction is delegated to :mod:`time_twist.release_build`,
which uses the frozen entropy codec and runtime. This module owns release-source
locking, provenance checks, transactional publication, and promotion.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .production_translation import materialize_production_maps
from .project import KNOWN_SCENARIO_BANKS
from .release_build import build_release_images
from .release_metadata import (
    BUILD_ENVIRONMENT_SCHEMA,
    CODE_LOGICAL_ROOT,
    CODE_PROVENANCE_SCHEMA,
    CODE_TREE_HASH_ALGORITHM,
    DEFAULT_KOUHEN_BASELINE,
    DEFAULT_PROJECT_ROOT,
    DEFAULT_RELEASE_TARGET,
    DEFAULT_SLIDE_TITLE_ASSET,
    DEFAULT_SOURCE_LOCK,
    DEFAULT_TITLE_ASSET,
    DEFAULT_ZENPEN_BASELINE,
    RELEASE_FILENAMES,
    RELEASE_MANIFEST_SCHEMA,
    RELEASE_OUTPUT_KEYS,
    RELEASE_TARGET_SCHEMA,
    SCENARIO_LOCATIONS,
    SOURCE_CHECKOUT_ROOT,
    SOURCE_LOCK_SCHEMA,
    SOURCE_NORMALIZATION_LF,
    SOURCE_NORMALIZATION_RAW,
    ReleaseBuildError,
    ReleasePaths,
    _atomic_write_json,
    _protected_release_paths,
    _read_json_object,
    _validate_destination_collision,
    _validated_output_records,
    authoritative_source_paths,
    build_code_provenance,
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
    validate_code_provenance,
    validate_release_manifest_metadata,
    validate_release_target,
    validate_source_lock,
    validate_source_lock_metadata,
    write_source_lock,
)
from .title import DEFAULT_SUBTITLE

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
    target instead of trusting filenames or a prior manifest. The structured
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
    manifest: Mapping[str, object], rebuilt: Mapping[str, object]
) -> None:
    """Bind candidate audit claims to a fresh deterministic rebuild."""
    for field in (
        "codec",
        "decoder_format",
        "record_framing",
        "fixed_decoder_surfaces",
        "nov3_exclusive_boundary",
        "scenario_banks",
        "component_sha256",
        "outputs",
    ):
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
    """Build canonical entropy images transactionally from approved sources.

    Candidate mode (``verify_target=False``) publishes a complete build without
    approving its hashes. Verified mode requires a promoted ``release_target``
    tied to the active source lock. No output is published until source, code,
    build, hash, and target checks all succeed.
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

    with tempfile.TemporaryDirectory(
        prefix="time_twist_release_text_"
    ) as translation_directory:
        production_translations = Path(translation_directory)
        materialize_production_maps(
            tuple(KNOWN_SCENARIO_BANKS),
            base_directory=paths.translations,
            override_directory=paths.production_overrides,
            review_directory=paths.production_review,
            output_directory=production_translations,
        )
        output_bytes, build_audit = build_release_images(
            paths.zenpen_baseline.read_bytes(),
            paths.kouhen_baseline.read_bytes(),
            translations_directory=production_translations,
            title_asset=paths.title_asset,
            slide_title_asset=paths.slide_title_asset,
            subtitle=subtitle,
        )

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
        "release_target_sha256": target_sha256 if verify_target else None,
        "release_id": target_payload.get("release_id") if target_payload else None,
        "subtitle": subtitle,
        "codec": build_audit["codec"],
        "decoder_format": build_audit["decoder_format"],
        "record_framing": build_audit["record_framing"],
        "fixed_decoder_surfaces": build_audit["fixed_decoder_surfaces"],
        "nov3_exclusive_boundary": build_audit["nov3_exclusive_boundary"],
        "scenario_banks": build_audit["scenario_banks"],
        "component_sha256": build_audit["components"],
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
    "DEFAULT_SLIDE_TITLE_ASSET",
    "DEFAULT_SOURCE_LOCK",
    "DEFAULT_TITLE_ASSET",
    "DEFAULT_ZENPEN_BASELINE",
    "RELEASE_FILENAMES",
    "RELEASE_MANIFEST_SCHEMA",
    "RELEASE_OUTPUT_KEYS",
    "RELEASE_TARGET_SCHEMA",
    "SCENARIO_LOCATIONS",
    "SOURCE_CHECKOUT_ROOT",
    "SOURCE_LOCK_SCHEMA",
    "SOURCE_NORMALIZATION_LF",
    "SOURCE_NORMALIZATION_RAW",
    "ReleaseBuildError",
    "ReleasePaths",
    "authoritative_source_paths",
    "build_code_provenance",
    "build_environment_provenance",
    "build_release",
    "build_release_images",
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
