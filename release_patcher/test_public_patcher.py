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


def _declared_sizes(patch: bytes) -> tuple[int, int]:
    position = 4
    source_size, position = patcher._bps_number(patch, position)
    target_size, _ = patcher._bps_number(patch, position)
    return source_size, target_size


def main() -> None:
    zenpen = patcher._patch_bytes("zenpen")
    kouhen = patcher._patch_bytes("kouhen")

    assert len(zenpen) == 93_711
    assert len(kouhen) == 79_852
    assert hashlib.sha256(zenpen).hexdigest() == patcher.ZENPEN_PATCH_SHA256
    assert hashlib.sha256(kouhen).hexdigest() == patcher.KOUHEN_PATCH_SHA256
    assert int.from_bytes(zenpen[-8:-4], "little") == 0x262F20AE

    for payload in (zenpen, kouhen):
        assert payload.startswith(b"BPS1")
        assert _declared_sizes(payload) == (
            patcher.SOURCE_BYTES,
            patcher.SOURCE_BYTES,
        )
        assert binascii.crc32(payload[:-4]) == int.from_bytes(
            payload[-4:],
            "little",
        )

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
            raise AssertionError("output/output alias collision was not rejected")

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