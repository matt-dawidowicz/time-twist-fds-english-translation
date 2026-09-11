from pathlib import Path

MODULE = Path("work/time_twist/production_translation.py")
TEST = Path("work/tests/test_production_translation.py")
PLACEHOLDER = Path("work/production_overrides/TT1A_pagination_policy.json")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


module = MODULE.read_text(encoding="utf-8")
module = replace_once(
    module,
    "def _semantic_template_parts(template: str) -> tuple[list[str], list[int]]:\n",
    "def _semantic_template_parts(\n"
    "    template: str,\n"
    "    *,\n"
    "    demoted_ctrl2_ordinals: frozenset[int] = frozenset(),\n"
    ") -> tuple[list[str], list[int]]:\n",
    "semantic-template signature",
)
module = replace_once(
    module,
    "    collapsed = [segments[0]]\n"
    "    kept_controls: list[int] = []\n"
    "    for index, control in enumerate(controls):\n"
    "        keep = (\n"
    "            control in SEMANTIC_CONTROLS\n"
    "            or index < first_visible\n"
    "            or index >= last_visible\n"
    "        )\n",
    "    collapsed = [segments[0]]\n"
    "    kept_controls: list[int] = []\n"
    "    ctrl2_ordinal = -1\n"
    "    for index, control in enumerate(controls):\n"
    "        if control == 2:\n"
    "            ctrl2_ordinal += 1\n"
    "        demoted_ctrl2 = (\n"
    "            control == 2 and ctrl2_ordinal in demoted_ctrl2_ordinals\n"
    "        )\n"
    "        keep = (\n"
    "            (control in SEMANTIC_CONTROLS and not demoted_ctrl2)\n"
    "            or index < first_visible\n"
    "            or index >= last_visible\n"
    "        )\n",
    "semantic-template body",
)
module = replace_once(
    module,
    "def _semantic_anchor_ordinals(template: str) -> frozenset[int]:\n",
    "def _semantic_anchor_ordinals(\n"
    "    template: str,\n"
    "    *,\n"
    "    demoted_ctrl2_ordinals: frozenset[int] = frozenset(),\n"
    ") -> frozenset[int]:\n",
    "anchor signature",
)
module = replace_once(
    module,
    "    segments, controls = _template_parts(template)\n"
    "    semantic_ordinal = -1\n"
    "    anchored: set[int] = set()\n"
    "    for index, control in enumerate(controls):\n"
    "        if control not in SEMANTIC_CONTROLS:\n"
    "            continue\n"
    "        semantic_ordinal += 1\n",
    "    segments, controls = _template_parts(template)\n"
    "    semantic_ordinal = -1\n"
    "    ctrl2_ordinal = -1\n"
    "    anchored: set[int] = set()\n"
    "    for index, control in enumerate(controls):\n"
    "        if control == 2:\n"
    "            ctrl2_ordinal += 1\n"
    "            if ctrl2_ordinal in demoted_ctrl2_ordinals:\n"
    "                continue\n"
    "        if control not in SEMANTIC_CONTROLS:\n"
    "            continue\n"
    "        semantic_ordinal += 1\n",
    "anchor body",
)
start = module.index("def validate_production_control_sequence(")
end = module.index("\n\ndef _layout_chunk_at_cursor", start)
module = module[:start] + '''def validate_production_control_sequence(source: str, production: str) -> None:
    """Preserve native semantics while allowing safe CTRL:2 pagination removal.

    Controls 1, 3, and 6 remain mandatory. CTRL:2 is a mixed page/timing
    control: production layout may omit it when it interrupts continuous prose,
    but may never invent one or move surviving semantic controls out of source
    order.
    """
    _source_segments, source_controls = _semantic_template_parts(source)
    _production_segments, production_controls = _template_parts(production)
    required = [
        value for value in source_controls if value in SEMANTIC_CONTROLS
    ]
    actual_semantic = [
        value for value in production_controls if value in SEMANTIC_CONTROLS
    ]

    source_index = 0
    omitted: list[int] = []
    for actual in actual_semantic:
        while source_index < len(required) and required[source_index] != actual:
            omitted.append(required[source_index])
            source_index += 1
        if source_index >= len(required):
            raise ProductionTranslationError(
                "production layout introduced or reordered semantic controls"
            )
        source_index += 1
    omitted.extend(required[source_index:])
    if any(value != 2 for value in omitted):
        raise ProductionTranslationError(
            "production layout lost or reordered one or more mandatory "
            "semantic controls"
        )

    unexpected = [
        value
        for value in production_controls
        if value not in SEMANTIC_CONTROLS | INSERTABLE_LAYOUT_CONTROLS
    ]
    if unexpected:
        raise ProductionTranslationError(
            f"production layout introduced unsupported controls: {unexpected}"
        )
''' + module[end:]
helper = '''def _weak_non_speaker_ctrl2_ordinals(text: str) -> frozenset[int]:
    """Find CTRL:2 page breaks that interrupt continuous English prose.

    A weak break falls inside a sentence or phrase rather than after normal
    terminal punctuation. If the following chunk begins with a speaker label,
    the control remains semantic even when the preceding phrase is incomplete.
    """
    segments, controls = _template_parts(text)
    visible_before = ""
    ctrl2_ordinal = -1
    demoted: set[int] = set()
    for index, control in enumerate(controls):
        visible_before += segments[index]
        if control != 2:
            continue
        ctrl2_ordinal += 1
        after = segments[index + 1]
        before_words = visible_before.split()
        combined_words = (visible_before + " " + after).split()
        end_word = len(before_words)
        next_visible = after.lstrip()
        speaker_spans = _speaker_label_spans(next_visible)
        starts_new_speaker = bool(speaker_spans and speaker_spans[0][0] == 0)
        if (
            not starts_new_speaker
            and not _is_strong_semantic_break(combined_words, end_word)
        ):
            demoted.add(ctrl2_ordinal)
    return frozenset(demoted)


def _layout_semantic_review(
    reviewed: str,
    template: str,
    *,
    demoted_ctrl2_ordinals: frozenset[int] = frozenset(),
) -> tuple[list[str], list[int]]:
    """Lay out prose against native semantics with selected page breaks demoted."""
    template_segments, controls = _semantic_template_parts(
        template, demoted_ctrl2_ordinals=demoted_ctrl2_ordinals
    )
    laid_out = _split_visible_text(
        reviewed,
        template_segments,
        controls,
        anchored_semantic_ordinals=_semantic_anchor_ordinals(
            template, demoted_ctrl2_ordinals=demoted_ctrl2_ordinals
        ),
    )
    return laid_out, controls


'''
module = replace_once(
    module,
    "def layout_review_text(record_id: str, reviewed: str, template: str) -> str:\n",
    helper + "def layout_review_text(record_id: str, reviewed: str, template: str) -> str:\n",
    "layout helper insertion",
)
module = replace_once(
    module,
    "    reviewed_controls = [int(value) for value in CONTROL_RE.findall(reviewed)]\n",
    "    reviewed_controls = [int(value) for value in CONTROL_RE.findall(reviewed)]\n"
    "    demoted_ctrl2_ordinals = frozenset()\n",
    "layout demotion initialization",
)
module = replace_once(
    module,
    "    else:\n"
    "        template_segments, controls = _semantic_template_parts(template)\n"
    "        laid_out = _split_visible_text(\n"
    "            reviewed,\n"
    "            template_segments,\n"
    "            controls,\n"
    "            anchored_semantic_ordinals=_semantic_anchor_ordinals(template),\n"
    "        )\n",
    "    else:\n"
    "        laid_out, controls = _layout_semantic_review(reviewed, template)\n"
    "        initial = laid_out[0]\n"
    "        for value, segment in zip(controls, laid_out[1:], strict=True):\n"
    "            initial += f\"{{CTRL:{value}}}{segment}\"\n"
    "        demoted_ctrl2_ordinals = _weak_non_speaker_ctrl2_ordinals(initial)\n"
    "        if demoted_ctrl2_ordinals:\n"
    "            laid_out, controls = _layout_semantic_review(\n"
    "                reviewed,\n"
    "                template,\n"
    "                demoted_ctrl2_ordinals=demoted_ctrl2_ordinals,\n"
    "            )\n",
    "layout semantic branch",
)
MODULE.write_text(module, encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = replace_once(
    test,
    "Newscaster: Late last{CTRL:0}night, Dr. Simon—the{CTRL:2}",
    "Newscaster: Late last{CTRL:0}night, Dr. Simon—the{CTRL:0}",
    "newscaster expectation",
)
needle = "    def test_greedy_wrap_uses_maximum_available_width(self) -> None:\n"
insert = '''    def test_weak_ctrl2_does_not_force_half_empty_box(self) -> None:
        """Fill four rows before paging when CTRL:2 cuts continuous prose."""
        template = (
            "Cautious, methodical.{CTRL:0}Rarely fail, but can{CTRL:2}"
            "seem a bit ordinary.{CTRL:0}Hardworking, principled{CTRL:3}"
            "Stubborn scholar type.{CTRL:4}You care till worn out.{CTRL:4}"
            "Romantic, but awkward."
        )
        reviewed = (
            "You're cautious and methodical, so you rarely fail, but you can "
            "come across as ordinary. Principled and diligent, you're a "
            "serious, stubborn scholar type. You worry so much about other "
            "people that you wear yourself out. You're awkward in love, but "
            "a romantic at heart."
        )

        output = layout_review_text("TT1A/g0/r24", reviewed, template)

        self.assertNotIn("{CTRL:2}", output)
        self.assertTrue(
            output.startswith(
                "You're cautious and{CTRL:0}methodical, so you{CTRL:0}"
                "rarely fail, but you can{CTRL:0}come across as ordinary."
            )
        )
        validate_renderer_buffer_layout(output)
        validate_production_control_sequence(template, output)

    def test_strong_ctrl2_pause_is_still_preserved(self) -> None:
        """Keep a genuine phrase boundary even when English pagination is greedy."""
        template = (
            "Maradul Barao Garadura{CTRL:0}{CTRL:2}"
            "Chant it over and over.{CTRL:3}"
            "Maradul Barao Garadura{CTRL:4}Maradul Barao Garadura!"
        )
        reviewed = (
            "Maradul Barao Garadura… Chant it again and again. "
            "Maradul Barao Garadura… Maradul Barao Garadura!"
        )

        output = layout_review_text("TT1A/g0/r29", reviewed, template)

        self.assertIn("Garadura…{CTRL:2}Chant", output)
        validate_production_control_sequence(template, output)

'''
test = replace_once(test, needle, insert + needle, "pagination regression tests")
TEST.write_text(test, encoding="utf-8")

if PLACEHOLDER.exists():
    PLACEHOLDER.unlink()
