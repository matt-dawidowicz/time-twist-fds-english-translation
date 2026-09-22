"""Recovered Time Twist audio-command selector semantics.

This module documents selector behavior that is independent of story-facing
sound names.  It intentionally distinguishes resident NOV3 effects from
scene-overlay effects, because the same $07E1 bit is reused by different
program overlays.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioCommand:
    """Describe one recovered audio selector."""

    value: int
    name: str
    handler: int
    details: str


AUDIO_LATCH_ROLES = {
    0x07E0: "resident APU/noise-SFX command latch",
    0x07E1: "scene-overlay SFX command latch",
    0x07E2: "resident pulse-channel SFX command latch",
    0x07E3: "resident music/FDS-audio command latch",
}

RETAIL_AUDIO_VALUES = {
    0x83: (0x80, 0x01, 0x02, 0x08, 0x04),
    0x90: (0x02, 0x80),
    0x91: (0x01, 0x80, 0x02, 0x04, 0x10, 0x08, 0x20, 0x40, 0x03),
    0x92: (0x01, 0x04, 0x02, 0x08, 0x80),
    0x93: (0x10, 0x40, 0x20, 0x80, 0x04, 0x01, 0x02),
}

# NOV3 $D804.  Opcode 90 uses only $02 and $80 in reachable retail source.
# $04 is also important because NOV2's native typewriter helper writes it
# directly to $07E0 outside the gameplay VM.
RESIDENT_LATCH0_COMMANDS = {
    0x02: AudioCommand(
        0x02,
        "noise_sweep",
        0xD843,
        (
            "Initializes a ten-step noise sequence through $D83A; writes "
            "$400E/$400C/$400F and counts down $07D5."
        ),
    ),
    0x04: AudioCommand(
        0x04,
        "typewriter_noise_click",
        0xD82A,
        (
            "Four-tick fixed noise burst ($400E=$13, $400C=$1D, "
            "$400F=$18). NOV2 $85C5 writes this value directly; reachable "
            "opcode 90 does not."
        ),
    ),
    0x80: AudioCommand(
        0x80,
        "stop_resident_sfx",
        0xD86C,
        (
            "Stops/resets the resident latch-0 effect path via $4015=$07 "
            "and clears $07E5."
        ),
    ),
}

# NOV3 selector at $D945.  Values identify exact paired sequence offsets in
# the byte stream beginning at $D958.  These are mechanical identities; a
# story-facing label is only safe when a call-site establishes one.
RESIDENT_LATCH2_SEQUENCES = {
    0x01: (0x00, 0x0A),
    0x02: (0x13, 0x2E),
    0x04: (0x49, 0x4E),
    0x08: (0x52, 0x58),
    0x80: (0x09, 0x00),
}

# NOV3 $DA3C.  Music data itself is scene-specific through $D8/$D9, but the
# selector mechanics are global and exact.
MUSIC_SELECTOR_SLOTS = {
    0x01: ("group", (8, 9, 10, 11, 12), "slot 8 intro, then loop slots 9-12"),
    0x02: ("group", (13, 14, 15, 16, 17), "loop slots 13-17"),
    0x04: ("group", (18, 19, 20, 21), "loop slots 18-21"),
    0x08: ("single", (3,), "fixed scene-music table slot 3"),
    0x10: ("single", (4,), "fixed scene-music table slot 4"),
    0x20: ("single", (5,), "fixed scene-music table slot 5"),
    0x40: ("single", (6,), "fixed scene-music table slot 6"),
    0x80: ("stop", (), "stop/clear active music and FDS-audio state"),
}

# Each full gameplay overlay installs a scene-specific byte-offset table used
# by NOV3 through $D8/$D9.  Partial same-address overlays intentionally inherit
# the corresponding high-tail audio data.
SCENE_MUSIC_TABLE_BASES = {
    "TT1B": 0xC20C,
    "TT2": 0xC0C4,
    "TT3A": 0xC25D,
    "TT4": 0xC126,
    "TT5": 0xC0E8,
    "TT6B": 0xC123,
    "TT6C": 0xC168,
    "TT6D": 0xC11B,
}

COMPOSED_AUDIO_OWNER = {
    "TT1A": "TT1B",
    "T22": "TT2",
    "TT3B": "TT3A",
    "T25": "TT5",
    "TT6A": "TT6B",
}

# Fresh-command dispatch for $07E1.  These are entry points reached when the
# corresponding command bit is presented to a quiescent overlay effect state.
# $80 is the common stop/reset sign bit and is documented separately.
SCENE_LATCH1_ENTRY_POINTS = {
    "TT1B": {
        0x01: 0xCF23,
        0x02: 0xCED9,
        0x04: 0xCEA6,
        0x08: 0xCF64,
        0x10: 0xCF60,
        0x20: 0xCF91,
        0x40: 0xCF93,
    },
    "TT2": {
        0x01: 0xD0F3,
        0x02: 0xD162,
        0x04: 0xD176,
        0x08: 0xD176,
    },
    "TT3A": {
        0x01: 0xD079,
        0x02: 0xCFFD,
        0x03: 0xD071,
        0x04: 0xCFD6,
        0x08: 0xD0AC,
        0x10: 0xD07B,
        0x20: 0xD0B0,
        0x40: 0xCFDA,
    },
    "TT4": {
        0x01: 0xD310,
        0x02: 0xD2E2,
        0x04: 0xD35F,
    },
    "TT5": {
        0x01: 0xCC8E,
        0x02: 0xCC24,
        0x04: 0xCC3D,
        0x08: 0xCCCB,
    },
    "TT6B": {
        0x01: 0xBF2A,
        0x02: 0xBE78,
        0x04: 0xBF5A,
    },
    "TT6C": {
        0x01: 0xCE12,
        0x02: 0xCD75,
        0x04: 0xCDC5,
        0x08: 0xCE46,
        0x10: 0xCE42,
    },
    "TT6D": {
        0x01: 0xABC0,
        0x02: 0xAB5D,
        0x04: 0xAC0F,
    },
}

SCENE_LATCH1_STOP_ENTRY_POINTS = {
    "TT1B": 0xCF54,
    "TT2": 0xD156,
    "TT3A": 0xD058,
    "TT4": 0xD350,
    "TT5": 0xCCBF,
    "TT6B": 0xBF1B,
    "TT6C": 0xCE06,
    "TT6D": 0xABF6,
}
