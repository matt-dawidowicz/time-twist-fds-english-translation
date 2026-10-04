"""Guard the v62 TT6B Eve-quiz answer correction.

The Japanese source contains distinct choices for "Fruit of wisdom" and
"Fruit of knowledge".  The retail result table routes the former to success.
The English correction preserves both translated labels but routes Knowledge
to the existing success continuation instead.
"""

from __future__ import annotations

from .release_metadata import ReleaseBuildError

TT6B_LOAD_ADDRESS = 0xA200
EVE_QUIZ_CPU_ADDRESS = 0xA643
EVE_QUIZ_OFFSET = EVE_QUIZ_CPU_ADDRESS - TT6B_LOAD_ADDRESS

# $A643:
#   31          relative selection-result dispatch
#   03 3F       choice 0 Wisdom -> success, choice 1 Knowledge -> wrong
EVE_QUIZ_EXPECTED = bytes.fromhex("31 03 3F")
EVE_QUIZ_REPLACEMENT = bytes.fromhex("31 3F 03")


def patch_tt6b_eve_quiz(data: bytes) -> bytes:
    """Route Fruit of knowledge, and only that choice, to quiz success."""
    start = EVE_QUIZ_OFFSET
    end = start + len(EVE_QUIZ_EXPECTED)
    if end > len(data):
        raise ReleaseBuildError("TT6B is too short for the Eve quiz result table")

    current = data[start:end]
    if current == EVE_QUIZ_REPLACEMENT:
        return data
    if current != EVE_QUIZ_EXPECTED:
        raise ReleaseBuildError(
            "TT6B Eve quiz source mismatch at "
            f"${EVE_QUIZ_CPU_ADDRESS:04X}"
        )

    result = bytearray(data)
    result[start:end] = EVE_QUIZ_REPLACEMENT
    return bytes(result)
