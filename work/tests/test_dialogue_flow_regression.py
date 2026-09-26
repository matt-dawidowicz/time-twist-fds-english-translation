"""Regression coverage for compiled dialogue-row ownership assumptions."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from time_twist.dialogue_flow import trace_dialogue

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRANSLATION_ROOT = PROJECT_ROOT / "work" / "translations"


class DialogueFlowRegressionTests(unittest.TestCase):
    """Keep every canonical scenario record inside the four-row renderer."""

    def test_all_canonical_records_are_geometry_safe(self) -> None:
        """Reject row crossings, fixed-row re-entry, and staging overwrites."""
        checked = 0
        for path in sorted(TRANSLATION_ROOT.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for record_id, text in payload.items():
                with self.subTest(record=record_id):
                    trace_dialogue(record_id, text)
                checked += 1
        self.assertEqual(checked, 1299)



    def test_no_unintended_premature_scroll_controls(self) -> None:
        """Reject scroll controls that manufacture blank dialogue rows."""
        allowed = {("TT4/g4/r20", 3)}
        found: set[tuple[str, int]] = set()

        for path in sorted(TRANSLATION_ROOT.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            for record_id, text in payload.items():
                row = 1
                visible_on_current_row = False
                parts = [
                    part
                    for part in re.split(
                        r"(\{CTRL:[0-7]\})", text
                    )
                    if part
                ]
                for part in parts:
                    match = re.fullmatch(
                        r"\{CTRL:([0-7])\}", part
                    )
                    if match is None:
                        if part.strip():
                            visible_on_current_row = True
                        continue

                    control = int(match.group(1))
                    if (
                        control in {3, 4}
                        and visible_on_current_row
                        and row < 4
                    ):
                        found.add((record_id, control))

                    if control in {0, 7}:
                        row = min(4, row + 1)
                    elif control == 1:
                        row = 2
                    elif control == 2:
                        row = 3
                    elif control in {3, 4, 6}:
                        row = 4
                    visible_on_current_row = False

        self.assertEqual(found, allowed)

    def test_corrected_scroll_boundaries_are_locked(self) -> None:
        """Keep the five playtest-reviewed pagination repairs intact."""
        expected = {
            "T22": {
                "T22/g0/r11": (
                    "Baron: Th-this is…!{CTRL:1}Jailer: Definitely the"
                    "{CTRL:0}bishop's handwriting!{CTRL:0}Baron: I knew it…"
                    "{CTRL:3}Jailer: We have to save{CTRL:4}that girl!"
                    "{CTRL:4}Baron: Right!"
                ),
            },
            "TT3A": {
                "TT3A/g2/r29": (
                    "He's holding a paper.{CTRL:1}Simon: A child just gave"
                    "{CTRL:0}me this. He said a{CTRL:0}stranger asked him to"
                    "{CTRL:4}deliver it.{CTRL:3}I take the paper.{CTRL:3}"
                    "The writing is in blue{CTRL:4}ink."
                ),
            },
            "TT3B": {
                "TT3B/g1/r22": (
                    "Schmidt: We'll be across{CTRL:0}the border soon."
                    "{CTRL:2}Cougar: I can't remember{CTRL:0}"
                    "a thing. How did I end{CTRL:4}up here…?{CTRL:3}"
                    "Simon: You must have{CTRL:4}taken quite a blow to"
                    "{CTRL:4}the head.{CTRL:3}Schmidt: But we saw"
                    "{CTRL:4}something terrible.{CTRL:3}"
                    "Cougar: It might change{CTRL:4}the way I look at my"
                    "{CTRL:4}whole life.{CTRL:3}Simon: Indeed…"
                ),
                "TT3B/g1/r23": (
                    "Hitler: Please, take me{CTRL:0}with you!{CTRL:2}"
                    "Devil: No. You have more{CTRL:0}evil to do here. Our"
                    "{CTRL:4}pact ends next year.{CTRL:3}"
                    "Hitler: Next year?!{CTRL:3}Devil: April 30, 1945."
                    "{CTRL:3}That is the day you die.{CTRL:4}"
                    "Remember it well.{CTRL:3}Hitler: …{CTRL:3}"
                    "Devil: I'll see you in{CTRL:4}Hell."
                ),
            },
            "TT4": {
                "TT4/g3/r19": (
                    "Soldier: The pain's much{CTRL:0}better… Take this as"
                    "{CTRL:0}thanks. I picked it up{CTRL:0}"
                    "on the battlefield.{CTRL:3}He pulls a small bell"
                    "{CTRL:4}from his robe.{CTRL:3}Soldier: They say an"
                    "{CTRL:4}Egyptian pharaoh used it{CTRL:4}"
                    "to ward off evil. It's{CTRL:4}the Warding Bell."
                ),
            },
        }
        for bank, records in expected.items():
            payload = json.loads(
                (TRANSLATION_ROOT / f"{bank}.json").read_text(encoding="utf-8")
            )
            for record_id, text in records.items():
                with self.subTest(record=record_id):
                    self.assertEqual(payload[record_id], text)
                    trace_dialogue(record_id, text)

    def test_shared_tt3a_departure_narration_is_gender_neutral(self) -> None:
        """Keep the shared male/female park branch narration context-safe."""
        payload = json.loads(
            (TRANSLATION_ROOT / "TT3A.json").read_text(encoding="utf-8")
        )
        text = payload["TT3A/g3/r23"]
        self.assertEqual(text, "They dash off at once.")
        self.assertNotRegex(text, r"\\b(?:he|she|his|her)\\b")
        trace_dialogue("TT3A/g3/r23", text)

    def test_plural_men_line_wraps_within_24_columns(self) -> None:
        """Lock the TT6C plural pronoun fix to a safe physical-row break."""
        payload = json.loads(
            (TRANSLATION_ROOT / "TT6C.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            payload["TT6C/g0/r29"],
            "They gaze solemnly at{CTRL:0}the baby.",
        )
        trace_dialogue("TT6C/g0/r29", payload["TT6C/g0/r29"])


if __name__ == "__main__":
    unittest.main()
