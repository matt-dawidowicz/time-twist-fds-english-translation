"""Fixed-address menu and choice table declarations.

The patching algorithms remain in :mod:`time_twist.ui`; this module holds
the reviewed per-bank data they consume.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Bank-specific fixed-address record tables
# ---------------------------------------------------------------------------

# These are the canonical full-word menu labels. The release builder jointly
# packs the 11 large menu tables with dialogue, regenerates page pointers, and
# preserves each overlay's fixed suffix. TT1A's direct-address records below
# retain their individual byte lengths.

# TT1A keeps the blood-type choices in a fixed-address record table before
# its normal scenario groups. NOV2 directly references the fourth record at
# $A465, so the fixed-address slots retain their original byte lengths. Keep
# the semantic labels unpadded: the native and entropy builders pad the slot
# bytes separately. Semantic trailing spaces are visible to NOV2's dynamic
# selection-width capture and incorrectly push the right arrow outward.
TT1A_BLOOD_TYPE_PATCHES = (
    (0x025B, bytes.fromhex("0F 71 F4"), "A"),
    (0x025E, bytes.fromhex("CD 6E 3E 80"), "B"),
    (0x0262, bytes.fromhex("13 71 F4"), "O"),
    (0x0265, bytes.fromhex("0F 71 9A DC 7D"), "AB"),
)

# The month selector immediately follows the blood-type table.  It first
# offers January-June plus a July-December branch, then a second set for
# July-December.  Each label is chosen to fill exactly its original record.
TT1A_MONTH_PATCHES = (
    (0x026A, bytes.fromhex("D7 61 51 FA"), "Jan"),
    (0x026E, bytes.fromhex("D7 E1 51 FA"), "Feb"),
    (0x0272, bytes.fromhex("D8 61 51 FA"), "Mar"),
    (0x0276, bytes.fromhex("D8 E1 51 FA"), "Apr"),
    (0x027A, bytes.fromhex("D9 61 51 FA"), "May"),
    (0x027E, bytes.fromhex("D9 E1 51 FA"), "Jun"),
    (0x0282, bytes.fromhex("DA 61 51 04 90 BE 80"), "Jul-Dec"),
    (0x0289, bytes.fromhex("DA 61 51 FA"), "Jul"),
    (0x028D, bytes.fromhex("DA E1 51 FA"), "Aug"),
    (0x0291, bytes.fromhex("DB 61 51 FA"), "Sep"),
    (0x0295, bytes.fromhex("D7 6D F0 A8 FD"), "Oct"),
    (0x029A, bytes.fromhex("D7 6B B0 A8 FD"), "Nov"),
    (0x029F, bytes.fromhex("D7 6B F0 A8 FD"), "Dec"),
)

# The final fixed records before TT1A's first scenario group are its
# confirmation choices.  The English strings exactly retain their original
# packed lengths, so the scenario table that begins at $A4C2 does not move.
TT1A_CONFIRMATION_PATCHES = (
    (0x02A4, bytes.fromhex("04 33 3E 80"), "Yes"),
    (0x02A8, bytes.fromhex("63 71 F4"), "No"),
)

# TT1B's 53 museum command, object, and interaction labels precede the
# scenario groups. These source offsets/hash guard the original table; the
# English release repacks its records and updates the recovered page pointers.
TT1B_FIXED_TEXT_START_OFFSET = 0x09F7
TT1B_FIXED_TEXT_END_OFFSET = 0x0AC5
TT1B_FIXED_TEXT_SOURCE_SHA256 = (
    "AF6969B469081B6992DF4893FCE6308ABB51896B5D2DAAD49AF0B23500E5FD4F"
)
TT1B_FIXED_TEXT_RECORDS = (
    "Look",
    "Talk",
    "Move",
    "Sky",
    "Area",
    "Museum",
    "Sign",
    "Body",
    "East",
    "West",
    "Use",
    "Attack",
    "Poke",
    "Walk",
    "Jar",
    "Exhibit",
    "Room",
    "Girl",
    "Monster",
    "Charm",
    "Hold hands",
    "Hug",
    "Smile at",
    "Compliment",
    "Shout",
    "Eyes",
    "Nose",
    "Ears",
    "Chest",
    "Man",
    "Map",
    "North",
    "House",
    "Nameplate",
    "Intercom",
    "Newspaper",
    "Magnifying glass",
    "Picture",
    "Old man",
    "Outside",
    "Ground",
    "Forward",
    "Back",
    "Simon",
    "Deeper",
    "Listen",
    "Church",
    "Priest",
    "Congregant",
    "Sermon",
    "Devil",
    "Time Belt",
    "Run away",
)

# TT2's menu table contains commands, inventory/object labels, choice verbs,
# and twenty history-quiz answers. Records are selected by page plus index;
# English records may change length when the page pointers are regenerated.
TT2_FIXED_TEXT_START_OFFSET = 0x0BB6
TT2_FIXED_TEXT_END_OFFSET = 0x0CD8
TT2_FIXED_TEXT_SOURCE_SHA256 = (
    "FD956CF1D33EDA350549FC3079729458A1B8D20EFAF2D6883361E5FD8C3F0B9E"
)
TT2_DICTIONARY_POINTER_OFFSET = 0x0016
TT2_LOAD_ADDRESS = 0xA200
FIXED_UI_DICTIONARY_ENTRY_COUNT = 31
TT2_DICTIONARY_ENTRIES = FIXED_UI_DICTIONARY_ENTRY_COUNT
TT2_FIXED_TEXT_RECORDS = (
    "Look",
    "Talk",
    "Take",
    "Use",
    "Listen",
    "Smell",
    "Move",
    "Room",
    "Pierre",
    "Body",
    "Glass",
    "Wine",
    "Empty bottle",
    "Drink",
    "Robe",
    "Key",
    "Outside",
    "Info",
    "Walk",
    "Area",
    "Signboard",
    "Posted sign",
    "Bottles",
    "Wear",
    "Take off",
    "Old Man",
    "Damascus",
    "Jerusalem",
    "Crimea",
    "Hundred Years",
    "Pacific Ocean",
    "Merchants",
    "Citizens",
    "Entertainers",
    "Criminals",
    "Guide",
    "Zoid",
    "Geld",
    "Guild",
    "Oido",
    "da Vinci",
    "Lacoste",
    "De Palma",
    "De Niro",
    "Danube",
    "U Thant",
    "Tools",
    "Offer",
    "Toolbox",
    "Chino",
    "Gordo",
    "Wait",
    "No",
    "Lugot",
    "Accept",
    "Refuse",
    "Wine",
    "Official",
    "Onlookers",
    "Building",
    "Jail",
    "Town",
    "Jailer",
    "Women",
    "Basement",
    "Bishop",
    "Jeanne",
    "Rope",
    "Candle",
    "Cell",
)

# T22's command and object-name table uses the same page-indexed relocation
# as TT2. Source offsets and the hash below guard the Japanese input table.
T22_FIXED_TEXT_START_OFFSET = 0x0729
T22_FIXED_TEXT_END_OFFSET = 0x07A6
T22_FIXED_TEXT_SOURCE_SHA256 = (
    "AF59D34E1084B43CC754BB24582D85FE7B085C0C478E65A2DD21F0ACA1D7D44F"
)
T22_FIXED_TEXT_RECORDS = (
    "Look",
    "Talk",
    "Use",
    "Listen",
    "Move",
    "Baron",
    "Jailer",
    "Women",
    "Robe",
    "Key",
    "Pact",
    "Take off",
    "Basement",
    "Outside",
    "Take",
    "Push",
    "Room",
    "Chino",
    "Wall",
    "Rope",
    "Hole",
    "Cell",
    "Open",
    "Box",
    "Scrap paper",
    "Back",
    "Scaffold",
    "Jeanne",
    "Bishop",
    "Lugot",
    "Onlookers",
    "Prison",
    "Walk",
)

# TT3A's menu table contains POW-camp, town, resistance, and quiz labels.
TT3A_FIXED_TEXT_START_OFFSET = 0x0A04
TT3A_FIXED_TEXT_END_OFFSET = 0x0BAC
TT3A_FIXED_TEXT_SOURCE_SHA256 = (
    "7CBFBAF8AEAE3831B8F9BB0E4A53BF746171BF554F8B7E6ADE7DBFE0AF47DCBA"
)
TT3A_FIXED_TEXT_RECORDS = (
    "Look",
    "Talk",
    "Take",
    "Use",
    "Move",
    "Area",
    "Body",
    "Pocket",
    "Pliers",
    "Outside fence",
    "Hit",
    "Info",
    "Room ",
    "Wall",
    "Charm",
    "Outside",
    "Push",
    "Enter",
    "Walk",
    "Floor",
    "Nick",
    "Ralph",
    "Frankie",
    "Stove",
    "Bed",
    "Shower room",
    "Sheet",
    "Clothes",
    "Mattress",
    "Tile",
    "Pebble",
    "Shower",
    "Wear",
    "Tunnel",
    "Soil",
    "Front",
    "Back",
    "Soldier",
    "Yes",
    "No",
    "Gun",
    "Throw",
    "Wire fence",
    "Woods",
    "Bench",
    "Man",
    "Simon",
    "Red writing",
    "Blue writing",
    "Notes",
    "Password",
    "Greeting",
    "Crumple",
    "Burn",
    "Tear",
    "Combine",
    "North",
    "East",
    "West",
    "Watermill",
    "Fountain",
    "Bottle",
    "Saw it",
    "Didn't see",
    "South",
    "Take out",
    "Paper",
    "Back",
    "Trash can",
    "Old man",
    "Gestapo",
    "Ghetto",
    "Residence",
    "Résistance",
    "Register",
    "Nazi boat",
    "Black",
    "Banana boat",
    "Gabin",
    "Truffaut",
    "Delon",
    "Belmondo",
    "Philippe",
    "Mont",
    "Patton",
    "Eisenhower",
    "Roosevelt",
    "Churchill",
    "MacA.",
    "Train",
    "Soldier",
    "Streetlamp",
    "Broom",
    "Woman",
)

# TT3B's menu table has the Forest Horder border scenes, vehicle chase, and
# later Germany-section labels.
TT3B_FIXED_TEXT_START_OFFSET = 0x0A32
TT3B_FIXED_TEXT_END_OFFSET = 0x0ACA
TT3B_FIXED_TEXT_SOURCE_SHA256 = (
    "F6A80FDE7793067B60219559175B2FC6098881D9289FAEF97054C6BB466D3CF0"
)
TT3B_FIXED_TEXT_RECORDS = (
    "Look",
    "Tal