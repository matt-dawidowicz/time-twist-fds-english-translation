"""Source-backed measurements shared by review tooling and tests.

These values are historical scenario-region evidence, not runtime
configuration. Current release fit is always recomputed from the
canonical translation maps before a build is accepted.
"""

PATCH_FOOTPRINT_RESULTS = {
    "TT1A": {"used": 1656, "capacity": 1669, "remaining": 13},
    "TT1B": {"used": 4022, "capacity": 4026, "remaining": 4},
    "TT2": {"used": 3834, "capacity": 3847, "remaining": 13},
    "T22": {"used": 1801, "capacity": 1812, "remaining": 11},
    "TT3A": {"used": 3733, "capacity": 3741, "remaining": 8},
    "TT3B": {"used": 1837, "capacity": 1840, "remaining": 3},
    "TT4": {"used": 4738, "capacity": 4741, "remaining": 3},
    "TT5": {"used": 3693, "capacity": 3702, "remaining": 9},
    "T25": {"used": 2363, "capacity": 2374, "remaining": 11},
    "TT6A": {"used": 2823, "capacity": 2833, "remaining": 10},
    "TT6B": {"used": 2298, "capacity": 2336, "remaining": 38},
    "TT6C": {"used": 3520, "capacity": 3536, "remaining": 16},
    "TT6D": {"used": 323, "capacity": 332, "remaining": 9},
}
