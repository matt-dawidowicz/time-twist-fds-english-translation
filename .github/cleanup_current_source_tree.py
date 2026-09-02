"""One-shot repository cleanup for the current-source-tree maintenance pass."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
BANKS = {
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
}


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected one occurrence in {path}, found {count}: {old!r}")
    write(path, content.replace(old, new, 1))


def regex_replace(path: str, pattern: str, replacement: str, *, count: int = 1) -> None:
    content = read(path)
    updated, changes = re.subn(pattern, replacement, content, count=count, flags=re.DOTALL)
    if changes != count:
        raise RuntimeError(
            f"expected {count} regex replacement(s) in {path}, found {changes}: {pattern!r}"
        )
    write(path, updated)


def prepend_archive_notice(path: str) -> None:
    content = read(path)
    notice = (
        "> **Historical snapshot.** This document records an earlier implementation or\n"
        "> release-review state. It is preserved for provenance, not as an operational\n"
        "> guide. Use [`../README.md`](../README.md) for current documentation. Commands,\n"
        "> paths, status values, and relative links below may reflect the archived state.\n\n"
    )
    if notice not in content:
        write(path, notice + content)


# ---------------------------------------------------------------------------
# 1. Separate current source records from obsolete translation snapshots.
# ---------------------------------------------------------------------------
run("git", "mv", "work/translated_scripts", "work/source_records")
for path in sorted((ROOT / "work/source_records").glob("*.json")):
    if path.stem not in BANKS:
        run("git", "rm", path.relative_to(ROOT).as_posix())
        continue
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"source-record root is not an object: {path}")
    for group in payload.get("groups", []):
        if not isinstance(group, dict):
            raise RuntimeError(f"invalid source-record group: {path}")
        for record in group.get("records", []):
            if not isinstance(record, dict):
                raise RuntimeError(f"invalid source record: {path}")
            record.pop("english", None)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

# The rolling checkpoint is superseded by per-bank review JSON plus the
# canonical generated progress report.
run("git", "rm", "work/Time_Twist_translation_progress.checkpoint.md")

# Completed external-patch comparison tooling is no longer maintained code.
for path in (
    "work/tools/external_translation_compare.py",
    "work/tools/external_system_text_compare.py",
    "work/tests/test_external_translation_compare.py",
    "work/tests/test_external_system_text_compare.py",
):
    run("git", "rm", path)

# ---------------------------------------------------------------------------
# 2. Archive historical implementation/release narratives and audit outputs.
# ---------------------------------------------------------------------------
(ROOT / "docs/archive").mkdir(parents=True, exist_ok=True)
for name in (
    "PROJECT_RETROSPECTIVE.md",
    "BUG_FIXES_AND_TITLE_IMPLEMENTATION.md",
    "SCENARIO_VALIDATION_HARDENING.md",
    "RELEASE_RISK_ASSESSMENT.md",
):
    run("git", "mv", f"docs/{name}", f"docs/archive/{name}")
    prepend_archive_notice(f"docs/archive/{name}")

(ROOT / "audit/third_party").mkdir(parents=True, exist_ok=True)
for name in (
    "external_translation_baseline.md",
    "external_translation_baseline.json",
    "external_fixed_ui_baseline.md",
    "external_fixed_ui_baseline.json",
):
    run("git", "mv", f"work/audits/{name}", f"audit/third_party/{name}")

write(
    "docs/archive/README.md",
    """# Historical documentation\n\nThis directory preserves implementation notes, hardening reports, retrospectives,\nand release-risk snapshots that were useful while the translation pipeline was\nbeing recovered and stabilized. They are **not current operating instructions**.\n\nUse [`../README.md`](../README.md) for the maintained documentation map. Git history\nremains the authoritative record for deleted code, removed command surfaces, and\nearlier versions of files. Archived documents intentionally retain historical\nterminology and may mention commands, paths, test counts, candidate hashes, or\ntranslation wording that no longer exists in the maintained tree.\n""",
)
write(
    "audit/third_party/README.md",
    """# Third-party comparison records\n\nThese files preserve the results and provenance of the completed comparison\nagainst a removed third-party English patch. The comparison was diagnostic only;\nthird-party wording was never a translation authority.\n\nThe one-off decoder/comparison programs and their dedicated tests were removed\nfrom the maintained tool surface after the audit was completed. Their exact code\nremains available in Git history. Current English is defined only by the project\ntranslation sources and fixed-UI code.\n""",
)

# ---------------------------------------------------------------------------
# 3. Remove the obsolete standalone insertion/UI-patch CLI and compatibility
#    facade while keeping the underlying release patch machinery.
# ---------------------------------------------------------------------------
cli_commands = read("work/time_twist/cli_commands.py")
cli_commands = cli_commands.replace(
    '"""Compose the lossless parsers and guarded patch layers as ``time-twist``.\n\n'
    'Individual patch commands remain small and explicit. Release commands discover\n'
    'a project checkout from the current directory or accept ``--project-root``, so\n'
    'the installed console command does not depend on package-bundled project data.\n"""',
    '"""Implement maintained ``time-twist`` inspection, review, and release commands.\n\n'
    'Release commands discover a project checkout from the current directory or accept\n'
    '``--project-root`` so the installed console command does not depend on package-\n'
    'bundled project data. Binary release construction is centralized in ``release``.\n"""',
)
cli_commands, changes = re.subn(
    r"from \.scenario import \(\n\s+parse_scenario_bank,\n\s+rebuild_scenario_bank,\n\s+render_symbols,\n\)",
    "from .scenario import parse_scenario_bank, render_symbols",
    cli_commands,
    count=1,
)
if changes != 1:
    raise RuntimeError("could not simplify scenario import in cli_commands.py")
cli_commands, changes = re.subn(
    r"\nfrom \.ui import \(.*?\n\)\n",
    "\n",
    cli_commands,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove standalone UI patcher imports")

new_extract = '''def command_scenario_extract(args: argparse.Namespace) -> None:\n    """Decode one scenario bank into source-only stable records.\n\n    The extracted document contains exact decoded Japanese, stable IDs, and raw\n    symbols only. English lives separately in ``work/translations`` and is never\n    recovered from or preserved in an existing output file.\n    """\n    bank_name, bank = _parse_source_bank(args)\n    groups: list[dict[str, object]] = []\n    for group_index, group_address in enumerate(bank.group_addresses):\n        records: list[dict[str, object]] = []\n        for record in bank.records:\n            if record.group_index != group_index:\n                continue\n            record_id = scenario_record_id(\n                bank_name,\n                group_index,\n                record.record_index,\n            )\n            records.append(\n                {\n                    "id": record_id,\n                    "record": record.record_index,\n                    "japanese": render_symbols(\n                        record.symbols,\n                        bank.dictionary,\n                    ),\n                    "symbols": [\n                        {"kind": symbol.kind.value, "value": symbol.value}\n                        for symbol in record.symbols\n                    ],\n                }\n            )\n        groups.append(\n            {\n                "group": group_index,\n                "address": f"0x{group_address:04X}",\n                "records": records,\n            }\n        )\n\n    document = {\n        "source": str(args.bank),\n        "load_address": f"0x{bank.load_address:04X}",\n        "dictionary_address": f"0x{bank.dictionary_address:04X}",\n        "group_table_address": f"0x{bank.group_table_address:04X}",\n        "groups": groups,\n    }\n    args.output.parent.mkdir(parents=True, exist_ok=True)\n    args.output.write_text(\n        json.dumps(document, ensure_ascii=False, indent=2) + "\\n",\n        encoding="utf-8",\n    )\n    print(args.output)\n\n\n'''
cli_commands, changes = re.subn(
    r"def command_scenario_extract\(.*?(?=def merge_translation_document)",
    new_extract,
    cli_commands,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not replace scenario extract/remove scenario insert")
cli_commands, changes = re.subn(
    r"def command_ui_patch\(.*?(?=def command_replace_file)",
    "",
    cli_commands,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove command_ui_patch")
cli_commands = cli_commands.replace(
    "    output = args.output or args.scenario\n",
    "    output = args.output\n",
    1,
)
write("work/time_twist/cli_commands.py", cli_commands)

write(
    "work/time_twist/cli.py",
    '''"""Public command-line entry point for the maintained ``time-twist`` CLI."""\n\nfrom __future__ import annotations\n\nimport json\n\nfrom .cli_parser import build_parser\n\n__all__ = ("build_parser", "main")\n\n\ndef main(argv: list[str] | None = None) -> None:\n    """Parse arguments, run one command, and present expected failures cleanly."""\n    parser = build_parser()\n    args = parser.parse_args(argv)\n    try:\n        args.function(args)\n    except (\n        OSError,\n        ValueError,\n        KeyError,\n        OverflowError,\n        json.JSONDecodeError,\n    ) as error:\n        message = str(error)\n        if isinstance(error, KeyError) and len(message) >= 2:\n            message = message.strip("'\\\"")\n        parser.exit(2, f"{parser.prog}: error: {message}\\n")\n\n\nif __name__ == "__main__":\n    main()\n''',
)

cli_parser = read("work/time_twist/cli_parser.py")
cli_parser = cli_parser.replace("    command_scenario_insert,\n", "")
cli_parser = cli_parser.replace("    command_ui_patch,\n", "")
cli_parser, changes = re.subn(
    r"\n    scenario_insert = subparsers\.add_parser\(.*?scenario_insert\.set_defaults\(function=command_scenario_insert\)\n",
    "\n",
    cli_parser,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove scenario-insert parser")
cli_parser, changes = re.subn(
    r"\n    ui_patch = subparsers\.add_parser\(.*?ui_patch\.set_defaults\(function=command_ui_patch\)\n",
    "\n",
    cli_parser,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove ui-patch parser")
cli_parser = cli_parser.replace(
    '            "Japanese text, and raw symbols. Existing English in the output "\n'
    '            "is retained only for matching stable record IDs."\n',
    '            "Japanese text, and raw symbols. The output is source-only; "\n'
    '            "English remains in the separate translation maps."\n',
    1,
)
cli_parser = cli_parser.replace(
    '        help="destination scenario JSON (default: update SCENARIO)",\n',
    '        required=True,\n'
    '        help="destination merged review JSON; the source document is never modified",\n',
    1,
)
write("work/time_twist/cli_parser.py", cli_parser)

# Source-record comparison loader: current English already comes from the
# authoritative translation maps in _scenario_rows().
comparison = read("work/generate_bilingual_comparison.py")
comparison = comparison.replace("work/translated_scripts", "work/source_records")
comparison = comparison.replace('WORK / "translated_scripts"', 'WORK / "source_records"')
write("work/generate_bilingual_comparison.py", comparison)

# The workbook keeps per-bank review checkpoints but no rolling snapshot file.
workbook = read("work/generate_translation_workbook.py")
workbook = workbook.replace(
    "Persist resumable per-bank JSON and a rolling generation checkpoint.",
    "Persist resumable per-bank JSON review checkpoints.",
)
workbook, changes = re.subn(
    r"\n\s{8}checkpoint = \[.*?\n\s{8}\(WORK / \"Time_Twist_translation_progress\.checkpoint\.md\"\)\.write_text\(.*?\n\s{8}\)\n",
    "\n",
    workbook,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove rolling workbook checkpoint writer")
write("work/generate_translation_workbook.py", workbook)

public_tree = read("work/tools/check_public_tree.py")
public_tree = public_tree.replace(
    '    Path("work/translations"),\n',
    '    Path("work/translations"),\n    Path("work/source_records"),\n',
    1,
)
write("work/tools/check_public_tree.py", public_tree)

# ---------------------------------------------------------------------------
# 4. Remove tests that lock obsolete compatibility behavior or duplicate old
#    English prose. Keep structural, validator, compression, and release tests.
# ---------------------------------------------------------------------------
replace_once(
    "work/tests/test_translation_workbook.py",
    "from time_twist.cli import PERSONALITY_QUESTION_IDS\n",
    "from time_twist.project import PERSONALITY_QUESTION_IDS\n",
)

modern = read("work/tests/test_modern_module_layout.py")
modern = modern.replace("    cli_commands,\n", "")
modern, changes = re.subn(
    r"    def test_cli_facade_exports_the_parser_and_command_implementations\(.*?(?=    def test_release_facade_exports_metadata_validation_helpers)",
    '''    def test_cli_entry_point_keeps_command_implementations_internal(\n        self,\n    ) -> None:\n        """Expose parser/main publicly without compatibility command aliases."""\n        self.assertIs(cli.build_parser, cli_parser.build_parser)\n        for name in (\n            "command_release_build",\n            "command_release_lock",\n            "command_scenario_insert",\n            "command_ui_patch",\n        ):\n            with self.subTest(name=name):\n                self.assertFalse(hasattr(cli, name))\n\n''',
    modern,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not modernize CLI module-layout test")
write("work/tests/test_modern_module_layout.py", modern)

hardening = read("work/tests/test_scenario_validation_hardening.py")
hardening = hardening.replace(
    "from time_twist.cli import command_scenario_extract, command_scenario_insert\n",
    "from time_twist.cli_commands import command_scenario_extract\n",
    1,
)
hardening, changes = re.subn(
    r"    def test_extract_preserves_english_only_for_matching_stable_id\(.*?(?=    def test_dictionary_boundary_can_include_fixed_ui_only_entries)",
    '''    def test_extract_discards_stale_english_fields(self) -> None:\n        """Keep decoded source records independent of previous English output."""\n        with tempfile.TemporaryDirectory() as directory:\n            root = Path(directory)\n            bank = root / "TT1A_source.bin"\n            output = root / "scenario.json"\n            _synthetic_bank(bank)\n\n            command_scenario_extract(SimpleNamespace(bank=bank, output=output))\n            document = json.loads(output.read_text(encoding="utf-8"))\n            document["groups"][0]["records"][0]["english"] = "STALE"\n            output.write_text(\n                json.dumps(document, ensure_ascii=False, indent=2) + "\\n",\n                encoding="utf-8",\n            )\n\n            command_scenario_extract(SimpleNamespace(bank=bank, output=output))\n            refreshed = json.loads(output.read_text(encoding="utf-8"))\n            record = refreshed["groups"][0]["records"][0]\n            self.assertEqual(record["id"], "TT1A/g0/r0")\n            self.assertNotIn("english", record)\n\n''',
    hardening,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not replace obsolete extract/insert tests")
hardening, changes = re.subn(
    r"    def test_fixed_ui_insert_rejects_no_compress\(.*?(?=    def test_rebuild_rejects_per_group_record_count_change)",
    "",
    hardening,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not remove legacy no-compress insertion test")
write("work/tests/test_scenario_validation_hardening.py", hardening)

integration = read("work/integration_tests/test_scenario.py")
integration = integration.replace(
    "from time_twist.cli import (\n    PERSONALITY_QUESTION_IDS,\n    command_scenario_extract,\n    merge_translation_document,\n)\n",
    "from time_twist.cli_commands import (\n    command_scenario_extract,\n    merge_translation_document,\n)\nfrom time_twist.project import PERSONALITY_QUESTION_IDS\n",
    1,
)
for method, next_method in (
    ("test_tt1b_sky_line_is_natural_and_width_safe", "test_tt1a_fortune_prediction_has_terminal_punctuation"),
    ("test_tt1a_fortune_prediction_has_terminal_punctuation", "test_editorial_regressions_preserve_meaning_and_terminology"),
    ("test_editorial_regressions_preserve_meaning_and_terminology", "test_fixed_footprint_rebuild_keeps_the_original_tail_address"),
):
    pattern = rf"    def {method}\(.*?(?=    def {next_method})"
    integration, changes = re.subn(pattern, "", integration, count=1, flags=re.DOTALL)
    if changes != 1:
        raise RuntimeError(f"could not remove stale editorial integration test {method}")
integration, changes = re.subn(
    r"    def test_personality_questions_are_complete_and_width_safe\(.*?(?=    def test_scenario_refresh_preserves_existing_english)",
    '''    def test_personality_questions_are_complete_and_width_safe(self) -> None:\n        """Validate every current personality question without duplicating prose."""\n        path = WORK_DIR / "translations/TT1A.json"\n        if not path.exists():\n            self.fail("translation fixture is not available")\n        translations = json.loads(path.read_text(encoding="utf-8"))\n        actual_ids = [f"TT1A/g0/r{record}" for record in range(6, 21)]\n        self.assertEqual(set(actual_ids), set(PERSONALITY_QUESTION_IDS))\n        for record_id in actual_ids:\n            with self.subTest(record=record_id):\n                validate_display_width(\n                    translations[record_id],\n                    allow_wrap=True,\n                )\n\n''',
    integration,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not de-duplicate personality-question prose test")
integration, changes = re.subn(
    r"    def test_scenario_refresh_preserves_existing_english\(.*?(?=    def test_english_dictionary_compresses_and_expands_losslessly)",
    '''    def test_scenario_refresh_is_source_only(self) -> None:\n        """Ensure private-fixture extraction never carries English forward."""\n        bank_path = WORK_DIR / "extracted_zenpen/side1_01_TT1A_A200.bin"\n        if not bank_path.exists():\n            self.fail("workspace fixture is not available")\n        with tempfile.TemporaryDirectory() as directory:\n            output = Path(directory) / "TT1A.json"\n            args = SimpleNamespace(bank=bank_path, output=output)\n            command_scenario_extract(args)\n            document = json.loads(output.read_text(encoding="utf-8"))\n            record = document["groups"][0]["records"][0]\n            record["english"] = "STALE"\n            output.write_text(\n                json.dumps(document, ensure_ascii=False, indent=2) + "\\n",\n                encoding="utf-8",\n            )\n\n            command_scenario_extract(args)\n            refreshed = json.loads(output.read_text(encoding="utf-8"))\n            refreshed_record = refreshed["groups"][0]["records"][0]\n            self.assertEqual(refreshed_record["id"], "TT1A/g0/r0")\n            self.assertNotIn("english", refreshed_record)\n\n''',
    integration,
    count=1,
    flags=re.DOTALL,
)
if changes != 1:
    raise RuntimeError("could not modernize private source-refresh test")
write("work/integration_tests/test_scenario.py", integration)

preview = read("work/preview_pixel_font.py")
preview = preview.replace("Do you prefer consommé", "Consommé over miso soup?")
write("work/preview_pixel_font.py", preview)

# ---------------------------------------------------------------------------
# 5. Make active documentation describe only the current workflow.
# ---------------------------------------------------------------------------
readme = read("README.md")
readme = readme.replace("All **2,052 extracted text records**", "All **2,058 text records**")
readme = readme.replace("work/translated_scripts/", "work/source_records/")
readme = readme.replace(
    "| `work/source_records/` | Extracted/review-oriented scenario records |",
    "| `work/source_records/` | Decoded Japanese/source-structure records; no English authority |",
)
readme = readme.replace(
    ", [full-word menu implementation](docs/FULL_WORD_MENU_IMPLEMENTATION.md), and [implementation notes](docs/BUG_FIXES_AND_TITLE_IMPLEMENTATION.md)",
    ", and [full-word menu implementation](docs/FULL_WORD_MENU_IMPLEMENTATION.md)",
)
readme, _ = re.subn(
    r"\nFor a source-level account of the verified game fixes,.*?manual Zenpen-to-Kouhen playthrough\.\n",
    "\nHistorical implementation notes, retrospectives, and dated release-risk reports are preserved under [`docs/archive/`](docs/archive/). They are provenance records, not current operating instructions.\n",
    readme,
    count=1,
    flags=re.DOTALL,
)
readme = readme.replace("- [`docs/PROJECT_RETROSPECTIVE.md`](docs/PROJECT_RETROSPECTIVE.md)\n", "")
readme = readme.replace("Python 3.11 and 3.12", "Python 3.11 and 3.14")
write("README.md", readme)

write(
    "docs/README.md",
    """# Documentation index\n\nThe maintained documentation describes the current source-only translation and\nrelease pipeline. Historical implementation snapshots live in [`archive/`](archive/README.md)\nand must not be treated as operating instructions.\n\n## Start here\n\n- **Play a candidate:** [Playtesting guide](../PLAYTESTING.md)\n- **Set up a checkout:** [Quickstart](../QUICKSTART.md)\n- **Improve English text:** [Translation contributor guide](../CONTRIBUTING_TRANSLATION.md)\n- **Change Python tooling or tests:** [Code contributor guide](../CONTRIBUTING_CODE.md)\n- **Tour the implementation:** [Code tour](CODE_TOUR.md)\n\nThe public repository contains no original or patched FDS images, BIOS files,\nextracted retail payloads, emulator states, or other private fixtures.\n\n## Translation and review\n\n1. [Translation workflow](TRANSLATION_WORKFLOW.md)\n2. [Workbook pipeline](WORKBOOK_PIPELINE.md)\n3. [Scenario-bank format](FORMATS.md#scenario-bank-layout)\n\n`work/translations/*.json` is the only scenario-English authority.\n`work/source_records/*.json` contains decoded Japanese, stable record IDs, and\nsource structure only. Generated workbooks are review surfaces, not replacement\nsources.\n\n## Binary and release architecture\n\n1. [Architecture](ARCHITECTURE.md)\n2. [Formats](FORMATS.md)\n3. [Development guide](DEVELOPMENT.md)\n4. [Module map](MODULE_MAP.md)\n5. [CLI reference](CLI_REFERENCE.md)\n6. [Maintainer release process](MAINTAINER_RELEASE_PROCESS.md)\n7. [Private fixtures](PRIVATE_FIXTURES.md)\n\nCandidate and strict release builds use the single source-locked release builder.\nLow-level parsing and inspection commands remain available, but obsolete standalone\nbank/UI construction commands are no longer part of the public CLI.\n\n## Menus, fixed UI, title, and font\n\n- [Full-word menu implementation](FULL_WORD_MENU_IMPLEMENTATION.md)\n- [NOV4 font-source safety](NOV4_FONT_SOURCE_SAFETY.md)\n- [Title sequence](TITLE_SEQUENCE.md)\n- [Runtime playtest matrix](PLAYTEST_MATRIX.md)\n\n## Authority map\n\n| Representation | Purpose |\n| --- | --- |\n| `work/translations/*.json` | Authoritative playable scenario English |\n| `work/source_records/*.json` | Decoded Japanese/source structure; no English authority |\n| `work/time_twist/ui.py` and `ui_fixed_tables.py` | Playable fixed/interface text and guarded patch logic |\n| `work/title_assets/Time Twist approved native title.png` | Native ROM-bound title geometry |\n| `work/title_assets/Time Twist approved native slide.png` | Native ROM-bound swipe geometry |\n| `work/release_sources.json` | Approved non-code input hashes |\n| `work/release_target.json` | Reviewed release-output authority after promotion |\n| `work/translation_workbook_banks/*.json` | Generated per-bank linguistic review |\n| `outputs/Time_Twist_complete_translation_workbook.*` | Generated aggregate review artifacts |\n| User-supplied FDS bytes | Authoritative original binary layout |\n\nNever replace exact Japanese evidence with reconstructed kanji, and never use an\narchived or generated English string as the playable source.\n\n## Historical records\n\n- [`archive/`](archive/README.md): retired implementation, hardening, retrospective,\n  and dated release-review documents.\n- [`../audit/third_party/`](../audit/third_party/README.md): completed third-party\n  comparison evidence.\n- Git history: exact deleted code, old command implementations, and prior file states.\n""",
)

write(
    "docs/TRANSLATION_WORKFLOW.md",
    """# Translation workflow\n\nThis is the maintained path from Japanese source evidence to a reviewable English\ncandidate. Scenario English has one authority: `work/translations/*.json`.\n\n## 1. Provide private source images\n\nPlace legally obtained clean Japanese images in the private overlay:\n\n```text\nwork/baseline/time_twist_zenpen_japan.fds\nwork/baseline/time_twist_kouhen_japan.fds\n```\n\nValidate and extract them without committing the retail data:\n\n```powershell\ntime-twist manifest work/baseline/time_twist_zenpen_japan.fds --output work/manifests/zenpen.json\ntime-twist manifest work/baseline/time_twist_kouhen_japan.fds --output work/manifests/kouhen.json\ntime-twist roundtrip work/baseline/time_twist_zenpen_japan.fds work/build/zenpen_roundtrip.fds\ntime-twist roundtrip work/baseline/time_twist_kouhen_japan.fds work/build/kouhen_roundtrip.fds\ntime-twist extract work/baseline/time_twist_zenpen_japan.fds work/extracted_zenpen\ntime-twist extract work/baseline/time_twist_kouhen_japan.fds work/extracted_kouhen\n```\n\nSee [Private fixtures](PRIVATE_FIXTURES.md) for the complete overlay policy.\n\n## 2. Refresh decoded source records only when source evidence changes\n\n`scenario-extract` writes Japanese/source-structure records. It deliberately does\nnot carry English forward from an older output. Example:\n\n```powershell\ntime-twist scenario-extract `\n  work/extracted_zenpen/side1_01_TT1A_A200.bin `\n  work/source_records/TT1A.json\n```\n\nThe checked-in source record contains stable IDs, exact decoded Japanese, and raw\nsymbol metadata. It is not a translation file.\n\n## 3. Edit the authoritative English map\n\nEdit the matching ID-keyed map directly:\n\n```text\nwork/translations/TT1A.json\n```\n\nPreserve source control-event order, supported characters, character voice,\nterminology, and renderer limits. The shared validators enforce the technical\ncontracts; translation review still requires reading the Japanese and gameplay\ncontext.\n\n## 4. Optionally generate a merged review document\n\n`scenario-merge` is a validator/review utility. It requires a separate output so\nit cannot silently turn a checked-in source record into a second English source:\n\n```powershell\ntime-twist scenario-merge `\n  work/source_records/TT1A.json `\n  work/translations/TT1A.json `\n  --output work/build/TT1A_review.json\n```\n\nDo not commit merged review JSON as a translation authority.\n\nFor a quick bank-capacity diagnostic with private source bytes:\n\n```powershell\ntime-twist scenario-footprint `\n  work/extracted_zenpen/side1_01_TT1A_A200.bin `\n  --translations work/translations/TT1A.json\n```\n\n## 5. Regenerate public review artifacts\n\n```powershell\npython work/generate_bilingual_comparison.py\npython work/generate_translation_workbook.py\npython work/run_tests.py unit\n```\n\nCI uses the fixture-free comparison generator and requires checked-in generated\nreview artifacts to match their sources. `work/translation_workbook_banks/` holds\nper-bank review checkpoints; `outputs/Time_Twist_translation_progress.md` is the\ncanonical aggregate progress report.\n\n## 6. Build one canonical candidate\n\nThere is no separate maintained scenario/UI construction path. The release builder\nencodes dialogue, shared menus, fixed UI, font, title, and container changes under\none source lock:\n\n```powershell\ntime-twist release-lock\ntime-twist release-lock --update\ntime-twist release-build --candidate --output-dir build/candidate\n```\n\nUse `release-lock` without `--update` first to inspect drift. Refresh the lock only\nfor reviewed intentional source changes.\n\nAudit full-word fixed-menu output:\n\n```powershell\npython work/tools/audit_fixed_menu_labels.py `\n  --candidate-fds "build/candidate/Time Twist - reproducible English four-side playtest.fds" `\n  --output-csv build/candidate/fixed_menu_label_audit.csv\n```\n\nThe expected canonical inventory is 721 full-word labels with zero blocked or\nfailed entries.\n\n## 7. Run private integration tests and playtest\n\nWith the complete legal private overlay:\n\n```powershell\npython work/run_tests.py integration\npython work/run_tests.py all\n```\n\nThen play the exact candidate named by its manifest. Focus on disk transitions,\nsave/load, long lines, menus, page clearing, title behavior, and the records still\nflagged for gameplay/visual verification in the generated progress report.\n\n## 8. Promote only the reviewed candidate\n\n```powershell\ntime-twist release-promote build/candidate/release_manifest.json `\n  --release-id english-playtest-YYYY-MM-DD\ntime-twist release-build\n```\n\nPromotion independently rebuilds and verifies the candidate before establishing a\nstrict release target. Never edit generated ROMs, merged review JSON, workbooks, or\narchived documents as a substitute for changing the authoritative source.\n""",
)

# Path/terminology updates across maintained documentation.
for path in [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "CONTRIBUTING_CODE.md", ROOT / "CONTRIBUTING_TRANSLATION.md", ROOT / "CONTRIBUTING.md", ROOT / "QUICKSTART.md", ROOT / "PLAYTESTING.md"]:
    if not path.exists():
        continue
    content = path.read_text(encoding="utf-8")
    content = content.replace("work/translated_scripts", "work/source_records")
    content = content.replace("Python 3.11 and 3.12", "Python 3.11 and 3.14")
    path.write_text(content, encoding="utf-8")

# Remove retired command sections from the active CLI reference.
cli_ref = read("docs/CLI_REFERENCE.md")
for command in ("scenario-insert", "ui-patch"):
    cli_ref, changes = re.subn(
        rf"\n### `{re.escape(command)}[^\n]*`\n.*?(?=\n### `|\n## )",
        "\n",
        cli_ref,
        count=1,
        flags=re.DOTALL,
    )
    if changes != 1:
        raise RuntimeError(f"could not remove retired CLI section: {command}")
cli_ref = cli_ref.replace(
    "destination scenario JSON (default: update SCENARIO)",
    "required destination merged review JSON; SCENARIO is never modified",
)
cli_ref += (
    "\n## Historical command surface\n\nEarlier revisions exposed standalone bank/UI construction commands in addition to "
    "the release builder. Those compatibility commands were removed after the "
    "source-locked release path became authoritative. Their implementation and "
    "documentation remain available in Git history and `docs/archive/`.\n"
)
write("docs/CLI_REFERENCE.md", cli_ref)

# Remove stale operational wording in otherwise-current design docs.
for path in (
    "docs/ARCHITECTURE.md",
    "docs/FORMATS.md",
    "docs/FULL_WORD_MENU_IMPLEMENTATION.md",
    "docs/DEVELOPMENT.md",
    "docs/MODULE_MAP.md",
    "docs/WORKBOOK_PIPELINE.md",
):
    content = read(path)
    content = content.replace("`scenario-insert`", "the retired standalone scenario builder")
    content = content.replace("`ui-patch`", "the retired standalone fixed-UI command")
    content = content.replace("scenario-insert", "retired standalone scenario builder")
    content = content.replace("ui-patch", "retired standalone fixed-UI command")
    write(path, content)

ui = read("work/time_twist/ui.py")
ui = ui.replace("``ui-patch`` compatibility path", "fixed-slot compatibility helpers")
ui = ui.replace("ui-patch", "fixed-slot patch")
write("work/time_twist/ui.py", ui)

# ---------------------------------------------------------------------------
# 6. Fix CI duplication and test the support floor plus current Python.
# ---------------------------------------------------------------------------
write(
    ".github/workflows/tests.yml",
    """name: tests\n\non:\n  push:\n    branches:\n      - main\n  pull_request:\n\nconcurrency:\n  group: tests-${{ github.event_name }}-${{ github.head_ref || github.ref_name }}\n  cancel-in-progress: true\n\njobs:\n  unit-tests:\n    runs-on: ubuntu-latest\n    strategy:\n      fail-fast: false\n      matrix:\n        python-version: [\"3.11\", \"3.14\"]\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n          cache: pip\n      - run: python work/tools/check_public_tree.py\n      - run: python -m pip install --upgrade pip\n      - run: python -m pip install -r requirements.txt\n      - run: python work/generate_bilingual_comparison_ci.py\n      - run: python work/generate_translation_workbook.py\n      - name: Verify generated translation review artifacts are current\n        run: git diff --exit-code -- outputs work/translation_workbook_banks\n      - run: python -m black --check work\n      - run: python -m ruff check work\n      - run: python -m pydocstyle --convention=pep257 work\n      - run: python -m mypy\n      - run: python work/run_tests.py unit\n      - if: matrix.python-version == '3.14'\n        run: python -m build\n      - if: matrix.python-version == '3.14'\n        run: python -m pip install --force-reinstall dist/*.whl\n      - if: matrix.python-version == '3.14'\n        name: Prove smoke test imports the installed wheel\n        run: >-\n          python -c \"from pathlib import Path; import time_twist;\n          from time_twist.release import build_code_provenance;\n          imported = Path(time_twist.__file__).resolve();\n          checkout = Path('work/time_twist').resolve(); print(imported);\n          assert checkout not in imported.parents,\n          f'import leaked from checkout: {imported}';\n          build_code_provenance(Path.cwd())\"\n      - if: matrix.python-version == '3.14'\n        run: time-twist --help\n      - if: matrix.python-version == '3.14'\n        run: time-twist release-build --help\n\n  required-unit-tests:\n    name: unit-tests\n    needs: unit-tests\n    if: ${{ always() }}\n    runs-on: ubuntu-latest\n    steps:\n      - name: Require every supported Python version to pass\n        run: test \"${{ needs.unit-tests.result }}\" = \"success\"\n""",
)

# ---------------------------------------------------------------------------
# 7. Fail the migration if stale operational state remains outside archives.
# ---------------------------------------------------------------------------
source_paths = sorted((ROOT / "work/source_records").glob("*.json"))
if {path.stem for path in source_paths} != BANKS:
    raise RuntimeError(
        "source_records must contain exactly the 13 canonical scenario banks"
    )
for path in source_paths:
    payload = json.loads(path.read_text(encoding="utf-8"))
    for group in payload["groups"]:
        for record in group["records"]:
            if "english" in record:
                raise RuntimeError(f"stale English remains in {path}")

active_text_paths = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CONTRIBUTING_CODE.md",
    ROOT / "CONTRIBUTING_TRANSLATION.md",
    ROOT / "QUICKSTART.md",
    ROOT / "PLAYTESTING.md",
    *sorted((ROOT / "docs").glob("*.md")),
    *sorted((ROOT / "work/time_twist").glob("*.py")),
]
for path in active_text_paths:
    if not path.exists():
        continue
    content = path.read_text(encoding="utf-8")
    for forbidden in (
        "work/translated_scripts",
        "Time_Twist_translation_progress.checkpoint.md",
    ):
        if forbidden in content:
            raise RuntimeError(f"stale active reference {forbidden!r} in {path}")

if (ROOT / "work/Time_Twist_translation_progress.checkpoint.md").exists():
    raise RuntimeError("obsolete rolling checkpoint still exists")

print("source-tree cleanup migration completed")
