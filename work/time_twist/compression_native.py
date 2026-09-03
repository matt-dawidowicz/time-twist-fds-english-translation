"""Optional verified bridge to the native editorial compression optimizer.

The canonical packed-text codec and reference compressor remain Python.  This
module only delegates the expensive deterministic search to the Rust helper,
then independently validates the returned dictionary, expanded symbol streams,
and exact packed byte count before the result can be used by higher layers.

Normal package installation does not require Rust or a native executable.  The
helper is discovered only when a caller explicitly requests the native backend.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .compression import expand_dictionary_symbols, packed_size
from .textcodec import EXTENDED_DICTIONARY_ENTRY_COUNT, PackedSymbol, SymbolKind

PROTOCOL = "TIME_TWIST_COMPRESSION_V1"
RESULT_PROTOCOL = "TIME_TWIST_COMPRESSION_RESULT_V1"
NATIVE_OPTIMIZER_ENV = "TIME_TWIST_NATIVE_OPTIMIZER"
NATIVE_OPTIMIZER_NAME = "time-twist-compression-optimizer"
DEFAULT_NATIVE_TIMEOUT_SECONDS = 300

ScenarioGroups = tuple[tuple[tuple[PackedSymbol, ...], ...], ...]
ScenarioDictionary = tuple[tuple[PackedSymbol, ...], ...]
CompressionResult = tuple[ScenarioGroups, ScenarioDictionary]


class NativeCompressionError(ValueError):
    """Report unavailable, malformed, or semantically invalid native output."""


def _symbol_identity(symbol: PackedSymbol) -> tuple[SymbolKind, int]:
    """Return the semantic portion of one symbol, excluding source offsets."""
    return symbol.kind, symbol.value


def _record_identity(
    record: tuple[PackedSymbol, ...],
) -> tuple[tuple[SymbolKind, int], ...]:
    """Return one record's semantic symbol identity."""
    return tuple(_symbol_identity(symbol) for symbol in record)


def _protocol_token(symbol: PackedSymbol) -> int:
    """Encode one Python symbol as a collision-free 16-bit protocol token."""
    if symbol.kind is SymbolKind.COMMON:
        kind = 0
    elif symbol.kind is SymbolKind.EXTENDED:
        kind = 1
    elif symbol.kind is SymbolKind.DICTIONARY:
        kind = 2
    elif symbol.kind is SymbolKind.CONTROL:
        kind = 3
    else:
        raise NativeCompressionError(
            f"unsupported native optimizer symbol kind {symbol.kind}"
        )
    if not 0 <= symbol.value <= 0xFF:
        raise NativeCompressionError(
            f"native optimizer symbol value {symbol.value} is out of range"
        )
    return (kind << 8) | symbol.value


def _python_symbol(token: int) -> PackedSymbol:
    """Decode one collision-free native protocol token into a Python symbol."""
    kind_code, value = divmod(token, 0x100)
    kinds = {
        0: SymbolKind.COMMON,
        1: SymbolKind.EXTENDED,
        2: SymbolKind.DICTIONARY,
        3: SymbolKind.CONTROL,
    }
    try:
        kind = kinds[kind_code]
    except KeyError as error:
        raise NativeCompressionError(
            f"native optimizer returned unsupported token 0x{token:04X}"
        ) from error
    if kind is SymbolKind.COMMON and not 0 <= value <= 47:
        raise NativeCompressionError("native optimizer returned invalid common glyph")
    if kind is SymbolKind.EXTENDED and not 0 <= value <= 63:
        raise NativeCompressionError("native optimizer returned invalid extended glyph")
    if kind is SymbolKind.DICTIONARY and not 1 <= value <= 68:
        raise NativeCompressionError(
            "native optimizer returned invalid dictionary reference"
        )
    if kind is SymbolKind.CONTROL and (not 0 <= value <= 7 or value == 5):
        raise NativeCompressionError("native optimizer returned invalid control")
    return PackedSymbol(kind, value, 0, 0)


def _format_record(record: tuple[PackedSymbol, ...]) -> str:
    """Serialize one record for the native stdin protocol."""
    if not record:
        return "-"
    return " ".join(f"{_protocol_token(symbol):04X}" for symbol in record)


def _parse_record(text: str) -> tuple[PackedSymbol, ...]:
    """Parse one native protocol record."""
    value = text.strip()
    if not value or value == "-":
        return ()
    symbols: list[PackedSymbol] = []
    for item in value.split():
        try:
            token = int(item, 16)
        except ValueError as error:
            raise NativeCompressionError(
                f"native optimizer returned invalid token {item!r}"
            ) from error
        if not 0 <= token <= 0xFFFF:
            raise NativeCompressionError(
                f"native optimizer token {item!r} exceeds 16 bits"
            )
        symbols.append(_python_symbol(token))
    return tuple(symbols)


def _serialize_problem(
    groups: ScenarioGroups,
    required_entries: ScenarioDictionary,
    *,
    max_bytes: int | None,
    maximum_entries: int,
    requires_full_dictionary: bool,
) -> str:
    """Serialize one complete optimization problem for a single process call."""
    lines = [
        PROTOCOL,
        f"MAX_ENTRIES {maximum_entries}",
        f"MAX_BYTES {max_bytes if max_bytes is not None else 'NONE'}",
        f"REQUIRES_FULL {int(requires_full_dictionary)}",
        f"REQUIRED {len(required_entries)}",
    ]
    lines.extend(f"ENTRY {_format_record(entry)}" for entry in required_entries)
    lines.append(f"GROUPS {len(groups)}")
    for group in groups:
        lines.append(f"GROUP {len(group)}")
        lines.extend(f"RECORD {_format_record(record)}" for record in group)
    lines.append("END")
    return "\n".join(lines) + "\n"


class _ResultLines:
    """Small strict reader for the native stdout protocol."""

    def __init__(self, text: str) -> None:
        self._lines = iter(text.splitlines())

    def next(self) -> str:
        """Return the next line or reject truncated output."""
        try:
            return next(self._lines)
        except StopIteration as error:
            raise NativeCompressionError(
                "native optimizer output ended unexpectedly"
            ) from error

    def value(self, prefix: str) -> str:
        """Return one required prefixed line's trailing value."""
        line = self.next()
        if not line.startswith(prefix):
            raise NativeCompressionError(
                f"native optimizer expected {prefix!r}, got {line!r}"
            )
        return line[len(prefix) :].strip()

    def require_end(self) -> None:
        """Require the exact END marker and no trailing nonblank lines."""
        if self.next().strip() != "END":
            raise NativeCompressionError("native optimizer output lacks END marker")
        if any(line.strip() for line in self._lines):
            raise NativeCompressionError("native optimizer output has trailing data")


def _parse_count(value: str, label: str) -> int:
    """Parse one nonnegative integer protocol field."""
    try:
        result = int(value)
    except ValueError as error:
        raise NativeCompressionError(
            f"native optimizer returned invalid {label}: {value!r}"
        ) from error
    if result < 0:
        raise NativeCompressionError(
            f"native optimizer returned negative {label}: {result}"
        )
    return result


def _parse_result(text: str) -> tuple[CompressionResult, int]:
    """Parse native stdout and return the candidate plus claimed packed size."""
    lines = _ResultLines(text)
    if lines.next().strip() != RESULT_PROTOCOL:
        raise NativeCompressionError("unsupported native optimizer result protocol")
    claimed_size = _parse_count(lines.value("PACKED_SIZE"), "PACKED_SIZE")
    dictionary_count = _parse_count(lines.value("DICTIONARY"), "DICTIONARY")
    dictionary = tuple(
        _parse_record(lines.value("ENTRY")) for _ in range(dictionary_count)
    )
    group_count = _parse_count(lines.value("GROUPS"), "GROUPS")
    groups: list[tuple[tuple[PackedSymbol, ...], ...]] = []
    for _ in range(group_count):
        record_count = _parse_count(lines.value("GROUP"), "GROUP")
        groups.append(
            tuple(_parse_record(lines.value("RECORD")) for _ in range(record_count))
        )
    lines.require_end()
    return (tuple(groups), dictionary), claimed_size


def native_optimizer_path() -> Path | None:
    """Return the explicitly built native optimizer path when available."""
    override = os.environ.get(NATIVE_OPTIMIZER_ENV)
    if override:
        path = Path(override).expanduser().resolve()
        return path if path.is_file() else None

    executable = NATIVE_OPTIMIZER_NAME + (".exe" if os.name == "nt" else "")
    project_root = Path(__file__).resolve().parents[2]
    checkout_candidate = (
        project_root
        / "native"
        / "compression_optimizer"
        / "target"
        / "release"
        / executable
    )
    if checkout_candidate.is_file():
        return checkout_candidate
    located = shutil.which(NATIVE_OPTIMIZER_NAME)
    return Path(located).resolve() if located else None


def native_optimizer_available() -> bool:
    """Return whether an explicitly built native optimizer can be executed."""
    return native_optimizer_path() is not None


def _validate_native_result(
    original_groups: ScenarioGroups,
    required_entries: ScenarioDictionary,
    result: CompressionResult,
    *,
    claimed_size: int,
    max_bytes: int | None,
    maximum_entries: int,
    requires_full_dictionary: bool,
) -> CompressionResult:
    """Independently prove native output preserves the canonical Python corpus."""
    groups, dictionary = result
    if len(groups) != len(original_groups):
        raise NativeCompressionError("native optimizer changed group count")
    if len(dictionary) > maximum_entries:
        raise NativeCompressionError("native optimizer exceeded dictionary limit")
    if requires_full_dictionary and len(dictionary) != maximum_entries:
        raise NativeCompressionError(
            "native optimizer did not satisfy full-dictionary requirement"
        )
    if len(dictionary) < len(required_entries):
        raise NativeCompressionError("native optimizer dropped required entries")
    for expected, actual in zip(required_entries, dictionary, strict=False):
        if _record_identity(expected) != _record_identity(actual):
            raise NativeCompressionError(
                "native optimizer changed the required dictionary prefix"
            )
    if len({_record_identity(entry) for entry in dictionary}) != len(dictionary):
        raise NativeCompressionError("native optimizer returned duplicate entries")
    if any(
        not entry
        or any(
            symbol.kind not in (SymbolKind.COMMON, SymbolKind.EXTENDED)
            for symbol in entry
        )
        for entry in dictionary
    ):
        raise NativeCompressionError(
            "native optimizer returned a non-flat dictionary entry"
        )

    for original_group, compressed_group in zip(
        original_groups, groups, strict=True
    ):
        if len(original_group) != len(compressed_group):
            raise NativeCompressionError("native optimizer changed record count")
        for original, compressed in zip(
            original_group, compressed_group, strict=True
        ):
            try:
                expanded = expand_dictionary_symbols(compressed, dictionary)
            except ValueError as error:
                raise NativeCompressionError(
                    f"native optimizer returned invalid dictionary references: {error}"
                ) from error
            if _record_identity(expanded) != _record_identity(original):
                raise NativeCompressionError(
                    "native optimizer changed the expanded symbol stream"
                )

    actual_size = packed_size(groups, dictionary)
    if actual_size != claimed_size:
        raise NativeCompressionError(
            "native optimizer packed-size claim differs from canonical Python packing"
        )
    if max_bytes is not None and actual_size > max_bytes:
        raise NativeCompressionError(
            f"native optimizer exceeded byte limit by {actual_size - max_bytes} bytes"
        )
    return groups, dictionary


def compress_english_groups_native(
    groups: ScenarioGroups,
    *,
    required_entries: ScenarioDictionary = (),
    max_bytes: int | None = None,
    maximum_entries: int = EXTENDED_DICTIONARY_ENTRY_COUNT,
    timeout_seconds: int = DEFAULT_NATIVE_TIMEOUT_SECONDS,
) -> CompressionResult:
    """Run and independently verify one native deterministic deep optimization.

    Args:
        groups: Uncompressed canonical Python scenario groups.
        required_entries: Fixed dictionary prefix, possibly carrying the
            ``requires_full_dictionary`` marker used by the reference compressor.
        max_bytes: Maximum packed groups-plus-dictionary footprint.
        maximum_entries: Maximum dictionary references supported by the decoder.
        timeout_seconds: Hard process timeout for one complete bank search.

    Returns:
        Verified compressed groups and flat dictionary.

    Raises:
        NativeCompressionError: If the executable is unavailable, fails,
            times out, emits malformed output, or returns a result that Python
            cannot independently prove equivalent to the input corpus.
    """
    if timeout_seconds < 1:
        raise NativeCompressionError("native optimizer timeout must be positive")
    if max_bytes is not None and max_bytes < 0:
        raise NativeCompressionError("max_bytes must be nonnegative")
    if not 1 <= maximum_entries <= EXTENDED_DICTIONARY_ENTRY_COUNT:
        raise NativeCompressionError("maximum dictionary entries is out of range")
    executable = native_optimizer_path()
    if executable is None:
        raise NativeCompressionError(
            "native compression optimizer is not built or discoverable"
        )
    requires_full_dictionary = bool(
        getattr(required_entries, "requires_full_dictionary", False)
    )
    request = _serialize_problem(
        groups,
        required_entries,
        max_bytes=max_bytes,
        maximum_entries=maximum_entries,
        requires_full_dictionary=requires_full_dictionary,
    )
    try:
        completed = subprocess.run(
            [str(executable)],
            input=request,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise NativeCompressionError(
            f"native compression optimizer could not run: {error}"
        ) from error
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise NativeCompressionError(
            f"native compression optimizer failed ({completed.returncode}): {detail}"
        )
    parsed, claimed_size = _parse_result(completed.stdout)
    return _validate_native_result(
        groups,
        required_entries,
        parsed,
        claimed_size=claimed_size,
        max_bytes=max_bytes,
        maximum_entries=maximum_entries,
        requires_full_dictionary=requires_full_dictionary,
    )
