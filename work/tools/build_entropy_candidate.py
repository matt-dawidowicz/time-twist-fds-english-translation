"""Build a frozen-entropy Time Twist candidate from explicit Japanese inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from time_twist.entropy_release import build_entropy_images
from time_twist.title import DEFAULT_SUBTITLE


def main() -> int:
    """Build three entropy playtest images and an audit manifest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--zenpen", type=Path, required=True)
    parser.add_argument("--kouhen", type=Path, required=True)
    parser.add_argument("--translations", type=Path, required=True)
    parser.add_argument("--title", type=Path, required=True)
    parser.add_argument("--slide-title", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subtitle", default=DEFAULT_SUBTITLE)
    args = parser.parse_args()

    outputs, manifest = build_entropy_images(
        args.zenpen.read_bytes(),
        args.kouhen.read_bytes(),
        translations_directory=args.translations,
        title_asset=args.title,
        slide_title_asset=args.slide_title,
        subtitle=args.subtitle,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    filenames = {
        "zenpen": "Time-Twist-English-Entropy-Zenpen.fds",
        "kouhen": "Time-Twist-English-Entropy-Kouhen.fds",
        "four_side": "Time-Twist-English-Entropy-four-side-playtest.fds",
    }
    for name, data in outputs.items():
        (args.output / filenames[name]).write_bytes(data)
    (args.output / "entropy_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
