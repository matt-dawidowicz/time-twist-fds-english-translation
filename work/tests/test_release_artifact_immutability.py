"""Freeze the current public-tree release files without rebuilding the game.

The pinned values are Git *blob* SHA-1 identities, not release provenance or
cryptographic trust attestations. They allow ROM-free CI to detect accidental
changes to already distributed binaries. A deliberate new release must review
and update this baseline explicitly.
"""

from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"

# (byte count, Git blob object ID) from main at commit 3e72973f516c.
ARTIFACTS: dict[str, tuple[int, str]] = {
    "Time-Twist-English-v1.1-Kouhen.bps": (
        25976,
        "fa0d8f75fcecfbc501d9240c11eb6c30160e0ca4",
    ),
    "Time-Twist-English-v1.1-Patcher.exe": (
        11215414,
        "3a6c0bed455c6cc8cc1643c0ce9f44ba68263766",
    ),
    "Time-Twist-English-v1.1-Windows.zip": (
        11012383,
        "298e1e1f15dd0d5cabb1644e936f38ece3671905",
    ),
    "Time-Twist-English-v1.1-Zenpen.bps": (
        30472,
        "3be1f2b59a988206891ed721089976700f9a0a59",
    ),
    "Time-Twist-v82-to-v83-Kouhen.bps": (
        123,
        "0d8a9e0f4276042e33f2514e0a7e6c7c6cab9a44",
    ),
    "Time-Twist-v82-to-v83-four-side.bps": (
        130,
        "f0ecd77604498fe6acd884ce38a112e75b85198a",
    ),
}


def git_blob_sha1(path: Path, size: int) -> str:
    """Stream Git's standard blob header and file bytes into an object ID."""
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class ReleaseArtifactImmutabilityTests(unittest.TestCase):
    """Make changes to the checked-in v1.1 binaries an explicit review event."""

    def test_exactly_the_six_approved_release_files_are_present(self) -> None:
        """Detect accidental packaging additions, omissions, or renames."""
        self.assertEqual(
            {path.name for path in RELEASE.iterdir() if path.is_file()},
            set(ARTIFACTS),
        )

    def test_all_published_tree_artifact_bytes_are_frozen(self) -> None:
        """Check the identity of every BPS, ZIP and Windows executable."""
        for filename, (expected_size, expected_blob) in ARTIFACTS.items():
            with self.subTest(filename=filename):
                path = RELEASE / filename
                self.assertTrue(path.is_file(), filename)
                self.assertEqual(path.stat().st_size, expected_size)
                self.assertEqual(
                    git_blob_sha1(path, expected_size),
                    expected_blob,
                    filename,
                )


if __name__ == "__main__":
    unittest.main()
