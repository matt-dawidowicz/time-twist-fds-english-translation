"""Shared structural and English validation for scenario translation data."""

from __future__ import annotations

from .english import (
    EnglishTextError,
    control_values,
    encode_english,
    validate_display_width,
)
from .textcodec import PackedSymbol

PERSONALITY_QUESTION_IDS = frozenset(
    f"TT1A/g0/r{record}" for record in range(6, 21)
)

# Experimental full-natural-dialogue overlay.  The locked translation maps keep
# the currently promoted compact wording, while this release-critical module can
# substitute the seven reviewed unconstrained lines for an isolated playtest
# branch.  Each tuple is (promoted compact text, experimental natural text).
# The expanded strings preserve the source control sequence exactly and use
# invisible spaces to make every native 24-column automatic wrap land between
# words.
FULL_NATURAL_DIALOGUE_OVERRIDES: dict[str, tuple[str, str]] = {
    "TT1B/g0/r1": (
        "Blue sky--how long gone?",
        "When was the last time  I saw a blue sky?",
    ),
    "TT1B/g0/r28": (
        "Me: Um...{CTRL:1}Girl: Seen everything?{CTRL:0}Me: No...",
        "Me: Um...{CTRL:1}Girl: Have you seen all the exhibits?{CTRL:0}Me: No...",
    ),
    "TT1B/g0/r31": (
        "Me: You mean you're...{CTRL:0}Devil: You might say so.{CTRL:0}"
        "Me: G-g-g-gah!{CTRL:6}Devil: My telepathy{CTRL:4}"
        "finally paid off.{CTRL:4}Me: ........",
        "Me: No way... You mean  you're...{CTRL:0}"
        "Devil: I am what you    might call... a devil.{CTRL:0}"
        "Me: G-g-g-gah!{CTRL:6}"
        "Devil: All that patient telepathy{CTRL:4}"
        "has finally paid off.{CTRL:4}Me: ...",
    ),
    "TT1B/g1/r14": (
        "Me: You're busty. Heh...{CTRL:1}Girl: Eek!",
        "Me: You've got quite a  pair... heh-heh.{CTRL:1}Girl: Eek!",
    ),
    "TT1B/g2/r5": (
        "...: I've lived here{CTRL:0}40 years! I won't leave!{CTRL:2}"
        "Me: I'm no land shark.{CTRL:6}...: Oh! Sorry.",
        "Resident: I've lived in this house{CTRL:0}"
        "for forty years! I'm    not leaving now!{CTRL:2}"
        "Me: I'm not one of      those developers trying "
        "to force you out.{CTRL:6}"
        "Resident: Oh! I-I'm     terribly sorry.",
    ),
    "TT3A/g2/r30": (
        "A fragment of the note.{CTRL:0}Blue ink:{CTRL:0}"
        "'... 4 km southwest...'{CTRL:0}'... Rebecca'",
        "One fragment of the     note.{CTRL:0}In blue ink:{CTRL:0}"
        '"...4 km southwest..."{CTRL:0}"...Rebecca."',
    ),
    "TT6A/g0/r13": (
        "Joseph: My betrothed,{CTRL:0}Mary, may be with child.{CTRL:2}"
        "I swear before God,{CTRL:0}I never even held her{CTRL:4}hand!{CTRL:3}"
        "Mary has no idea how.{CTRL:4}Can that be true?{CTRL:3}"
        "Me: Hee-haw...{CTRL:3}Joseph: I trust nothing!{CTRL:4}"
        "Our betrothal is over!",
        "Joseph: The truth is...{CTRL:0}"
        "my betrothed, Mary,     seems to be with child.{CTRL:2}"
        "But I swear to God,{CTRL:0}"
        "I've never so much as   held her{CTRL:4}hand!{CTRL:3}"
        "Mary says she has no    idea how it happened...{CTRL:4}"
        "but can that possibly   be true?{CTRL:3}Me: Hee-haw...{CTRL:3}"
        "Joseph: I can't believe in anything anymore!{CTRL:4}"
        "The engagement is off!",
    ),
}

FULL_NATURAL_DIALOGUE_IDS = frozenset(FULL_NATURAL_DIALOGUE_OVERRIDES)
WRAPPED_SCENARIO_IDS = PERSONALITY_QUESTION_IDS | FULL_NATURAL_DIALOGUE_IDS


def scenario_record_id(
    bank_name: str, group_index: int, record_index: int
) -> str:
    """Return the canonical stable ID for one scenario record."""
    return f"{bank_name}/g{group_index}/r{record_index}"


def experimental_natural_dialogue(record_id: str, english: object) -> object:
    """Substitute one reviewed natural line only for its promoted compact form.

    The equality guard keeps this experiment from silently overriding an
    explicit caller edit.  A normal release build still supplies the promoted
    translation-map value, so the playtest branch receives the natural text.
    """
    override = FULL_NATURAL_DIALOGUE_OVERRIDES.get(record_id)
    if override is None:
        return english
    compact, natural = override
    return natural if english == compact else english


def encode_validated_english(
    record_id: str,
    english: object,
    japanese: str,
) -> tuple[PackedSymbol, ...]:
    """Validate one nonempty translation and return its native symbols.

    The shared policy covers type/nonempty checks, exact control-tag order,
    renderer width, explicitly reviewed wrapping exceptions, and glyph
    encodability.  On this experimental branch, seven promoted compact lines
    are replaced by their reviewed full-natural counterparts before validation.
    Callers add only their command-specific error context.
    """
    english = experimental_natural_dialogue(record_id, english)
    if not isinstance(english, str) or not english:
        raise EnglishTextError("English translation must be a nonempty string")
    if control_values(english) != control_values(japanese):
        raise EnglishTextError("control tags changed")
    validate_display_width(
        english,
        allow_wrap=record_id in WRAPPED_SCENARIO_IDS,
    )
    return encode_english(english)
