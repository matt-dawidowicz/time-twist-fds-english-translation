"""Retired v64 builder.

v64 is unsafe and intentionally cannot be rebuilt from this entry point.
Use build_v65_month_menu.py instead.
"""

raise SystemExit(
    "v64 is withdrawn: its $0433 width relocation overlaps live $043B state "
    "and its historical $821B helper can bypass the modern $22xx PPU address "
    "setup. Use work/tools/build_v65_month_menu.py."
)
