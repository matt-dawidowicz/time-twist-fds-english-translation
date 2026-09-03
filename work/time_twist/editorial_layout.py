"""Generate safe English presentation layouts without rewriting prose.

The translation remains the editorial authority. This module only decides
where a verified presentation row advance may replace an ordinary inter-word
space so every visible row fits Time Twist's 24-tile dialogue width.

Layout generation is deliberately separate from compression. A caller may
score the returned alternatives against an entire scenario bank, because a
break changes dictionary opportunities on both sides of the control token.
"""

from __future__ import annotations

from functools import cache

from .english import DISPLAY_COLUMNS, EnglishTextError, validate_display_width
from .scenario_validation import PRESENTATION_LINE_CONTROL

DEFAULT_MAX_LAYOUT_VARIANTS = 4096


def _control_tag(value: int) -> str:
    """Return one canonical textual control token."""
    return f"{{CTRL:{value}}}"


def presentation_break_variants(
    text: str,
    *,
    columns: int = DISPLAY_COLUMNS,
    control: int = PRESENTATION_LINE_CONTROL,
    max_variants: int = DEFAULT_MAX_LAYOUT_VARIANTS,
) -> tuple[str, ...]:
    """Return minimum-row word-wrap layouts for one natural sentence.

    Args:
        text: Natural English containing visible characters and spaces only;
            existing control tags are rejected so semantic controls cannot be
            moved accidentally by this helper.
        columns: Maximum visible width of one renderer row.
        control: Verified presentation row-advance control to insert in place
            of selected spaces.
        max_variants: Safety cap for pathological sets of equally minimal
            layouts.

    Returns:
        The unmodified sentence alone when it already fits one row. Otherwise,
        deterministically ordered layouts that use the fewest possible rows,
        preserve every visible word, and replace selected single spaces with
        the presentation control.

    Raises:
        EnglishTextError: If input already contains a control tag, contains
            repeated/leading/trailing spaces, no legal wrapping exists, or the
            set of equally minimal layouts exceeds ``max_variants``.
        ValueError: If ``columns`` or ``max_variants`` is not positive.

    Extra rows are not compression candidates. Once a sentence can be shown in
    N safe rows, an N+1-row layout adds another control and another literal
    candidate boundary without solving an additional display constraint. This
    keeps whole-bank scoring focused on editorially useful alternatives instead
    of combinatorially many gratuitous line breaks.

    This routine does not choose the cheapest minimum-row layout. Compression-
    aware callers should score the alternatives after inserting the record into
    its complete bank so record alignment and dictionary interactions are
    measured exactly.
    """
    if columns < 1:
        raise ValueError("columns must be positive")
    if max_variants < 1:
        raise ValueError("max_variants must be positive")
    if "{CTRL:" in text:
        raise EnglishTextError(
            "presentation layout input must not contain existing controls"
        )
    if not text or text.strip() != text or "  " in text:
        raise EnglishTextError(
            "presentation layout input must use single internal spaces"
        )
    if len(text) <= columns:
        validate_display_width(text, columns=columns)
        return (text,)

    words = tuple(text.split(" "))
    if any(len(word) > columns for word in words):
        raise EnglishTextError(
            "a word is wider than the renderer and cannot be safely wrapped"
        )
    break_tag = _control_tag(control)

    @cache
    def minimum_rows_from(index: int) -> int:
        """Return the fewest legal rows needed from one word onward."""
        if index == len(words):
            return 0
        best = len(words) + 1
        width = 0
        for end in range(index, len(words)):
            word = words[end]
            width += len(word) if end == index else len(word) + 1
            if width > columns:
                break
            best = min(best, 1 + minimum_rows_from(end + 1))
        return best

    minimum_rows = minimum_rows_from(0)
    if minimum_rows > len(words):
        raise EnglishTextError("no legal presentation layout exists")

    @cache
    def layouts_from(index: int) -> tuple[tuple[str, ...], ...]:
        """Return only minimum-row line tuples beginning at one word index."""
        if index == len(words):
            return ((),)
        target_rows = minimum_rows_from(index)
        layouts: list[tuple[str, ...]] = []
        width = 0
        for end in range(index, len(words)):
            word = words[end]
            width += len(word) if end == index else len(word) + 1
            if width > columns:
                break
            if 1 + minimum_rows_from(end + 1) != target_rows:
                continue
            line = " ".join(words[index : end + 1])
            for suffix in layouts_from(end + 1):
                layouts.append((line, *suffix))
                if len(layouts) > max_variants:
                    raise EnglishTextError(
                        "presentation layout search exceeded variant limit"
                    )
        return tuple(layouts)

    line_layouts = layouts_from(0)
    if not line_layouts:
        raise EnglishTextError("no legal presentation layout exists")

    variants = tuple(
        break_tag.join(lines)
        for lines in sorted(line_layouts, key=lambda lines: lines)
    )
    for variant in variants:
        validate_display_width(variant, columns=columns)
    return variants
