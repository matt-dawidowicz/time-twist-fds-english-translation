"""NOV2 runtime patch for the frozen production entropy grammar.

This module owns the complete production NOV2 codec/runtime sequence directly.
It combines the proven English renderer fixes, the two native dictionary-depth
changes required for nested entropy references, and the frozen entropy decoder.

Production records are bit-contiguous inside each independently addressed
stream. The scanner therefore preserves ``$6A/$6B/$6C`` across record
separators and frame-budget returns; only genuinely new byte-addressed streams
reset the bit mask to ``$80``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .entropy_codec import (
    CATEGORY_BASES,
    CATEGORY_PAYLOAD_BITS,
    CATEGORY_PREFIXES,
)

NOV2_LOAD_ADDRESS = 0x6000
NOV2_SIZE = 0x4200
NOV3_LOAD_ADDRESS = 0xD7B5
PALETTE_CPU_RANGE = range(0x9390, 0x93B0)

SCANNER_CPU_ADDRESS = 0x80B1
SCANNER_REGION_SIZE = 0xA3
FRONTEND_CPU_ADDRESS = 0x815E
FRONTEND_REGION_SIZE = 69
CATEGORY_CPU_ADDRESS = 0x81E0
CATEGORY_REGION_SIZE = 70
MENU_WIDTH_WORK_RAM_ADDRESS = 0x042D
MENU_MAX_STAGED_GLYPHS = 18
LEADING_CONTROL_RESUME_CPU_ADDRESS = 0x819E


class EntropyRuntimeError(ValueError):
    """Report source drift or an invalid entropy runtime assembly."""


@dataclass(frozen=True)
class RuntimePatch:
    """One source-verified size-neutral patch inside NOV2."""

    file_offset: int
    expected: bytes
    replacement: bytes
    label: str

    def __post_init__(self) -> None:
        """Validate offset and enforce size-neutral replacement."""
        if self.file_offset < 0:
            raise EntropyRuntimeError(f"{self.label}: negative file offset")
        if len(self.expected) != len(self.replacement):
            raise EntropyRuntimeError(f"{self.label}: patch changed size")

    @property
    def cpu_address(self) -> int:
        """Return the loaded CPU address of the first patched byte."""
        return NOV2_LOAD_ADDRESS + self.file_offset

    def apply(self, data: bytearray) -> None:
        """Apply the patch, accepting an already-patched buffer idempotently."""
        end = self.file_offset + len(self.expected)
        if end > len(data):
            raise EntropyRuntimeError(
                f"{self.label}: NOV2 ends before file 0x{end:04X}"
            )
        current = bytes(data[self.file_offset : end])
        if current == self.replacement:
            return
        if current != self.expected:
            raise EntropyRuntimeError(
                f"{self.label}: source mismatch at file 0x{self.file_offset:04X} "
                f"/ CPU ${self.cpu_address:04X}: got {current.hex(' ').upper()}"
            )
        data[self.file_offset : end] = self.replacement


def _hex(value: str) -> bytes:
    """Parse a compact hexadecimal patch literal."""
    return bytes.fromhex(value)


# A leading semantic/presentation control can flush stale staged cells before
# decoding any glyph from the new record. Keep its marker through that flush,
# then clear it at the control-specific resume-to-decoder call site.
LEADING_CONTROL_RESUME_PATCHES = (
    RuntimePatch(
        file_offset=0x1FFD,
        expected=_hex("20 5E 81"),
        replacement=_hex("20 9E 81"),
        label="route scroll-row4 resume through leading-marker clear",
    ),
    RuntimePatch(
        file_offset=0x2016,
        expected=_hex("20 5E 81"),
        replacement=_hex("20 9E 81"),
        label="route row3 resume through leading-marker clear",
    ),
    RuntimePatch(
        file_offset=0x202F,
        expected=_hex("20 5E 81"),
        replacement=_hex("20 9E 81"),
        label="route row2 resume through leading-marker clear",
    ),
    RuntimePatch(
        file_offset=0x2048,
        expected=_hex("20 5E 81"),
        replacement=_hex("20 9E 81"),
        label="route row4 resume through leading-marker clear",
    ),
)

# Proven English-renderer fixes that entropy builds still require. These are
# not a second codec: they repair native renderer behavior before the entropy
# decoder itself is installed.
BASE_RUNTIME_PATCHES = (
    RuntimePatch(
        file_offset=0x21D3,
        expected=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C BE 82"),
        replacement=_hex("A5 3A C9 25 B0 4D 69 20 85 3A 4C C5 82"),
        label="extended dictionary entry-point fix",
    ),
    RuntimePatch(
        file_offset=0x2378,
        expected=_hex("AC"),
        replacement=_hex("B0"),
        label="extended code 63 dollar-sign tile redirect",
    ),
    RuntimePatch(
        file_offset=0x2383,
        expected=_hex("00"),
        replacement=_hex("01"),
        label="retain one-shot leading-control typewriter marker",
    ),
    RuntimePatch(
        file_offset=0x247E,
        expected=_hex("20 C5 85"),
        replacement=_hex("20 8D 98"),
        label="route typewriter SFX through leading-control gate",
    ),
)

# The Japanese menu renderer used fixed six-glyph geometry. Earlier English
# builds merely raised two loop counts to eight; reverse engineering and live
# MesenCE testing later proved that limit was an implementation artifact. The
# production renderer records each decoded label's pixel width in Work RAM and
# derives draw counts, two-column placement, and cursor geometry from that one
# value. Keep the retail/live-tested horizontal anchor: left cursor x=$20 and
# left text x=$28. The earlier modernization accidentally shifted both columns
# four tiles (32 px) to the right while changing the width metadata ABI.
# Every replacement remains size-neutral inside NOV2.
DYNAMIC_MENU_LAYOUT_PATCHES = (
    RuntimePatch(
        file_offset=0x0D8A,
        expected=_hex(
            "0A A8 B1 C5 85 3C C8 B1 C5 85 3D A5 3C 85 C5 A5 3D 85 C6 4C FF 69"
        ),
        replacement=_hex(
            "4C 3A 6C A4 32 C0 04 90 0A 98 29 03 A8 B9 2D 04 69 2F 60 A9 20 60"
        ),
        label="width-aware menu column base",
    ),
    RuntimePatch(
        file_offset=0x0DDC,
        expected=_hex(
            "B1 C5 85 3C C8 B1 C5 85 3D A5 3C 85 C5 A5 3D 85 C6 4C FF 69"
        ),
        replacement=_hex(
            "4C 3C 6C A5 98 38 E5 99 A8 8A 0A 0A 99 2D 04 A9 00 85 69 60"
        ),
        label="menu width Work RAM recorder",
    ),
    RuntimePatch(
        file_offset=0x345D,
        expected=_hex("10"),
        replacement=_hex("24"),
        label="expanded variable-width menu clear span",
    ),
    RuntimePatch(
        file_offset=0x3481,
        expected=_hex(
            "29 03 0A 85 3C A9 00 06 3C 2A 06 3C 2A 06 3C 2A 06 3C 2A 06 3C 2A "
            "85 3D A5 32 C9 04 90 10 A9 51 18 65 3C 85 3C A9 22 65 3D 85 3D 4C BC "
            "94 A9 49 18 65 3C 85 3C A9 22 65 3D 85 3D A9 06 85 31 A2 00"
        ),
        replacement=_hex(
            "AA 29 03 0A 0A 0A 0A 0A 0A 85 3C A9 00 85 3D 8A C9 04 90 0D 29 03 A8 "
            "B9 2D 04 4A 4A 4A 69 47 D0 02 A9 45 65 3C 85 3C A9 22 65 3D 85 3D BD "
            "2D 04 4A 4A 4A D0 02 A9 06 85 31 A2 00 EA EA EA EA EA EA"
        ),
        label="metadata-driven menu renderer geometry",
    ),
    RuntimePatch(
        file_offset=0x34E5,
        expected=_hex("A2 01 A9 06 85 31"),
        replacement=_hex("8A 4A 85 31 A2 01"),
        label="paired-row dynamic menu draw count",
    ),
    RuntimePatch(
        file_offset=0x3885,
        expected=_hex("A5 32 C9 04 90 05 A9 80 4C 92 98 A9 40 85 14"),
        replacement=_hex("20 8D 6D 85 14 4C 94 98 A5 73 D0 1A 4C C5 85"),
        label="width-aware leading menu cursor and typewriter gate",
    ),
)


# Back/Cancel is keyed to whether the current menu has a real parent, not to
# the number of visible choices. The native dispatcher at $99DC already returns
# when $9C is zero; the defect is that root-menu setup can save the current
# menu as its own Back destination.
#
# The entropy renderer owns five NOP bytes at $814A. They are part of the
# scanner's canonical replacement image and hold the no-parent stub so the
# scanner hash guard remains idempotent. The no-parent descriptor path branches
# to a freed $6B70 trampoline, which reaches that stub; STY clears $9C while Y
# is zero, then normal setup resumes at $6BBB. The real-parent path that stores
# $C5/$C6 into $9B/$9C remains byte-identical. Three state-table entries are
# redirected from duplicate handler $6B70 to equivalent handler $6B66 so $6B70
# can be reused.
PARENT_BACK_GUARD_STUB_CPU_ADDRESS = 0x814A
PARENT_BACK_GUARD_STUB = _hex("84 9C 4C BB 6B")

PARENT_BACK_GUARD_PATCHES = (
    RuntimePatch(
        file_offset=0x0A97,
        expected=_hex("70 6B 70 6B"),
        replacement=_hex("66 6B 66 6B"),
        label="free duplicate state handler 6B70 entries 1-2",
    ),
    RuntimePatch(
        file_offset=0x0A9D,
        expected=_hex("70 6B"),
        replacement=_hex("66 6B"),
        label="free duplicate state handler 6B70 entry 3",
    ),
    RuntimePatch(
        file_offset=0x0B70,
        expected=_hex("4C 01 61"),
        replacement=_hex("4C 4A 81"),
        label="no-parent Back guard trampoline",
    ),
    RuntimePatch(
        file_offset=0x0BA9,
        expected=_hex("F0 10"),
        replacement=_hex("F0 C5"),
        label="route no-parent menu setup through Back guard",
    ),
)


class _Assembler:
    """Minimal deterministic assembler for the small 6502 replacement blocks."""

    def __init__(self, origin: int) -> None:
        """Initialize the helper state."""
        self.origin = origin
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str, str | int]] = []

    @property
    def pc(self) -> int:
        """Return the current assembler program counter."""
        return self.origin + len(self.data)

    def label(self, name: str) -> None:
        """Record an assembler label at the current program counter."""
        if name in self.labels:
            raise EntropyRuntimeError(f"duplicate assembler label {name}")
        self.labels[name] = self.pc

    def emit(self, *values: int) -> None:
        """Append raw bytes to the assembled runtime."""
        if any(not 0 <= value <= 0xFF for value in values):
            raise EntropyRuntimeError("assembler byte is outside 0..255")
        self.data.extend(values)

    def absolute(self, opcode: int, target: str | int) -> None:
        """Record an absolute-address fixup in the assembled runtime."""
        self.emit(opcode, 0, 0)
        self.fixups.append((len(self.data) - 2, "absolute", target))

    def relative(self, opcode: int, target: str | int) -> None:
        """Record a relative-address fixup in the assembled runtime."""
        self.emit(opcode, 0)
        self.fixups.append((len(self.data) - 1, "relative", target))

    def finish(self) -> bytes:
        """Resolve assembler fixups and return the completed runtime bytes."""
        for position, kind, target in self.fixups:
            address = (
                self.labels[target] if isinstance(target, str) else target
            )
            if kind == "absolute":
                self.data[position] = address & 0xFF
                self.data[position + 1] = (address >> 8) & 0xFF
                continue
            source = self.origin + position + 1
            displacement = address - source
            if not -128 <= displacement <= 127:
                raise EntropyRuntimeError(
                    f"relative branch from ${source:04X} to ${address:04X} "
                    "is out of range"
                )
            self.data[position] = displacement & 0xFF
        return bytes(self.data)


def _entropy_tree() -> bytes:
    """Serialize the frozen prefix trie for the compact category decoder."""
    root: dict[int | str, object] = {}
    for category, prefix in enumerate(CATEGORY_PREFIXES):
        node = root
        for bit_text in prefix:
            bit = int(bit_text)
            child = node.setdefault(bit, {})
            if not isinstance(child, dict):
                raise EntropyRuntimeError(
                    "entropy prefix collides with a leaf"
                )
            node = child
        if node:
            raise EntropyRuntimeError("entropy prefix is not a unique leaf")
        node["category"] = category

    nodes: list[int | None] = []

    def emit_node(node: dict[int | str, object]) -> int:
        """Serialize one node of the entropy decode trie."""
        index = len(nodes)
        nodes.append(None)
        category = node.get("category")
        if isinstance(category, int):
            nodes[index] = 0x80 | category
            return index
        left = node.get(0)
        right = node.get(1)
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise EntropyRuntimeError("entropy prefix trie is incomplete")
        left_index = emit_node(left)
        right_index = emit_node(right)
        if left_index != index + 1:
            raise EntropyRuntimeError("left entropy child is not implicit")
        nodes[index] = right_index
        return index

    emit_node(root)
    if len(nodes) != 31 or any(value is None for value in nodes):
        raise EntropyRuntimeError("unexpected serialized entropy tree size")
    return bytes(value for value in nodes if value is not None)


ENTROPY_TREE = _entropy_tree()


def _build_scanner() -> tuple[bytes, int, int, int, int, int]:
    """Build the resumable record scanner plus its two initialization stubs."""
    assembler = _Assembler(SCANNER_CPU_ADDRESS)
    assembler.absolute(0x8D, 0x7F79)  # STA $7F79 -- work budget

    # A=$FF is used only for a fresh dictionary seek. Scenario/menu scanner
    # resumes use ordinary budgets and must preserve the current bit mask.
    assembler.emit(0xC9, 0xFF)
    assembler.relative(0xD0, "save_x")
    assembler.emit(0xA9, 0x80, 0x85, 0x6C)

    # The native callers keep live state in X. Save it once per scanner entry,
    # not once per record: the inner record loop jumps past this push.
    assembler.label("save_x")
    assembler.emit(0x8A, 0x48)

    assembler.label("record_top")
    assembler.emit(0xA9, 0x00, 0xC5, 0xC2)
    assembler.relative(0xD0, "scan_symbol")
    assembler.absolute(0x4C, "clear_return")

    assembler.label("scan_symbol")
    assembler.absolute(0x20, CATEGORY_CPU_ADDRESS)
    # Do not borrow zero-page state here. $74 is live native engine state.
    assembler.emit(0x48, 0xA8)
    assembler.absolute(0xB9, "bits_table")
    assembler.emit(0xAA, 0xA0, 0x00, 0xE0, 0x00)
    assembler.relative(0xF0, "payload_done")

    assembler.label("payload_loop")
    assembler.absolute(0x20, 0x8328)
    assembler.emit(0xCA)
    assembler.relative(0xD0, "payload_loop")

    assembler.label("payload_done")
    assembler.emit(0x68)
    assembler.relative(0xD0, "scan_symbol")

    # Category zero is CTRL5. Do not align: the next record begins at the next
    # unread bit in the same stream.
    assembler.emit(0xA5, 0xC2, 0x38, 0xE9, 0x01, 0x85, 0xC2)

    # $D7B5 is the exact exclusive boundary where NOV3 begins.
    assembler.emit(0xA5, 0x6B, 0xC9, 0xD7)
    assembler.relative(0x90, "boundary_ok")
    assembler.relative(0xD0, "clear_return")
    assembler.emit(0xA5, 0x6A, 0xC9, 0xB5)
    assembler.relative(0xB0, "clear_return")

    assembler.label("boundary_ok")
    assembler.absolute(0xCE, 0x7F79)
    assembler.relative(0xF0, "budget_return")
    assembler.absolute(0x4C, "record_top")

    assembler.label("clear_return")
    assembler.emit(0xA9, 0x00)
    assembler.absolute(0x8D, 0x7F78)
    assembler.label("budget_return")
    assembler.emit(0x68, 0xAA, 0x60)

    assembler.label("bits_table")
    assembler.emit(*CATEGORY_PAYLOAD_BITS)
    assembler.label("base_table")
    assembler.emit(*CATEGORY_BASES)

    assembler.label("pointer_init")
    assembler.emit(0xA9, 0x80, 0x85, 0x6C, 0xA9, 0xFF)
    assembler.absolute(0x8D, 0x7F78)
    assembler.emit(0x60)

    assembler.label("menu_init")
    assembler.emit(0x85, 0xC2, 0xA9, 0x80, 0x85, 0x6C, 0xA0, 0x00, 0x60)

    # Width metadata is stored as pixels at $042D+visual-index. $A8 is the
    # selected visual slot, so the trailing marker is text_base + width + 8.
    # Keep the historical 25-byte scanner allocation size-neutral; the final
    # six NOPs are unreachable padding after RTS.
    assembler.label("selection_span")
    assembler.emit(0x98, 0x48)  # TYA / PHA -- preserve caller Y
    assembler.emit(0xA4, 0xA8)  # LDY $A8 -- selected visual slot
    assembler.absolute(0xB9, MENU_WIDTH_WORK_RAM_ADDRESS)
    assembler.emit(0x18, 0x69, 0x08, 0x65, 0x14, 0x85, 0x31)
    assembler.emit(0x68, 0xA8, 0xA5, 0x31, 0x60)
    assembler.emit(0xEA, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA)

    blob = assembler.finish()
    if len(blob) > SCANNER_REGION_SIZE:
        raise EntropyRuntimeError(
            f"entropy scanner uses {len(blob)} of {SCANNER_REGION_SIZE} bytes"
        )
    return (
        blob,
        assembler.labels["bits_table"],
        assembler.labels["base_table"],
        assembler.labels["pointer_init"],
        assembler.labels["menu_init"],
        assembler.labels["selection_span"],
    )


def _build_category_decoder() -> bytes:
    """Build the compact trie walker in the recovered decoder region."""
    assembler = _Assembler(CATEGORY_CPU_ADDRESS)
    assembler.emit(0xA2, 0x00)
    assembler.label("loop")
    assembler.absolute(0xBD, "tree")
    assembler.relative(0x30, "leaf")
    assembler.emit(0x48, 0xA0, 0x00)
    assembler.absolute(0x20, 0x8328)
    assembler.relative(0xB0, "right")
    assembler.emit(0x68, 0xE8)
    assembler.absolute(0x4C, "loop")
    assembler.label("right")
    assembler.emit(0x68, 0xAA)
    assembler.absolute(0x4C, "loop")
    assembler.label("leaf")
    assembler.emit(0x29, 0x0F, 0x60)
    assembler.label("tree")
    assembler.emit(*ENTROPY_TREE)

    blob = assembler.finish()
    if len(blob) > CATEGORY_REGION_SIZE:
        raise EntropyRuntimeError(
            "entropy category decoder exceeds its region"
        )
    return blob


def _build_frontend(bits_address: int, base_address: int) -> bytes:
    """Decode one entropy token and dispatch to the native semantic handlers."""
    assembler = _Assembler(FRONTEND_CPU_ADDRESS)
    assembler.emit(0x8A, 0x48)
    assembler.absolute(0x20, CATEGORY_CPU_ADDRESS)
    # Preserve the category on the CPU stack instead of borrowing $74, which
    # belongs to unrelated native engine state.
    assembler.emit(0x48, 0xA8)
    assembler.absolute(0xB9, bits_address)
    assembler.emit(0xAA, 0xA9, 0x00, 0x85, 0x3A, 0xA0, 0x00, 0xE0, 0x00)
    assembler.relative(0xF0, "payload_done")
    assembler.label("payload_loop")
    assembler.absolute(0x20, 0x8328)
    assembler.emit(0xCA)
    assembler.relative(0xD0, "payload_loop")
    assembler.label("payload_done")
    assembler.emit(0x68, 0xA8)
    assembler.absolute(0xB9, base_address)
    assembler.emit(0x18, 0x65, 0x3A, 0x85, 0x3A, 0x68, 0xAA, 0x98)
    assembler.emit(0xC9, 0x02)
    assembler.relative(0x90, "control")
    assembler.emit(0xC9, 0x08)
    assembler.relative(0x90, "common")
    assembler.emit(0xC9, 0x0F)
    assembler.relative(0x90, "dictionary")
    assembler.absolute(0x4C, 0x8226)  # native extended handler
    assembler.label("control")
    assembler.absolute(0x4C, 0x8242)
    assembler.label("common")
    assembler.absolute(0x4C, 0x81A6)
    assembler.label("dictionary")
    assembler.absolute(0x4C, 0x82C5)
    blob = assembler.finish()
    if len(blob) > FRONTEND_REGION_SIZE:
        raise EntropyRuntimeError("entropy frontend exceeds its region")
    return blob


(
    _SCANNER_CODE,
    ENTROPY_BITS_TABLE_CPU_ADDRESS,
    ENTROPY_BASE_TABLE_CPU_ADDRESS,
    ENTROPY_POINTER_INIT_CPU_ADDRESS,
    ENTROPY_MENU_INIT_CPU_ADDRESS,
    ENTROPY_SELECTION_SPAN_CPU_ADDRESS,
) = _build_scanner()
_CATEGORY_CODE = _build_category_decoder()
_FRONTEND_CODE = _build_frontend(
    ENTROPY_BITS_TABLE_CPU_ADDRESS,
    ENTROPY_BASE_TABLE_CPU_ADDRESS,
)

SCANNER_CODE_BYTES = len(_SCANNER_CODE)
CATEGORY_CODE_BYTES = len(_CATEGORY_CODE)
FRONTEND_CODE_BYTES = len(_FRONTEND_CODE)

_TOP_LEVEL_CODE = bytes.fromhex("A2 00 86 71 86 72 86 73 EA EA")
_POINTER_BRANCH = bytes(
    (
        0x4C,
        ENTROPY_POINTER_INIT_CPU_ADDRESS & 0xFF,
        ENTROPY_POINTER_INIT_CPU_ADDRESS >> 8,
        0xEA,
        0xEA,
        0xEA,
    )
)
_MENU_BRANCH = bytes(
    (
        0x20,
        ENTROPY_MENU_INIT_CPU_ADDRESS & 0xFF,
        ENTROPY_MENU_INIT_CPU_ADDRESS >> 8,
        0xEA,
    )
)
_MENU_WIDTH_CAPTURE_CALL = bytes.fromhex("20 DF 6D 60 EA")
_DYNAMIC_SELECTION_SPAN_CALL = bytes(
    (
        0x20,
        ENTROPY_SELECTION_SPAN_CPU_ADDRESS & 0xFF,
        ENTROPY_SELECTION_SPAN_CPU_ADDRESS >> 8,
        0x24,
        0x48,
        0x85,
        0x14,
    )
)
_DICTIONARY_REJOIN = bytes.fromhex("4C 5E 81")

_SCANNER_BLOCK = _SCANNER_CODE + bytes((0xEA,)) * (
    SCANNER_REGION_SIZE - len(_SCANNER_CODE)
)
_parent_back_guard_stub_offset = (
    PARENT_BACK_GUARD_STUB_CPU_ADDRESS - SCANNER_CPU_ADDRESS
)
_stub_end = _parent_back_guard_stub_offset + len(PARENT_BACK_GUARD_STUB)
if not 0 <= _parent_back_guard_stub_offset < _stub_end <= len(_SCANNER_BLOCK):
    raise EntropyRuntimeError("parent Back guard stub escaped scanner region")
if _SCANNER_BLOCK[_parent_back_guard_stub_offset:_stub_end] != bytes(
    (0xEA,)
) * len(PARENT_BACK_GUARD_STUB):
    raise EntropyRuntimeError(
        "parent Back guard stub no longer owns NOP space"
    )
_SCANNER_BLOCK = (
    _SCANNER_BLOCK[:_parent_back_guard_stub_offset]
    + PARENT_BACK_GUARD_STUB
    + _SCANNER_BLOCK[_stub_end:]
)
_LEADING_CONTROL_RESUME_WRAPPER = _hex("46 73 4C 5E 81")
if (
    FRONTEND_CPU_ADDRESS + len(_FRONTEND_CODE)
    != LEADING_CONTROL_RESUME_CPU_ADDRESS
):
    raise EntropyRuntimeError("leading-control resume wrapper address drifted")
if (
    len(_FRONTEND_CODE) + len(_LEADING_CONTROL_RESUME_WRAPPER)
    != FRONTEND_REGION_SIZE
):
    raise EntropyRuntimeError(
        "leading-control resume wrapper no longer fits frontend"
    )
_FRONTEND_BLOCK = _FRONTEND_CODE + _LEADING_CONTROL_RESUME_WRAPPER
_CATEGORY_BLOCK = _CATEGORY_CODE + bytes((0xEA,)) * (
    CATEGORY_REGION_SIZE - len(_CATEGORY_CODE)
)

# Production replaces NOV2's complete fixed 51-record text region with this
# entropy stream. Records 3-7 are the shared disk-change card, so keep their
# user-facing wording complete here even though the pre-entropy staging records
# in ui.py remain size-locked as ``Part2``/``SideA``. The entropy block has
# enough recovered slack to render the proper ``Part 2`` and ``Side A`` on
# every current and future card that uses the shared NOV2 prompt records.
_INTERNAL_TABLE_STREAM = bytes.fromhex(
    "9cafbf3f79a3e5f4fcfcff1c379261b31c91febee0641c9429f76048f6bedbee"
    "4bfcd6f6be3c8ff594db703c4e5453ee9fe3ce7e9f732979cfd3ee654f81225ab"
    "bc0d7c0912d5de640f81801e63f69f70c4d13eef2f47f57bb4bbbca14fbb9da6"
    "9252f23e253d791febebccf7d6d0f23efd3ee3ca93f53bbbbbbbbbbbbbdb99ad2"
    "8e677a24f752b28f28d8f808f3a93d084aca3d7f547002f20ecc4e547b7b5875"
    "8f81576bca0b2c1295221d64fbe41fab872d5d9f758c9754be66f2ddd60866b5"
    "1f5ba3e67219d48f4b99ba3e67219d6fcce41d1f3390ce963334aca275f20fd5"
    "c396aecfbcd52436de1cb5767df00329d3cfedf94d3ef35490db79514fbb35e3e"
    "00653a79f313d4769e1cb575fb92dfdaa75f66d2caf8a119abb84f5fbdfbf725b"
    "fb9ba564dcd2a069cce827659aec9828466ce0"
)
_INTERNAL_TABLE_BLOCK = _INTERNAL_TABLE_STREAM + bytes(
    338 - len(_INTERNAL_TABLE_STREAM)
)
if len(_INTERNAL_TABLE_STREAM) != 309 or len(_INTERNAL_TABLE_BLOCK) != 338:
    raise EntropyRuntimeError("internal entropy table size changed")


@dataclass(frozen=True)
class HashGuardedPatch:
    """One fixed-size replacement guarded by the source region SHA-256."""

    cpu_address: int
    size: int
    expected_sha256: str
    replacement: bytes
    label: str

    def __post_init__(self) -> None:
        """Validate patch bounds, size neutrality, and digest shape."""
        if self.cpu_address < NOV2_LOAD_ADDRESS:
            raise EntropyRuntimeError(f"{self.label}: address precedes NOV2")
        if self.size != len(self.replacement):
            raise EntropyRuntimeError(
                f"{self.label}: replacement changed size"
            )
        if len(self.expected_sha256) != 64:
            raise EntropyRuntimeError(f"{self.label}: malformed source digest")

    @property
    def file_offset(self) -> int:
        """Return the NOV2-relative byte offset of the patch."""
        return self.cpu_address - NOV2_LOAD_ADDRESS

    def apply(self, data: bytearray) -> None:
        """Apply the guarded patch idempotently to a mutable NOV2 image."""
        end = self.file_offset + self.size
        if end > len(data):
            raise EntropyRuntimeError(f"{self.label}: NOV2 is too short")
        current = bytes(data[self.file_offset : end])
        if current == self.replacement:
            return
        digest = hashlib.sha256(current).hexdigest().upper()
        if digest != self.expected_sha256.upper():
            raise EntropyRuntimeError(
                f"{self.label}: source drift at ${self.cpu_address:04X}; "
                f"got {digest}"
            )
        data[self.file_offset : end] = self.replacement


ENTROPY_RUNTIME_PATCHES = (
    HashGuardedPatch(
        0x80A9,
        6,
        "570EB4E863C98E4193AA42179F18A26560343998EDE1E766BA71DBD01BAA7A8D",
        _POINTER_BRANCH,
        "entropy stream pointer initialization",
    ),
    HashGuardedPatch(
        0x80B1,
        SCANNER_REGION_SIZE,
        "541427E7B3BE828955CD537B923AA496C76364E3C1770CE5ED9E041BD894E068",
        _SCANNER_BLOCK,
        "bit-contiguous entropy scanner",
    ),
    HashGuardedPatch(
        0x8154,
        10,
        "FC27C8BA692687F01284D4838644C3B44FB99E152DFEB7762FC2F4EED8A996FA",
        _TOP_LEVEL_CODE,
        "entropy top-level renderer initialization",
    ),
    HashGuardedPatch(
        0x815E,
        FRONTEND_REGION_SIZE,
        "D02A0217AE5E3D0E0249CAF254E4DB769019F9A840D5B775D81ACFEC86FAA048",
        _FRONTEND_BLOCK,
        "entropy semantic dispatch frontend",
    ),
    HashGuardedPatch(
        0x81E0,
        CATEGORY_REGION_SIZE,
        "5746E2B506C1B093D2045674B9A95EAAEB93822BC6DD3973AD42F1384F56CCBF",
        _CATEGORY_BLOCK,
        "entropy prefix-category decoder",
    ),
    HashGuardedPatch(
        0x82E8,
        3,
        "23EB54D2FFD037A03D23E3A88782895B6F79A35B54C43D22611F1F185E8CAF8D",
        _DICTIONARY_REJOIN,
        "nested dictionary entropy rejoin",
    ),
    HashGuardedPatch(
        0x85D9,
        338,
        "FC47107EE720B1AAD5F67A059FE5F8E94941033AFA69E58D7CE3A4CD7000014B",
        _INTERNAL_TABLE_BLOCK,
        "NOV2 fixed 51-record entropy table",
    ),
    HashGuardedPatch(
        0x9402,
        4,
        "CC2A96A8812992B0D78C1A9E5002A11C6C7D5D1E081760CF699352CF77980852",
        _MENU_BRANCH,
        "menu entropy page initialization",
    ),
    HashGuardedPatch(
        0x946B,
        5,
        "002AAB0B912D72966AEF53951C21D4652EA570282197847178F097CB3E4F353E",
        _MENU_WIDTH_CAPTURE_CALL,
        "capture decoded menu width in Work RAM",
    ),
    HashGuardedPatch(
        0x989F,
        7,
        "795716EA363F392E7057E46EE5DFE8D2001269B21826E48372059E3D095499AD",
        _DYNAMIC_SELECTION_SPAN_CALL,
        "dynamic menu trailing cursor span",
    ),
)

# The native dictionary expander already saves the text pointer triplet on the
# CPU stack, so these two depth-counter patches are the only prerequisites for
# nested backward entropy references.
ENTROPY_PREREQUISITE_PATCHES = (
    RuntimePatch(
        file_offset=0x22C5,
        expected=bytes.fromhex("A9 FF 85 71"),
        replacement=bytes.fromhex("E6 71 EA EA"),
        label="entropy nested dictionary depth increment",
    ),
    RuntimePatch(
        file_offset=0x2311,
        expected=bytes.fromhex("A9 00 85 71"),
        replacement=bytes.fromhex("C6 71 EA EA"),
        label="entropy nested dictionary depth decrement",
    ),
)


def _guard_entropy_prerequisites(data: bytes) -> None:
    """Validate entropy prerequisites."""
    for patch in ENTROPY_PREREQUISITE_PATCHES:
        end = patch.file_offset + len(patch.replacement)
        if data[patch.file_offset : end] != patch.replacement:
            raise EntropyRuntimeError(
                f"{patch.label}: direct entropy prerequisite is absent at "
                f"${patch.cpu_address:04X}"
            )


def patch_entropy_nov2(data: bytes) -> bytes:
    """Install the complete frozen entropy runtime on a UI-patched NOV2.

    The operation is size-neutral, source-verified, and idempotent. The caller
    applies :func:`time_twist.ui.patched_nov2_ui`; this function then applies
    the proven renderer fixes, the two nested-dictionary prerequisites, and the
    entropy runtime itself. No alternate decoder or scan-limit mode exists.
    """
    if len(data) != NOV2_SIZE:
        raise EntropyRuntimeError(
            f"NOV2 must be {NOV2_SIZE} bytes, got {len(data)}"
        )
    result = bytearray(data)
    for resume_patch in LEADING_CONTROL_RESUME_PATCHES:
        resume_patch.apply(result)
    for base_patch in BASE_RUNTIME_PATCHES:
        base_patch.apply(result)
    for menu_patch in DYNAMIC_MENU_LAYOUT_PATCHES:
        menu_patch.apply(result)
    for prerequisite_patch in ENTROPY_PREREQUISITE_PATCHES:
        prerequisite_patch.apply(result)
    _guard_entropy_prerequisites(result)
    palette_before = bytes(
        result[
            PALETTE_CPU_RANGE.start
            - NOV2_LOAD_ADDRESS : PALETTE_CPU_RANGE.stop
            - NOV2_LOAD_ADDRESS
        ]
    )
    for runtime_patch in ENTROPY_RUNTIME_PATCHES:
        runtime_patch.apply(result)
    for parent_patch in PARENT_BACK_GUARD_PATCHES:
        parent_patch.apply(result)
    _guard_entropy_prerequisites(result)
    palette_after = bytes(
        result[
            PALETTE_CPU_RANGE.start
            - NOV2_LOAD_ADDRESS : PALETTE_CPU_RANGE.stop
            - NOV2_LOAD_ADDRESS
        ]
    )
    if palette_after != palette_before:
        raise EntropyRuntimeError("entropy runtime touched live palette data")
    return bytes(result)
