"""Validate fixed-menu labels against the recovered variable-width renderer.

This module deliberately does not reuse the dialogue ``DISPLAY_COLUMNS`` rule.
Menus have their own staging and two-column geometry.  The production renderer
stages up to 18 glyphs for one label and places the second column from the
corresponding first-column width.  Call-site pairing remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass

MENU_MAX_STAGED_GLYPHS = 18
MENU_MAX_PAIRED_GLYPHS = 20
LEFT_LEADING_CURSOR_X = 0x40
LEFT_TEXT_X = 0x48
RIGHT_TEXT_BASE_AFTER_LEFT_X = 0x58
RIGHTMOST_SAFE_CURSOR_X = 0xF8
GLYPH_PIXELS = 8


class MenuGeometryError(ValueError):
    """Report a label or two-column pairing that exceeds proven menu geometry."""


@dataclass(frozen=True)
class MenuPairGeometry:
    """Describe the recovered screen coordinates for one two-column menu row."""

    left_glyphs: int
    right_glyphs: int
    left_text_x: int
    right_text_x: int
    right_leading_cursor_x: int
    right_trailing_cursor_x: int


def menu_glyph_count(text: str) -> int:
    """Return visible glyph count for a fixed-menu label.

    Fixed menu labels are plain visible strings, not dialogue/control markup.
    Reject control tags here so a future caller cannot accidentally apply a
    dialogue-layout convention to this renderer.
    """
    if not text:
        raise MenuGeometryError("menu label must not be empty")
    if "{CTRL:" in text:
        raise MenuGeometryError(
            "menu labels cannot contain dialogue control tags"
        )
    return len(text)


def validate_menu_label(text: str) -> int:
    """Validate one label against the recovered 18-glyph staging span."""
    glyphs = menu_glyph_count(text)
    if glyphs > MENU_MAX_STAGED_GLYPHS:
        raise MenuGeometryError(
            f"menu label {text!r} uses {glyphs} glyphs; "
            f"recovered staging supports {MENU_MAX_STAGED_GLYPHS}"
        )
    return glyphs


def menu_pair_geometry(left: str, right: str) -> MenuPairGeometry:
    """Return and validate dynamic two-column coordinates for one paired row.

    Historical live-tested code placed the right text two tiles after the end
    of the left text.  Under that recovered layout the right trailing cursor is
    ``0x58 + 8 * (left_glyphs + right_glyphs)``.  ``0xF8`` is the conservative
    last safe cursor coordinate before the 256-pixel wrap.
    """
    left_glyphs = validate_menu_label(left)
    right_glyphs = validate_menu_label(right)
    combined = left_glyphs + right_glyphs
    right_text_x = RIGHT_TEXT_BASE_AFTER_LEFT_X + GLYPH_PIXELS * left_glyphs
    right_leading = right_text_x - GLYPH_PIXELS
    right_trailing = right_text_x + GLYPH_PIXELS * right_glyphs
    if (
        combined > MENU_MAX_PAIRED_GLYPHS
        or right_trailing > RIGHTMOST_SAFE_CURSOR_X
    ):
        raise MenuGeometryError(
            f"paired menu labels {left!r} / {right!r} use {combined} glyphs; "
            f"right trailing cursor would be x={right_trailing} (safe <= "
            f"{RIGHTMOST_SAFE_CURSOR_X})"
        )
    return MenuPairGeometry(
        left_glyphs=left_glyphs,
        right_glyphs=right_glyphs,
        left_text_x=LEFT_TEXT_X,
        right_text_x=right_text_x,
        right_leading_cursor_x=right_leading,
        right_trailing_cursor_x=right_trailing,
    )


def primary_menu_descriptors(
    data: bytes,
    *,
    load_address: int = 0xA200,
) -> tuple[tuple[int, ...], ...]:
    """Decode every recovered `$A210` primary-menu descriptor in one overlay.

    Header words `$A210/$A212` delimit a compact table. Each descriptor is one
    count byte followed by that many one-based fixed-label record indices. This
    is the same representation consumed by NOV2 `$9529/$951B/$9561` before
    runtime predicate filtering compacts the visible choice array.
    """
    if len(data) < 0x14:
        raise MenuGeometryError(
            "overlay is too short for menu header pointers"
        )
    start = int.from_bytes(data[0x10:0x12], "little") - load_address
    end = int.from_bytes(data[0x12:0x14], "little") - load_address
    if not 0 <= start <= end <= len(data):
        raise MenuGeometryError(
            f"primary-menu table ${start + load_address:04X}-"
            f"${end + load_address:04X} is outside overlay"
        )
    descriptors: list[tuple[int, ...]] = []
    cursor = start
    while cursor < end:
        count = data[cursor]
        record_end = cursor + 1 + count
        if count == 0 or record_end > end:
            raise MenuGeometryError(
                f"malformed primary-menu descriptor at file offset 0x{cursor:04X}"
            )
        descriptors.append(tuple(data[cursor + 1 : record_end]))
        cursor = record_end
    return tuple(descriptors)


def possible_compacted_pairs(
    descriptor: tuple[int, ...],
) -> tuple[tuple[int, int], ...]:
    """Return every two-column pair possible after order-preserving filtering.

    NOV2 `$9803` compacts surviving choices in order. The visible grid pairs
    slots 0/4, 1/5, 2/6, and 3/7. Enumerating all subsets through eight visible
    choices deliberately over-approximates runtime predicates, so a clean audit
    proves width safety without having to assume a particular story-flag state.
    """
    from itertools import combinations

    pairs: set[tuple[int, int]] = set()
    count = len(descriptor)
    for visible_count in range(5, min(8, count) + 1):
        for positions in combinations(range(count), visible_count):
            visible = tuple(descriptor[index] for index in positions)
            for slot in range(visible_count - 4):
                pairs.add((visible[slot], visible[slot + 4]))
    return tuple(sorted(pairs))


def validate_descriptor_geometry(
    labels: tuple[str, ...],
    descriptors: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, int], ...]:
    """Validate label coverage and every possible compacted two-column pair."""
    referenced: set[int] = set()
    pairs: set[tuple[int, int]] = set()
    for descriptor_index, descriptor in enumerate(descriptors):
        for record_index in descriptor:
            if not 1 <= record_index <= len(labels):
                raise MenuGeometryError(
                    f"descriptor {descriptor_index} references label {record_index}, "
                    f"outside 1..{len(labels)}"
                )
            referenced.add(record_index)
            validate_menu_label(labels[record_index - 1])
        for left_index, right_index in possible_compacted_pairs(descriptor):
            menu_pair_geometry(labels[left_index - 1], labels[right_index - 1])
            pairs.add((left_index, right_index))
    expected = set(range(1, len(labels) + 1))
    if referenced != expected:
        missing = sorted(expected - referenced)
        raise MenuGeometryError(
            f"primary-menu descriptors do not cover {len(missing)} labels: "
            f"{missing[:8]}"
        )
    return tuple(sorted(pairs))
