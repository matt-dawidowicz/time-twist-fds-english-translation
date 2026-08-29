"""Normalize the generated PR #20 CLI-boundary regression test."""

from __future__ import annotations

from pathlib import Path

PATH = Path("work/tests/test_modern_cli_boundaries.py")
OLD = '''            with self.subTest(bank=bank_name):
                with self.assertRaisesRegex(SystemExit, "release-build"):
                    _require_standalone_scenario_bank(
                        bank_name, "scenario-insert"
                    )
'''
NEW = '''            with self.subTest(bank=bank_name), self.assertRaisesRegex(
                SystemExit, "release-build"
            ):
                _require_standalone_scenario_bank(bank_name, "scenario-insert")
'''

text = PATH.read_text(encoding="utf-8")
if text.count(OLD) != 1:
    raise SystemExit("generated CLI-boundary context block did not match once")
PATH.write_text(text.replace(OLD, NEW), encoding="utf-8")
