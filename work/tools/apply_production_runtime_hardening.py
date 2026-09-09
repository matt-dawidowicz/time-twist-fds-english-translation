"""Apply the production NOV2 runtime hardening to a built FDS candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from time_twist.production_runtime import patch_fds_image


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_fds", type=Path)
    parser.add_argument("output_fds", type=Path)
    args = parser.parse_args()

    source = args.input_fds.read_bytes()
    patched = patch_fds_image(source)
    args.output_fds.parent.mkdir(parents=True, exist_ok=True)
    args.output_fds.write_bytes(patched)

    print(f"input:  {len(source)} bytes  SHA-256 {_sha256(source)}")
    print(f"output: {len(patched)} bytes  SHA-256 {_sha256(patched)}")
    print(f"changed bytes: {sum(a != b for a, b in zip(source, patched, strict=True))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
