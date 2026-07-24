"""Patch fixed-address UI text and small verified program fragments.

Normal dialogue is rebuilt through :mod:`time_twist.scenario`; this module owns
text that is referenced directly by 6502 code or stored in separate overlays.
Most replacements must preserve a complete table and every individual packed
record boundary.  Short code patches compare exact source bytes before
writing, and larger tables use SHA-256 revision guards.

Public ``patched_*`` functions are pure: they accept one extracted FDS file as
``bytes`` and return replacement bytes or raise :class:`UiPatchError`.
"""

from __future__ import annotations

import hashlib

from .compression import symbol_bit_length
from .english import encode_english
from .font import render_glyph
from .textcodec import (
    BitReader,
    PackedSymbol,
    SymbolKind,
    decode_symbol,
    pack_records,
    split_records,
)


# ---------------------------------------------------------------------------
# Shared NOV2/NOV4 prompts and input behavior
# ---------------------------------------------------------------------------

START_PROMPT_OFFSET = 0x2651
NOV4_START_PROMPT_OFFSET = 0x0095
ORIGINAL_START_PROMPT = bytes.fromhex("28 12 F5 A2 CD F4")
ENGLISH_START_PROMPT = pack_records([encode_english("START ")])

# NOV2 composes its disk-change message from five independently packed
# records: game half, requested side, and the instruction line.  Keeping each
# replacement exactly the same size preserves the surrounding program data.
DISK_PROMPT_PATCHES = (
    (0x260D, bytes.fromhex("C6 DB A3 B5 8F A0"), "PART1 "),
    (0x2613, bytes.fromhex("24 27 2D 63 E8"), "PART2"),
    (0x2618, bytes.fromhex("F0 1E E2 1B 6C FA"), "{CTRL:0}SIDEA"),
    (0x261E, bytes.fromhex("F1 9A DC 43 6D 9F 40"), "{CTRL:0}SIDE B"),
    (
        0x2625,
        bytes.fromhex("F1 E0 DD 52 65 A4 3E 3C A0 7E 80"),
        "{CTRL:0}{CTRL:0}INSERT NOW",
    ),
)

# NOV2 also has a separate two-record warning for an inserted side that does
# not match the part/side currently requested by the game.  It was missed by
# the normal disk-prompt patch because it lives later in the program and is
# only visible after a bad swap.  With the English font installed, the
# untouched Japanese records rendered as the gibberish seen in playtesting.
WRONG_DISK_PATCHES = (
    (
        0x26E8,
        bytes.fromhex("43 0B AA 3F 7F 92 D3 18 3E 17 E8"),
        "WRONG DISK!",
    ),
    (
        0x26F3,
        bytes.fromhex("F1 BF DF EF F7 E6 EA 93 2A 94 81 78 CF A0"),
        "{CTRL:0}TRY ANOTHER SIDE",
    ),
)
WAIT_PROMPT_OFFSET = 0x25D9
ORIGINAL_WAIT_PROMPT = bytes.fromhex(
    "2F 33 30 FE 37 FB F1 1E 40 7C 79 40 FD"
)
ENGLISH_WAIT_PROMPT = pack_records([encode_english("PLEASE WAIT... ")])

# ---------------------------------------------------------------------------
# Kouhen direct-boot guard (SON-KOUH)
# ---------------------------------------------------------------------------

# Kouhen's 739-byte startup program is used only when the second game is
# booted directly.  It draws a Japanese warning from 21 private 1bpp tiles and
# an RLE-compressed nametable fragment; none of that text passes through the
# normal scenario decoder.  Preserve the program, vectors, addresses, and
# exact file size while replacing only those two assets.  The English wording
# describes the required action more clearly than a literal "load from the
# first-part disk": Kouhen must inherit live state from Zenpen and is not a
# standalone boot disk.
KOUHEN_BOOT_GUARD_SOURCE_SHA256 = (
    "EE32CD2462B224A55B875694D8C34A362754A92630DCDB1A40451AA331C43847"
)
KOUHEN_BOOT_GUARD_SIZE = 0x02E3
KOUHEN_BOOT_GUARD_TILEMAP_OFFSET = 0x01EC
KOUHEN_BOOT_GUARD_TILEMAP_END = 0x0227
KOUHEN_BOOT_GUARD_CHR_OFFSET = 0x0233
KOUHEN_BOOT_GUARD_TILE_COUNT = 21
KOUHEN_BOOT_GUARD_BLANK_TILE = 0x14
KOUHEN_BOOT_GUARD_PPU_START = 0x20D0
KOUHEN_BOOT_GUARD_DECODED_SIZE = 414
KOUHEN_BOOT_GUARD_LINES = (
    (11, "PLEASE START WITH"),
    (13, "PART 1"),
)
KOUHEN_BOOT_GUARD_TILE_CHARACTERS = (
    "P", "L", "E", "A", "S", "T", "R", "W", "I", "H", "1",
)

# NOV2 normally fills unused menu-buffer cells with $AC.  The menu renderer
# treats $AC as transparent, so an opaque common-space tile is still needed
# there.  Dialogue is handled separately below: making all 24 dialogue tail
# cells opaque caused the typewriter cadence to process them as silent
# characters.
NOV2_BLANK_TILE = 0xC0
NOV2_OPAQUE_CLEAR_PATCHES = (
    (0x345B, 0xAC, NOV2_BLANK_TILE, "menu choice"),
)

# NOV2's scroll uploader must retain this indexed load.  It copies the valid
# bottom dialogue row to the nametable before the text buffer shifts.  An
# earlier clear attempt replaced the load with ``LDA #$C0 / NOP``; that erased
# complete sentences at CTRL:3/CTRL:4 transitions (including the chant and the
# narration line immediately after it).  Keep the bytes here as a regression
# guard, not as a patch target.  Dialogue tails remain transparent $AC so they
# are skipped without producing a row of invisible typewriter sounds.
NOV2_DIALOGUE_ROW_COPY = (
    0x2571,
    bytes.fromhex("B9 D7 87"),
)

# The menu input dispatcher enters its B-button action at $99DC.  The
# original code correctly returns when no Back destination was saved, but a
# one-choice menu can save its own address as that destination.  Pressing B
# then closes and redraws the same menu, making the top border slide through
# the START label.
#
# NOV2 has no expandable space: it occupies $6000-$A1FF, immediately below
# NOV4.  Reuse the twelve bytes at $6A2E-$6A39 by redirecting three duplicate
# state-table JMPs to identical handlers that already exist.  The replacement
# B action keeps the original $9C=0 guard at $99DC intact, then:
#
# * returns through the existing RTS at $6A93 when the menu has one choice;
# * performs the original action-4/state-$22 transition for larger menus.
#
# Thus the post-title START menu ignores B without changing Back/Cancel on
# normal multi-choice menus.
NOV2_SINGLE_CHOICE_B_PATCHES = (
    (
        0x0A0D,
        bytes.fromhex("31 6A 34 6A"),
        bytes.fromhex("40 6A 40 6A"),
        "duplicate state handlers 1-2",
    ),
    (
        0x0A13,
        bytes.fromhex("34 6A"),
        bytes.fromhex("40 6A"),
        "duplicate state handler 4",
    ),
    (
        0x0A17,
        bytes.fromhex("37 6A"),
        bytes.fromhex("73 6B"),
        "duplicate state handler 6",
    ),
    (
        0x0A25,
        bytes.fromhex("F0 07"),
        bytes.fromhex("F0 19"),
        "shared state-return branch",
    ),
    (
        0x0A2E,
        bytes.fromhex("4C 01 61 4C 01 61 4C 01 61 4C DB 89"),
        bytes.fromhex("A4 98 88 F0 60 A9 04 85 A1 4C B8 7D"),
        "single-choice B guard helper",
    ),
    (
        0x39E1,
        bytes.fromhex("A9 04 85 A1 A9 22 4C 09 61"),
        bytes.fromhex("4C 2E 6A EA EA EA EA EA EA"),
        "B action detour",
    ),
)

# ---------------------------------------------------------------------------
# Bank-specific fixed-address record tables
# ---------------------------------------------------------------------------

# TT1A keeps the blood-type choices in a fixed-address record table before
# its normal scenario groups.  NOV2 directly references the fourth record at
# $A465, so every replacement must retain its individual byte length.  The
# trailing spaces are invisible but preserve all four original addresses.
TT1A_BLOOD_TYPE_PATCHES = (
    (0x025B, bytes.fromhex("0F 71 F4"), "A "),
    (0x025E, bytes.fromhex("CD 6E 3E 80"), "B  "),
    (0x0262, bytes.fromhex("13 71 F4"), "O "),
    (0x0265, bytes.fromhex("0F 71 9A DC 7D"), "AB   "),
)

# The month selector immediately follows the blood-type table.  It first
# offers January-June plus a July-December branch, then a second set for
# July-December.  Each label is chosen to fill exactly its original record.
TT1A_MONTH_PATCHES = (
    (0x026A, bytes.fromhex("D7 61 51 FA"), "JAN"),
    (0x026E, bytes.fromhex("D7 E1 51 FA"), "FEB"),
    (0x0272, bytes.fromhex("D8 61 51 FA"), "MAR"),
    (0x0276, bytes.fromhex("D8 E1 51 FA"), "APR"),
    (0x027A, bytes.fromhex("D9 61 51 FA"), "MAY"),
    (0x027E, bytes.fromhex("D9 E1 51 FA"), "JUN"),
    (0x0282, bytes.fromhex("DA 61 51 04 90 BE 80"), "JUL-DEC"),
    (0x0289, bytes.fromhex("DA 61 51 FA"), "JUL"),
    (0x028D, bytes.fromhex("DA E1 51 FA"), "AUG"),
    (0x0291, bytes.fromhex("DB 61 51 FA"), "SEP"),
    (0x0295, bytes.fromhex("D7 6D F0 A8 FD"), "OCT  "),
    (0x029A, bytes.fromhex("D7 6B B0 A8 FD"), "NOV  "),
    (0x029F, bytes.fromhex("D7 6B F0 A8 FD"), "DEC  "),
)

# The final fixed records before TT1A's first scenario group are its
# confirmation choices.  The English strings exactly retain their original
# packed lengths, so the scenario table that begins at $A4C2 does not move.
TT1A_CONFIRMATION_PATCHES = (
    (0x02A4, bytes.fromhex("04 33 3E 80"), "YES"),
    (0x02A8, bytes.fromhex("63 71 F4"), "NO"),
)

# TT1B begins the museum investigation and keeps its command, object, and
# interaction labels in a fixed-address table before the normal scenario
# groups.  Several two-byte records can only hold readable English through a
# dictionary reference, so the scenario rebuild reserves the entries below.
# All 53 replacement records retain their original individual byte lengths.
TT1B_FIXED_TEXT_START_OFFSET = 0x09F7
TT1B_FIXED_TEXT_END_OFFSET = 0x0AC5
TT1B_FIXED_TEXT_SOURCE_SHA256 = (
    "AF6969B469081B6992DF4893FCE6308ABB51896B5D2DAAD49AF0B23500E5FD4F"
)
TT1B_REQUIRED_DICTIONARY_TEXT = (
    "LOOK", "TALK", "MUSEUM", "BODY", "EYES", "PICTURE", "SIMON",
    "ASK", "MEMBER", "DEVIL", "NOSE", "EARS", "SKY", "SIGN", "CHEST",
    "HOUSE", "CHURCH", "PRIEST", "EST", "ROUND",
)
TT1B_FIXED_TEXT_RECORDS = (
    "LOOK", "TALK", "MOVE", "SKY", "AROUND", "MUSEUM", "SIGN", "BODY",
    "EAST", "WEST", "USE", "HIT", "POKE", "WLK", "PT", "EXH", "ROOM",
    "GIRL", "MON", "SPELL", "HOLD", "HUG", "SMILE", "PRA", "SH", "EYES",
    "NOSE", "EARS", "CHEST", "MAN", "MP", "N", "HOUSE", "PLATE", "ICOM",
    "NEWS", "LENS", "PICTURE", "OLD", "FRT", "GROUND", "FWD", "BCK", "SIMON",
    "R", "ASK", "CHURCH", "PRIEST", "MEMBER", "SERMON", "DEVIL", "BELT",
    "RUN",
)

# TT2 has a second packed-text table outside its scenario groups.  It contains
# the command menu, inventory/object labels, choice verbs, and the twenty
# history-quiz answers.  The game references individual records by absolute
# address, so every replacement must retain its own original byte length.
TT2_FIXED_TEXT_START_OFFSET = 0x0BB6
TT2_FIXED_TEXT_END_OFFSET = 0x0CD8
TT2_FIXED_TEXT_SOURCE_SHA256 = (
    "FD956CF1D33EDA350549FC3079729458A1B8D20EFAF2D6883361E5FD8C3F0B9E"
)
TT2_DICTIONARY_POINTER_OFFSET = 0x0016
TT2_LOAD_ADDRESS = 0xA200
TT2_DICTIONARY_ENTRIES = 31
TT2_FIXED_TEXT_RECORDS = (
    "SE",
    "SAY",
    "GT",
    "USE",
    "AS",
    "SN",
    "GO",
    "IN",
    "PIER",
    "BOD",
    "GLS",
    "WINE",
    "EMPTY",
    "DR",
    "RB",
    "KY",
    "OUT",
    "DATA",
    "GO",
    "AREA",
    "SIGN",
    "POST",
    "BT",
    "ON",
    "OF",
    "MAN",
    "DAM",
    "JERUS",
    "CRI",
    "100",
    "PAC",
    "MER",
    "COM",
    "ACT",
    "CRK",
    "GDE",
    "ZOI",
    "GEL",
    "GLD",
    "OID",
    "VINCI",
    "CST",
    "PAL",
    "NIRO",
    "DAN",
    "THA",
    "TLS",
    "GO",
    "BOX",
    "Chino",
    "Gordo",
    "WT",
    "NO",
    "Lugot",
    "YES",
    "NO",
    "AL",
    "Guard",
    "CROWD",
    "BLD",
    "JAIL",
    "TN",
    "JAIL",
    "WMN",
    "CEL",
    "Bishop",
    "Jeanne",
    "ROPE",
    "LAMP",
    "CELL",
)

# T22 uses the same fixed-table mechanism for its command and object names.
# Unlike TT2, its 125-byte reservation is tight enough that the scenario
# compressor must reserve a few shared dictionary entries.  The resulting
# dialogue still has 36 bytes of headroom, while this table remains exactly
# at its original $A929-$A9A6 addresses.
T22_FIXED_TEXT_START_OFFSET = 0x0729
T22_FIXED_TEXT_END_OFFSET = 0x07A6
T22_FIXED_TEXT_SOURCE_SHA256 = (
    "AF59D34E1084B43CC754BB24582D85FE7B085C0C478E65A2DD21F0ACA1D7D44F"
)
T22_REQUIRED_DICTIONARY_TEXT = (
    "Baron",
    "Bishop",
    "Jailer",
    "Lugot",
    "Jeanne",
    "Chino",
    "SCAFFOLD",
    "CROWD",
)
T22_FIXED_TEXT_RECORDS = (
    "SE",
    "SAY",
    "USE",
    "AS",
    "GO",
    "Baron",
    "Jailer",
    "WMN",
    "RB",
    "KY",
    "PACT",
    "OF",
    "CEL",
    "OUT",
    "GT",
    "PS",
    "IN",
    "Chino",
    "WL",
    "ROPE",
    "HL",
    "JAL",
    "OPEN",
    "B",
    "PPR",
    "BCK",
    "SCAFFOLD",
    "Jeanne",
    "Bishop",
    "Lugot",
    "CROWD",
    "PRIS",
    "GO",
)

# TT3A's fixed table combines normal commands and objects with the answer
# choices for its wartime-history identity check.  The scenario itself has
# only five bytes of spare RAM, so this table uses the ordinary translated
# dictionary and compact labels to retain its exact 424-byte reservation.
TT3A_FIXED_TEXT_START_OFFSET = 0x0A04
TT3A_FIXED_TEXT_END_OFFSET = 0x0BAC
TT3A_FIXED_TEXT_SOURCE_SHA256 = (
    "7CBFBAF8AEAE3831B8F9BB0E4A53BF746171BF554F8B7E6ADE7DBFE0AF47DCBA"
)
TT3A_FIXED_TEXT_RECORDS = (
    "SE", "SAY", "GT", "USE", "GO", "AREA", "BOD", "POCKT",
    "PLI", "OUT", "HIT", "DATA", "IN", "WL", "CHARM", "OUT",
    "PS", "IN", "WLK", "FL", "Nick", "RAL", "Frankie", "STOVE",
    "BED", "SHWR", "SHT", "RB", "MATT", "TILE", "RCK", "SHWR",
    "WR", "TUN", "SL", "FR", "BCK", "SOL", "YES", "NO",
    "GUN", "TOSS", "FNC", "WD", "BCH", "MAN", "SIM", "RED",
    "BLUE", "NOTES", "PASS", "GRT", "CRM", "BRN", "TEAR", "JN",
    "N", "E", "W", "MILL", "FNT", "BT", "SW", "NO", "S", "GET",
    "PP", "BCK", "TRASH", "Old man", "Gestapo", "GHETO", "RESID",
    "RESIST", "REGSTR", "G-BT", "NAZI", "UBOAT", "BANANA", "GABN",
    "DLN", "BELMO", "PHIL", "TRUFT", "MONTY", "PTTN", "EISEN",
    "ROOSVLT", "CHRCHL", "MACARTH", "YS", "NO", "BRM", "LAMP",
    "WMN",
)

# TT3B's compact action/object table fits its original 87 bytes with one
# natural five-letter battle verb (GUARD) in place of the longer DEFEND.
TT3B_FIXED_TEXT_START_OFFSET = 0x0420
TT3B_FIXED_TEXT_END_OFFSET = 0x0477
TT3B_FIXED_TEXT_SOURCE_SHA256 = (
    "999B38FD507E1B5777D893C1009551E63FBD9153DCDB59A383BAC72313A9D8E4"
)
TT3B_FIXED_TEXT_RECORDS = (
    "SE", "SAY", "GT", "USE", "GO", "AREA", "MILL", "SIM", "WMN",
    "GUN", "CHARM", "Schmidt", "OUT", "FGT", "GUARD", "RUN", "AS",
    "RD", "TX", "Hitler", "Cougar",
)

# TT4's fixed-address table contains its command menu, medical-treatment
# choices, characters and objects, the five-sages logic puzzle, and the Greek
# history quiz.  As in the corrected Zenpen tables, every one of the 97
# records must keep its own original byte allocation.
TT4_FIXED_TEXT_START_OFFSET = 0x0CD3
TT4_FIXED_TEXT_END_OFFSET = 0x0E8B
TT4_FIXED_TEXT_SOURCE_SHA256 = (
    "B28692367059E8AB5396FF23552FDD2E2279130845EA2964F05E1F7EA19D377C"
)
TT4_FIXED_TEXT_RECORDS = (
    "SE", "SAY", "TREAT", "USE", "S", "GO", "IN", "STAT", "PRST",
    "HD", "SLAP", "PRESS", "CHIN", "KNEE", "EARS", "EYES", "NOSE",
    "PAUSE", "CONT", "O", "OIL", "BL", "GV", "EAT", "LCK", "OUT",
    "AREA", "BLD", "MRCH", "MAN", "BOD", "SL", "BY", "H", "NO",
    "TMPL", "S", "DATA", "DAR", "YTH", "UP", "DN", "LVL", "WARM",
    "COOL", "RB", "CRUSH", "PRICK", "NONE", "OIL", "WRAP", "N", "E",
    "W", "GRL", "MOM", "PLNT", "DOKU", "JIAO", "GRIND", "BOIL", "RD",
    "TK", "SOL", "SP", "SWING", "BCK", "WLK", "SOCR", "PYTH",
    "PLATO", "HEROD", "HOM", "SE", "FISH", "KID", "NIC", "POL", "ARIS",
    "IMEL", "JAKAR", "SPAR", "DAEDAL", "HERAC", "NAPOL", "GORBY", "AGAM",
    "KAN", "PARTSN", "AISNO", "PARTH", "STR", "MEL", "FIG", "RICE",
    "PEARL", "COFE",
)

# TT5's fixed-address table contains its action menu, plantation task and
# quantity choices, American-history quiz answers, livestock puzzle digits,
# bottle controls, and late-chapter locations.  The short labels keep all 113
# separately addressed records inside their original allocations.
TT5_FIXED_TEXT_START_OFFSET = 0x0AA5
TT5_FIXED_TEXT_END_OFFSET = 0x0C92
TT5_FIXED_TEXT_SOURCE_SHA256 = (
    "443013AA1921DD6EDDC01E5C38E301624D27BFDCD8B4525DE237451751E44D54"
)
TT5_FIXED_TEXT_RECORDS = (
    "SE", "SAY", "AS", "GO", "George", "BL", "MEN", "AREA", "RUIN",
    "TRACK", "N", "E", "W", "GT", "OPEN", "DATA", "ROOM", "MN",
    "WD", "DRAW", "OUT", "USE", "CT", "YS", "NO", "OK", "AGAIN",
    "SCHED", "CALL", "WATER", "COT", "ROOF", "WOOD", "WEED",
    "4B", "6B", "8B", "10B", "25", "26", "27", "28",
    "1P", "2P", "3P", "4P", "60 CM", "65 CM", "70 CM",
    "75 CM", "30M", "60M", "90M", "120M", "TM", "TRDR",
    "MARINE", "CAV", "RED", "WT", "BK", "DEWI", "STOWE", "AKINO",
    "MARY", "WHITNY", "KILAU", "ETNA", "RUSH", "OIWA", "PROJ", "GIN",
    "PLOW", "CAM", "AIR", "VCR", "BCK", "ANS", "PROB", "CW",
    "SHP", "PG", "1", "2", "3", "4", "5", "6", "7", "8", "TENS",
    "ONES", "0", "1", "2", "3", "4", "5", "6UP", "6", "7", "8", "9",
    "POUR", "END", "LARGE", "MEDIUM", "SM", "MANR", "MEYER", "CAVE",
    "STAT", "IN",
)

# T25's fixed table contains the mansion investigation and flooded-island
# action/object labels.  Each of its 42 records is referenced independently.
T25_FIXED_TEXT_START_OFFSET = 0x098A
T25_FIXED_TEXT_END_OFFSET = 0x0A43
T25_FIXED_TEXT_SOURCE_SHA256 = (
    "5B96A30331E8E68609B817B068A41F32ECDF3D8AB8A7C667D85CD3E612270DF6"
)
T25_FIXED_TEXT_RECORDS = (
    "SE", "SAY", "USE", "GO", "SK", "SOL", "COFE", "OFR", "MANR", "ROOM",
    "WGN", "MEYR", "George", "LINC", "POT", "OUT", "WD", "HALL", "AREA",
    "GUEST", "STUDY", "STAIR", "GT", "OPEN", "DK", "DRAW", "1ST", "2ND",
    "3RD", "P", "AS", "HIDE", "DOWN", "UP", "ON", "BOAT", "COY", "RV",
    "ME", "COY1", "COY2", "COY3",
)

# TT6A's fixed table contains the donkey-specific verbs and the Nazareth
# village, home, and workshop object labels.
TT6A_FIXED_TEXT_START_OFFSET = 0x0547
TT6A_FIXED_TEXT_END_OFFSET = 0x05EC
TT6A_FIXED_TEXT_SOURCE_SHA256 = (
    "BAB73CA358662FF6D05E52B84AF7327850B3D29DAD118E19EDB5F53C6A548270"
)
TT6A_FIXED_TEXT_RECORDS = (
    "SE", "AS", "SM", "HL", "GO", "AREA", "SK", "BOD", "JOS", "NOD",
    "TURN", "SL", "VL", "DR", "DATA", "ELDER", "KID", "WL", "TRGH", "RP",
    "HAY", "WATER", "HL", "R H", "L HSE", "RV", "ROOM", "MARY", "BL",
    "MILL", "BRC", "NECK", "WT", "OUT", "ON", "DOWN", "TOOL", "BD",
    "ON BD", "BK", "KIDS",
)

# TT6B's fixed table contains travel, stable-animal, history-quiz, and animal
# interaction labels.  The quiz answers use recognizable compact spellings.
TT6B_FIXED_TEXT_START_OFFSET = 0x0580
TT6B_FIXED_TEXT_END_OFFSET = 0x0687
TT6B_FIXED_TEXT_SOURCE_SHA256 = (
    "DABABCA65A7EB469E1CD0EB41B2711D9B2721FFD3C011676442C28193EE50B6B"
)
TT6B_FIXED_TEXT_RECORDS = (
    "SE", "AS", "SM", "HL", "GO", "AREA", "JOS", "MARY", "BOD", "SL",
    "GLR", "YELL", "TONG", "WINK", "SAY", "EAT", "TENT", "CML", "MEN",
    "N", "E", "W", "S", "FWD", "BCK", "ATK", "WLK", "ROOM", "TRGH", "HR",
    "SHP", "CW", "DNG", "WIS", "KNOW", "ISIS", "BAL", "JHV", "IRQ",
    "JORDN", "SYR", "EGYPT", "DAVID", "SOLO", "SAM", "JAC", "ISC",
    "SADM", "ABRAM", "SATN", "CST", "ZORO", "OIL", "HAY", "WAG", "FLEA",
    "HUG", "SMILE", "PRSE", "HOOF", "TAIL", "MANE",
)

# TT6C's fixed table contains finale actions plus answer choices drawn from
# every earlier chapter.  Compact proper-name spellings keep all 94 absolute
# record addresses unchanged.
TT6C_FIXED_TEXT_START_OFFSET = 0x08B8
TT6C_FIXED_TEXT_END_OFFSET = 0x0A4F
TT6C_FIXED_TEXT_SOURCE_SHA256 = (
    "580A8C45C48A3D468FA446DC6D4294A32D5CF78DFB76C630E63D8BB6282606BD"
)
TT6C_FIXED_TEXT_RECORDS = (
    "SE", "D", "LEAP", "GT", "JR", "SAY", "AS", "EAT", "USE", "ROOM",
    "JOS", "MARY", "B", "MEN", "MY BOD", "KSH", "BOD", "TBELT", "MOVE",
    "OPEN", "GO", "AREA", "GND", "HL", "PNL", "YS", "LD", "N", "E", "W",
    "S", "RD", "BONES", "P", "TX", "OT", "4", "5", "6", "7", "Cougar",
    "Ruger", "Hauer", "Berger", "GLZR", "SMT", "TAVN", "TLR", "CATH",
    "MYLEN", "LRA", "ISABL", "MOROC", "REBEC", "BREAD", "TRAD", "AUST",
    "FRAN", "SWIS", "BELG", "PLANT", "AMACH", "DOKU", "SENBR", "DAEDL",
    "CENTA", "ATL", "CERBR", "FRED", "BOB", "TM", "JM", "SRW", "COY",
    "REIN", "PUMA", "GOLD", "SILVER", "COPPER", "TIN", "MAGDA", "NZR",
    "BETH", "JERUS", "BISH", "MEYER", "HITLR", "NIK", "JEAN", "ALEX",
    "LINC", "LEFT", "UP", "R",
)


class UiPatchError(ValueError):
    """Report an incompatible source, fixed-slot overrun, or unsafe UI patch.

    UI patch helpers raise this exception before returning modified bytes when
    source fingerprints, instruction patterns, encoded sizes, or bank capacity
    differ from verified assumptions.  Callers should inspect the source version
    or shorten/recompress text instead of forcing a partial write.
    """


def _encode_kouhen_guard_rle(values: bytes) -> bytes:
    """Encode a SON-KOUH startup nametable fragment.

    Args:
        values: Decoded tile IDs in PPU upload order.

    Returns:
        Native count-prefix data terminated by ``$FF``.

    Runs are split at 62 because ``$FF`` terminates the decoder. Single-byte
    remainders use literals because they are shorter than a two-byte run.
    """

    encoded = bytearray()
    index = 0
    while index < len(values):
        value = values[index]
        run = 1
        while index + run < len(values) and values[index + run] == value:
            run += 1

        remaining = run
        while remaining:
            # $FF terminates this decoder, so the largest legal run prefix is
            # $FE: 62 copies.  A final single byte is cheaper as a literal.
            chunk = min(remaining, 62)
            if chunk == 1:
                encoded.append(value)
            else:
                encoded.extend((0xC0 | chunk, value))
            remaining -= chunk
        index += run
    encoded.append(0xFF)
    return bytes(encoded)


def _kouhen_boot_guard_assets() -> tuple[bytes, bytes]:
    """Build the Kouhen direct-boot message tilemap and private glyphs.

    Returns:
        A fixed-size, padded RLE stream and direct-upload 1bpp glyph rows.

    Raises:
        UiPatchError: If the message exhausts private tile IDs, falls outside
            the recovered nametable fragment, or cannot fit the original RLE
            allocation.
        FontPatchError: If a message character has no deterministic glyph.

    Glyph bits are inverted relative to NOV4's stored font because SON-KOUH
    uploads its private patterns directly instead of expanding inverse rows.
    """

    tile_by_character = {
        character: tile
        for tile, character in enumerate(KOUHEN_BOOT_GUARD_TILE_CHARACTERS)
    }
    if len(tile_by_character) >= KOUHEN_BOOT_GUARD_BLANK_TILE:
        raise UiPatchError("Kouhen boot message uses too many private tiles")

    tilemap = bytearray(
        [KOUHEN_BOOT_GUARD_BLANK_TILE] * KOUHEN_BOOT_GUARD_DECODED_SIZE
    )
    nametable_start = KOUHEN_BOOT_GUARD_PPU_START - 0x2000
    for row, text in KOUHEN_BOOT_GUARD_LINES:
        column = (32 - len(text)) // 2
        start = row * 32 + column - nametable_start
        end = start + len(text)
        if start < 0 or end > len(tilemap):
            raise UiPatchError("Kouhen boot message is outside its nametable fragment")
        tilemap[start:end] = bytes(
            KOUHEN_BOOT_GUARD_BLANK_TILE
            if character == " "
            else tile_by_character[character]
            for character in text
        )

    stream = _encode_kouhen_guard_rle(bytes(tilemap))
    stream_size = KOUHEN_BOOT_GUARD_TILEMAP_END - KOUHEN_BOOT_GUARD_TILEMAP_OFFSET
    if len(stream) > stream_size:
        raise UiPatchError(
            f"Kouhen boot tilemap needs {len(stream)} bytes but has {stream_size}"
        )
    # The decoder stops at the first $FF; additional terminators safely retain
    # the fixed address of the following CHR upload routine.
    stream = stream.ljust(stream_size, b"\xFF")

    glyphs = bytearray(KOUHEN_BOOT_GUARD_TILE_COUNT * 8)
    for character, tile in tile_by_character.items():
        # The dialogue font stores zeroes as ink because NOV4 expands inverse
        # 1bpp patterns.  SON-KOUH uploads its private tiles directly, so flip
        # the bits to obtain white glyphs on its black background.
        glyph = bytes(value ^ 0xFF for value in render_glyph(character))
        glyphs[tile * 8 : (tile + 1) * 8] = glyph
    return stream, bytes(glyphs)


def patched_kouhen_boot_guard(data: bytes) -> bytes:
    """Translate Kouhen's direct-boot warning without changing program code.

    Args:
        data: Original 739-byte SON-KOUH component.

    Returns:
        A same-size copy with only the RLE tilemap and private glyph rows
        replaced.

    Raises:
        UiPatchError: If size or SHA-256 does not match the recovered source,
            or generated assets exceed their fixed locations.
    """

    if len(data) != KOUHEN_BOOT_GUARD_SIZE:
        raise UiPatchError(
            f"SON-KOUH has size {len(data)}, expected {KOUHEN_BOOT_GUARD_SIZE}"
        )
    if hashlib.sha256(data).hexdigest().upper() != KOUHEN_BOOT_GUARD_SOURCE_SHA256:
        raise UiPatchError("SON-KOUH does not match the known Japanese source")

    stream, glyphs = _kouhen_boot_guard_assets()
    chr_end = KOUHEN_BOOT_GUARD_CHR_OFFSET + len(glyphs)
    result = bytearray(data)
    result[KOUHEN_BOOT_GUARD_TILEMAP_OFFSET:KOUHEN_BOOT_GUARD_TILEMAP_END] = stream
    result[KOUHEN_BOOT_GUARD_CHR_OFFSET:chr_end] = glyphs
    return bytes(result)


def _patched_start_prompt(data: bytes, offset: int, component: str) -> bytes:
    """Replace one unique packed start prompt at a recovered offset.

    Args:
        data: Extracted component bytes.
        offset: Expected start of the Japanese packed record.
        component: Human-readable name used in diagnostics.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If source/replacement sizes differ, the input is short,
            expected bytes differ, or the source prompt is not globally unique.
    """

    if len(ENGLISH_START_PROMPT) != len(ORIGINAL_START_PROMPT):
        raise UiPatchError("translated start prompt changed packed size")
    end = offset + len(ORIGINAL_START_PROMPT)
    if len(data) < end:
        raise UiPatchError(f"{component} is too short for the recovered start prompt")
    if data[offset:end] != ORIGINAL_START_PROMPT:
        raise UiPatchError(
            f"{component} start prompt does not match the known source bytes"
        )
    if data.count(ORIGINAL_START_PROMPT) != 1:
        raise UiPatchError(f"{component} start prompt source is not unique")

    result = bytearray(data)
    result[offset:end] = ENGLISH_START_PROMPT
    return bytes(result)


def _patched_disk_prompts(data: bytes) -> bytes:
    """Translate every normal NOV2 FDS side-change record.

    Args:
        data: NOV2 bytes containing all recovered prompt slots.

    Returns:
        A same-size copy with each prompt replaced independently.

    Raises:
        UiPatchError: If a replacement changes size, a slot is missing, or its
            source bytes differ.
        EnglishTextError: If configured English cannot be encoded.
    """

    result = bytearray(data)
    for offset, original, english in DISK_PROMPT_PATCHES:
        replacement = pack_records([encode_english(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"disk prompt at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end:
            raise UiPatchError("NOV2 is too short for the recovered disk prompt")
        if result[offset:end] != original:
            raise UiPatchError(
                f"NOV2 disk prompt at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _patched_wrong_disk_message(data: bytes) -> bytes:
    """Translate each NOV2 wrong-disk fallback record.

    Args:
        data: NOV2 bytes containing the recovered warning slots.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If any slot size or source bytes differ.
        EnglishTextError: If configured English cannot be encoded.
    """

    result = bytearray(data)
    for offset, original, english in WRONG_DISK_PATCHES:
        replacement = pack_records([encode_english(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"wrong-disk message at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end or result[offset:end] != original:
            raise UiPatchError(
                f"wrong-disk message at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _patched_wait_prompt(data: bytes) -> bytes:
    """Translate ``しばらく おまちください`` in its fixed NOV2 slot.

    Args:
        data: NOV2 bytes.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If packed sizes differ or source bytes are unknown.
    """

    if len(ENGLISH_WAIT_PROMPT) != len(ORIGINAL_WAIT_PROMPT):
        raise UiPatchError("translated wait prompt changed packed size")
    end = WAIT_PROMPT_OFFSET + len(ORIGINAL_WAIT_PROMPT)
    if len(data) < end or data[WAIT_PROMPT_OFFSET:end] != ORIGINAL_WAIT_PROMPT:
        raise UiPatchError("NOV2 wait prompt does not match the known source")
    result = bytearray(data)
    result[WAIT_PROMPT_OFFSET:end] = ENGLISH_WAIT_PROMPT
    return bytes(result)


def _patched_opaque_text_clears(data: bytes) -> bytes:
    """Clear complete menu tails without breaking dialogue row copies.

    Args:
        data: NOV2 bytes with the recovered rendering instructions.

    Returns:
        A same-size copy with selected clear-mode operands changed.

    Raises:
        UiPatchError: If a patch byte or the protected dialogue-copy sequence
            differs from the known source.

    The protected sequence is checked but not changed. This guards against a
    broad rendering fix that previously restored menu rows at the cost of
    ordinary dialogue replacement.
    """

    result = bytearray(data)
    for offset, original, replacement, label in NOV2_OPAQUE_CLEAR_PATCHES:
        if len(result) <= offset or result[offset] != original:
            raise UiPatchError(
                f"NOV2 {label} clear at 0x{offset:04X} does not match source"
            )
        result[offset] = replacement
    offset, original = NOV2_DIALOGUE_ROW_COPY
    end = offset + len(original)
    if len(result) < end or result[offset:end] != original:
        raise UiPatchError(
            f"NOV2 dialogue row copy at 0x{offset:04X} does not match source"
        )
    return bytes(result)


def _patched_single_choice_b_guard(data: bytes) -> bytes:
    """Make B a no-op only while a one-choice menu is active.

    Args:
        data: NOV2 bytes containing the recovered input branches.

    Returns:
        A same-size copy with guarded branch/code fragments installed.

    Raises:
        UiPatchError: If a replacement changes size or a source instruction
            differs.

    Multi-choice Back/Cancel behavior is deliberately left untouched.
    """

    result = bytearray(data)
    for offset, original, replacement, label in NOV2_SINGLE_CHOICE_B_PATCHES:
        end = offset + len(original)
        if len(original) != len(replacement):
            raise UiPatchError(f"NOV2 {label} patch changed size")
        if len(result) < end or result[offset:end] != original:
            raise UiPatchError(
                f"NOV2 {label} at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def patched_nov2_ui(data: bytes) -> bytes:
    """Apply the complete, ordered NOV2 interface patch set.

    Args:
        data: Compatible NOV2 component bytes.

    Returns:
        A same-size copy containing wait/disk/wrong-disk/start translations,
        opaque menu-tail clearing, and the one-choice B guard.

    Raises:
        UiPatchError: If any revision guard or size invariant fails.
        EnglishTextError: If configured prompt text cannot be encoded.

    Patch order is intentional because every helper validates the bytes it
    owns while leaving disjoint regions available to later helpers.
    """

    with_wait_prompt = _patched_wait_prompt(data)
    with_disk_prompts = _patched_disk_prompts(with_wait_prompt)
    with_wrong_disk_message = _patched_wrong_disk_message(with_disk_prompts)
    with_start_prompt = _patched_start_prompt(
        with_wrong_disk_message, START_PROMPT_OFFSET, "NOV2"
    )
    with_opaque_clears = _patched_opaque_text_clears(with_start_prompt)
    return _patched_single_choice_b_guard(with_opaque_clears)


def patched_nov4_ui(data: bytes) -> bytes:
    """Patch the live-menu NOV4 copy of ``さいしょから`` with ``START``.

    Args:
        data: Compatible NOV4 component bytes.

    Returns:
        A same-size patched copy.

    Raises:
        UiPatchError: If the prompt is missing, nonunique, or size-incompatible.

    The Japanese and English records both occupy six packed bytes, so neither
    the following NOV4 data nor any FDS file offsets move.
    """

    return _patched_start_prompt(data, NOV4_START_PROMPT_OFFSET, "NOV4")


def patched_tt1a_ui(data: bytes) -> bytes:
    """Translate TT1A blood-type, month, and confirmation choices.

    Args:
        data: TT1A scenario/program bank containing the Japanese slots.

    Returns:
        A same-size copy preserving every subsequent fixed address.

    Raises:
        UiPatchError: If a configured replacement changes packed size, the
            bank is short, or a source slot differs.
        EnglishTextError: If configured choice text cannot be encoded.
    """

    result = bytearray(data)
    for offset, original, english in (
        *TT1A_BLOOD_TYPE_PATCHES,
        *TT1A_MONTH_PATCHES,
        *TT1A_CONFIRMATION_PATCHES,
    ):
        replacement = pack_records([encode_english(english)])
        if len(replacement) != len(original):
            raise UiPatchError(
                f"TT1A choice label at 0x{offset:04X} changed packed size"
            )
        end = offset + len(original)
        if len(result) < end:
            raise UiPatchError("TT1A is too short for the fixed choice tables")
        if result[offset:end] != original:
            raise UiPatchError(
                f"TT1A choice label at 0x{offset:04X} does not match source"
            )
        result[offset:end] = replacement
    return bytes(result)


def _tt2_dictionary(data: bytes) -> tuple[tuple[PackedSymbol, ...], ...]:
    """Decode the bank dictionary shared by all fixed UI table patchers.

    Args:
        data: Rebuilt scenario bank whose pointer at ``$0016`` is valid.

    Returns:
        Exactly :data:`TT2_DICTIONARY_ENTRIES` aligned dictionary records.

    Raises:
        UiPatchError: If the bank is too short or its dictionary pointer lies
            outside the bank.
        PackedTextError: If the dictionary stream is truncated.

    The historical function name remains for compatibility, but the layout is
    shared by TT1B, T22, TT3-TT6, and T25 after scenario insertion.
    """

    pointer_end = TT2_DICTIONARY_POINTER_OFFSET + 2
    if len(data) < pointer_end:
        raise UiPatchError("TT2 is too short for its dictionary pointer")
    address = int.from_bytes(
        data[TT2_DICTIONARY_POINTER_OFFSET:pointer_end], "little"
    )
    offset = address - TT2_LOAD_ADDRESS
    if offset < 0 or offset >= len(data):
        raise UiPatchError("TT2 dictionary pointer is outside the bank")
    reader = BitReader(data, offset * 8)
    records: list[tuple[PackedSymbol, ...]] = []
    while len(records) < TT2_DICTIONARY_ENTRIES:
        record: list[PackedSymbol] = []
        while True:
            symbol = decode_symbol(reader)
            if symbol.kind is SymbolKind.SEPARATOR:
                reader.align_to_next_byte()
                records.append(tuple(record))
                break
            record.append(symbol)
    return tuple(records)


def _encode_with_dictionary(
    text: str,
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
) -> tuple[PackedSymbol, ...]:
    """Encode one label using the cheapest matching flat dictionary entries.

    Args:
        text: Supported English label without record separators.
        dictionary: Ordered flat English dictionary already present in the
            rebuilt bank.

    Returns:
        The minimum-bit symbol sequence for ``text`` under that dictionary.

    Raises:
        EnglishTextError: If ``text`` contains an unsupported character/tag.

    Dynamic programming chooses, at each literal position, between emitting
    the next symbol and any dictionary entry that matches the remaining text.
    The cost is measured in native bits, so the result is the shortest symbol
    sequence for the fixed dictionary rather than a greedy word replacement.
    Ties retain Python's tuple-order minimum, making identical input
    deterministic.
    """

    source = encode_english(text)
    normalized_dictionary = tuple(
        tuple(PackedSymbol(symbol.kind, symbol.value, 0, 0) for symbol in entry)
        for entry in dictionary
    )
    best: list[tuple[int, tuple[PackedSymbol, ...]] | None] = [
        None
    ] * (len(source) + 1)
    best[len(source)] = (0, ())
    for position in range(len(source) - 1, -1, -1):
        suffix = best[position + 1]
        assert suffix is not None
        choices = [
            (
                symbol_bit_length(source[position]) + suffix[0],
                (source[position], *suffix[1]),
            )
        ]
        for index, entry in enumerate(normalized_dictionary, start=1):
            end = position + len(entry)
            if tuple(source[position:end]) != entry:
                continue
            tail = best[end]
            assert tail is not None
            choices.append(
                (
                    9 + tail[0],
                    (
                        PackedSymbol(SymbolKind.DICTIONARY, index, 0, 0),
                        *tail[1],
                    ),
                )
            )
        best[position] = min(choices, key=lambda choice: choice[0])
    encoded = best[0]
    assert encoded is not None
    return encoded[1]


def _encode_at_exact_record_size(
    text: str,
    dictionary: tuple[tuple[PackedSymbol, ...], ...],
    target_size: int,
) -> bytes:
    """Encode one label without changing the following record's address.

    Args:
        text: Visible English label.
        dictionary: Bank dictionary used for compression.
        target_size: Exact packed allocation of the original record.

    Returns:
        One packed record of exactly ``target_size`` bytes.

    Raises:
        UiPatchError: If the shortest representation already exceeds the slot
            or zero-or-more trailing spaces cannot reach the exact allocation.
        EnglishTextError: If the label cannot be encoded.

    The renderer does not display trailing common-space tiles. Add as many
    as are necessary to consume the record's original byte allocation after
    the shortest dictionary-aware encoding has been chosen.
    """

    encoded = _encode_with_dictionary(text, dictionary)
    common_space = encode_english(" ")[0]
    while len(pack_records((encoded,))) < target_size:
        encoded = (*encoded, common_space)
    packed = pack_records((encoded,))
    if len(packed) != target_size:
        raise UiPatchError(
            f"fixed label {text!r} needs {len(packed)} bytes but its slot is "
            f"{target_size} bytes"
        )
    return packed


def _patched_fixed_record_table(
    data: bytes,
    *,
    start: int,
    end: int,
    source_sha256: str,
    records: tuple[str, ...],
    component: str,
) -> bytes:
    """Translate a fixed table while preserving every record boundary.

    Args:
        data: Rebuilt scenario bank with its final English dictionary.
        start: File offset of the fixed table.
        end: Exclusive fixed-table boundary.
        source_sha256: Expected hash of the complete Japanese source table.
        records: English replacements in exact record order.
        component: Bank name used in diagnostics.

    Returns:
        A same-size bank copy preserving the complete fixed-table footprint and
        every record start.

    Raises:
        UiPatchError: If the table is missing/unknown, record framing differs,
            any translation cannot fit its exact slot, or total size changes.
        PackedTextError: If source or replacement packing is invalid.
        EnglishTextError: If configured text cannot be encoded.

    The complete Japanese table is hash-checked, decoded into byte-aligned
    record slots, and rebuilt with the bank's already-generated English
    dictionary.  Each replacement is independently padded to its original slot
    size before the complete table is written back.
    """

    source = data[start:end]
    if len(source) != end - start:
        raise UiPatchError(f"{component} is too short for its fixed text table")
    if hashlib.sha256(source).hexdigest().upper() != source_sha256:
        raise UiPatchError(
            f"{component} fixed text table does not match the known source"
        )

    original_records, parsed_end = split_records(source, limit=len(records))
    if parsed_end != len(source):
        raise UiPatchError(
            f"{component} fixed text table has unexpected trailing bytes"
        )
    original_sizes = tuple(
        split_records(source, offset=offset, limit=1)[1] - offset
        for offset in _record_starts(source, len(original_records))
    )
    dictionary = _tt2_dictionary(data)
    replacement = b"".join(
        _encode_at_exact_record_size(text, dictionary, size)
        for text, size in zip(records, original_sizes)
    )
    if len(replacement) != len(source):
        raise UiPatchError(
            f"translated {component} fixed text table changed size "
            f"({len(source)} -> {len(replacement)})"
        )
    result = bytearray(data)
    result[start:end] = replacement
    return bytes(result)


def _record_starts(data: bytes, count: int) -> tuple[int, ...]:
    """Locate each record start in an aligned packed table.

    Args:
        data: Packed table beginning at record zero.
        count: Number of records to locate.

    Returns:
        ``count`` byte offsets relative to ``data``.

    Raises:
        PackedTextError: If fewer than ``count`` complete records exist.
    """

    starts: list[int] = []
    offset = 0
    for _ in range(count):
        starts.append(offset)
        _, offset = split_records(data, offset=offset, limit=1)
    return tuple(starts)


def patched_tt2_ui(data: bytes) -> bytes:
    """Translate TT2's fixed command, object, and history-quiz table.

    Args:
        data: Rebuilt TT2 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the Japanese table is unknown or any record cannot
            occupy its exact original slot.
    """

    return _patched_fixed_record_table(
        data,
        start=TT2_FIXED_TEXT_START_OFFSET,
        end=TT2_FIXED_TEXT_END_OFFSET,
        source_sha256=TT2_FIXED_TEXT_SOURCE_SHA256,
        records=TT2_FIXED_TEXT_RECORDS,
        component="TT2",
    )


def patched_tt1b_ui(data: bytes) -> bytes:
    """Translate TT1B's fixed command, object, and interaction table.

    Args:
        data: Rebuilt TT1B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the Japanese table is unknown or any record cannot
            occupy its exact original slot.
    """

    return _patched_fixed_record_table(
        data,
        start=TT1B_FIXED_TEXT_START_OFFSET,
        end=TT1B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT1B_FIXED_TEXT_SOURCE_SHA256,
        records=TT1B_FIXED_TEXT_RECORDS,
        component="TT1B",
    )


def patched_t22_ui(data: bytes) -> bytes:
    """Translate T22's fixed command and object-name table.

    Args:
        data: Rebuilt T22 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=T22_FIXED_TEXT_START_OFFSET,
        end=T22_FIXED_TEXT_END_OFFSET,
        source_sha256=T22_FIXED_TEXT_SOURCE_SHA256,
        records=T22_FIXED_TEXT_RECORDS,
        component="T22",
    )


def patched_tt3a_ui(data: bytes) -> bytes:
    """Translate TT3A's fixed command, object, and history-quiz table.

    Args:
        data: Rebuilt TT3A bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT3A_FIXED_TEXT_START_OFFSET,
        end=TT3A_FIXED_TEXT_END_OFFSET,
        source_sha256=TT3A_FIXED_TEXT_SOURCE_SHA256,
        records=TT3A_FIXED_TEXT_RECORDS,
        component="TT3A",
    )


def patched_tt3b_ui(data: bytes) -> bytes:
    """Translate TT3B's fixed command, object, and battle-action table.

    Args:
        data: Rebuilt TT3B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT3B_FIXED_TEXT_START_OFFSET,
        end=TT3B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT3B_FIXED_TEXT_SOURCE_SHA256,
        records=TT3B_FIXED_TEXT_RECORDS,
        component="TT3B",
    )


def patched_tt4_ui(data: bytes) -> bytes:
    """Translate TT4's fixed command, treatment, and quiz table.

    Args:
        data: Rebuilt TT4 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT4_FIXED_TEXT_START_OFFSET,
        end=TT4_FIXED_TEXT_END_OFFSET,
        source_sha256=TT4_FIXED_TEXT_SOURCE_SHA256,
        records=TT4_FIXED_TEXT_RECORDS,
        component="TT4",
    )


def patched_tt5_ui(data: bytes) -> bytes:
    """Translate TT5's fixed command, puzzle, and history-quiz table.

    Args:
        data: Rebuilt TT5 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT5_FIXED_TEXT_START_OFFSET,
        end=TT5_FIXED_TEXT_END_OFFSET,
        source_sha256=TT5_FIXED_TEXT_SOURCE_SHA256,
        records=TT5_FIXED_TEXT_RECORDS,
        component="TT5",
    )


def patched_t25_ui(data: bytes) -> bytes:
    """Translate T25's fixed mansion and flooded-island action table.

    Args:
        data: Rebuilt T25 bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=T25_FIXED_TEXT_START_OFFSET,
        end=T25_FIXED_TEXT_END_OFFSET,
        source_sha256=T25_FIXED_TEXT_SOURCE_SHA256,
        records=T25_FIXED_TEXT_RECORDS,
        component="T25",
    )


def patched_tt6a_ui(data: bytes) -> bytes:
    """Translate TT6A's fixed donkey-action and Nazareth object table.

    Args:
        data: Rebuilt TT6A bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT6A_FIXED_TEXT_START_OFFSET,
        end=TT6A_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6A_FIXED_TEXT_SOURCE_SHA256,
        records=TT6A_FIXED_TEXT_RECORDS,
        component="TT6A",
    )


def patched_tt6b_ui(data: bytes) -> bytes:
    """Translate TT6B's fixed travel, quiz, and animal-action table.

    Args:
        data: Rebuilt TT6B bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT6B_FIXED_TEXT_START_OFFSET,
        end=TT6B_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6B_FIXED_TEXT_SOURCE_SHA256,
        records=TT6B_FIXED_TEXT_RECORDS,
        component="TT6B",
    )


def patched_tt6c_ui(data: bytes) -> bytes:
    """Translate TT6C's fixed finale-action and retrospective-quiz table.

    Args:
        data: Rebuilt TT6C bank with its final English dictionary.

    Returns:
        A same-size bank preserving every fixed record address.

    Raises:
        UiPatchError: If the table revision or fixed-slot layout differs.
    """

    return _patched_fixed_record_table(
        data,
        start=TT6C_FIXED_TEXT_START_OFFSET,
        end=TT6C_FIXED_TEXT_END_OFFSET,
        source_sha256=TT6C_FIXED_TEXT_SOURCE_SHA256,
        records=TT6C_FIXED_TEXT_RECORDS,
        component="TT6C",
    )
