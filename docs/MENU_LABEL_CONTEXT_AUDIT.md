# Contextual menu-label length audit — September 24, 2026

## Purpose

Fixed menu labels should be judged in the menu where they actually appear, not
against a global character limit. A label is worth editorial review when it is
both long in absolute terms and substantially longer than the median choice in
one of its recovered primary-menu descriptors.

The audit in `work/tools/audit_menu_geometry.py` reports a contextual outlier
when a label is at least 12 visible glyphs and at least 5 glyphs longer than the
median label in that actual menu context. This is a review signal, not an
automatic shortening rule.

## Change accepted

### TT1B — `Magnifying glass` -> `Magnifier`

The museum/parlor object menu is:

- Room
- Newspaper
- Magnifier
- Picture
- Old man
- Body

`Magnifying glass` was 16 glyphs against a seven-glyph median and visually
dominated an otherwise compact object list. `Magnifier` names the same object
naturally and unambiguously in this context, so the shorter form is preferred.

Scenario prose remains free to say `magnifying glass`; this is only the compact
menu label.

## Reviewed outliers retained

The remaining contextual outliers are intentional because shortening would
remove useful gameplay meaning or produce worse English.

| Bank | Label | Context | Decision |
| --- | --- | --- | --- |
| TT3A | Blue writing | Bench / Man / Simon / Red writing / Blue writing / Notes | Keep. The game uses two separate thin sheets: Simon's writing is blue, the bottle sheet is red, and overlaying their complementary text reveals the Rebecca message. |
| TT6B | Stick out tongue | Glare / Shout / Stick out tongue / Wink | Keep. Shorter forms such as `Tongue out` are less natural as an action command. |
| TT4 | Medicinal herb | Medicinal herb / Olive / Oil / Bell | Keep. `Herb` would blur a generic medical item with the chapter's named herbs. |
| TT4 | Wrap with cloth | Apply oil / Wrap with cloth / Leave it | Keep. The object of the treatment action is meaningful; `Wrap` is underspecified. |
| T25 | Outside window | Room / Desk / Outside window / Drawer | Keep. This is specifically the navigation target outside the window, not the window itself. |

## Policy

1. Preserve complete, natural English unless a label is a real visual outlier in
   its actual menu.
2. Prefer a shorter synonym only when it preserves the same gameplay referent or
   action without ambiguity.
3. Do not pad strings with spaces or change renderer geometry to compensate for
   one lexical outlier.
4. Treat the contextual-outlier report as an editorial review queue, not a
   mechanical failure condition.
5. Re-run the menu-geometry audit whenever fixed labels change.
