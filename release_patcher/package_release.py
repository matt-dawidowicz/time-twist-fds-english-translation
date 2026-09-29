from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
from pathlib import Path

PATCHES = {
    "zenpen": (
        "Time-Twist-English-v1.0-Zenpen.bps",
        "89ecec172ddd935dfa4aab42a87054bffd958399f41d4c476df7c7322523a0a4",
    ),
    "kouhen": (
        "Time-Twist-English-v1.0-Kouhen.bps",
        "8b5602b35efd0e1f06665b59d741fd0609628f8c6f1e25c50c3280b58efeb4f8",
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
    advanced = args.package_dir / "advanced"
    advanced.mkdir(parents=True, exist_ok=True)
    lines = []
    for kind, (filename, expected) in PATCHES.items():
        data = load_patch(root / "patches", kind)
        target = advanced / filename
        target.write_bytes(data)
        lines.append(f"{expected.upper()}  advanced/{filename}")
    (args.package_dir / "SHA256SUMS.txt").write_text(
        "\n".join(lines) + "\n", encoding="ascii"
    )

if __name__ == "__main__":
    main()
