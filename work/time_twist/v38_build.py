"""Build the approved v38 checkpoint from active maps and frozen compiler inputs.

The private v25 baseline supplies the established font, title and engine. The
hash-checked recovery compiler supplies v38 dictionaries, allocation and runtime
patches. Recovered scenario English is an immutable regression oracle only:
both compiler text inputs are regenerated from the active translation maps.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from .fds import FdsImage
from .production_translation import CANONICAL_RECORD_COUNTS
from .release_metadata import (
    SCENARIO_LOCATIONS,
    ReleaseBuildError,
    sha256_bytes,
)

BASELINE_SHA256 = (
    "813cdceb190e9714f7489c1bd5500f8e2ead3b3942f789ccf68bc6f3696bfc19"
)
OUTPUT_SHA256 = (
    "62c5dbc2de33c484de9f8c1318fc903642eb08e2b4d5fa8e28384dc699c4c400"
)
IMAGE_BYTES = 262000


def restore_checkpoint(bundle: Path, destination: Path) -> dict[str, str]:
    """Validate and restore compiler inputs, returning approved literal text."""
    manifest = json.loads(
        (bundle / "manifest.json").read_text(encoding="utf-8")
    )
    for item in manifest["files"]:
        relative = Path(item["path"])
        payload = Path(item["payload"])
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or len(payload.parts) != 1
        ):
            raise ReleaseBuildError("invalid checkpoint file path")
        raw = gzip.decompress(
            base64.b64decode((bundle / "payload" / payload).read_bytes())
        )
        if (
            len(raw) != item["bytes"]
            or hashlib.sha256(raw).hexdigest() != item["sha256"]
        ):
            raise ReleaseBuildError(f"checkpoint input mismatch: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    layouts = json.loads(
        (destination / "data/layouts.json").read_text(encoding="utf-8")
    )
    return {record: layout["literal"] for record, layout in layouts.items()}


def validate_checkpoint_records(
    actual: dict[str, str], approved: dict[str, str]
) -> None:
    """Reject any missing, extra or changed v38 wording or layout control."""
    if len(approved) != 1299:
        raise ReleaseBuildError(
            "v38 checkpoint must contain exactly 1299 records"
        )
    different = sorted(
        key
        for key in actual.keys() | approved.keys()
        if actual.get(key) != approved.get(key)
    )
    if different:
        raise ReleaseBuildError(
            f"active text differs from approved v38 in {len(different)} records: "
            + ", ".join(different[:10])
        )


def validate_checkpoint_record_ids(
    actual: dict[str, str], approved: dict[str, str]
) -> None:
    """Require active maps to retain the complete recovered v38 record topology."""
    if len(approved) != 1299:
        raise ReleaseBuildError(
            "v38 checkpoint must contain exactly 1299 records"
        )
    missing = sorted(approved.keys() - actual.keys())
    extra = sorted(actual.keys() - approved.keys())
    if missing or extra:
        raise ReleaseBuildError(
            "active text record topology differs from recovered v38; "
            f"missing={missing[:10]}, extra={extra[:10]}"
        )


def build_release_images(
    baseline: bytes,
    *,
    translations_directory: Path,
    compiler_bundle: Path,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Build source-locked active text with the recovered v38 compiler.

    Exact v38 text must still reproduce the historical v38 ROM hash. Later
    reviewed text revisions retain the recovered record topology and compiler
    contract but receive their release identity through candidate promotion.
    """
    if (
        len(baseline) != IMAGE_BYTES
        or hashlib.sha256(baseline).hexdigest() != BASELINE_SHA256
    ):
        raise ReleaseBuildError(
            "the exact private v25 safe-encoding baseline is required"
        )
    actual: dict[str, str] = {}
    for bank in CANONICAL_RECORD_COUNTS:
        actual.update(
            json.loads(
                (translations_directory / f"{bank}.json").read_text(
                    encoding="utf-8"
                )
            )
        )
    with tempfile.TemporaryDirectory(prefix="time_twist_v38_") as directory:
        root = Path(directory)
        source = root / "source"
        approved = restore_checkpoint(compiler_bundle, source)
        validate_checkpoint_record_ids(actual, approved)
        # Active maps are source-locked release inputs. The recovered v38 text
        # remains the immutable historical oracle, but later reviewed candidates
        # may intentionally differ in wording or presentation controls.
        # These are the only scenario text inputs read by the frozen compiler.
        (source / "data/layouts.json").write_text(
            json.dumps(
                {key: {"literal": value} for key, value in actual.items()}
            ),
            encoding="utf-8",
        )
        (source / "data/determinate_english.json").write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "record": key,
                            "target_english": " ".join(
                                re.sub(r"\{CTRL:[0-7]\}", " ", value).split()
                            ),
                        }
                        for key, value in actual.items()
                    ]
                }
            ),
            encoding="utf-8",
        )
        private_baseline = root / "baseline.fds"
        private_baseline.write_bytes(baseline)
        output = root / "output"
        result = subprocess.run(
            [
                sys.executable,
                str(source / "build_v38.py"),
                "--baseline",
                str(private_baseline),
                "--output-dir",
                str(output),
            ],
            cwd=source,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if result.returncode:
            raise ReleaseBuildError(
                "v38 compiler failure" + "\n" + result.stdout + result.stderr
            )
        built = (
            output / "Time-Twist-v38-PROTECTIVE-AMULET-CANDIDATE.fds"
        ).read_bytes()
        emitted = json.loads(
            (output / "reports/v38_emitted_text.json").read_text(
                encoding="utf-8"
            )
        )
        validate_checkpoint_records(emitted, actual)
        if len(built) != IMAGE_BYTES:
            raise ReleaseBuildError(
                f"release output has {len(built)} bytes; expected {IMAGE_BYTES}"
            )
        if (
            actual == approved
            and hashlib.sha256(built).hexdigest() != OUTPUT_SHA256
        ):
            raise ReleaseBuildError(
                "v38 text did not reproduce the approved v38 checkpoint"
            )
        report = json.loads(
            (output / "reports/v38_build.json").read_text(encoding="utf-8")
        )
    return _release_audit(baseline, built, report)


def _release_audit(
    baseline: bytes, built: bytes, report: dict
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Describe the actual final banks, including menus relocated after packing."""
    before, after = FdsImage.from_bytes(baseline), FdsImage.from_bytes(built)
    banks = {}
    for name, (part, side) in SCENARIO_LOCATIONS.items():
        index = side + (2 if part == "kouhen" else 0)
        old = before.sides[index].find_file(name).data
        data = after.sides[index].find_file(name).data
        end = 0xA200 + len(data)
        banks[name] = {
            "records": CANONICAL_RECORD_COUNTS[name],
            "dictionary_entries": report["banks"][name]["entry_count"],
            "source_bytes": len(old),
            "output_bytes": len(data),
            "loaded_end": f"0x{end:04X}",
            "nov3_headroom": 0xD7B5 - end,
            "sha256": sha256_bytes(data),
        }
    surfaces = {}
    for name, menu in report["inherited_v32_menu_changes"].items():
        surfaces[name] = {
            "records": menu["record_count"],
            "streams": len(menu["page_sizes"]),
            "packed_bytes": menu["used_bytes"],
            "capacity_bytes": max(
                menu["allocation_bytes"], menu["used_bytes"]
            ),
        }
    ui = report["inherited_v32_nov2_ui"]
    surfaces["NOV2"] = {
        "records": ui["record_count"],
        "streams": 1,
        "packed_bytes": ui["stream_bytes"],
        "capacity_bytes": ui["stream_bytes"],
    }
    audit: dict[str, object] = {
        "codec": "frozen-entropy-v1",
        "decoder_format": "entropy-only",
        "record_framing": "v38 checkpoint: bit-contiguous records; menu pages byte-aligned",
        "fixed_decoder_surfaces": surfaces,
        "nov3_exclusive_boundary": "0xD7B5",
        "scenario_banks": banks,
        "components": {
            name: sha256_bytes(after.sides[side].find_file(name).data)
            for name, side in (("NOV2", 0), ("NOV4", 0), ("SON-KOUH", 2))
        },
    }
    return {
        "zenpen": built[:131000],
        "kouhen": built[131000:],
        "four_side": built,
    }, audit
