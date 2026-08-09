"""Print lightweight statistics that help distinguish code, text, and graphics."""

from __future__ import annotations

import argparse
import collections
import math
from pathlib import Path


def entropy(data: bytes) -> float:
    """Calculate Shannon entropy for a binary region.

    Args:
        data: Bytes whose value-frequency distribution should be measured.

    Returns:
        Entropy in bits per byte.  Empty input returns ``0.0``.

    Note:
        Entropy is only a triage signal.  High entropy can indicate compressed
        text, graphics, code, or unrelated dense data; it is not a format proof.
    """
    counts = collections.Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def main() -> None:
    """Print byte-frequency and rolling entropy diagnostics for binary banks.

    Inputs:
        Accepts one or more input paths and an optional integer ``--window``
        using Python's base-prefix syntax, such as ``0x200``.

    Outputs:
        Prints file size, the sixteen most common byte values, and per-window
        entropy plus rough text/control/padding ratios to standard output.

    Raises:
        OSError: If an input file cannot be read.
        ValueError: If ``--window`` cannot be parsed or is zero/negative when
            consumed by :class:`range`.

    Side Effects:
        Reads input files only; no binaries or reports are modified.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument(
        "--window", type=lambda value: int(value, 0), default=0x200
    )
    args = parser.parse_args()

    for path in args.inputs:
        data = path.read_bytes()
        print(f"{path} size=${len(data):04X}")
        print(
            "  top bytes: "
            + " ".join(
                f"{value:02X}:{count}"
                for value, count in collections.Counter(data).most_common(16)
            )
        )
        print("  offset  entropy  <=5F    80-8F   FF")
        for offset in range(0, len(data), args.window):
            block = data[offset : offset + args.window]
            low = sum(value <= 0x5F for value in block) / len(block)
            control = sum(0x80 <= value <= 0x8F for value in block) / len(
                block
            )
            ff = block.count(0xFF) / len(block)
            print(
                f"  {offset:04X}    {entropy(block):5.2f}   {low:5.1%}   {control:5.1%}  {ff:5.1%}"
            )
        print()


if __name__ == "__main__":
    main()
