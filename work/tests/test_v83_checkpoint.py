"""Guard v83 checkpoint provenance and the separated shared responses."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from time_twist.release_metadata import ReleaseBuildError
from time_twist.v50_finalizer import FINAL_RELEASE_SHA256
from time_twist.v83_checkpoint import (
    ADDED_RECORD_IDS,
    DELTA_SHA256,
    V83_SHA256,
    load_v83_delta,
    promote_release_to_v83,
    validate_v83_sources,
)

ROOT = Path(__file__).resolve().parents[2]


class V83CheckpointTests(unittest.TestCase):
    """Reject unknown inputs and preserve route-specific translation records."""

    def test_delta_binds_both_reviewed_images(self) -> None:
        """Keep source, delta, and target hashes independently checked."""
        data = load_v83_delta()
        self.assertEqual(data[:4], b"TTD1")
        self.assertEqual(data[4:36].hex().upper(), FINAL_RELEASE_SHA256)
        self.assertEqual(data[36:68].hex().upper(), V83_SHA256)
        self.assertEqual(
            hashlib.sha256(data).hexdigest().upper(), DELTA_SHA256
        )
        with self.assertRaisesRegex(ReleaseBuildError, "source SHA-256"):
            promote_release_to_v83(b"unrecognized ROM")

    def test_explicit_recovery_root_overrides_installed_module_path(self) -> None:
        """Resolve checkpoint artifacts from the selected checkout."""
        with patch(
            "time_twist.v83_checkpoint.RECOVERY_ROOT",
            ROOT / "missing",
        ):
            data = load_v83_delta(
                recovery_root=ROOT / "recovery" / "v83"
            )
        self.assertEqual(hashlib.sha256(data).hexdigest().upper(), DELTA_SHA256)

    def test_missing_and_corrupt_patch_parts_are_rejected(self) -> None:
        """Never silently accept a partial or altered checkpoint artifact."""
        with (
            patch("time_twist.v83_checkpoint.RECOVERY_ROOT", ROOT / "missing"),
            self.assertRaises(ReleaseBuildError),
        ):
            load_v83_delta()
        with (
            patch("pathlib.Path.read_text", return_value="not base64!"),
            self.assertRaises(ReleaseBuildError),
        ):
            load_v83_delta()

    def test_source_audit_rejects_unrecognized_image(self) -> None:
        """Reject an unknown image before attempting scenario text validation."""
        with self.assertRaises(ReleaseBuildError):
            validate_v83_sources(b"wrong", ROOT / "work/translations")

    def test_response_records_do_not_change_unrelated_referents(self) -> None:
        """Separate Belle and empty actions from shared male/exclamation text."""
        records = {
            key: value
            for path in (ROOT / "work/translations").glob("*.json")
            for key, value in json.loads(path.read_text()).items()
        }
        self.assertEqual(records["TT5/g0/r9"], "He's unconscious.")
        self.assertEqual(records["TT5/g4/r0"], "She's unconscious.")
        self.assertEqual(
            records["T22/g1/r16"], "They watch with bated{CTRL:0}breath."
        )
        self.assertEqual(
            {key: records[key] for key in ADDED_RECORD_IDS},
            {
                "T22/g1/r26": "Use what?",
                "T25/g2/r12": "Use what?",
                "TT2/g5/r9": "Use what?",
                "TT4/g5/r23": "Take what?",
                "TT5/g3/r27": "Take what?",
                "TT5/g4/r0": "She's unconscious.",
            },
        )


if __name__ == "__main__":
    unittest.main()
