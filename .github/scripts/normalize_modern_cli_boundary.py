"""Normalize PR #20 tests after the guarded modern-interface refactor."""

from __future__ import annotations

from pathlib import Path

BOUNDARY_PATH = Path("work/tests/test_modern_cli_boundaries.py")
BOUNDARY_OLD = '''            with self.subTest(bank=bank_name):
                with self.assertRaisesRegex(SystemExit, "release-build"):
                    _require_standalone_scenario_bank(
                        bank_name, "scenario-insert"
                    )
'''
BOUNDARY_NEW = '''            with self.subTest(bank=bank_name), self.assertRaisesRegex(
                SystemExit, "release-build"
            ):
                _require_standalone_scenario_bank(bank_name, "scenario-insert")
'''

boundary_text = BOUNDARY_PATH.read_text(encoding="utf-8")
if boundary_text.count(BOUNDARY_OLD) != 1:
    raise SystemExit("generated CLI-boundary context block did not match once")
BOUNDARY_PATH.write_text(
    boundary_text.replace(BOUNDARY_OLD, BOUNDARY_NEW),
    encoding="utf-8",
)

HARDENING_PATH = Path("work/tests/test_scenario_validation_hardening.py")
hardening_text = HARDENING_PATH.read_text(encoding="utf-8")
replacements = (
    (
        "def test_fixed_ui_insert_rejects_no_compress(self) -> None:",
        "def test_relocated_ui_insert_redirects_to_release_build(self) -> None:",
        "legacy insert test name",
    ),
    (
        '"""Verify the current contract described by this regression test."""\n        with tempfile.TemporaryDirectory() as directory:',
        '"""Reject relocated-menu insertion before obsolete compression options matter."""\n        with tempfile.TemporaryDirectory() as directory:',
        "legacy insert test docstring",
    ),
    (
        'self.assertRaisesRegex(SystemExit, "--no-compress")',
        'self.assertRaisesRegex(SystemExit, "release-build")',
        "legacy insert error assertion",
    ),
)
for old, new, label in replacements:
    if hardening_text.count(old) != 1:
        raise SystemExit(f"{label} did not match once")
    hardening_text = hardening_text.replace(old, new, 1)
HARDENING_PATH.write_text(hardening_text, encoding="utf-8")
