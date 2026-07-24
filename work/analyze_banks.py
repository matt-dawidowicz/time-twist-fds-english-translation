"""Print lightweight statistics that help distinguish code, text, and graphics."""

from __future__ import annotations

import argparse
import collections
import math
from pathlib import Path


def entropy(data: bytes) -> float:
    counts = collections.Counter(data)
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--window", type=lambda value: int(value, 0), default=0x200)
    args = parser.parse_args()

    for path in args.inputs:
        data = path.read_bytes()
        print(f"{path} size=${len(data):04X}")
        print(
            "  top bytes: "
            + " ".join(f"{value:02X}:{count}" for value, count in collections.Counter(data).most_common(16))
        )
        print("  offset  entropy  <=5F    80-8F   FF")
        for offset in range(0, len(data), args.window):
            block = data[offset : offset + args.window]
            low = sum(value <= 0x5F for value in block) / len(block)
            control = sum(0x80 <= value <= 0x8F for value in block) / len(block)
            ff = block.count(0xFF) / len(block)
            print(f"  {offset:04X}    {entropy(block):5.2f}   {low:5.1%}   {control:5.1%}  {ff:5.1%}")
        print()


if __name__ == "__main__":
    main()
