"""CLI contracts for incremental verification and layout inspection."""

from __future__ import annotations

import unittest
from pathlib import Path

from time_twist.cli_parser import build_parser


class IncrementalCliTests(unittest.TestCase):
    """Keep public incremental verification commands stable."""

    def test_build_verify_only_does_not_require_output(self) -> None:
        """Allow read-only verification without an output path."""
        args = build_parser().parse_args(
            ["build", "candidate.fds", "--verify-only"]
        )
        self.assertEqual(args.image, Path("candidate.fds"))
        self.assertTrue(args.verify_only)
        self.assertIsNone(args.output)

    def test_build_output_mode_remains_available(self) -> None:
        """Keep the ordinary incremental candidate-build syntax."""
        args = build_parser().parse_args(
            ["build", "candidate.fds", "--output", "next.fds"]
        )
        self.assertEqual(args.output, Path("next.fds"))
        self.assertFalse(args.verify_only)

    def test_inspect_layout_command_is_registered(self) -> None:
        """Expose read-only placement/capacity inspection."""
        args = build_parser().parse_args(
            ["inspect-layout", "candidate.fds"]
        )
        self.assertEqual(args.command, "inspect-layout")
        self.assertEqual(args.image, Path("candidate.fds"))


if __name__ == "__main__":
    unittest.main()
