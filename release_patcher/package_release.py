"""Assemble the public patcher package and verified published BPS patches."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

import TimeTwistPatcher as patcher

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads(
    (ROOT / "patch_manifest.json").read_text(encoding="utf-8")
)
PATCHES = {
    kind: (entry["filename"], entry["patch_sha256"].lower())
    for kind, entry in MANIFEST["patches"].items()
}


def digest(data: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def load_patch(patch_dir: Path, kind: str) -> bytes:
    """Decode one public or upgrade patch and verify its manifest identity."""
    if kind in {"zenpen", "kouhen"}:
        data = patcher._patch_bytes(kind)
    else:
        parts = sorted(patch_dir.glob(f"{kind}.bps.gz.b64.part*"))
        if not parts:
            raise RuntimeError(f"missing {kind} patch chunks")
        encoded = "".join(
            part.read_text(encoding="ascii").strip() for part in parts
        )
        data = gzip.decompress(base64.b64decode(encoded, validate=True))
    if digest(data) != PATCHES[kind][1]:
        raise RuntimeError(f"{kind} patch hash mismatch")
    return data


def main() -> None:
    """Write all published BPS files and checksums for every packaged file."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()
    package_dir = args.package_dir
    bps_dir = package_dir / "BPS-Patches"
    bps_dir.mkdir(parents=True, exist_ok=True)
    for kind, (filename, _) in PATCHES.items():
        (bps_dir / filename).write_bytes(load_patch(ROOT / "patches", kind))
    (package_dir / "PATCH-INPUTS.json").write_bytes(
        (ROOT / "patch_manifest.json").read_bytes()
    )
    lines = [
        f"{digest(path.read_bytes()).upper()}  {path.relative_to(package_dir).as_posix()}"
        for path in sorted(package_dir.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS.txt"
    ]
    (package_dir / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    main()
