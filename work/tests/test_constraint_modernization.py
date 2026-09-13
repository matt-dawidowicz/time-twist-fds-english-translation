"""Regression contracts for the 2026-09-13 constraint modernization."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.menu_geometry import (
    MENU_MAX_STAGED_GLYPHS,
    MenuGeometryError,
    menu_pair_geometry,
    possible_compacted_pairs,
    primary_menu_descriptors,
    validate_descriptor_geometry,
    validate_menu_label,
)
from time_twist.release_build import (
    FOUR_SIDE_RELEASE_BYTES,
    RELEASE_OUTPUT_SIZES,
    TWO_SIDE_RELEASE_BYTES,
    _validate_release_output_sizes,
)
from time_twist.release_metadata import ReleaseBuildError


class MenuGeometryTests(unittest.TestCase):
    """Lock recovered variable-width menu geometry instead of dialogue width."""

    def test_individual_staging_limit_is_eighteen_glyphs(self) -> None:
        """Accept the recovered span and reject a nineteenth staged glyph."""
        self.assertEqual(validate_menu_label("X" * 18), MENU_MAX_STAGED_GLYPHS)
        with self.assertRaises(MenuGeometryError):
            validate_menu_label("X" * 19)

    def test_known_wide_pairs_fit_dynamic_two_column_geometry(self) -> None:
        """Keep historically troublesome full-word pairings inside the screen."""
        pairs = (
            ("Montgomery", "Churchill"),
            ("Agamemnon", "Parthenon"),
            ("Projector", "Airplane"),
            ("Patton", "MacArthur"),
            ("Saddam", "Zoroaster"),
            ("Strawberry", "Pearl"),
            ("Fisherman", "Statue"),
            ("Lacoste", "U Thant"),
            ("Socrates", "Homer"),
            ("Newspaper", "Body"),
            ("Scaffold", "Crowd"),
        )
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                geometry = menu_pair_geometry(left, right)
                self.assertLessEqual(geometry.right_trailing_cursor_x, 0xF8)

    def test_pair_overflow_fails_closed(self) -> None:
        """Reject a pair whose dynamic trailing cursor would wrap the screen."""
        with self.assertRaises(MenuGeometryError):
            menu_pair_geometry("X" * 11, "Y" * 10)

    def test_primary_descriptor_parser_and_compaction_model(self) -> None:
        """Decode recovered count/index records and over-approximate filtering."""
        data = bytearray(b"\x00" * 0x80)
        data[0x10:0x12] = (0xA240).to_bytes(2, "little")
        data[0x12:0x14] = (0xA24C).to_bytes(2, "little")
        # 5 choices then 5 choices: 6 + 6 bytes total.
        data[0x40:0x4C] = bytes((5, 1, 2, 3, 4, 5, 5, 2, 3, 4, 5, 6))
        descriptors = primary_menu_descriptors(bytes(data))
        self.assertEqual(descriptors, ((1, 2, 3, 4, 5), (2, 3, 4, 5, 6)))
        self.assertIn((1, 5), possible_compacted_pairs(descriptors[0]))
        labels = ("A", "BB", "CCC", "DDDD", "EEEEE", "FFFFFF")
        pairs = validate_descriptor_geometry(labels, descriptors)
        self.assertIn((1, 5), pairs)


class ReleaseSizeInvariantTests(unittest.TestCase):
    """Make exact 65,500-byte sides a release contract, not an accident."""

    def test_exact_two_and_four_side_sizes_pass(self) -> None:
        """Accept only the fixed two-side and four-side archival byte counts."""
        output = {
            "zenpen": bytes(TWO_SIDE_RELEASE_BYTES),
            "kouhen": bytes(TWO_SIDE_RELEASE_BYTES),
            "four_side": bytes(FOUR_SIDE_RELEASE_BYTES),
        }
        _validate_release_output_sizes(output)
        self.assertEqual(RELEASE_OUTPUT_SIZES["four_side"], 262_000)

    def test_one_byte_drift_fails_release(self) -> None:
        """Reject a candidate even when it misses the final invariant by one byte."""
        output = {
            "zenpen": bytes(TWO_SIDE_RELEASE_BYTES),
            "kouhen": bytes(TWO_SIDE_RELEASE_BYTES),
            "four_side": bytes(FOUR_SIDE_RELEASE_BYTES - 1),
        }
        with self.assertRaises(ReleaseBuildError):
            _validate_release_output_sizes(output)


class PolicyAndHistoryTests(unittest.TestCase):
    """Preserve current policy while retaining permanent development history."""

    def test_release_builder_has_no_retired_per_bank_dictionary_caps(
        self,
    ) -> None:
        """Keep the production optimizer on one explicit 128-entry policy."""
        root = Path(__file__).resolve().parents[2]
        source = (root / "work" / "time_twist" / "release_build.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ENTROPY_DICTIONARY_ENTRY_CAPS", source)
        self.assertIn("maximum_entries=128", source)

    def test_maintained_docs_do_not_restate_retired_constraints(self) -> None:
        """Keep obsolete limits in history only, never as current guidance."""
        root = Path(__file__).resolve().parents[2]
        maintained = (
            root / "docs" / "ARCHITECTURE.md",
            root / "docs" / "FORMATS.md",
            root / "docs" / "FULL_WORD_MENU_IMPLEMENTATION.md",
            root / "docs" / "GAMEPLAY_SCRIPT_ENGINE.md",
            root / "docs" / "GAMEPLAY_GRAPHICS_ENGINE.md",
            root / "docs" / "REVERSE_ENGINEERING_GUIDE.md",
            root / "docs" / "README.md",
        )
        retired_claims = (
            "TT2` is\ncapped at 96",
            "supports eight glyphs. The production runtime",
            "menu labels must fit six or eight visible glyphs",
            "engine parameter write; exact field semantics incomplete",
            "exact distinction between hotspot markers `$FD` and `$FE`",
            "room/sequence/presentation-state table; higher-level semantics still incomplete",
            "script/event pointer table; higher-level semantics still incomplete",
            "gameplay graphics are unknown",
        )
        for path in maintained:
            text = path.read_text(encoding="utf-8")
            for claim in retired_claims:
                with self.subTest(path=path.name, claim=claim):
                    self.assertNotIn(claim, text)

    def test_superseded_engineering_notes_live_only_in_history(self) -> None:
        """Keep dated audit/bisect records out of the maintained docs root."""
        root = Path(__file__).resolve().parents[2]
        moved = {
            "RUNTIME_BISECT.md": "RUNTIME_BISECT_20260829.md",
            "GAMEPLAY_VM_COMPLETION_20260912.md": (
                "GAMEPLAY_VM_COMPLETION_20260912.md"
            ),
        }
        for old_name, history_name in moved.items():
            with self.subTest(old_name=old_name):
                self.assertFalse((root / "docs" / old_name).exists())
                self.assertTrue(
                    (root / "docs" / "history" / history_name).is_file()
                )

    def test_constraint_history_is_permanent_and_specific(self) -> None:
        """Fail if cleanup erases the architectural development record."""
        root = Path(__file__).resolve().parents[2]
        history = (
            root / "docs" / "history" / "CONSTRAINT_MODERNIZATION_20260913.md"
        )
        amendment = (
            root
            / "docs"
            / "history"
            / "POST_INTEGRATION_VALIDATION_20260913.md"
        )
        policy = root / "docs" / "history" / "README.md"
        index = root / "docs" / "README.md"
        self.assertTrue(history.is_file())
        self.assertTrue(amendment.is_file())
        self.assertTrue(policy.is_file())
        self.assertIn("history/README.md", index.read_text(encoding="utf-8"))
        text = history.read_text(encoding="utf-8")
        policy_text = policy.read_text(encoding="utf-8")
        amendment_text = amendment.read_text(encoding="utf-8")
        for required in (
            "262,000 bytes",
            "$9390-$93AF",
            "$042D",
            "TT2=96",
            "Do not delete",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertIn("Do not delete", policy_text)
        self.assertIn("run #1264", amendment_text)
        self.assertIn("PR #60", amendment_text)
        self.assertIn("PR #62", amendment_text)


if __name__ == "__main__":
    unittest.main()
