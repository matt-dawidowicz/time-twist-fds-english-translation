#!/usr/bin/env python3
"""Restore the additional historical v34-v37 source lineage recovered with v38."""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "lineage_manifest.json"
PAYLOAD = HERE / "lineage_payload"

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    args = p.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        encoded = (PAYLOAD / item["payload"]).read_text(encoding="ascii")
        raw = gzip.decompress(base64.b64decode("".join(encoded.split())))
        if len(raw) != item["bytes"]:
            raise SystemExit(f"size mismatch: {item['path']}")
        got = hashlib.sha256(raw).hexdigest()
        if got != item["sha256"]:
            raise SystemExit(f"sha256 mismatch: {item['path']}: {got}")
        dest = args.output / item["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        print(f"RESTORED {item['path']}")
    print(f"PASS restored {len(manifest['files'])} historical lineage files")

if __name__ == "__main__":
    main()
