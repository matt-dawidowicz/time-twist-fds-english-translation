"""One-shot guarded removal of the superseded fixed-slot architecture."""

from __future__ import annotations

import ast
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace exactly one source fragment or fail closed."""
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def remove_top_level_nodes(
    path: Path,
    *,
    definitions: set[str] = frozenset(),
    assignments: set[str] = frozenset(),
) -> None:
    """Remove named top-level defs/classes/assignments using AST line spans."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    found: set[str] = set()
    for node in tree.body:
        name: str | None = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in definitions:
                name = node.name
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {
                target.id
                for target in targets
                if isinstance(target, ast.Name)
            }
            matched = names & assignments
            if len(matched) == 1:
                name = next(iter(matched))
        if name is not None:
            assert node.end_lineno is not None
            spans.append((node.lineno - 1, node.end_lineno, name))
            found.add(name)
    expected = definitions | assignments
    if found != expected:
        raise SystemExit(
            f"{path}: node mismatch; missing={sorted(expected - found)}, "
            f"unexpected={sorted(found - expected)}"
        )
    for start, end, _ in sorted(spans, reverse=True):
        del lines[start:end]
    path.write_text("".join(lines), encoding="utf-8")


def rewrite_project() -> None:
    """Keep only bank identity and original-source dictionary-floor logic."""
    Path("work/time_twist/project.py").write_text(
        '''"""Project-wide scenario bank identity and source-layout helpers."""

from __future__ import annotations

import re
from pathlib import Path

from . import scenario_validation as _scenario_validation
from .textcodec import SymbolKind, split_records
from .ui import FIXED_RECORD_TABLE_SPECS

PERSONALITY_QUESTION_IDS = _scenario_validation.PERSONALITY_QUESTION_IDS

KNOWN_SCENARIO_BANKS = (
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
)


def source_dictionary_reference_floor(bank_name: str, data: bytes) -> int:
    """Return the largest source dictionary slot used outside scenario groups."""
    spec = FIXED_RECORD_TABLE_SPECS.get(bank_name)
    if spec is None:
        return 0
    records, actual_end = split_records(
        data,
        offset=spec.start,
        limit=len(spec.records),
    )
    if actual_end != spec.end:
        raise ValueError(
            f"{bank_name} fixed source table ended at 0x{actual_end:04X}; "
            f"expected 0x{spec.end:04X}"
        )
    return max(
        (
            symbol.value
            for record in records
            for symbol in record
            if symbol.kind is SymbolKind.DICTIONARY
        ),
        default=0,
    )


def infer_bank_name(path: Path, explicit: str | None = None) -> str:
    """Return a validated scenario bank name from an explicit value or filename."""
    if explicit is not None:
        candidate = explicit.upper()
        if candidate not in KNOWN_SCENARIO_BANKS:
            raise ValueError(f"unknown scenario bank name: {explicit}")
        return candidate

    stem = path.stem.upper()
    matches = [
        bank
        for bank in KNOWN_SCENARIO_BANKS
        if re.search(rf"(?:^|_){re.escape(bank)}(?:_|$)", stem)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"cannot infer one scenario bank from {path.name!r}; "
            "pass --bank-name explicitly"
        )
    return matches[0]
''',
        encoding="utf-8",
    )


def simplify_release() -> None:
    """Remove legacy dictionary/UI candidate validation from non-relocated banks."""
    path = Path("work/time_twist/release.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''from .project import (
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
''',
        'from .project import source_dictionary_reference_floor\n',
        "release project import",
    )
    start_marker = "    capacity = scenario_capacity\n    maximum_dictionary_entries = EXTENDED_DICTIONARY_ENTRY_COUNT\n"
    start = text.find(start_marker, text.find("def build_scenario_bank"))
    end = text.find("\n\ndef _replace(", start)
    if start < 0 or end < 0:
        raise SystemExit("release non-relocated block markers not found")
    replacement = '''    capacity = scenario_capacity
    compressed, dictionary = compress_english_groups(
        groups,
        max_bytes=capacity - pointer_bytes,
        optimize=True,
        maximum_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
    )
    rebuilt = rebuild_scenario_bank(
        bank,
        compressed,
        dictionary=dictionary,
        preserve_memory_footprint=True,
        maximum_dictionary_entries=EXTENDED_DICTIONARY_ENTRY_COUNT,
    )
    if patcher is not None:
        rebuilt = patcher(rebuilt)

    used = packed_size(compressed, dictionary) + pointer_bytes
    return ScenarioBuildResult(
        data=rebuilt,
        records=len(bank.records),
        dictionary_entries=len(dictionary),
        packed_bytes=used,
        capacity_bytes=capacity,
    )
'''
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def simplify_cli() -> None:
    """Remove translated fixed-slot dictionary reservations from standalone CLI."""
    path = Path("work/time_twist/cli_commands.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''from .project import (
    infer_bank_name,
    required_dictionary_entries,
    source_dictionary_reference_floor,
)
''',
        '''from .project import infer_bank_name, source_dictionary_reference_floor
''',
        "CLI project import",
    )
    text = replace_once(
        text,
        "    required_entries = required_dictionary_entries(bank_name)\n",
        "",
        "CLI required-entry assignment",
    )
    text = replace_once(
        text,
        "            required_entries=required_entries,\n",
        "",
        "CLI required-entry compression argument",
    )
    # The footprint command's standalone translated branch no longer reserves
    # dictionary words from the retired fixed-slot path.
    text = text.replace(
        "        required_entries=required_dictionary_entries(bank_name),\n",
        "",
    )
    path.write_text(text, encoding="utf-8")


def simplify_compression() -> None:
    """Remove the old full-dictionary marker path and cheapen hot inner loops."""
    path = Path("work/time_twist/compression.py")
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name == "compress_english_groups"
    )
    assert node.end_lineno is not None
    lines = text.splitlines(keepends=True)
    replacement = '''def compress_english_groups(
    groups: tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    *,
    required_entries: tuple[tuple[PackedSymbol, ...], ...] = (),
    max_bytes: int | None = None,
    optimize: bool = False,
    maximum_entries: int = MAX_DICTIONARY_ENTRIES,
    candidate_validator: (
        Callable[
            [
                tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
                tuple[tuple[PackedSymbol, ...], ...],
            ],
            bool,
        ]
        | None
    ) = None,
) -> tuple[
    tuple[tuple[tuple[PackedSymbol, ...], ...], ...],
    tuple[tuple[PackedSymbol, ...], ...],
]:
    """Compress groups and widen deterministic search only when needed.

    Required entries remain an immutable dictionary prefix. Capacity-constrained
    optimized callers return the compatible greedy result immediately when it
    already fits; otherwise bounded beam/order search is compared. Unconstrained
    optimized callers retain the full minimum-size comparison behavior.
    """
    if max_bytes is not None and max_bytes < 0:
        raise ValueError("max_bytes must be nonnegative")
    if not 1 <= maximum_entries <= EXTENDED_DICTIONARY_ENTRY_COUNT:
        raise ValueError("maximum dictionary entries is out of range")

    if optimize:
        baseline = compress_english_groups(
            groups,
            required_entries=required_entries,
            max_bytes=max_bytes,
            optimize=False,
            maximum_entries=maximum_entries,
        )
        baseline_size = packed_size(*baseline)
        baseline_valid = candidate_validator is None or candidate_validator(
            *baseline
        )
        if max_bytes is not None and baseline_size <= max_bytes and baseline_valid:
            return baseline

        candidates = [baseline] if baseline_valid else []
        candidates.extend(
            [
                _compress_english_groups_beam(
                    groups,
                    required_entries=required_entries,
                    maximum_entries=maximum_entries,
                ),
                _improve_dictionary_order(
                    groups,
                    baseline[1],
                    required_entry_count=len(required_entries),
                    maximum_entries=maximum_entries,
                ),
            ]
        )
        headroom = None if max_bytes is None else max_bytes - baseline_size
        if headroom is not None and headroom <= EXTENDED_BEAM_HEADROOM_BYTES:
            candidates.append(
                _compress_english_groups_beam(
                    groups,
                    required_entries=required_entries,
                    beam_width=EXTENDED_BEAM_WIDTH,
                    branch_factor=EXTENDED_BEAM_BRANCH_FACTOR,
                    maximum_entries=maximum_entries,
                )
            )
        if candidate_validator is not None:
            candidates = [
                result for result in candidates if candidate_validator(*result)
            ]
        if not candidates:
            raise ValueError(
                "no compression candidate satisfies the release constraints"
            )
        return min(candidates, key=_compression_result_key)

    primary = _compress_english_groups_greedy(
        groups,
        required_entries=required_entries,
        candidate_limit=MAX_CANDIDATES_TO_EVALUATE,
        maximum_entries=maximum_entries,
    )
    primary_size = packed_size(*primary)
    if max_bytes is None or primary_size <= max_bytes:
        return primary

    fallback = _compress_english_groups_greedy(
        groups,
        required_entries=required_entries,
        candidate_limit=None,
        maximum_entries=maximum_entries,
    )
    if packed_size(*fallback) < primary_size:
        return fallback
    return primary
'''
    lines[node.lineno - 1 : node.end_lineno] = [replacement + "\n"]
    text = "".join(lines)
    text = replace_once(
        text,
        "        entry_bits = len(pack_records((candidate,))) * 8\n",
        "        entry_bits = _record_packed_size(candidate) * 8\n",
        "candidate entry-size arithmetic",
    )
    text = replace_once(
        text,
        "                    tuple(record[position : position + candidate_length])\n                    == candidate\n",
        "                    record[position : position + candidate_length] == candidate\n",
        "tuple-slice candidate comparison",
    )
    old = '''                for start in range(len(segment)):
                    maximum = min(MAX_CANDIDATE_TOKENS, len(segment) - start)
                    for length in range(2, maximum + 1):
                        counts[tuple(segment[start : start + length])] += 1
                segment = []
'''
    new = '''                literal_segment = tuple(segment)
                for start in range(len(literal_segment)):
                    maximum = min(
                        MAX_CANDIDATE_TOKENS, len(literal_segment) - start
                    )
                    for length in range(2, maximum + 1):
                        counts[literal_segment[start : start + length]] += 1
                segment = []
'''
    text = replace_once(text, old, new, "candidate tuple slicing")
    path.write_text(text, encoding="utf-8")


def remove_legacy_ui() -> None:
    """Delete unreachable fixed-slot dictionary patchers and fallback tables."""
    path = Path("work/time_twist/ui.py")
    remove_top_level_nodes(
        path,
        definitions={
            "_tt2_dictionary",
            "_encode_with_dictionary",
            "_encode_at_exact_record_size",
            "_parse_fixed_label_fallbacks",
            "_patched_fixed_record_table",
            "patched_tt1b_ui",
            "patched_tt2_ui",
            "patched_t22_ui",
            "patched_tt3a_ui",
            "patched_tt3b_ui",
            "patched_tt4_ui",
            "patched_tt5_ui",
            "patched_t25_ui",
            "patched_tt6a_ui",
            "patched_tt6b_ui",
            "patched_tt6c_ui",
        },
        assignments={"FIXED_TEXT_BLOCKED_FALLBACKS"},
    )
    text = path.read_text(encoding="utf-8")
    old_doc = '''"""Patch fixed-address UI text and small verified program fragments.

Normal dialogue is rebuilt through :mod:`time_twist.scenario`; this module owns
text that is referenced directly by 6502 code or stored in separate overlays.
Most replacements must preserve a complete table and every individual packed
record boundary.  Short code patches compare exact source bytes before
writing, and larger tables use SHA-256 revision guards.

Public ``patched_*`` functions are pure: they accept one extracted FDS file as
``bytes`` and return replacement bytes or raise :class:`UiPatchError`.
"""
'''
    new_doc = '''"""Patch standalone UI/program fragments and relocate scenario menu tables.

NOV2, NOV4, TT1A, and the Kouhen direct-boot overlay use source-verified
size-neutral patches. The other playable scenario banks expose recovered menu
metadata here so the canonical release builder can repack full-word labels,
regenerate page pointers, and relocate their movable prefixes safely.
"""
'''
    text = replace_once(text, old_doc, new_doc, "ui module docstring")
    # Retired exports existed only to support the deleted fixed-slot patch path.
    for line in (
        "TT1B_REQUIRED_DICTIONARY_TEXT = _fixed_tables.TT1B_REQUIRED_DICTIONARY_TEXT\n",
        "FIXED_UI_DICTIONARY_ENTRY_COUNT = _fixed_tables.FIXED_UI_DICTIONARY_ENTRY_COUNT\n",
        "T22_REQUIRED_DICTIONARY_TEXT = _fixed_tables.T22_REQUIRED_DICTIONARY_TEXT\n",
    ):
        text = text.replace(line, "")
    path.write_text(text, encoding="utf-8")


def clean_fixed_table_metadata() -> None:
    """Remove old translated fixed-slot dictionary reservation constants."""
    path = Path("work/time_twist/ui_fixed_tables.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.endswith("_REQUIRED_DICTIONARY_TEXT") or target.id == (
                "FIXED_UI_DICTIONARY_ENTRY_COUNT"
            ):
                names.add(target.id)
    if not names:
        raise SystemExit("no legacy fixed-table dictionary constants found")
    remove_top_level_nodes(path, assignments=names)
    text = path.read_text(encoding="utf-8")
    old_doc = '''"""Fixed-address menu and choice table declarations.

The patching algorithms remain in :mod:`time_twist.ui`; this module holds
the reviewed per-bank data they consume.
"""
'''
    new_doc = '''"""Recovered menu/choice table declarations for canonical repacking.

TT1A retains source-locked fixed-size choices. The remaining tables provide
source boundaries, hashes, and reviewed full-word labels used by the release
builder's relocated menu/scenario layout.
"""
'''
    text = replace_once(text, old_doc, new_doc, "fixed-table module docstring")
    text = text.replace(
        '''# Experimental all-full-word target note:
# The fixed-table tuples below intentionally name the desired full English
# menu/choice labels. Some labels may not fit the current byte-for-byte fixed
# slots until a follow-up compression/repacking pass reserves dictionary
# entries, changes packing strategy, or otherwise proves a safe fit.

''',
        "",
    )
    path.write_text(text, encoding="utf-8")


def rewrite_project_tests() -> None:
    """Test only project identity and the still-valid source boundary model."""
    Path("work/tests/test_project.py").write_text(
        '''"""Regression tests for current project identity and source layout."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.project import infer_bank_name


class ProjectConfigurationTests(unittest.TestCase):
    """Protect scenario-bank identity and filename inference."""

    def test_bank_name_inference_accepts_supported_patterns(self) -> None:
        """Recognize extracted and generated filenames without ambiguity."""
        self.assertEqual(infer_bank_name(Path("side1_01_TT1A_A200.bin")), "TT1A")
        self.assertEqual(infer_bank_name(Path("TT1A_candidate.bin")), "TT1A")

    def test_bank_name_inference_rejects_ambiguous_or_unknown_names(self) -> None:
        """Fail closed rather than guessing a bank name."""
        with self.assertRaises(ValueError):
            infer_bank_name(Path("translated_candidate.bin"))
        with self.assertRaises(ValueError):
            infer_bank_name(Path("TT1A_TT1B.bin"))

    def test_explicit_bank_name_is_validated(self) -> None:
        """Accept a supported override and reject unknown bank identifiers."""
        self.assertEqual(infer_bank_name(Path("anything.bin"), "TT6D"), "TT6D")
        with self.assertRaises(ValueError):
            infer_bank_name(Path("anything.bin"), "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )


def rewrite_ui_tests() -> None:
    """Replace fixed-slot compatibility tests with modern relocation contracts."""
    Path("work/tests/test_ui_fixed_tables.py").write_text(
        '''"""Fixture-free tests for canonical menu tables and standalone UI copy."""

from __future__ import annotations

import unittest

from time_twist import ui, ui_fixed_tables
from time_twist.english import encode_english
from time_twist.textcodec import pack_records

RELOCATED_BANKS = {
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
}


class FixedMenuTableTests(unittest.TestCase):
    """Protect the full-word menu data used by canonical release repacking."""

    def test_specs_cover_exactly_the_relocated_menu_banks(self) -> None:
        """Keep relocation metadata aligned with the modern release architecture."""
        self.assertEqual(set(ui.FIXED_RECORD_TABLE_SPECS), RELOCATED_BANKS)

    def test_specs_match_source_declarations_and_all_labels_encode(self) -> None:
        """Bind every spec to its source offsets/hash and supported English glyphs."""
        for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items():
            with self.subTest(bank=bank_name):
                self.assertEqual(
                    spec.start,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_START_OFFSET"),
                )
                self.assertEqual(
                    spec.end,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_END_OFFSET"),
                )
                self.assertEqual(
                    spec.source_sha256,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_SOURCE_SHA256"),
                )
                self.assertEqual(
                    spec.records,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_RECORDS"),
                )
                self.assertTrue(all(encode_english(text) for text in spec.records))
                self.assertEqual(
                    ui.fixed_record_table_page_pointer_bytes(bank_name),
                    2 * ((len(spec.records) - 1) // 32),
                )

    def test_high_value_full_word_labels_are_not_abbreviated(self) -> None:
        """Lock representative labels that motivated the relocated layout."""
        self.assertIn("Intercom", ui.FIXED_RECORD_TABLE_SPECS["TT1B"].records)
        self.assertIn("Resistance", ui.FIXED_RECORD_TABLE_SPECS["TT3A"].records)
        self.assertIn("Fight", ui.FIXED_RECORD_TABLE_SPECS["TT3B"].records)
        self.assertIn("South", ui.FIXED_RECORD_TABLE_SPECS["TT4"].records)

    def test_disk_copy_remains_size_neutral_and_mixed_case(self) -> None:
        """Keep source-locked FDS prompts readable without moving NOV2 code."""
        for collection in (
            ui.DISK_PROMPT_PATCHES,
            ui.SIDE_NUMBER_ERROR_PATCHES,
            ui.DISK_NUMBER_ERROR_PATCHES,
            ui.WRONG_DISK_PATCHES,
        ):
            for _, original, replacement in collection:
                with self.subTest(replacement=replacement):
                    self.assertEqual(
                        len(pack_records((encode_english(replacement),))),
                        len(original),
                    )
        self.assertEqual(ui.DISK_SET_ERROR_ENGLISH, "Bad side.")
        self.assertEqual(ui.KOUHEN_BOOT_GUARD_LINES, ((11, "Please start with"), (13, "Part 1")))

    def test_tt1a_fixed_choices_remain_title_case(self) -> None:
        """Keep the one non-relocated scenario bank's source-locked choices."""
        self.assertEqual(
            tuple(patch[2] for patch in ui.TT1A_CONFIRMATION_PATCHES),
            ("Yes", "No"),
        )
        self.assertEqual(ui.TT1A_MONTH_PATCHES[0][2], "Jan")
        self.assertEqual(ui.TT1A_MONTH_PATCHES[-1][2], "Dec")


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )


def modernize_remaining_tests() -> None:
    """Remove obsolete reservation tests and stale required-entry mocks."""
    hardening = Path("work/tests/test_scenario_validation_hardening.py")
    remove_top_level_test_methods = {
        "test_fixed_ui_dictionary_requirement_fails_closed",
        "test_undersized_fixed_slot_labels_are_reserved",
    }
    source = hardening.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    found: set[str] = set()
    for cls in tree.body:
        if not isinstance(cls, ast.ClassDef):
            continue
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name in remove_top_level_test_methods:
                assert node.end_lineno is not None
                spans.append((node.lineno - 1, node.end_lineno, node.name))
                found.add(node.name)
    if found != remove_top_level_test_methods:
        raise SystemExit("legacy hardening test methods did not match")
    for start, end, _ in sorted(spans, reverse=True):
        del lines[start:end]
    text = "".join(lines)
    text = text.replace(
        "from time_twist.project import required_dictionary_entries\n",
        "",
    )
    text = replace_once(
        text,
        "def test_fixed_ui_insert_rejects_no_compress(self) -> None:",
        "def test_relocated_ui_insert_redirects_to_release_build(self) -> None:",
        "relocated insert test name",
    )
    text = replace_once(
        text,
        'self.assertRaisesRegex(SystemExit, "--no-compress")',
        'self.assertRaisesRegex(SystemExit, "release-build")',
        "relocated insert assertion",
    )
    hardening.write_text(text, encoding="utf-8")

    live_fit = Path("work/tests/test_live_translation_fit.py")
    text = live_fit.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''from time_twist.project import (
    KNOWN_SCENARIO_BANKS,
    required_dictionary_entries,
)
''',
        "from time_twist.project import KNOWN_SCENARIO_BANKS\n",
        "live-fit project import",
    )
    text = replace_once(
        text,
        "        required_entries=required_dictionary_entries(bank_name),\n",
        "",
        "live-fit required entries",
    )
    live_fit.write_text(text, encoding="utf-8")

    policy = Path("work/tests/test_release_extended_dictionary_policy.py")
    text = policy.read_text(encoding="utf-8")
    mock_block = '''                patch(
                    "time_twist.release.required_dictionary_entries",
                    return_value=(),
                ),
'''
    text = replace_once(text, mock_block, "", "release policy legacy mock")
    policy.write_text(text, encoding="utf-8")


def main() -> None:
    """Apply the complete guarded deep-cleanup pass."""
    rewrite_project()
    simplify_release()
    simplify_cli()
    simplify_compression()
    remove_legacy_ui()
    clean_fixed_table_metadata()
    rewrite_project_tests()
    rewrite_ui_tests()
    modernize_remaining_tests()


if __name__ == "__main__":
    main()
