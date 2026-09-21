#!/usr/bin/env python3
"""CI-safe integrity check for the recovered v38 source bundle."""
from __future__ import annotations
import base64, gzip, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
payload = HERE / "payload"

for item in manifest["files"]:
    encoded = (payload / item["payload"]).read_text(encoding="ascii")
    raw = gzip.decompress(base64.b64decode("".join(encoded.split())))
    if len(raw) != item["bytes"]:
        raise SystemExit(f"size mismatch: {item['path']}")
    got = hashlib.sha256(raw).hexdigest()
    if got != item["sha256"]:
        raise SystemExit(f"sha256 mismatch: {item['path']}: {got}")

print(
    f"PASS recovered v38 payloads {len(manifest['files'])}/{len(manifest['files'])}; "
    f"ROM gate {manifest['expected_rom_sha256']}"
)
