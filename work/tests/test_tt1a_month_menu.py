"""Regression tests for the v64 twelve-month Fortune Teller selector."""

from __future__ import annotations

import unittest

from time_twist.tt1a_month_menu import (
    MONTH_DESCRIPTOR,
    MONTH_GRID,
    MONTH_LABELS,
    twelve_month_navigation,
)


class TwelveMonthFortuneMenuTests(unittest.TestCase):
    def test_month_descriptor_contains_all_real_month_ids_once(self) -> None:
        self.assertEqual(
            MONTH_DESCRIPTOR,
            (5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17),
        )
        self.assertEqual(len(MONTH_DESCRIPTOR), 12)
        self.assertEqual(len(set(MONTH_DESCRIPTOR)), 12)
        self.assertNotIn(11, MONTH_DESCRIPTOR)

    def test_visible_grid_is_the_intended_four_by_three_layout(self) -> None:
        self.assertEqual(
            MONTH_GRID,
            (
                ("Jan", "May", "Sep"),
                ("Feb", "Jun", "Oct"),
                ("Mar", "Jul", "Nov"),
                ("Apr", "Aug", "Dec"),
            ),
        )
        self.assertEqual(
            MONTH_LABELS,
            (
                "Jan", "Feb", "Mar", "Apr",
                "May", "Jun", "Jul", "Aug",
                "Sep", "Oct", "Nov", "Dec",
            ),
        )

    def test_navigation_is_bounded_for_all_twelve_slots(self) -> None:
        for slot in range(12):
            for direction in ("up", "down", "left", "right"):
                target = twelve_month_navigation(slot, direction)
                self.assertGreaterEqual(target, 0)
                self.assertLess(target, 12)

    def test_vertical_navigation_wraps_inside_each_column(self) -> None:
        for column in range(3):
            base = column * 4
            self.assertEqual(twelve_month_navigation(base, "up"), base + 3)
            self.assertEqual(
                twelve_month_navigation(base + 3, "down"),
                base,
            )

    def test_horizontal_navigation_preserves_row(self) -> None:
        for slot in range(12):
            for direction in ("left", "right"):
                target = twelve_month_navigation(slot, direction)
                self.assertEqual(target & 3, slot & 3)


if __name__ == "__main__":
    unittest.main()
