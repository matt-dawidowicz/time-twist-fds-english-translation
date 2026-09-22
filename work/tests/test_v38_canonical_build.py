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
    validate_checkpoint_record_ids,
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

    def test_v38_checkpoint_is_complete_and_self_consistent(self) -> None:
        """Keep the historical 1,299-record v38 oracle exact."""
        self.assertEqual(len(self.approved), 1299)
        validate_checkpoint_records(self.approved, self.approved)

    def test_active_maps_keep_the_recovered_record_topology(self) -> None:
        """Allow reviewed post-v38 text while preserving every recovered record ID."""
        self.assertEqual(len(self.actual), 1299)
        validate_checkpoint_record_ids(self.actual, self.approved)

    def test_every_v38_record_is_protected_against_checkpoint_edits(self) -> None:
        """Prove that the historical v38 oracle rejects any one-record mutation."""
        for record, text in self.approved.items():
            with self.subTest(record=record):
                changed = dict(self.approved)
                changed[record] = text + " stale"
                with self.assertRaisesRegex(ReleaseBuildError, "1 records"):
                    validate_checkpoint_records(changed, self.approved)

    def test_checkpoint_missing_extra_and_control_changes_are_rejected(
        self,
    ) -> None:
        """Guard historical v38 IDs and controls independently of active maps."""
        record = "TT1A/g0/r0"
        missing = dict(self.approved)
        extra = dict(self.approved)
        control = dict(self.approved)
        del missing[record]
        extra["TT1A/g99/r99"] = "Extra"
        control[record] = control[record].replace("{CTRL:1}", "{CTRL:0}")

        with self.assertRaises(ReleaseBuildError):
            validate_checkpoint_record_ids(missing, self.approved)
        with self.assertRaises(ReleaseBuildError):
            validate_checkpoint_record_ids(extra, self.approved)
        with self.assertRaises(ReleaseBuildError):
            validate_checkpoint_records(control, self.approved)

    def test_invalid_baseline_fails_before_compiler_execution(self) -> None:
        """Reject a Japanese ROM or arbitrary input instead of falling back."""
        with self.assertRaisesRegex(ReleaseBuildError, "exact private v25"):
            build_release_images(
                b"wrong", translations_directory=ROOT, compiler_bundle=BUNDLE
            )


if __name__ == "__main__":
    unittest.main()
