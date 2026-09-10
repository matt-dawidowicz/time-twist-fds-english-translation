"""NOV2 runtime patch for the frozen production entropy grammar.

Entropy mode installs directly on top of the proven NOV2 UI/runtime fixes. It
retains only the two native dictionary-depth changes required by the entropy
semantic handlers; the discarded Adaptive255 scanner, escape decoder, and
high-RAM scan-limit staging are not installed first.

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
from .production_runtime import (
    ProductionRuntimeError,
    RuntimePatch,
    patch_nov2,
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


class EntropyRuntimeError(ProductionRuntimeError):
    """Report source drift or an invalid entropy runtime assembly."""


class _Assembler:
    """Minimal deterministic assembler for the small 6502 replacement blocks."""

    def __init__(self, origin: int) -> None:
        self.origin = origin
        self.data = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str, str | int]] = []

    @property
    def pc(self) -> int:
        return self.origin + len(self.data)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise EntropyRuntimeError(f"duplicate assembler label {name}")
        self.labels[name] = self.pc

    def emit(self, *values: int) -> None:
        if any(not 0 <= value <= 0xFF for value in values):
            raise EntropyRuntimeError("assembler byte is outside 0..255")
        self.data.extend(values)

    def absolute(self, opcode: int, target: str | int) -> None:
        self.emit(opcode, 0, 0)
        self.fixups.append((len(self.data) - 2, "absolute", target))

    def relative(self, opcode: int, target: str | int) -> None:
        self.emit(opcode, 0)
        self.fixups.append((len(self.data) - 1, "relative", target))

    def finish(self) -> bytes:
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
    return bytes(int(value) for value in nodes)


ENTROPY_TREE = _entropy_tree()


def _build_scanner() -> tuple[bytes, int, int, int, int]:
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
_DICTIONARY_REJOIN = bytes.fromhex("4C 5E 81")

_SCANNER_BLOCK = _SCANNER_CODE + bytes((0xEA,)) * (
    SCANNER_REGION_SIZE - len(_SCANNER_CODE)
)
_FRONTEND_BLOCK = _FRONTEND_CODE + bytes((0xEA,)) * (
    FRONTEND_REGION_SIZE - len(_FRONTEND_CODE)
)
_CATEGORY_BLOCK = _CATEGORY_CODE + bytes((0xEA,)) * (
    CATEGORY_REGION_SIZE - len(_CATEGORY_CODE)
)

_INTERNAL_TABLE_STREAM = bytes.fromhex(
    "9cafbf3f79a3e5f4fcfcff1c379261b31c91febee0641c9429f76048f6bedbee"
    "4bfcd6f6be3c8ff594db703c4e5453ee9fe3ce7e9f732979cfd3eca9f0244b57"
    "435f0244b5779903e0600798fda7dc31344fbbcbd1fd5eed2eef2853eee769a4"
    "94bc8f894f5e47fafaf33df5b43c8fbf4fb8f2a4fd4eeeeeeeeeeeeef6e66b4a"
    "399de893dd4aca3ca363e023cea4f4212b28f5fd51c00bc83b313951eded61d6"
    "3e055daf282cb04a54887593ef907eae1cb5767dd6325d52f99bcb7758219ad4"
    "7d6e8f99c867523d2e66e8f99c8675bf3390747cce433a58ccd2b289d7c83f5"
    "70e5abb3ef35490db7872d5d9f7c00ca74f3fb7e534fbcd52436de5453eecd78"
    "f80194e9e7cc4f51da7872d5d7ee4b7f6a9d7d9b4b2be28466aee13d7ef7efd"
    "c96fee6e9593734a81a733a09d966bb260a119b380"
)
_INTERNAL_TABLE_BLOCK = _INTERNAL_TABLE_STREAM + bytes(
    338 - len(_INTERNAL_TABLE_STREAM)
)
if len(_INTERNAL_TABLE_STREAM) != 308 or len(_INTERNAL_TABLE_BLOCK) != 338:
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
)

# These are the only Adaptive255-era semantics retained by entropy: the native
# dictionary expander already saves the text pointer triplet on the CPU stack,
# so a depth counter allows nested backward references to unwind correctly.
# Everything else in the Adaptive255 runtime is superseded by entropy code.
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
    the proven non-Adaptive production runtime fixes, the two nested-dictionary
    prerequisites, and the entropy runtime itself. No Adaptive255 scanner,
    escape decoder, or $E000 scan-limit staging is installed.
    """
    if len(data) != NOV2_SIZE:
        raise EntropyRuntimeError(
            f"NOV2 must be {NOV2_SIZE} bytes, got {len(data)}"
        )
    result = bytearray(patch_nov2(data))
    for patch in ENTROPY_PREREQUISITE_PATCHES:
        patch.apply(result)
    _guard_entropy_prerequisites(result)
    palette_before = bytes(
        result[
            PALETTE_CPU_RANGE.start
            - NOV2_LOAD_ADDRESS : PALETTE_CPU_RANGE.stop
            - NOV2_LOAD_ADDRESS
        ]
    )
    for patch in ENTROPY_RUNTIME_PATCHES:
        patch.apply(result)
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
