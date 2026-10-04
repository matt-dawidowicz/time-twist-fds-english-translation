"""Regression tests for the safe twelve-month Fortune Teller selector."""

from __future__ import annotations

import unittest

from time_twist.tt1a_month_menu import (
    MENU_WIDTH_WORK_RAM_ADDRESS,
    MENU_WIDTH_WORK_RAM_END,
    MONTH_DESCRIPTOR,
    MONTH_GRID,
    MONTH_LABELS,
    month_text_ppu_address,
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

    def test_width_array_uses_gap_before_event_flags(self) -> None:
        self.assertEqual(MENU_WIDTH_WORK_RAM_ADDRESS, 0x0470)
        self.assertEqual(MENU_WIDTH_WORK_RAM_END, 0x047B)
        self.assertGreater(MENU_WIDTH_WORK_RAM_ADDRESS, 0x046F)
        self.assertLess(MENU_WIDTH_WORK_RAM_END, 0x0480)
        self.assertFalse(
            MENU_WIDTH_WORK_RAM_ADDRESS <= 0x043B <= MENU_WIDTH_WORK_RAM_END
        )

    def test_all_month_text_addresses_are_nametable_addresses(self) -> None:
        self.assertEqual(
            tuple(month_text_ppu_address(slot) for slot in range(12)),
            (
                0x2245, 0x2285, 0x22C5, 0x2305,
                0x224E, 0x228E, 0x22CE, 0x230E,
                0x2257, 0x2297, 0x22D7, 0x2317,
            ),
        )
        for slot in range(12):
            self.assertGreaterEqual(month_text_ppu_address(slot), 0x2000)
            self.assertLessEqual(month_text_ppu_address(slot), 0x23BF)

    def test_native_navigation_is_bounded_for_all_twelve_slots(self) -> None:
        for slot in range(12):
            for direction in ("up", "down", "left", "right"):
                target = twelve_month_navigation(slot, direction)
                self.assertGreaterEqual(target, 0)
                self.assertLess(target, 12)

    def test_native_up_down_are_linear_with_wrap(self) -> None:
        self.assertEqual(twelve_month_navigation(0, "up"), 11)
        self.assertEqual(twelve_month_navigation(11, "down"), 0)
        for slot in range(11):
            self.assertEqual(twelve_month_navigation(slot, "down"), slot + 1)
        for slot in range(1, 12):
            self.assertEqual(twelve_month_navigation(slot, "up"), slot - 1)

    def test_native_left_right_move_four_slots(self) -> None:
        for slot in range(12):
            left = twelve_month_navigation(slot, "left")
            right = twelve_month_navigation(slot, "right")
            self.assertEqual(left, slot - 4 if slot >= 4 else slot)
            self.assertEqual(right, slot + 4 if slot + 4 < 12 else slot)


if __name__ == "__main__":
    unittest.main()
