from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from pathlib import Path

PATCHES = {
    "zenpen": (
        "Time-Twist-English-v1.0-Zenpen.bps",
        "a42ec859f7b28fa61356d6ea2fe650a29c1172129738f1136572ef427df9e255",
    ),
    "kouhen": (
        "Time-Twist-English-v1.0-Kouhen.bps",
        "9af9ad6e479c8024427766a1f4c1396ed76d8b33baf919bfa430507ef6f21879",
    ),
}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_patch(patch_dir: Path, kind: str) -> bytes:
    parts = sorted(patch_dir.glob(f"{kind}.bps.gz.b64.part*"))
    if not parts:
        raise RuntimeError(f"missing {kind} patch chunks")
    encoded = "".join(part.read_text(encoding="ascii").strip() for part in parts)
    data = gzip.decompress(base64.b64decode(encoded, validate=True))
    expected = PATCHES[kind][1]
    if digest(data) != expected:
        raise RuntimeError(f"{kind} patch hash mismatch")
    return data

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    bps_dir = args.package_dir / "BPS-Patches"
    bps_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for kind, (filename, expected) in PATCHES.items():
        data = load_patch(root / "patches", kind)
        target = bps_dir / filename
        target.write_bytes(data)
        lines.append(f"{expected.upper()}  BPS-Patches/{filename}")
    (args.package_dir / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )

if __name__ == "__main__":
    main()
