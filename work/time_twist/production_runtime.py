"""Source-verified NOV2 runtime hardening for production English builds.

Codec-neutral English fixes live in :mod:`time_twist.production_runtime_support`.
The historical Adaptive255 runtime is loaded only when a caller explicitly
requests ``adaptive_dictionary=True``. This keeps the maintained entropy path
independent of the discarded adaptive implementation while preserving the
legacy diagnostic entry point.
"""

from __future__ import annotations

from .fds import FdsImage
from .production_runtime_support import (
    NOV2_LOAD_ADDRESS,
    PRODUCTION_RUNTIME_PATCHES,
    ProductionRuntimeError,
    RuntimePatch,
    patch_proven_nov2,
)

NOV2_SIDE_INDEX = 0
NOV2_FILENAME = "NOV2"

# $9390-$93AF is live palette data. Do not place code, tables, or scratch
# storage there. RC3/RC4 did so experimentally and produced visible corruption.
PALETTE_DATA_RANGE = range(0x3390, 0x33B0)


def __getattr__(name: str):
    """Lazily preserve the historical adaptive patch-table export."""
    if name == "ADAPTIVE_DICTIONARY_RUNTIME_PATCHES":
        from .adaptive_runtime import ADAPTIVE_DICTIONARY_RUNTIME_PATCHES

        return ADAPTIVE_DICTIONARY_RUNTIME_PATCHES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def patch_nov2(data: bytes, *, adaptive_dictionary: bool = False) -> bytes:
    """Return NOV2 with proven fixes and optional historical adaptive patches."""
    result = bytearray(patch_proven_nov2(data))
    if adaptive_dictionary:
        from .adaptive_runtime import apply_adaptive_runtime_patches

        apply_adaptive_runtime_patches(result)
    return bytes(result)


def patch_fds_image(
    raw: bytes,
    *,
    adaptive_dictionary: bool = False,
) -> bytes:
    """Patch NOV2 in a complete FDS image without changing its payload size."""
    image = FdsImage.from_bytes(raw)
    if len(image.sides) <= NOV2_SIDE_INDEX:
        raise ProductionRuntimeError("FDS image has no Zenpen side A")
    nov2 = image.sides[NOV2_SIDE_INDEX].find_file(NOV2_FILENAME)
    original_size = len(nov2.data)
    nov2.data = patch_nov2(
        nov2.data,
        adaptive_dictionary=adaptive_dictionary,
    )
    if len(nov2.data) != original_size:
        raise ProductionRuntimeError("NOV2 production hardening changed size")
    return image.to_bytes()
