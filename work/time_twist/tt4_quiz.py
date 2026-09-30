"""Correct the TT4 Athena-temple quiz result mapping.

The frozen v38 compiler preserves the retail five-choice target table, but its
third target is the success path while the source menu's fifth choice is
Parthenon.  Patch only that target table; keep all other quiz control flow
byte-identical.
"""

from __future__ import annotations

from .release_metadata import ReleaseBuildError

TT4_LOAD_ADDRESS = 0xA200
ATHENA_QUIZ_CPU_ADDRESS = 0xAE3C
ATHENA_QUIZ_OFFSET = ATHENA_QUIZ_CPU_ADDRESS - TT4_LOAD_ADDRESS

# $AE3C:
#   28 33       open the five-choice temple-answer menu
#   31          relative result dispatch
#   DB DB 06 DB DB
#               choices 0..4; the frozen image incorrectly accepts choice 2
#   92          first opcode of the success continuation at $AE44
ATHENA_QUIZ_EXPECTED = bytes.fromhex("28 33 31 DB DB 06 DB DB 92")
ATHENA_QUIZ_REPLACEMENT = bytes.fromhex("28 33 31 DB DB DB DB 06 92")


def patch_tt4_athena_quiz(data: bytes) -> bytes:
    """Make Parthenon (choice 4) the sole success result for the Athena quiz."""
    start = ATHENA_QUIZ_OFFSET
    end = start + len(ATHENA_QUIZ_EXPECTED)
    if end > len(data):
        raise ReleaseBuildError("TT4 is too short for the Athena quiz table")

    current = data[start:end]
    if current == ATHENA_QUIZ_REPLACEMENT:
        return data
    if current != ATHENA_QUIZ_EXPECTED:
        raise ReleaseBuildError(
            "TT4 Athena quiz source mismatch at "
            f"${ATHENA_QUIZ_CPU_ADDRESS:04X}"
        )

    result = bytearray(data)
    result[start:end] = ATHENA_QUIZ_REPLACEMENT
    return bytes(result)
