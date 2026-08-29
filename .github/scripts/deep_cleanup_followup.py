"""Finish modern consumers after the deep PR #20 architecture cleanup."""

from __future__ import annotations

import ast
from pathlib import Path


def remove_assignments(path: Path, names: set[str]) -> None:
    """Remove exact top-level assignments by AST line span."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int, str]] = []
    found: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        matches = {
            target.id
            for target in targets
            if isinstance(target, ast.Name) and target.id in names
        }
        if not matches:
            continue
        if len(matches) != 1 or node.end_lineno is None:
            raise SystemExit(f"unexpected assignment shape in {path}")
        name = next(iter(matches))
        spans.append((node.lineno - 1, node.end_lineno, name))
        found.add(name)
    if found != names:
        raise SystemExit(f"assignment mismatch in {path}: {sorted(names - found)}")
    for start, end, _ in sorted(spans, reverse=True):
        del lines[start:end]
    path.write_text("".join(lines), encoding="utf-8")


def modernize_comparison_generator() -> None:
    """Build review fixed-table specs from the canonical mapping."""
    path = Path("work/generate_bilingual_comparison.py")
    text = path.read_text(encoding="utf-8")
    start = text.find("FIXED_SPECS = (\n")
    end = text.find("\n\n\ndef _fixed_rows", start)
    if start < 0 or end < 0:
        raise SystemExit("comparison FIXED_SPECS block not found")
    replacement = '''FIXED_SPECS = tuple(
    (bank_name, spec.start, spec.end, spec.records)
    for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items()
)'''
    path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def modernize_target_audit() -> None:
    """Audit canonical menu specs directly instead of legacy module aliases."""
    path = Path("work/tools/audit_full_word_menu_targets.py")
    text = path.read_text(encoding="utf-8")
    old = '''    for bank_name in SCENARIO_LOCATIONS:
        records_name = f"{bank_name}_FIXED_TEXT_RECORDS"
        if not hasattr(ui, records_name):
            continue
        records = getattr(ui, records_name)
        for index, label in enumerate(records):
'''
    new = '''    for bank_name, spec in ui.FIXED_RECORD_TABLE_SPECS.items():
        if bank_name not in SCENARIO_LOCATIONS:
            raise ValueError(f"unknown relocated menu bank: {bank_name}")
        for index, label in enumerate(spec.records):
'''
    if text.count(old) != 1:
        raise SystemExit("target-audit legacy records lookup did not match once")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def modernize_facade_test() -> None:
    """Test the canonical spec facade rather than retired individual aliases."""
    path = Path("work/tests/test_modern_module_layout.py")
    text = path.read_text(encoding="utf-8")
    old = '''    def test_ui_facade_exports_the_fixed_table_data(self) -> None:
        """Keep fixed-table callers independent of the declarative-data split."""
        self.assertIs(
            ui.TT1B_FIXED_TEXT_RECORDS,
            ui_fixed_tables.TT1B_FIXED_TEXT_RECORDS,
        )
        self.assertIs(
            ui.T22_FIXED_TEXT_RECORDS,
            ui_fixed_tables.T22_FIXED_TEXT_RECORDS,
        )
        self.assertIs(
            ui.TT6C_FIXED_TEXT_RECORDS,
            ui_fixed_tables.TT6C_FIXED_TEXT_RECORDS,
        )
'''
    new = '''    def test_ui_facade_exports_the_canonical_fixed_table_specs(self) -> None:
        """Keep callers on one declarative relocated-menu mapping."""
        for bank_name in ("TT1B", "T22", "TT6C"):
            with self.subTest(bank=bank_name):
                spec = ui.FIXED_RECORD_TABLE_SPECS[bank_name]
                self.assertIs(
                    spec.records,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_RECORDS"),
                )
                self.assertEqual(
                    spec.start,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_START_OFFSET"),
                )
                self.assertEqual(
                    spec.end,
                    getattr(ui_fixed_tables, f"{bank_name}_FIXED_TEXT_END_OFFSET"),
                )
'''
    if text.count(old) != 1:
        raise SystemExit("legacy UI facade test did not match once")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


remove_assignments(
    Path("work/time_twist/ui_fixed_tables.py"),
    {
        "TT2_DICTIONARY_POINTER_OFFSET",
        "TT2_LOAD_ADDRESS",
        "TT2_DICTIONARY_ENTRIES",
    },
)
modernize_comparison_generator()
modernize_target_audit()
modernize_facade_test()
