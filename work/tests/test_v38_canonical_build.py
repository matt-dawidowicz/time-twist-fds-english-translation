"""Guard the full active v38 text set and the default compiler selection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from time_twist.release_metadata import ReleaseBuildError
from time_twist.v38_build import (
    build_release_images,
    restore_checkpoint,
    validate_checkpoint_records,
)

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "recovery/v38/repro_bundle"


class V38CanonicalBuildTests(unittest.TestCase):
    """Reject stale wording, changed controls, and the wrong baseline."""

    @classmethod
    def setUpClass(cls) -> None:
        """Read the independently hash-checked checkpoint without private ROMs."""
        with tempfile.TemporaryDirectory() as directory:
            cls.approved = restore_checkpoint(BUNDLE, Path(directory))
        cls.actual = {
            record: text
            for path in (ROOT / "work/translations").glob("*.json")
            for record, text in json.loads(
                path.read_text(encoding="utf-8")
            ).items()
        }

    def test_every_active_record_matches_approved_wording_and_controls(
        self,
    ) -> None:
        """Compare all 1,299 records, not just a sample of known corrections."""
        self.assertEqual(len(self.actual), 1299)
        validate_checkpoint_records(self.actual, self.approved)

    def test_every_record_is_protected_against_unapproved_edits(self) -> None:
        """Prove that altering any one record is rejected independently of locks."""
        for record, text in self.actual.items():
            with self.subTest(record=record):
                changed = dict(self.actual)
                changed[record] = text + " stale"
                with self.assertRaisesRegex(ReleaseBuildError, "1 records"):
                    validate_checkpoint_records(changed, self.approved)

    def test_missing_extra_and_control_only_changes_are_rejected(self) -> None:
        """Guard IDs and pagination even when visible English is unchanged."""
        record = "TT1A/g0/r0"
        variants = [dict(self.actual) for _ in range(3)]
        del variants[0][record]
        variants[1]["TT1A/g99/r99"] = "Extra"
        variants[2][record] = variants[2][record].replace(
            "{CTRL:1}", "{CTRL:0}"
        )
        for changed in variants:
            with self.assertRaises(ReleaseBuildError):
                validate_checkpoint_records(changed, self.approved)

    def test_invalid_baseline_fails_before_compiler_execution(self) -> None:
        """Reject a Japanese ROM or arbitrary input instead of falling back."""
        with self.assertRaisesRegex(ReleaseBuildError, "exact private v25"):
            build_release_images(
                b"wrong", translations_directory=ROOT, compiler_bundle=BUNDLE
            )


if __name__ == "__main__":
    unittest.main()
