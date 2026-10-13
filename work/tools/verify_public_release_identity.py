"""Verify v1.1 release identity from two legally obtained retail FDS images.

Original and generated game data remain local. All three patched ROMs are
written to a temporary directory and deleted after independent checks.
Pinned expected digests intentionally do not depend on the patcher constants.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "release_patcher"))

from TimeTwistPatcher import PatcherError, build_outputs  # noqa: E402

EXPECTED_INPUTS = {
    "zenpen": (
        "B9424DD29EE195A9FA9AC4F844F058C380E30F7ACA741218789FA8611F741916"
    ),
    "kouhen": (
        "F62A7424FE489CBE479C3EBAABE4CE62D85127601FFD3D08ABD4E5A0DC39442A"
    ),
}
EXPECTED_OUTPUTS = {
    "Time Twist - English Translation v1.1 - Zenpen.fds": (
        131_000,
        "0784FE632DB3DB424E963CCA840982942F689A4385EFE9BDE3E7940F325599F7",
    ),
    "Time Twist - English Translation v1.1 - Kouhen.fds": (
        131_000,
        "8327F1130563C3C6E87CBE67DA227429BAAC59E596B49D67BE1018FD3A2E398F",
    ),
    "Time Twist - English Translation v1.1.fds": (
        262_000,
        "4BBCCB13033B39570B3FE3EB64FBEBA4A9BD4C5C73248852F22665E4A3A9E17A",
    ),
}


def _digest(path: Path) -> str:
    """Hash a file in bounded chunks without copying its contents."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify(zenpen: Path, kouhen: Path) -> None:
    """Run the actual patcher and independently verify all output files."""
    inputs = {"zenpen": zenpen, "kouhen": kouhen}
    for part, path in inputs.items():
        actual = _digest(path)
        if actual != EXPECTED_INPUTS[part]:
            raise ValueError(
                f"{part}: not the pinned canonical retail image: {actual}"
            )

    with tempfile.TemporaryDirectory(prefix="time-twist-verify-") as tmp:
        results = build_outputs(
            zenpen,
            kouhen,
            Path(tmp),
            two_disk=True,
            four_side=True,
        )
        found = {result.path.name for result in results}
        if found != EXPECTED_OUTPUTS.keys():
            raise ValueError(f"unexpected output filenames: {sorted(found)}")
        for result in results:
            size, expected = EXPECTED_OUTPUTS[result.path.name]
            actual = _digest(result.path)
            if result.path.stat().st_size != size or actual != expected:
                raise ValueError(
                    f"release identity mismatch: {result.path.name}"
                )
            print(f"PASS {result.path.name}: {size:,} bytes; SHA-256 {actual}")
    print("All outputs match the frozen English v1.1 release identity.")


def main() -> int:
    """Take private retail-file paths and refuse unsupported images."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zenpen", type=Path)
    parser.add_argument("kouhen", type=Path)
    args = parser.parse_args()
    try:
        verify(args.zenpen, args.kouhen)
    except (OSError, ValueError, PatcherError) as exc:
        parser.exit(1, f"Release verification failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
