"""Public, ROM-free verification for the distributable patcher."""

from __future__ import annotations

import binascii
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import TimeTwistPatcher as patcher  # noqa: E402
import package_release as package  # noqa: E402
from build_patches import create_bps  # noqa: E402


def _declared_sizes(patch: bytes) -> tuple[int, int]:
    position = 4
    source_size, position = patcher._bps_number(patch, position)
    target_size, _ = patcher._bps_number(patch, position)
    return source_size, target_size


def main() -> None:
    zenpen = patcher._patch_bytes("zenpen")
    kouhen = patcher._patch_bytes("kouhen")

    assert patcher.VERSION == package.MANIFEST["version"] == "1.1"
    assert (
        package.MANIFEST["combined_sha256"] == patcher.FOUR_SIDE_TARGET_SHA256
    )
    assert hashlib.sha256(zenpen).hexdigest() == patcher.ZENPEN_PATCH_SHA256
    assert hashlib.sha256(kouhen).hexdigest() == patcher.KOUHEN_PATCH_SHA256
    for kind, record in package.MANIFEST["patches"].items():
        payload = package.load_patch(ROOT / "patches", kind)
        assert len(payload) == record["patch_bytes"]
        assert payload.startswith(b"BPS1")
        assert _declared_sizes(payload) == (
            record["source_bytes"],
            record["target_bytes"],
        )
        assert binascii.crc32(payload[:-4]) == int.from_bytes(
            payload[-4:], "little"
        )
        assert (
            f"{int.from_bytes(payload[-8:-4], 'little'):08X}"
            == record["target_crc32"]
        )
        if kind in {"zenpen", "kouhen"}:
            expected = (
                patcher.ZENPEN_TARGET_SHA256
                if kind == "zenpen"
                else patcher.KOUHEN_TARGET_SHA256
            )
            assert record["target_sha256"] == expected
    for source, target in [
        (b"", b""),
        (b"", b"hello"),
        (b"unchanged", b"unchanged"),
        (
            bytes(range(256)) * 2,
            bytes(range(256))[50:] + b"changed" + bytes(range(256)),
        ),
        (b"x" * 2000, b"before" + b"x" * 2000 + b"after"),
    ]:
        payload = create_bps(source, target, "fixture")
        assert patcher.apply_bps(source, payload) == target
        assert create_bps(source, target, "fixture") == payload
        corrupt = payload[:-1] + bytes([payload[-1] ^ 1])
        try:
            patcher.apply_bps(source, corrupt)
        except patcher.PatcherError:
            pass
        else:
            raise AssertionError("corrupt BPS accepted")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        source = root / patcher.ZENPEN_OUTPUT
        source.write_bytes(b"test")
        try:
            patcher._assert_destinations_safe(
                (source,),
                (source,),
                overwrite=True,
            )
        except patcher.PatcherError:
            pass
        else:
            raise AssertionError("source/output collision was not rejected")

        first_output = root / "first-output.fds"
        second_output = root / "second-output.fds"
        first_output.write_bytes(b"alias-test")
        try:
            second_output.hardlink_to(first_output)
        except OSError:
            second_output.symlink_to(first_output)

        try:
            patcher._assert_destinations_safe(
                (),
                (first_output, second_output),
                overwrite=True,
            )
        except patcher.PatcherError:
            pass
        else:
            raise AssertionError(
                "output/output alias collision was not rejected"
            )

        existing = root / "already-exists.fds"
        existing.write_bytes(b"old")
        try:
            patcher._assert_destinations_safe(
                (),
                (existing,),
                overwrite=False,
            )
        except patcher.PatcherError:
            pass
        else:
            raise AssertionError("existing output was overwritten implicitly")

        atomic = root / "atomic.bin"
        patcher._atomic_write(atomic, b"verified")
        assert atomic.read_bytes() == b"verified"

    print("Public patch resources and output-safety checks verified.")


if __name__ == "__main__":
    main()
