from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import TimeTwistPatcher as patcher  # noqa: E402

def main() -> None:
    zenpen = patcher._patch_bytes("zenpen")
    kouhen = patcher._patch_bytes("kouhen")
    assert len(zenpen) == 93719
    assert len(kouhen) == 79852
    assert hashlib.sha256(zenpen).hexdigest() == patcher.ZENPEN_PATCH_SHA256
    assert hashlib.sha256(kouhen).hexdigest() == patcher.KOUHEN_PATCH_SHA256

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source = root / "Time Twist - English Translation v1.0 - Zenpen.fds"
        source.write_bytes(b"test")
        try:
            patcher._assert_destinations_safe((source,), (source,))
        except patcher.PatcherError:
            pass
        else:
            raise AssertionError("source/output collision was not rejected")

    print("Public patch resources and output-safety checks verified.")

if __name__ == "__main__":
    main()
