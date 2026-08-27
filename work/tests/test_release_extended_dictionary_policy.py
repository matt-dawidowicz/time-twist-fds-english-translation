"""Regression coverage for the all-bank extended dictionary release policy."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from time_twist.release import build_scenario_bank
from time_twist.textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT


class ReleaseExtendedDictionaryPolicyTests(unittest.TestCase):
    """Keep non-relocated playable banks free of the old 31-entry ceiling."""

    def test_tt6d_accepts_dictionary_entry_32(self) -> None:
        """Prove the canonical non-relocated path permits more than 31 entries."""
        fake_bank = SimpleNamespace(
            group_addresses=(0xA240,),
            load_address=0xA200,
            dictionary_end_offset=0xA0,
            records=(object(),),
        )
        groups = (((),),)
        dictionary = tuple(() for _ in range(32))
        compressed = groups

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch(
                    "time_twist.release.source_dictionary_reference_floor",
                    return_value=0,
                ),
                patch(
                    "time_twist.release.parse_scenario_bank",
                    return_value=fake_bank,
                ),
                patch(
                    "time_twist.release._load_translation_map", return_value={}
                ),
                patch(
                    "time_twist.release._encoded_groups", return_value=groups
                ),
                patch(
                    "time_twist.release.required_dictionary_entries",
                    return_value=(),
                ),
                patch(
                    "time_twist.release.compress_english_groups",
                    return_value=(compressed, dictionary),
                ) as compress,
                patch(
                    "time_twist.release.rebuild_scenario_bank",
                    return_value=b"rebuilt",
                ) as rebuild,
                patch("time_twist.release.packed_size", return_value=1),
            ):
                result = build_scenario_bank(
                    bytes(0xA0),
                    "TT6D",
                    temporary_directory=root,
                    translations_directory=root,
                )

        self.assertEqual(result.dictionary_entries, 32)
        self.assertEqual(
            compress.call_args.kwargs["maximum_entries"],
            EXTENDED_DICTIONARY_ENTRY_COUNT,
        )
        self.assertEqual(
            rebuild.call_args.kwargs["maximum_dictionary_entries"],
            EXTENDED_DICTIONARY_ENTRY_COUNT,
        )


if __name__ == "__main__":
    unittest.main()
