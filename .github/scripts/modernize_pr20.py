"""One-shot guarded refactor for PR #20's modern CLI/release boundary."""

from __future__ import annotations

import re
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace exactly one known block and fail closed on source drift."""
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def modernize_release_metadata() -> None:
    """Keep only the TT1A same-size patcher on the canonical release path."""
    path = Path("work/time_twist/release_metadata.py")
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"from \.ui import \(\n(?:    patched_[^\n]+,\n)+\)",
        "from .ui import patched_tt1a_ui",
        text,
        count=1,
    )
    if count != 1:
        raise SystemExit("release UI import block did not match exactly once")
    text = replace_once(
        updated,
        '''SCENARIO_UI_PATCHERS: dict[str, Callable[[bytes], bytes]] = {
    "TT1A": patched_tt1a_ui,
    "TT1B": patched_tt1b_ui,
    "TT2": patched_tt2_ui,
    "T22": patched_t22_ui,
    "TT3A": patched_tt3a_ui,
    "TT3B": patched_tt3b_ui,
    "TT4": patched_tt4_ui,
    "TT5": patched_tt5_ui,
    "T25": patched_t25_ui,
    "TT6A": patched_tt6a_ui,
    "TT6B": patched_tt6b_ui,
    "TT6C": patched_tt6c_ui,
}
''',
        '''SCENARIO_UI_PATCHERS: dict[str, Callable[[bytes], bytes]] = {
    "TT1A": patched_tt1a_ui,
}
''',
        "release scenario patcher map",
    )
    path.write_text(text, encoding="utf-8")


def modernize_cli_commands() -> None:
    """Remove obsolete fixed-slot patch commands for relocated scenario banks."""
    path = Path("work/time_twist/cli_commands.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''from .ui import (
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_t22_ui,
    patched_t25_ui,
    patched_tt1a_ui,
    patched_tt1b_ui,
    patched_tt2_ui,
    patched_tt3a_ui,
    patched_tt3b_ui,
    patched_tt4_ui,
    patched_tt5_ui,
    patched_tt6a_ui,
    patched_tt6b_ui,
    patched_tt6c_ui,
)
''',
        '''from .ui import (
    FIXED_RECORD_TABLE_SPECS,
    patched_kouhen_boot_guard,
    patched_nov2_ui,
    patched_nov4_ui,
    patched_tt1a_ui,
)
''',
        "CLI UI imports",
    )
    text = replace_once(
        text,
        "PERSONALITY_QUESTION_IDS = _PERSONALITY_QUESTION_IDS\n\n\n",
        '''PERSONALITY_QUESTION_IDS = _PERSONALITY_QUESTION_IDS


def _require_standalone_scenario_bank(bank_name: str, operation: str) -> None:
    """Reject banks whose current English layout requires joint menu repacking."""
    if bank_name in FIXED_RECORD_TABLE_SPECS:
        raise SystemExit(
            f"{operation} does not support {bank_name}'s relocated full-word "
            "menu layout; use release-build for the current playable architecture"
        )


''',
        "standalone-bank helper insertion",
    )
    text = replace_once(
        text,
        '''def command_scenario_insert(args: argparse.Namespace) -> None:
    """Insert merged JSON only after structural and display validation."""
    bank_name, bank = _parse_source_bank(args)
    document = json.loads(args.translation.read_text(encoding="utf-8"))
''',
        '''def command_scenario_insert(args: argparse.Namespace) -> None:
    """Insert merged JSON only after structural and display validation."""
    bank_name, bank = _parse_source_bank(args)
    _require_standalone_scenario_bank(bank_name, "scenario-insert")
    document = json.loads(args.translation.read_text(encoding="utf-8"))
''',
        "scenario-insert guard",
    )
    text = replace_once(
        text,
        '''    if (
        translated_count == total_count
        and args.no_compress
        and getattr(required_entries, "requires_full_dictionary", False)
    ):
        raise SystemExit(
            f"{bank_name} fixed UI requires a complete 31-entry English "
            "dictionary; --no-compress cannot produce a safe ui-patch input"
        )
''',
        "",
        "obsolete 31-entry insert guard",
    )
    text = replace_once(
        text,
        '''    if args.translations is None:
        return
    translations = json.loads(args.translations.read_text(encoding="utf-8"))
''',
        '''    if args.translations is None:
        return
    _require_standalone_scenario_bank(bank_name, "scenario-footprint")
    translations = json.loads(args.translations.read_text(encoding="utf-8"))
''',
        "scenario-footprint guard",
    )
    text = replace_once(
        text,
        '''    patcher = {
        "SON-KOUH": patched_kouhen_boot_guard,
        "NOV2": patched_nov2_ui,
        "NOV4": patched_nov4_ui,
        "TT1A": patched_tt1a_ui,
        "TT1B": patched_tt1b_ui,
        "TT2": patched_tt2_ui,
        "T22": patched_t22_ui,
        "TT3A": patched_tt3a_ui,
        "TT3B": patched_tt3b_ui,
        "TT4": patched_tt4_ui,
        "TT5": patched_tt5_ui,
        "T25": patched_t25_ui,
        "TT6A": patched_tt6a_ui,
        "TT6B": patched_tt6b_ui,
        "TT6C": patched_tt6c_ui,
    }[args.component]
''',
        '''    patcher = {
        "SON-KOUH": patched_kouhen_boot_guard,
        "NOV2": patched_nov2_ui,
        "NOV4": patched_nov4_ui,
        "TT1A": patched_tt1a_ui,
    }[args.component]
''',
        "modern ui-patch map",
    )
    path.write_text(text, encoding="utf-8")


def modernize_cli_parser() -> None:
    """Advertise only the current supported standalone CLI surface."""
    path = Path("work/time_twist/cli_parser.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '"receive a compact English dictionary."',
        '"receive a compact English dictionary. Banks with relocated "\n            "full-word menus must be built through release-build."',
        "scenario-insert description",
    )
    text = replace_once(
        text,
        '''        help=(
            "diagnostic: preserve the original dictionary on a complete bank; "
            "unavailable for banks whose fixed UI requires 31 English entries"
        ),
''',
        '''        help=(
            "diagnostic: preserve the original dictionary on a supported "
            "standalone complete bank"
        ),
''',
        "scenario-insert no-compress help",
    )
    text = replace_once(
        text,
        '"remaining bytes or a hard overrun."',
        '"remaining bytes or a hard overrun. Translated relocated-menu "\n            "banks must use release-build."',
        "scenario-footprint description",
    )
    text = replace_once(
        text,
        '''        choices=(
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
''',
        '''        choices=("SON-KOUH", "NOV2", "NOV4", "TT1A"),
''',
        "ui-patch parser choices",
    )
    text = replace_once(
        text,
        '"Patch one extracted component\'s fixed prompts, menu labels, "\n            "commands, objects, quiz answers, or small input/program behavior."',
        '"Patch one standalone component\'s source-verified prompts, "\n            "choices, title menu, or small input/program behavior. Relocated "\n            "scenario menus are owned by release-build."',
        "ui-patch description",
    )
    path.write_text(text, encoding="utf-8")


def modernize_cli_docs() -> None:
    """Remove documentation for the superseded 31-entry fixed-slot workflow."""
    path = Path("docs/CLI_REFERENCE.md")
    text = path.read_text(encoding="utf-8")
    replacements = (
        (
            '''Reports the fixed text reservation and, with a complete translation map,
compressed use and remaining bytes. For banks with fixed-address UI text, the
source reservation includes dictionary entries referenced by those verified
source tables as well as ordinary scenario dialogue. Banks whose translated
fixed UI consumes the English dictionary must also produce all 31 dictionary
entries or the footprint check fails closed.
''',
            '''Reports the source scenario reservation and, for standalone-layout banks with a
complete translation map, compressed use and remaining bytes. Source-only
inspection remains available for every bank. The 11 banks whose current English
menus are jointly repacked and relocated must use `release-build` for translated
capacity because their playable footprint spans both menu and scenario regions.
''',
            "CLI footprint docs",
        ),
        (
            '''Rebuilds scenario groups and pointers only after validating group indices,
record indices, stable IDs, control order, display width, and glyph support.
Complete translations receive a new English dictionary; partial work keeps the
Japanese dictionary. `--bank-name` is available when the input filename does
not safely identify its bank. Capacity-constrained complete builds retry the
deterministic compressor without candidate pruning if the normal fast search
misses the native reservation. They then compare that valid result with bounded
beam search and fixed-prefix-safe dictionary reordering and keep the smallest
exact output. Fixed-UI banks also retry when the fast search stops before all
31 required English dictionary slots are populated, and fail if no search can
produce a complete dictionary.

`--no-compress` is diagnostic only. A fully translated bank whose fixed UI
requires the 31-entry English dictionary rejects that option before writing an
output, because preserving the Japanese dictionary cannot produce a safe input
for the later `ui-patch` step.
''',
            '''Rebuilds scenario groups and pointers only after validating group indices,
record indices, stable IDs, control order, display width, and glyph support.
Complete translations receive a new English dictionary; partial work keeps the
Japanese dictionary. `--bank-name` is available when the input filename does
not safely identify its bank. The command is intentionally limited to banks
whose current English layout is self-contained in the scenario reservation
(currently TT1A and TT6D). The 11 relocated-menu banks fail closed and direct
maintainers to `release-build`, which owns their combined menu/scenario layout.

`--no-compress` remains a diagnostic option for supported standalone banks; it
preserves the original dictionary on a complete bank.
''',
            "CLI insert docs",
        ),
        (
            '''Applies one source-verified fixed UI/text-table patch. Supported components are
`SON-KOUH`, `NOV2`, `NOV4`, `TT1A`, `TT1B`, `TT2`, `T22`, `TT3A`, `TT3B`,
`TT4`, `TT5`, `T25`, `TT6A`, `TT6B`, and `TT6C`.

The command rejects source-byte, record-count, table-hash, dictionary, and
exact-slot mismatches.
''',
            '''Applies one source-verified standalone UI/program patch. Supported components
are `SON-KOUH`, `NOV2`, `NOV4`, and `TT1A`. The 11 scenario banks with
relocated full-word menu tables are not standalone patch targets; `release-build`
repacks those tables together with dialogue and regenerates their page pointers.

The command rejects source-byte and fixed-layout mismatches.
''',
            "CLI ui-patch docs",
        ),
        (
            '''For the 11 banks with scenario menu tables, this canonical path packs the
unabbreviated labels together with dialogue, uses the guarded 68-entry English
dictionary decoder, regenerates the menu page pointers, and preserves the
overlay's original fixed suffix. The standalone `scenario-insert` and
`ui-patch` commands retain the older 31-entry, fixed-slot diagnostic workflow;
use `release-build` for the full-word playable result.
''',
            '''For the 11 banks with scenario menu tables, this canonical path packs the
unabbreviated labels together with dialogue, uses the guarded 68-entry English
dictionary decoder, regenerates the menu page pointers, and preserves the
overlay's original fixed suffix. It is the only supported translated build path
for those banks; standalone scenario/UI commands fail closed rather than
reproducing the superseded 31-entry fixed-slot architecture.
''',
            "CLI release docs",
        ),
    )
    for old, new, label in replacements:
        text = replace_once(text, old, new, label)
    path.write_text(text, encoding="utf-8")


def write_boundary_tests() -> None:
    """Add a public regression test for the modern command/release boundary."""
    Path("work/tests/test_modern_cli_boundaries.py").write_text(
        '''"""Regression tests for the modern release/standalone command boundary."""

from __future__ import annotations

import unittest

from time_twist.cli_commands import _require_standalone_scenario_bank
from time_twist.cli_parser import build_parser
from time_twist.release import SCENARIO_UI_PATCHERS
from time_twist.ui import FIXED_RECORD_TABLE_SPECS


class ModernCliBoundaryTests(unittest.TestCase):
    """Keep relocated menu banks on the canonical release path."""

    def test_release_uses_only_the_tt1a_same_size_scenario_patcher(self) -> None:
        """Relocated menu banks must bypass the legacy patcher map."""
        self.assertEqual(set(SCENARIO_UI_PATCHERS), {"TT1A"})

    def test_relocated_banks_reject_standalone_translated_operations(self) -> None:
        """Direct maintainers to release-build for every relocated-menu bank."""
        for bank_name in FIXED_RECORD_TABLE_SPECS:
            with self.subTest(bank=bank_name):
                with self.assertRaisesRegex(SystemExit, "release-build"):
                    _require_standalone_scenario_bank(bank_name, "scenario-insert")
        _require_standalone_scenario_bank("TT1A", "scenario-insert")
        _require_standalone_scenario_bank("TT6D", "scenario-insert")

    def test_ui_patch_parser_exposes_only_standalone_components(self) -> None:
        """Do not advertise the superseded scenario fixed-slot patchers."""
        parser = build_parser()
        namespace = parser.parse_args(
            ["ui-patch", "source.bin", "output.bin", "--component", "TT1A"]
        )
        self.assertEqual(namespace.component, "TT1A")
        with self.assertRaises(SystemExit):
            parser.parse_args(
                ["ui-patch", "source.bin", "output.bin", "--component", "TT2"]
            )


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )


def main() -> None:
    """Apply every guarded modernization transformation."""
    modernize_release_metadata()
    modernize_cli_commands()
    modernize_cli_parser()
    modernize_cli_docs()
    write_boundary_tests()


if __name__ == "__main__":
    main()
