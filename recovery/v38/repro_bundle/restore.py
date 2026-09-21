#!/usr/bin/env python3
"""Restore the minimal recovered v38 reproduction source tree."""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
PAYLOAD = HERE / "payload"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    for item in manifest["files"]:
        encoded = (PAYLOAD / item["payload"]).read_text(encoding="ascii")
        raw = gzip.decompress(base64.b64decode("".join(encoded.split())))
        if len(raw) != item["bytes"]:
            raise SystemExit(f"size mismatch: {item['path']}")
        if sha256(raw) != item["sha256"]:
            raise SystemExit(f"sha256 mismatch: {item['path']}")
        dest = args.output / item["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        print(f"RESTORED {item['path']}")
    print("PASS restored recovered v38 source tree")

if __name__ == "__main__":
    main()
