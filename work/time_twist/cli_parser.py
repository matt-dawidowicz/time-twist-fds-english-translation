"""Argument registration for the public ``time-twist`` command.

Command implementations live in :mod:`time_twist.cli_commands`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .cli_commands import (
    command_combine,
    command_extract,
    command_font_patch,
    command_manifest,
    command_release_build,
    command_release_lock,
    command_release_promote,
    command_replace_file,
    command_roundtrip,
    command_scenario_extract,
    command_scenario_footprint,
    command_scenario_insert,
    command_scenario_merge,
    command_title_patch,
    command_ui_patch,
)
from .title import DEFAULT_SUBTITLE


def build_parser() -> argparse.ArgumentParser:
    """Construct the complete command-line parser.

    Returns:
        Configured parser whose successful subcommand namespaces include a
        ``function`` callback.

    The function is side-effect free: it does not inspect the filesystem,
    import user configuration, or parse process arguments.
    """
    parser = argparse.ArgumentParser(
        prog="time-twist",
        description=(
            "Inspect, extract, translate, rebuild, and verify Time Twist "
            "Famicom Disk System images."
        ),
        epilog=(
            "All patch commands validate the recovered source layout. "
            "Original and patched ROM images are intentionally not stored "
            "in the repository."
        ),
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    manifest = subparsers.add_parser(
        "manifest",
        help="describe every side and named FDS file as JSON",
        description=(
            "Parse an archival FDS image and report its header convention, "
            "disk metadata, side capacity, and named file layout."
        ),
    )
    manifest.add_argument("image", type=Path, help="source .fds image")
    manifest.add_argument(
        "--output",
        type=Path,
        help="write JSON to this file instead of standard output",
    )
    manifest.set_defaults(function=command_manifest)

    extract = subparsers.add_parser(
        "extract",
        help="extract every named FDS file payload",
        description=(
            "Write one .bin file per FDS file. Output names include side, "
            "file index, FDS name, and load address."
        ),
    )
    extract.add_argument("image", type=Path, help="source .fds image")
    extract.add_argument("output_dir", type=Path, help="destination directory")
    extract.set_defaults(function=command_extract)

    roundtrip = subparsers.add_parser(
        "roundtrip",
        help="prove lossless FDS parse/serialization",
        description=(
            "Parse and serialize an image, print both SHA-256 values, and "
            "fail unless the complete output is byte-identical."
        ),
    )
    roundtrip.add_argument("image", type=Path, help="source .fds image")
    roundtrip.add_argument(
        "output", type=Path, help="rebuilt verification image"
    )
    roundtrip.set_defaults(function=command_roundtrip)

    combine = subparsers.add_parser(
        "combine",
        help="combine sides from multiple FDS images",
        description=(
            "Append every side from each image in argument order. The first "
            "image determines whether the result has a 16-byte FDS header."
        ),
    )
    combine.add_argument(
        "images",
        nargs="+",
        type=Path,
        help="two or more source images in desired side order",
    )
    combine.add_argument(
        "--output",
        required=True,
        type=Path,
        help="combined output .fds path",
    )
    combine.set_defaults(function=command_combine)

    scenario_extract = subparsers.add_parser(
        "scenario-extract",
        help="decode a packed scenario bank to editable JSON",
        description=(
            "Decode group pointers, packed records, dictionary references, "
            "Japanese text, and raw symbols. Existing English in the output "
            "is retained only for matching stable record IDs."
        ),
    )
    scenario_extract.add_argument(
        "bank", type=Path, help="extracted scenario .bin"
    )
    scenario_extract.add_argument(
        "--bank-name",
        choices=(
            "TT1A",
            "TT1B",
            "TT2",
            "T22",
            "TT3A",
            "TT3B",
            "TT4",
            "TT5",
            "T25",
            "TT6A",
            "TT6B",
            "TT6C",
            "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_extract.add_argument(
        "output", type=Path, help="scenario JSON path"
    )
    scenario_extract.set_defaults(function=command_scenario_extract)

    scenario_insert = subparsers.add_parser(
        "scenario-insert",
        help="encode translated JSON into a scenario bank",
        description=(
            "Rebuild scenario groups and pointers while retaining code/data "
            "outside the original text reservation. Fully translated banks "
            "receive a compact English dictionary."
        ),
    )
    scenario_insert.add_argument(
        "bank", type=Path, help="clean extracted bank"
    )
    scenario_insert.add_argument(
        "--bank-name",
        choices=(
            "TT1A",
            "TT1B",
            "TT2",
            "T22",
            "TT3A",
            "TT3B",
            "TT4",
            "TT5",
            "T25",
            "TT6A",
            "TT6B",
            "TT6C",
            "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_insert.add_argument(
        "translation",
        type=Path,
        help="merged scenario JSON containing English fields",
    )
    scenario_insert.add_argument("output", type=Path, help="rebuilt bank .bin")
    scenario_insert.add_argument(
        "--no-compress",
        action="store_true",
        help=(
            "diagnostic: preserve the original dictionary on a complete bank; "
            "unavailable for banks whose fixed UI requires 31 English entries"
        ),
    )
    scenario_insert.set_defaults(function=command_scenario_insert)

    scenario_merge = subparsers.add_parser(
        "scenario-merge",
        help="validate and merge an ID-keyed English map",
        description=(
            "Merge translations into extracted scenario JSON while checking "
            "IDs, control order, display width, and font encodability."
        ),
    )
    scenario_merge.add_argument(
        "scenario",
        type=Path,
        help="scenario-extract JSON document",
    )
    scenario_merge.add_argument(
        "translations",
        type=Path,
        help="JSON object mapping record IDs to English",
    )
    scenario_merge.add_argument(
        "--output",
        type=Path,
        help="destination scenario JSON (default: update SCENARIO)",
    )
    scenario_merge.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow translation IDs to cover only part of the bank",
    )
    scenario_merge.set_defaults(function=command_scenario_merge)

    scenario_footprint = subparsers.add_parser(
        "scenario-footprint",
        help="report fixed text capacity and compressed usage",
        description=(
            "Show the scenario reservation and fixed tail. With a complete "
            "translation map, build the English dictionary and report "
            "remaining bytes or a hard overrun."
        ),
    )
    scenario_footprint.add_argument(
        "bank", type=Path, help="clean extracted bank"
    )
    scenario_footprint.add_argument(
        "--bank-name",
        choices=(
            "TT1A",
            "TT1B",
            "TT2",
            "T22",
            "TT3A",
            "TT3B",
            "TT4",
            "TT5",
            "T25",
            "TT6A",
            "TT6B",
            "TT6C",
            "TT6D",
        ),
        help="explicit bank name when the filename is nonstandard",
    )
    scenario_footprint.add_argument(
        "--translations",
        type=Path,
        help="optional ID-keyed English JSON map",
    )
    scenario_footprint.set_defaults(function=command_scenario_footprint)

    font_patch = subparsers.add_parser(
        "font-patch",
        help="install the translated 8x8 dialogue font",
        description=(
            "Replace recovered NOV4 font-table glyph rows without changing "
            "the component's size."
        ),
    )
    font_patch.add_argument("nov4", type=Path, help="source NOV4 .bin")
    font_patch.add_argument("output", type=Path, help="patched NOV4 .bin")
    font_patch.set_defaults(function=command_font_patch)

    title_patch = subparsers.add_parser(
        "title-patch",
        help="build and install the English title assets",
        description=(
            "Install a reviewed native 256x240 indexed NES title asset, retain "
            "the animated clock sprites, and append relocated NOV4 helpers "
            "and nametables below resident NOV3."
        ),
    )
    title_patch.add_argument(
        "nov4", type=Path, help="source/patched-size NOV4 .bin"
    )
    title_patch.add_argument(
        "target",
        type=Path,
        help="approved 256x240 indexed final-title image",
    )
    title_patch.add_argument("output", type=Path, help="expanded NOV4 .bin")
    title_patch.add_argument(
        "--slide-target",
        type=Path,
        help=(
            "approved 256x240 indexed monochrome swipe image; defaults to "
            "the named sibling beside target"
        ),
    )
    title_patch.add_argument(
        "--subtitle",
        default=DEFAULT_SUBTITLE,
        help=f"title subtitle (default: {DEFAULT_SUBTITLE!r})",
    )
    title_patch.set_defaults(function=command_title_patch)

    ui_patch = subparsers.add_parser(
        "ui-patch",
        help="apply a verified fixed UI/text-table patch",
        description=(
            "Patch one extracted component's fixed prompts, menu labels, "
            "commands, objects, quiz answers, or small input/program behavior."
        ),
    )
    ui_patch.add_argument("source", type=Path, help="source component .bin")
    ui_patch.add_argument("output", type=Path, help="patched component .bin")
    ui_patch.add_argument(
        "--component",
        choices=(
            "SON-KOUH",
            "NOV2",
            "NOV4",
            "TT1A",
            "TT1B",
            "TT2",
            "T22",
            "TT3A",
            "TT3B",
            "TT4",
            "TT5",
            "T25",
            "TT6A",
            "TT6B",
            "TT6C",
        ),
        default="NOV2",
        help="owning FDS component (default: NOV2)",
    )
    ui_patch.set_defaults(function=command_ui_patch)

    replace_file = subparsers.add_parser(
        "replace-file",
        help="replace one named file and rebuild its FDS image",
        description=(
            "Replace the unique FDS file NAME on zero-based SIDE, refresh its "
            "size field, and fail if the rebuilt side exceeds 65,500 bytes."
        ),
    )
    replace_file.add_argument("image", type=Path, help="input .fds image")
    replace_file.add_argument("side", type=int, help="zero-based side index")
    replace_file.add_argument("name", help="exact printable FDS filename")
    replace_file.add_argument(
        "data", type=Path, help="replacement payload .bin"
    )
    replace_file.add_argument("output", type=Path, help="rebuilt output .fds")
    replace_file.set_defaults(function=command_replace_file)

    release_lock = subparsers.add_parser(
        "release-lock",
        help="validate or update the approved release-input lock",
        description=(
            "Check all baseline, translation-map, and title-asset hashes. "
            "Use --update only when intentionally promoting edited sources."
        ),
    )
    release_lock.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_lock.add_argument(
        "--lock",
        type=Path,
        help="source-lock JSON path (default: PROJECT/work/release_sources.json)",
    )
    release_lock.add_argument(
        "--update",
        action="store_true",
        help="rewrite the lock from the current approved source files",
    )
    release_lock.set_defaults(function=command_release_lock)

    release_build = subparsers.add_parser(
        "release-build",
        help="build Zenpen, Kouhen, and a combined four-side image",
        description=(
            "Validate the approved source lock, rebuild every scenario bank, "
            "apply fixed UI/font/title patches, and emit output hashes."
        ),
    )
    release_build.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_build.add_argument(
        "--output-dir",
        type=Path,
        help="output directory (default: PROJECT/build/release)",
    )
    release_build.add_argument(
        "--lock",
        type=Path,
        help="approved source-lock JSON path (default: PROJECT/work/release_sources.json)",
    )
    release_build.add_argument(
        "--target",
        type=Path,
        help="promoted output target (default: PROJECT/work/release_target.json)",
    )
    release_build.add_argument(
        "--candidate",
        action="store_true",
        help="publish an unpromoted candidate instead of verifying the release target",
    )
    release_build.set_defaults(function=command_release_build)

    release_promote = subparsers.add_parser(
        "release-promote",
        help="promote a reviewed candidate manifest into the release target",
        description=(
            "Verify every candidate output and its active source lock, then write "
            "the versioned target used by strict release builds."
        ),
    )
    release_promote.add_argument(
        "candidate_manifest",
        type=Path,
        help="candidate release_manifest.json produced by release-build --candidate",
    )
    release_promote.add_argument(
        "--project-root",
        type=Path,
        help="project checkout (auto-discovered from the current directory by default)",
    )
    release_promote.add_argument(
        "--target",
        type=Path,
        help="target JSON path (default: PROJECT/work/release_target.json)",
    )
    release_promote.add_argument(
        "--release-id",
        help="human-readable target identifier (default: english-playtest)",
    )
    release_promote.set_defaults(function=command_release_promote)
    return parser
