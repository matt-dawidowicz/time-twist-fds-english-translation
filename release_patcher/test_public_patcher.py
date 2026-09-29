from __future__ import annotations

import hashlib
from pathlib import Path
import sys

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
    print("Public patch resources decoded and verified.")

if __name__ == "__main__":
    main()
