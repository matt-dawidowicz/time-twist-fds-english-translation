"""Fixture-free tests for the Mesen FDS clean-state preflight."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import check_mesen_fds_state


class MesenFdsStateTests(unittest.TestCase):
    """Protect runtime certification from stale filename-matched IPS state."""

    def test_clean_state_accepts_candidate_without_matching_ips(self) -> None:
        """Allow certification when no active sidecar matches the candidate."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "Time Twist candidate.fds"
            saves = root / "Saves"
            candidate.write_bytes(b"FDS")
            saves.mkdir()
            (saves / "Different candidate.ips").write_bytes(b"PATCH")

            self.assertEqual(
                check_mesen_fds_state.find_active_sidecars(candidate, saves),
                (),
            )
            check_mesen_fds_state.check_clean_state(candidate, saves)

    def test_matching_ips_is_rejected_recursively(self) -> None:
        """Detect Mesen sidecars even when the Saves tree has subdirectories."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "Time Twist candidate.fds"
            saves = root / "Saves"
            nested = saves / "FDS"
            candidate.write_bytes(b"FDS")
            nested.mkdir(parents=True)
            sidecar = nested / "Time Twist candidate.ips"
            sidecar.write_bytes(b"PATCH")

            self.assertEqual(
                check_mesen_fds_state.find_active_sidecars(candidate, saves),
                (sidecar,),
            )
            with self.assertRaisesRegex(
                check_mesen_fds_state.MesenFdsStateError,
                "active Mesen FDS write overlay",
            ):
                check_mesen_fds_state.check_clean_state(candidate, saves)

    def test_matching_is_case_insensitive(self) -> None:
        """Model Windows filename matching used by the normal Mesen workflow."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "Time Twist Candidate.fds"
            saves = root / "Saves"
            candidate.write_bytes(b"FDS")
            saves.mkdir()
            sidecar = saves / "time twist candidate.IPS"
            sidecar.write_bytes(b"PATCH")

            self.assertEqual(
                check_mesen_fds_state.find_active_sidecars(candidate, saves),
                (sidecar,),
            )

    def test_backup_suffix_is_not_treated_as_active(self) -> None:
        """Permit quarantined evidence such as .ips.stale-backup files."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = root / "Time Twist candidate.fds"
            saves = root / "Saves"
            candidate.write_bytes(b"FDS")
            saves.mkdir()
            (saves / "Time Twist candidate.ips.stale-backup").write_bytes(
                b"PATCH"
            )

            check_mesen_fds_state.check_clean_state(candidate, saves)


if __name__ == "__main__":
    unittest.main()
